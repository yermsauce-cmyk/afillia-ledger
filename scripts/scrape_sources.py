#!/usr/bin/env python3
"""
Scrape TikTok policy sources + Reddit RSS + Google News RSS.

Free, no API keys required. Uses requests + BeautifulSoup.

Usage:
    python scrape_sources.py                # scrape everything in config.yaml
    python scrape_sources.py --only reddit # scrape just reddit
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG, project_path  # noqa: E402

UA = "AfilliaLedgerBot/1.0 (+https://github.com/local)"
TIMEOUT = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    netloc = urlparse(url).netloc.replace("www.", "")
    return f"{netloc}_{h}"


def fetch(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def scrape_html(url: str, label: str) -> str:
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return f"# {label}\n# source: {url}\n# fetched: {_now()}\n\n{text}\n"


def scrape_rss(url: str, label: str) -> str:
    xml = fetch(url)
    root = ET.fromstring(xml)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        # strip HTML from description
        desc = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)
        items.append(f"## {title}\n{link}\n{pub}\n\n{desc}\n")
    body = "\n---\n".join(items) if items else "(no items)"
    return f"# {label}\n# source: {url}\n# fetched: {_now()}\n\n{body}\n"


def write_output(name: str, content: str) -> Path:
    out_dir = project_path("logs", "raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"{stamp}_{name}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def run(only: str | None = None) -> list[Path]:
    sources = CONFIG.get("sources", {})
    written: list[Path] = []

    if only in (None, "guidelines"):
        for entry in sources.get("guidelines", []):
            try:
                content = scrape_html(entry["url"], entry["label"])
                written.append(write_output(_slug(entry["url"]), content))
                print(f"✓ scraped {entry['label']}")
            except Exception as e:
                print(f"✗ failed {entry['url']}: {e}", file=sys.stderr)

    if only in (None, "reddit"):
        for url in sources.get("reddit", []):
            try:
                content = scrape_rss(url, f"Reddit RSS: {url}")
                written.append(write_output(_slug(url), content))
                print(f"✓ scraped {url}")
            except Exception as e:
                print(f"✗ failed {url}: {e}", file=sys.stderr)

    if only in (None, "rss"):
        for url in sources.get("rss", []):
            try:
                content = scrape_rss(url, f"Google News: {url}")
                written.append(write_output(_slug(url), content))
                print(f"✓ scraped {url}")
            except Exception as e:
                print(f"✗ failed {url}: {e}", file=sys.stderr)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape TikTok policy sources")
    parser.add_argument("--only", choices=["guidelines", "reddit", "rss"])
    args = parser.parse_args()
    written = run(args.only)
    print(f"\nWrote {len(written)} file(s) to logs/raw/")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
