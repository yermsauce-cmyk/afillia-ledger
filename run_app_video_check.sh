#!/usr/bin/env bash
# Launch the Afillia.ledger video compliance checker.
# Usage: ./run_app_video_check.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "🌙 Starting Afillia Ledger Video Compliance Checker..."
echo "📍 Will open at: http://localhost:8504"
echo ""

python3 -m streamlit run video_check.py \
    --server.port 8504 \
    --server.address localhost \
    --server.headless true \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#ff006e" \
    --theme.backgroundColor "#0a0a0f" \
    --theme.secondaryBackgroundColor "#1a0a1f" \
    --theme.textColor "#ffffff"
