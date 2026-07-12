#!/usr/bin/env python3
"""
Pre-post compliance checkpoint for Afillia TikTok content.

Uses rules from config.yaml so updates don't require code changes.

Usage:
    python compliance_check.py --caption "..." --hashtags "#Afilla #SyntheticSeduction"
    python compliance_check.py --file post.txt
    echo "caption" | python compliance_check.py --stdin

Exit codes:
    0 = approved
    1 = blocked (high risk)
    2 = needs review (medium risk)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG, project_path  # noqa: E402

LOG_FILE = project_path("logs", "compliance_checks.log")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(payload: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": _now(), **payload}
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def check(caption: str, hashtags: list[str]) -> dict:
    rules = CONFIG.get("compliance", {})
    text = (caption + " " + " ".join(hashtags)).lower()

    required = [h.lower() for h in rules.get("required_hashtags", [])]
    missing_required = [h for h in required if h not in text]

    banned_hits = [t for t in rules.get("banned_terms", []) if t.lower() in text]
    risky_hits = [t for t in rules.get("risky_terms", []) if t.lower() in text]

    too_long = len(caption) > rules.get("max_caption_length", 2200)

    if banned_hits or too_long:
        risk = "high"
        approved = False
    elif missing_required or risky_hits:
        risk = "medium"
        approved = True  # approved with review
    else:
        risk = "low"
        approved = True

    return {
        "caption": caption,
        "hashtags": hashtags,
        "missing_required_hashtags": missing_required,
        "banned_term_hits": banned_hits,
        "risky_term_hits": risky_hits,
        "too_long": too_long,
        "risk_level": risk,
        "ai_label_required": rules.get("require_ai_label", True),
        "approved": approved,
        "needs_review": risk == "medium",
    }


def _read_caption(args: argparse.Namespace) -> tuple[str, list[str]]:
    if args.stdin:
        caption = sys.stdin.read().strip()
        hashtags = re.findall(r"#\w+", caption)
        return caption, hashtags
    if args.file:
        caption = Path(args.file).read_text(encoding="utf-8").strip()
        hashtags = re.findall(r"#\w+", caption)
        if args.hashtags:
            hashtags += re.findall(r"#\w+", args.hashtags)
        return caption, list(dict.fromkeys(hashtags))
    hashtags = re.findall(r"#\w+", args.hashtags or "")
    return args.caption or "", hashtags


def main() -> int:
    parser = argparse.ArgumentParser(description="Afillia pre-post compliance check")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--caption", help="Post caption text")
    group.add_argument("--file", help="Read caption from file")
    group.add_argument("--stdin", action="store_true", help="Read caption from stdin")
    parser.add_argument("--hashtags", default="", help="Space-separated hashtags")
    parser.add_argument("--quiet", action="store_true", help="Suppress JSON output")
    args = parser.parse_args()

    caption, hashtags = _read_caption(args)
    result = check(caption, hashtags)
    _log(result)

    if not args.quiet:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result["approved"]:
        return 1
    if result["needs_review"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
