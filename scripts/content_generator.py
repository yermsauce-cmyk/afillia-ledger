"""
Afillia content generator — uses local Ollama LLM with the persona prompt.

Generates captions, hashtag sets, and content ideas in-character as Afilla.
Supports AGENT MODE for structured JSON output.

Usage:
    python content_generator.py --pillar dance --trend "viral sound"
    python content_generator.py --pillar fan_cta --agent-mode
    echo "prompt" | python content_generator.py --stdin
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG, project_path  # noqa: E402
from compliance_check import check as compliance_check  # noqa: E402

PROMPT_FILE = project_path("prompts", "afillia_tiktok_prompt.md")
OUT_DIR = project_path("logs", "content_ideas")


PILLARS = {
    "dance": "Viral dance/trend adaptation (15-30s clip)",
    "fitness": "Fitness/glow-up transformation",
    "lifestyle": "Lifestyle teaser (Miami nights, workouts, food)",
    "fan_cta": "Fan-exclusive call-to-action (Fanvue teaser)",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_prompt(agent_mode: bool = False) -> str:
    base = PROMPT_FILE.read_text(encoding="utf-8")
    if agent_mode:
        base += "\n\nAGENT MODE: Output structured JSON with keys: caption, hashtags, pillar, hook, cta, compliance_notes."
    return base


def _build_user_request(pillar: str, trend: str, topic: str) -> str:
    parts = [f"Pillar: {pillar} — {PILLARS.get(pillar, pillar)}"]
    if trend:
        parts.append(f"Trend to adapt: {trend}")
    if topic:
        parts.append(f"Topic: {topic}")
    parts.append("Generate 3 caption variants + recommended hashtags + a hook line.")
    return "\n".join(parts)


def call_ollama(prompt: str) -> str:
    cfg = CONFIG.get("llm", {})
    base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
    model = cfg.get("model", "qwen3-coder:latest")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": cfg.get("temperature", 0.7)},
    }
    r = requests.post(
        f"{base}/api/generate",
        json=payload,
        timeout=cfg.get("timeout_seconds", 120),
    )
    r.raise_for_status()
    return r.json().get("response", "")


def extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#\w+", text)


def generate(pillar: str, trend: str, topic: str, agent_mode: bool) -> dict:
    system_prompt = _load_prompt(agent_mode)
    user_request = _build_user_request(pillar, trend, topic)
    full_prompt = f"{system_prompt}\n\n---\n\n{user_request}\n\nDate: {_now()}\nLocation: Miami, Florida"

    print(f"Generating via Ollama ({CONFIG.get('llm', {}).get('model')})...", file=sys.stderr)
    raw = call_ollama(full_prompt)

    # Extract hashtags from the response
    hashtags = extract_hashtags(raw)

    # Run compliance check on the first caption-like line
    first_caption = ""
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 20:
            first_caption = line
            break

    compliance = None
    if first_caption:
        compliance = compliance_check(first_caption, hashtags)

    # Save to disk
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"{pillar}_{stamp}.md"
    header = (
        f"# Content Idea — {pillar}\n\n"
        f"- Generated: {_now()}\n"
        f"- Trend: {trend or 'n/a'}\n"
        f"- Topic: {topic or 'n/a'}\n"
        f"- Agent Mode: {agent_mode}\n\n"
    )
    out_path.write_text(header + raw + "\n", encoding="utf-8")

    return {
        "pillar": pillar,
        "trend": trend,
        "topic": topic,
        "agent_mode": agent_mode,
        "raw_output": raw,
        "extracted_hashtags": hashtags,
        "first_caption_preview": first_caption,
        "compliance_check": compliance,
        "saved_to": str(out_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Afillia content via Ollama")
    parser.add_argument("--pillar", choices=list(PILLARS.keys()), default="lifestyle")
    parser.add_argument("--trend", default="", help="Trend to adapt (e.g. 'viral sound name')")
    parser.add_argument("--topic", default="", help="Specific topic (e.g. 'Miami sunset workout')")
    parser.add_argument("--agent-mode", action="store_true",
                        help="Switch to analytical JSON output mode")
    args = parser.parse_args()

    try:
        result = generate(args.pillar, args.trend, args.topic, args.agent_mode)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Ollama. Is it running? Try: ollama serve", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
