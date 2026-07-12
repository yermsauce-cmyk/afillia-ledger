"""
Performance tracking for @afillia TikTok account.

Stores post metrics in logs/performance.jsonl (one JSON per line per post).
Calculates progress toward 10k follower goal + Fanvue conversion.

Usage:
    python performance.py log --post-id "abc123" --views 5000 --saves 150 --shares 50 --new-followers 120
    python performance.py summary
    python performance.py goals
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import project_path  # noqa: E402

PERF_FILE = project_path("logs", "performance.jsonl")
GOALS_FILE = project_path("logs", "goals.json")

DEFAULT_GOALS = {
    "followers_target": 10000,
    "weekly_follower_growth_target": 200,
    "views_per_post_target": 5000,
    "save_rate_target": 0.03,      # 3% of views
    "share_rate_target": 0.01,    # 1% of views
    "fanvue_conversion_target": 0.02,  # 2% of TikTok followers
    "posts_per_week_target": 4,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_files() -> None:
    PERF_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PERF_FILE.exists():
        PERF_FILE.touch()
    if not GOALS_FILE.exists():
        GOALS_FILE.write_text(json.dumps(DEFAULT_GOALS, indent=2), encoding="utf-8")


def log_post(post_id: str, views: int, saves: int, shares: int,
             new_followers: int, pillar: str = "unknown", notes: str = "") -> dict:
    _ensure_files()
    entry = {
        "timestamp": _now(),
        "post_id": post_id,
        "pillar": pillar,
        "views": views,
        "saves": saves,
        "shares": shares,
        "new_followers": new_followers,
        "save_rate": round(saves / views, 4) if views else 0,
        "share_rate": round(shares / views, 4) if views else 0,
        "notes": notes,
    }
    with PERF_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_entries() -> list[dict]:
    _ensure_files()
    entries = []
    for line in PERF_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def load_goals() -> dict:
    _ensure_files()
    return json.loads(GOALS_FILE.read_text(encoding="utf-8"))


def set_goals(**kwargs) -> dict:
    _ensure_files()
    goals = load_goals()
    goals.update({k: v for k, v in kwargs.items() if v is not None})
    GOALS_FILE.write_text(json.dumps(goals, indent=2), encoding="utf-8")
    return goals


def summary() -> dict:
    entries = load_entries()
    goals = load_goals()
    if not entries:
        return {"total_posts": 0, "goals": goals}

    total_views = sum(e["views"] for e in entries)
    total_saves = sum(e["saves"] for e in entries)
    total_shares = sum(e["shares"] for e in entries)
    total_new_followers = sum(e["new_followers"] for e in entries)

    # Group by week
    weeks: dict[str, dict] = {}
    for e in entries:
        week = e["timestamp"][:10]  # YYYY-MM-DD
        # ISO week
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            iso_week = dt.strftime("%Y-W%V")
        except Exception:
            iso_week = week
        if iso_week not in weeks:
            weeks[iso_week] = {"posts": 0, "views": 0, "followers": 0}
        weeks[iso_week]["posts"] += 1
        weeks[iso_week]["views"] += e["views"]
        weeks[iso_week]["followers"] += e["new_followers"]

    return {
        "total_posts": len(entries),
        "total_views": total_views,
        "total_saves": total_saves,
        "total_shares": total_shares,
        "total_new_followers": total_new_followers,
        "avg_save_rate": round(total_saves / total_views, 4) if total_views else 0,
        "avg_share_rate": round(total_shares / total_views, 4) if total_views else 0,
        "weeks": weeks,
        "goals": goals,
    }


def goal_progress(current_followers: int = 0) -> dict:
    goals = load_goals()
    target = goals["followers_target"]
    progress_pct = round(current_followers / target * 100, 2) if target else 0
    remaining = max(target - current_followers, 0)

    # Estimate weeks to goal based on avg weekly growth
    s = summary()
    weeks_data = s.get("weeks", {})
    if weeks_data:
        avg_weekly = sum(w["followers"] for w in weeks_data.values()) / len(weeks_data)
        weeks_to_goal = round(remaining / avg_weekly, 1) if avg_weekly > 0 else None
    else:
        weeks_to_goal = None

    return {
        "current_followers": current_followers,
        "target": target,
        "remaining": remaining,
        "progress_pct": progress_pct,
        "avg_weekly_growth": avg_weekly if weeks_data else 0,
        "weeks_to_goal": weeks_to_goal,
        "fanvue_subs_target": round(current_followers * goals["fanvue_conversion_target"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Track @afillia performance")
    sub = parser.add_subparsers(dest="cmd", required=True)

    log_p = sub.add_parser("log", help="Log a post's metrics")
    log_p.add_argument("--post-id", required=True)
    log_p.add_argument("--views", type=int, required=True)
    log_p.add_argument("--saves", type=int, required=True)
    log_p.add_argument("--shares", type=int, required=True)
    log_p.add_argument("--new-followers", type=int, required=True)
    log_p.add_argument("--pillar", default="unknown",
                       choices=["dance", "fitness", "lifestyle", "fan_cta", "unknown"])
    log_p.add_argument("--notes", default="")

    sub.add_parser("summary", help="Show aggregate stats")
    sub.add_parser("goals", help="Show goal progress")

    goals_p = sub.add_parser("set-goal", help="Update a goal")
    goals_p.add_argument("--followers-target", type=int)
    goals_p.add_argument("--weekly-follower-growth-target", type=int)
    goals_p.add_argument("--views-per-post-target", type=int)
    goals_p.add_argument("--save-rate-target", type=float)
    goals_p.add_argument("--share-rate-target", type=float)
    goals_p.add_argument("--fanvue-conversion-target", type=float)
    goals_p.add_argument("--posts-per-week-target", type=int)

    args = parser.parse_args()

    if args.cmd == "log":
        entry = log_post(args.post_id, args.views, args.saves, args.shares,
                         args.new_followers, args.pillar, args.notes)
        print(json.dumps(entry, indent=2))
    elif args.cmd == "summary":
        print(json.dumps(summary(), indent=2))
    elif args.cmd == "goals":
        # Need current follower count — read from latest entry or env
        current = int(os.environ.get("AFILLIA_CURRENT_FOLLOWERS", "0"))
        print(json.dumps(goal_progress(current), indent=2))
    elif args.cmd == "set-goal":
        kwargs = {k.replace("-", "_"): v for k, v in vars(args).items()
                  if k not in ("cmd",) and v is not None}
        print(json.dumps(set_goals(**kwargs), indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
