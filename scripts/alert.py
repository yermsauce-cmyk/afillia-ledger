#!/usr/bin/env python3
"""
Alert on policy changes / keyword hits.

Free channels:
  - macOS desktop notification (osascript)
  - Email via SMTP (Gmail App Password — free)
  - Generic webhook (Slack/Discord free tier)

Usage:
    python alert.py --text "..." --level high
    cat logs/summaries/summary_*.md | python alert.py --stdin --level medium
"""

from __future__ import annotations

import argparse
import os
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CONFIG  # noqa: E402


def desktop_notify(title: str, body: str) -> bool:
    if not CONFIG.get("alerting", {}).get("desktop", {}).get("enabled", False):
        return False
    script = f'display notification "{body}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=10)
        return True
    except Exception as e:
        print(f"desktop notify failed: {e}", file=sys.stderr)
        return False


def email_send(subject: str, body: str) -> bool:
    cfg = CONFIG.get("alerting", {}).get("email", {})
    if not cfg.get("enabled"):
        return False
    sender = cfg.get("from")
    recipients = cfg.get("to") or []
    if not sender or not recipients:
        print("email not configured (missing from/to)", file=sys.stderr)
        return False
    pw = os.environ.get(cfg.get("app_password_env", "AFILLIA_SMTP_APP_PASSWORD"), "")
    if not pw:
        print("email app password env var not set", file=sys.stderr)
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as s:
            s.starttls()
            s.login(sender, pw)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"email send failed: {e}", file=sys.stderr)
        return False


def webhook_send(body: str) -> bool:
    cfg = CONFIG.get("alerting", {}).get("webhook", {})
    if not cfg.get("enabled") or not cfg.get("url"):
        return False
    try:
        requests.post(cfg["url"], json={"text": body}, timeout=15)
        return True
    except Exception as e:
        print(f"webhook failed: {e}", file=sys.stderr)
        return False


def classify(text: str) -> str:
    rules = CONFIG.get("alerts", {}).get("risk_levels", {})
    text_l = text.lower()
    for term in rules.get("high", []):
        if term.lower() in text_l:
            return "high"
    for term in rules.get("medium", []):
        if term.lower() in text_l:
            return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(description="Send alerts")
    parser.add_argument("--text", help="Alert body text")
    parser.add_argument("--stdin", action="store_true", help="Read body from stdin")
    parser.add_argument("--level", choices=["low", "medium", "high"], default=None)
    parser.add_argument("--subject", default="Afillia Ledger Alert")
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read().strip()
    elif args.text:
        text = args.text
    else:
        parser.error("provide --text or --stdin")

    level = args.level or classify(text)
    subject = f"[{level.upper()}] {args.subject}"

    sent = []
    if desktop_notify(subject, text[:200]):
        sent.append("desktop")
    if email_send(subject, text):
        sent.append("email")
    if webhook_send(f"{subject}\n\n{text}"):
        sent.append("webhook")

    print(json_dumps := f'{{"level": "{level}", "channels": {sent}}}')
    return 0 if sent or level == "low" else 1


if __name__ == "__main__":
    sys.exit(main())
