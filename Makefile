# Afillia.ledger — convenience targets
# Usage: make <target>

PYTHON ?= python3

..DEFAULT_GOAL := help

.PHONY: help install scrape summarize check alert pipeline scheduler scheduler-bg app app-v2 app-v2-bg app-video-check worker worker-bg worker-stop app-stop test clean

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*## .*' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python deps (requests, beautifulsoup4, pyyaml, streamlit)
	$(PYTHON) -m pip install --user requests beautifulsoup4 pyyaml streamlit

app: ## Launch the original Streamlit dashboard (may crash on slow Ollama)
	bash run_app.sh

app-stop: ## Stop the original dashboard
	@pkill -f "streamlit run app.py" && echo "stopped" || echo "not running"

app-v2: ## Launch the crash-resistant v2 dashboard (handoff-based)
	bash run_app_v2.sh

app-v2-bg: ## Launch v2 dashboard in background
	nohup python3 -m streamlit run app_v2.py --server.port 8502 --server.headless true \
		--browser.gatherUsageStats false > logs/streamlit_v2.log 2>&1 & \
		echo "started PID $$! — http://localhost:8502"

app-video-check: ## Launch the video compliance checker on port 8504
	bash run_app_video_check.sh

app-video-check-bg: ## Launch the video compliance checker in background
	nohup python3 -m streamlit run video_check.py --server.port 8504 --server.headless true \
		--browser.gatherUsageStats false > logs/video_check.log 2>&1 & \
		echo "started PID $$! — http://localhost:8504"

app-video-check-open: ## Launch the video compliance checker and open it in the browser
	bash run_app_video_check_open.sh

worker: ## Run the handoff worker in foreground (Ctrl-C to stop)
	$(PYTHON) scripts/pipeline_handoff.py --poll 5

worker-bg: ## Run the handoff worker in background
	nohup $(PYTHON) scripts/pipeline_handoff.py --poll 5 > logs/worker.log 2>&1 & \
		echo "started PID $$!"

worker-stop: ## Stop the handoff worker
	@pkill -f "pipeline_handoff.py" && echo "stopped" || echo "not running"

jobs-list: ## List recent pipeline jobs
	$(PYTHON) scripts/pipeline_handoff.py --list

jobs-run-once: ## Process all queued jobs once and exit
	$(PYTHON) scripts/pipeline_handoff.py --once

scrape: ## Scrape TikTok guidelines + Reddit + RSS
	$(PYTHON) scripts/scrape_sources.py

summarize: ## Summarize latest raw scrape via local LLM
	$(PYTHON) scripts/summarize.py

check: ## Run compliance check (CAPTION="..." HASHTAGS="#Afilla ...")
	$(PYTHON) scripts/compliance_check.py --caption "$(CAPTION)" --hashtags "$(HASHTAGS)"

alert: ## Send a test alert
	$(PYTHON) scripts/alert.py --text "Test alert from Afillia.ledger" --level low

pipeline: ## Run full pipeline once (scrape → summarize → alert)
	bash scripts/run_pipeline.sh

scheduler: ## Run scheduler in foreground (Ctrl-C to stop)
	$(PYTHON) scripts/scheduler.py

scheduler-bg: ## Run scheduler in background, log to logs/scheduler.log
	nohup $(PYTHON) scripts/scheduler.py --interval 300 > logs/scheduler.log 2>&1 & \
		echo "started PID $$!"

test: ## Run smoke tests
	bash scripts/test.sh

clean: ## Remove logs and __pycache__
	rm -rf logs/raw/* logs/summaries/* logs/compliance_checks.log logs/.last_run
	find . -type d -name __pycache__ -exec rm -rf {} +
