#!/usr/bin/env python3
"""
Lightweight in-process scheduler — no cron required.

Runs the full pipeline (scrape → summarize → alert) on a daily schedule
using a simple sleep loop. Designed to be launched once and left running
(e.g. via `nohup`, `screen`, or `tmux`).

Usage:
    python scheduler.py                # run forever
    python scheduler.py --once         # run once and exit
    python scheduler.py --interval 60  # check every 60s (default 300s)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG  # noqa: E402

# Import the pipeline modules
import scrape_sources  # noqa: E402
import summarize  # noqa: E402
import alert  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _last_run_date() -> str | None:
    p = Path(__file__).resolve().parent.parent / "logs" / ".last_run"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return None


def _mark_run() -> None:
    p = Path(__file__).resolve().parent.parent / "logs"
    p.mkdir(parents=True, exist_ok=True)
    (p / ".last_run").write_text(datetime.now(timezone.utc).strftime("%Y-%m-%d"), encoding="utf-8")


def run_pipeline() -> None:
    print(f"\n=== Pipeline run @ {_now()} ===")
    try:
        scrape_sources.run()
    except Exception as e:
        print(f"scrape failed: {e}", file=sys.stderr)
        return

    try:
        summarize.main([])
    except SystemExit as e:
        if e.code != 0:
            print(f"summarize exited {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"summarize failed: {e}", file=sys.stderr)
        return

    # Alert on the latest summary if it contains alert keywords
    summaries_dir = Path(__file__).resolve().parent.parent / "logs" / "summaries"
    latest = max(summaries_dir.glob("summary_*.md"), default=None)
    if latest:
        text = latest.read_text(encoding="utf-8")
        alert.main(["--text", text, "--subject", f"Policy digest: {latest.name}"])

    _mark_run()


def should_run_today() -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _last_run_date() != today


def main() -> int:
    parser = argparse.ArgumentParser(description="Afillia pipeline scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=300, help="Check interval (seconds)")
    args = parser.parse_args()

    if args.once:
        run_pipeline()
        return 0

    print(f"Scheduler started. Interval: {args.interval}s. Ctrl-C to stop.")
    while True:
        try:
            if should_run_today():
                run_pipeline()
            else:
                print(f"[{_now()}] already ran today, sleeping...")
        except KeyboardInterrupt:
            print("\nstopped.")
            return 0
        except Exception as e:
            print(f"loop error: {e}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
