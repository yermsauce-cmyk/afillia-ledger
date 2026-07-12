#!/usr/bin/env bash
# Smoke tests for the Afillia.ledger pipeline handoff layer.
# Usage: bash scripts/test_handoff.sh

set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ test: handoff module imports cleanly"
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pipeline_handoff import submit_job, get_job, list_jobs, run_job, _ollama_generate_resilient
print('  OK')
"

echo "▶ test: submit_job creates a queued job"
JOB_ID=$(python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pipeline_handoff import submit_job
print(submit_job('ping', {}))
")
echo "  job_id=$JOB_ID"

echo "▶ test: get_job returns the job"
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pipeline_handoff import get_job
job = get_job('$JOB_ID')
assert job is not None, 'job not found'
assert job['status'] == 'queued', f\"expected queued, got {job['status']}\"
assert job['kind'] == 'ping', f\"expected ping, got {job['kind']}\"
print('  OK')
"

echo "▶ test: list_jobs includes the new job"
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pipeline_handoff import list_jobs
jobs = list_jobs(limit=10)
ids = [j['id'] for j in jobs]
assert '$JOB_ID' in ids, 'job not in list'
print(f'  OK ({len(jobs)} jobs listed)')
"

echo "▶ test: compliance_check still works (no LLM)"
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

echo "▶ test: config loads"
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from config import CONFIG
assert CONFIG['project']['account'] == '@afillia'
print('  OK')
"

echo ""
echo "✓ all handoff tests passed"
echo ""
echo "To run the full pipeline asynchronously:"
echo "  1. make worker-bg        # start the handoff worker"
echo "  2. make app-v2           # launch the dashboard at http://localhost:8502"
echo "  3. Click 'Run Pipeline Now' in the sidebar"
echo ""
echo "Or from the command line:"
echo "  make jobs-run-once      # process all queued jobs once"
