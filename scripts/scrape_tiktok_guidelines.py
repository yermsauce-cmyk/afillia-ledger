#!/usr/bin/env python3
"""
Scrape TikTok Community Guidelines + Reddit/X chatter and dump raw text
for the policy summarizer prompt to consume.

Usage:
    python scrape_tiktok_guidelines.py --out ../logs/raw_scrape_<date>.txt

This is a stub — wire up requests/BeautifulSoup or an API client as needed.
"""

import argparse
from datetime import datetime
from pathlib import Path

SOURCES = [
    "https://www.tiktok.com/community-guidelines",
    "https://www.reddit.com/r/TikTok/",
    "https://www.reddit.com/r/TikTokHelp/",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape TikTok policy sources")
    parser.add_argument("--out", required=True, help="Output file path")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"# Raw scrape @ {datetime.utcnow().isoformat()}Z\n"
    body = "\n".join(f"## {url}\n[fetched: TODO]\n" for url in SOURCES)

    out_path.write_text(header + body + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
