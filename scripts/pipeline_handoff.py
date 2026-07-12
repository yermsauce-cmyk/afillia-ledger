#!/usr/bin/env python3
"""
Pipeline Handoff — async, crash-resistant orchestrator for Afillia.ledger.

The original pipeline calls Ollama synchronously with a 60-300s timeout.
On this machine, qwen3-coder:latest (30.5B) takes longer than that for
even trivial prompts, so the Streamlit app crashes mid-request.

This module replaces the synchronous Ollama call with a **handoff pattern**:

    1. Submit the job to a local queue (JSON file on disk).
    2. A background worker picks it up and runs Ollama with a generous
       timeout + automatic retry + model fallback.
    3. The UI polls the queue for status and reads the result when ready.

The UI never blocks on Ollama. If Ollama is slow, missing, or crashes,
the UI keeps working and shows the job status.

Usage:
    from pipeline_handoff import submit_job, get_job, list_jobs

    job_id = submit_job("summarize", {"prompt": "..."})
    # ... later ...
    job = get_job(job_id)
    if job["status"] == "done":
        print(job["result"])
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG, project_path  # noqa: E402

# Queue lives on disk so it survives Streamlit reruns / crashes.
QUEUE_DIR = project_path("logs", "jobs")
QUEUE_DIR.mkdir(parents=True, exist_ok=True)

# Generous timeout — qwen3-coder 30B needs minutes, not seconds.
OLLAMA_TIMEOUT = 1800  # 30 minutes
RETRY_BACKOFF = [30, 60, 120, 300]  # seconds between retries

# Fallback chain — try smaller/faster models if the primary hangs.
FALLBACK_MODELS = [
    "qwen3-coder:latest",   # primary (30.5B)
    "qwen2.5-coder:7b",     # fallback if pulled
    "qwen2.5:7b",           # generic fallback
    "llama3.2:3b",          # tiny fallback
]


# ---------- Job lifecycle ----------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return QUEUE_DIR / f"{job_id}.json"


def submit_job(kind: str, payload: dict[str, Any]) -> str:
    """Create a job and return its ID. Does NOT run Ollama."""
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "kind": kind,            # "summarize" | "generate_content" | "ping"
        "payload": payload,
        "status": "queued",      # queued | running | done | failed
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "attempts": 0,
        "model_used": None,
    }
    _job_path(job_id).write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    p = _job_path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    jobs = []
    for p in sorted(QUEUE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            jobs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
        if len(jobs) >= limit:
            break
    return jobs


def _update_job(job_id: str, **fields: Any) -> dict[str, Any]:
    job = get_job(job_id) or {}
    job.update(fields)
    _job_path(job_id).write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


# ---------- Ollama call with resilience ----------

def _ollama_generate(prompt: str, model: str, temperature: float) -> str:
    cfg = CONFIG.get("llm", {})
    base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    r = requests.post(
        f"{base}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def _ollama_generate_resilient(prompt: str, temperature: float = 0.2) -> tuple[str, str]:
    """Try the configured model, then fall back through smaller models.

    Returns (response_text, model_used). Raises the last exception if all fail.
    """
    cfg = CONFIG.get("llm", {})
    primary = cfg.get("model", "qwen3-coder:latest")
    chain = [primary] + [m for m in FALLBACK_MODELS if m != primary]

    last_err: Exception | None = None
    for model in chain:
        for attempt, backoff in enumerate([0] + RETRY_BACKOFF):
            if backoff:
                time.sleep(backoff)
            try:
                text = _ollama_generate(prompt, model, temperature)
                if text.strip():
                    return text, model
            except requests.exceptions.ReadTimeout:
                last_err = TimeoutError(f"{model} timed out after {OLLAMA_TIMEOUT}s")
            except requests.exceptions.ConnectionError as e:
                last_err = e
                break  # no point retrying if Ollama is offline
            except Exception as e:
                last_err = e
        # move to next model in chain
    raise last_err or RuntimeError("All Ollama models failed")


# ---------- Job runners ----------

def _run_summarize(job: dict[str, Any]) -> None:
    from summarize import build_prompt, load_inputs, collect_inputs  # type: ignore
    payload = job["payload"]
    input_path = payload.get("input_path")
    inputs = collect_inputs(Path(input_path)) if input_path else collect_inputs(None)
    if not inputs:
        raise RuntimeError("No input files in logs/raw/. Run scrape_sources.py first.")
    sources_text = load_inputs(inputs)
    prompt = build_prompt(sources_text)
    text, model = _ollama_generate_resilient(prompt, temperature=0.2)

    out_dir = project_path("logs", "summaries")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"summary_{stamp}.md"
    header = (
        f"# Policy Summary\n\n"
        f"- Generated: {_now()}\n"
        f"- Inputs: {', '.join(p.name for p in inputs)}\n"
        f"- Model: {model}\n\n"
    )
    out_path.write_text(header + text + "\n", encoding="utf-8")
    _update_job(
        job["id"],
        result={"text": text, "saved_to": str(out_path), "model": model},
    )


def _run_generate_content(job: dict[str, Any]) -> None:
    from content_generator import _load_prompt, _build_user_request, extract_hashtags  # type: ignore
    from compliance_check import check as compliance_check  # type: ignore
    payload = job["payload"]
    pillar = payload["pillar"]
    trend = payload.get("trend", "")
    topic = payload.get("topic", "")
    agent_mode = payload.get("agent_mode", False)

    system_prompt = _load_prompt(agent_mode)
    user_request = _build_user_request(pillar, trend, topic)
    full_prompt = f"{system_prompt}\n\n---\n\n{user_request}\n\nDate: {_now()}\nLocation: Miami, Florida"
    text, model = _ollama_generate_resilient(full_prompt, temperature=0.7)

    hashtags = extract_hashtags(text)
    first_caption = ""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 20:
            first_caption = line
            break
    compliance = compliance_check(first_caption, hashtags) if first_caption else None

    out_dir = project_path("logs", "content_ideas")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{pillar}_{stamp}.md"
    header = (
        f"# Content Idea — {pillar}\n\n"
        f"- Generated: {_now()}\n"
        f"- Trend: {trend or 'n/a'}\n"
        f"- Topic: {topic or 'n/a'}\n"
        f"- Agent Mode: {agent_mode}\n"
        f"- Model: {model}\n\n"
    )
    out_path.write_text(header + text + "\n", encoding="utf-8")
    _update_job(
        job["id"],
        result={
            "pillar": pillar,
            "raw_output": text,
            "extracted_hashtags": hashtags,
            "first_caption_preview": first_caption,
            "compliance_check": compliance,
            "saved_to": str(out_path),
            "model": model,
        },
    )


def _run_ping(job: dict[str, Any]) -> None:
    """Quick health check — uses a tiny prompt with a short timeout."""
    text, model = _ollama_generate_resilient("Reply with the single word: pong", temperature=0.0)
    _update_job(job["id"], result={"text": text.strip(), "model": model})


RUNNERS = {
    "summarize": _run_summarize,
    "generate_content": _run_generate_content,
    "ping": _run_ping,
}


def run_job(job_id: str) -> None:
    """Execute a queued job. Updates status throughout. Safe to call repeatedly."""
    job = get_job(job_id)
    if not job:
        return
    if job["status"] in ("done", "running"):
        return

    _update_job(job_id, status="running", started_at=_now(), attempts=job["attempts"] + 1)
    runner = RUNNERS.get(job["kind"])
    if not runner:
        _update_job(job_id, status="failed", finished_at=_now(),
                    error=f"unknown job kind: {job['kind']}")
        return
    try:
        runner(job)
        _update_job(job_id, status="done", finished_at=_now())
    except Exception as e:
        _update_job(job_id, status="failed", finished_at=_now(), error=str(e))


def run_all_pending() -> int:
    """Run every queued job once. Returns count processed."""
    count = 0
    for job in list_jobs(limit=200):
        if job["status"] == "queued":
            run_job(job["id"])
            count += 1
    return count


# ---------- Worker (run as a background process) ----------

def worker_loop(poll_seconds: int = 5) -> None:
    """Long-running worker. Picks up queued jobs and runs them."""
    print(f"[worker] started, polling every {poll_seconds}s, queue={QUEUE_DIR}", flush=True)
    while True:
        try:
            n = run_all_pending()
            if n:
                print(f"[worker] processed {n} job(s)", flush=True)
        except KeyboardInterrupt:
            print("\n[worker] stopped.", flush=True)
            return
        except Exception as e:
            print(f"[worker] loop error: {e}", flush=True)
        time.sleep(poll_seconds)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Afillia pipeline handoff worker")
    parser.add_argument("--once", action="store_true", help="Run pending jobs once and exit")
    parser.add_argument("--poll", type=int, default=5, help="Poll interval (seconds)")
    parser.add_argument("--list", action="store_true", help="List recent jobs and exit")
    args = parser.parse_args()

    if args.list:
        for j in list_jobs():
            print(f"{j['status']:8s} {j['kind']:18s} {j['id']}  {j['created_at']}")
        return 0

    if args.once:
        n = run_all_pending()
        print(f"processed {n} job(s)")
        return 0

    worker_loop(args.poll)
    return 0


if __name__ == "__main__":
    sys.exit(main())
