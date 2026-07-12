#!/usr/bin/env bash
# Launch the video compliance checker and open it in the default browser.
# Usage: ./run_app_video_check_open.sh

set -euo pipefail
cd "$(dirname "$0")"

URL="http://localhost:8504"

if pgrep -f "streamlit run video_check.py" > /dev/null; then
  echo "✅ Video compliance checker already running"
else
  echo "🌙 Starting Afillia Ledger Video Compliance Checker..."
  nohup python3 -m streamlit run video_check.py --server.port 8504 --server.headless true --browser.gatherUsageStats false > logs/video_check.log 2>&1 &
  echo "  started PID $!"
  sleep 3
fi

echo "🌐 Opening $URL"
open "$URL"
