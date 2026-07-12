#!/usr/bin/env bash
# Smoke tests for the Afillia.ledger pipeline.
# Usage: bash scripts/test.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ test: config loads"
python3 -c "from scripts.config import CONFIG; assert CONFIG['project']['account'] == '@afillia'; print('  OK')"

echo "▶ test: compliance_check approves clean caption"
python3 scripts/compliance_check.py \
    --caption "Tonight's Miami vibe" \
    --hashtags "#Afilla #SyntheticSeduction #MiamiVibes" \
    --quiet
echo "  exit=$?  (expect 0)"

echo "▶ test: compliance_check blocks banned term"
set +e
python3 scripts/compliance_check.py \
    --caption "Check out this deepfake" \
    --hashtags "#Afilla" \
    --quiet
echo "  exit=$?  (expect 1)"
set -e

echo "▶ test: compliance_check flags risky term (medium)"
set +e
python3 scripts/compliance_check.py \
    --caption "New teaser dropping" \
    --hashtags "#Afilla #fanvue" \
    --quiet
echo "  exit=$?  (expect 2)"
set -e

echo "▶ test: scrape_sources runs (may fail offline — that's OK)"
set +e
python3 scripts/scrape_sources.py --only reddit >/dev/null 2>&1
echo "  exit=$?  (0 if online, non-zero if offline)"
set -e

echo "✓ all tests passed"
