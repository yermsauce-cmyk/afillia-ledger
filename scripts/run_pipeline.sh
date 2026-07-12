#!/usr/bin/env bash
# One-command pipeline: scrape → summarize → alert
# Usage: ./scripts/run_pipeline.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ scrape_sources.py"
python3 scripts/scrape_sources.py

echo "▶ summarize.py"
python3 scripts/summarize.py

echo "▶ alert.py (latest summary)"
LATEST=$(ls -t logs/summaries/summary_*.md 2>/dev/null | head -1 || true)
if [[ -n "${LATEST}" ]]; then
  python3 scripts/alert.py --text "$(cat "${LATEST}")" --subject "Policy digest: $(basename "${LATEST}")"
else
  echo "no summary to alert on"
fi

echo "✓ pipeline complete"
