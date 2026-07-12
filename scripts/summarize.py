#!/usr/bin/env python3
"""
Summarize scraped policy text using a free local LLM (Ollama).

Reads everything in logs/raw/, sends it to the configured model with the
policy_summarizer_prompt, and writes a digest to logs/summaries/.

Usage:
    python summarize.py
    python summarize.py --input logs/raw/<file>.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG, project_path  # noqa: E402

PROMPT_FILE = project_path("prompts", "policy_summarizer_prompt.md")
RAW_DIR = project_path("logs", "raw")
OUT_DIR = project_path("logs", "summaries")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_inputs(paths: list[Path]) -> str:
    chunks = []
    for p in paths:
        chunks.append(f"\n\n===== FILE: {p.name} =====\n{p.read_text(encoding='utf-8')}")
    return "".join(chunks)


def build_prompt(sources_text: str) -> str:
    base = PROMPT_FILE.read_text(encoding="utf-8")
    return (
        f"{base}\n\n"
        f"Sources:\n{sources_text}\n\n"
        f"Date: {_now()}\n\n"
        "Respond in valid Markdown with the four sections requested."
    )


def call_ollama(prompt: str) -> str:
    cfg = CONFIG.get("llm", {})
    base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
    model = cfg.get("model", "qwen3-coder:latest")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": cfg.get("temperature", 0.2)},
    }
    r = requests.post(
        f"{base}/api/generate",
        json=payload,
        timeout=cfg.get("timeout_seconds", 120),
    )
    r.raise_for_status()
    return r.json().get("response", "")


def collect_inputs(arg_path: Path | None) -> list[Path]:
    if arg_path:
        return [arg_path]
    if not RAW_DIR.exists():
        return []
    return sorted(RAW_DIR.glob("*.txt"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize scraped policy text")
    parser.add_argument("--input", type=Path, help="Single raw file to summarize")
    parser.add_argument(
        "--provider",
        choices=["ollama", "none"],
        default=None,
        help="Override LLM provider (default from config.yaml)",
    )
    args = parser.parse_args()

    inputs = collect_inputs(args.input)
    if not inputs:
        print("No input files found in logs/raw/. Run scrape_sources.py first.")
        return 1

    sources_text = load_inputs(inputs)
    prompt = build_prompt(sources_text)

    provider = args.provider or CONFIG.get("llm", {}).get("provider", "ollama")
    if provider == "none":
        print("LLM provider disabled. Prompt written to logs/summaries/_prompt.txt")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "_prompt.txt").write_text(prompt, encoding="utf-8")
        return 0

    print(f"Summarizing {len(inputs)} file(s) via {provider}...")
    summary = call_ollama(prompt)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"summary_{stamp}.md"
    header = (
        f"# Policy Summary\n\n"
        f"- Generated: {_now()}\n"
        f"- Inputs: {', '.join(p.name for p in inputs)}\n"
        f"- Model: {CONFIG.get('llm', {}).get('model')}\n\n"
    )
    out_path.write_text(header + summary + "\n", encoding="utf-8")
    print(f"✓ wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
