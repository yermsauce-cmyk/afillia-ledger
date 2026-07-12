#!/usr/bin/env bash
# Launch the Afillia.ledger Streamlit dashboard
# Usage: ./run_app.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "🌙 Starting Afillia Ledger Dashboard..."
echo "📍 Will open at: http://localhost:8501"
echo ""

python3 -m streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#ff006e" \
    --theme.backgroundColor "#0a0a0f" \
    --theme.secondaryBackgroundColor "#1a0a1f" \
    --theme.textColor "#ffffff"
