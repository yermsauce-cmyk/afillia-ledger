#!/usr/bin/env bash
# Launch the crash-resistant Afillia.ledger v2 dashboard.
# Starts the handoff worker in the background, then opens Streamlit.
# Usage: ./run_app_v2.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "🌙 Starting Afillia Ledger v2 (handoff-based)..."
echo ""

# Start the handoff worker if not already running
if ! pgrep -f "pipeline_handoff.py" > /dev/null; then
    echo "▶ Starting handoff worker in background..."
    nohup python3 scripts/pipeline_handoff.py --poll 5 \
        > logs/worker.log 2>&1 &
    echo "  worker PID: $!"
    sleep 1
else
    echo "✅ Handoff worker already running"
fi

echo ""
echo "📍 Dashboard will open at: http://localhost:8502"
echo ""

python3 -m streamlit run app_v2.py \
    --server.port 8502 \
    --server.address localhost \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#ff006e" \
    --theme.backgroundColor "#0a0a0f" \
    --theme.secondaryBackgroundColor "#1a0a1f" \
    --theme.textColor "#ffffff"
