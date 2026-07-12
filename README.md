# Afillia.ledger — TikTok Policy + Compliance Agent

A fully **free, open-source** pipeline that monitors TikTok policy changes, summarizes them with a local LLM, alerts on risk, and gates every post through a compliance checker. Built for the **@afillia** synthetic creator account.

> **Zero paywalls.** Runs entirely on your Mac with Ollama + Python stdlib + a few free libraries.

---

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  Scrape     │───▶│  Summarize   │───▶│  Classify   │───▶│  Alert      │
│  (requests  │    │  (Ollama     │    │  (keyword   │    │  (macOS /   │
│  + BS4 +    │    │  qwen3-coder │    │  rules)     │    │  email /    │
│  RSS)       │    │  — FREE)     │    │             │    │  webhook)   │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
                                              ┌──────────────────────────┐
                                              │  Compliance Gate         │
                                              │  (pre-post check, CLI)   │
                                              └──────────────────────────┘
```

---

## Folder Structure

```
Afillia.ledger/
├── README.md
├── Makefile                       # one-command pipeline
├── config.yaml                    # all rules, sources, alert channels
├── .env.example                   # optional credentials (copy → .env)
├── .gitignore
├── app.py                         # original Streamlit dashboard (sync, may crash)
├── app_v2.py                      # crash-resistant v2 dashboard (handoff-based)
├── run_app.sh                     # launcher for app.py
├── run_app_v2.sh                  # launcher for app_v2.py (starts worker too)
├── prompts/
│   ├── afillia_tiktok_prompt.md   # persona + brand guidelines
│   └── policy_summarizer_prompt.md# system prompt for the summarizer LLM
├── workflows/
│   ├── example_n8n_compliance.json    # full n8n graph (Ollama + Telegram)
│   ├── make_com_blueprint.json        # Make.com equivalent
│   └── cline_owl_alpha_prompt.md      # Cline / Owl Alpha system prompt
├── scripts/
│   ├── README.md
│   ├── config.py                  # shared config loader (yaml + .env)
│   ├── scrape_sources.py          # TikTok + Reddit RSS + Google News
│   ├── summarize.py               # Ollama summarizer (free local LLM)
│   ├── content_generator.py       # in-character Afilla content via Ollama
│   ├── compliance_check.py        # pre-post gate (exit 0/1/2)
│   ├── alert.py                   # macOS notify + SMTP + webhook
│   ├── performance.py             # post metrics + goal tracking
│   ├── pipeline_handoff.py        # async job queue + resilient Ollama caller
│   ├── scheduler.py               # cron-free daily runner
│   ├── run_pipeline.sh            # one-shot bash pipeline
│   ├── test.sh                    # original smoke tests
│   └── test_handoff.sh            # handoff-layer smoke tests
└── logs/
    ├── .gitkeep
    ├── raw/                       # scraped text dumps
    ├── summaries/                 # LLM-generated digests
    ├── content_ideas/             # generated captions
    ├── jobs/                      # handoff queue (one JSON per job)
    ├── compliance_checks.log      # JSON-per-line audit trail
    ├── performance.jsonl          # post metrics
    ├── goals.json                 # follower/conversion targets
    ├── worker.log                 # handoff worker stdout
    └── .last_run                  # scheduler marker
```

---

## Quick Start

```bash
cd ~/Desktop/Afillia.ledger

# 1. Install deps (one-time, all free)
make install

# 2. Make sure Ollama is running with the model pulled
ollama serve &              # if not already running
ollama pull qwen3-coder     # already pulled on this machine

# 3. Run the full pipeline once (synchronous — may be slow)
make pipeline

# 4. Or run individual steps
make scrape
make summarize
make alert

# 5. Compliance-check any caption before posting
make check CAPTION="Tonight's Miami vibe" HASHTAGS="#Afilla #SyntheticSeduction #MiamiVibes"

# 6. Start the daily scheduler in the background
make scheduler-bg

# 7. Run smoke tests
make test
```

## Crash-Resistant v2 (Recommended)

The original `app.py` calls Ollama synchronously with a 60-300s timeout.
On this machine, `qwen3-coder:latest` (30.5B params) takes longer than
that for even trivial prompts, so the Streamlit app crashes mid-request.

**v2 fixes this** with a pipeline handoff pattern:

```
┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  UI      │───▶│  Job Queue   │───▶│  Worker     │───▶│  Ollama     │
│  (never  │    │  (JSON on    │    │  (30-min    │    │  (with      │
│  blocks) │    │   disk)      │    │   timeout + │    │   retry +   │
│          │◀───│              │◀───│   fallback) │    │   fallback) │
└──────────┘    └──────────────┘    └─────────────┘    └─────────────┘
```

```bash
# Start the handoff worker (background)
make worker-bg

# Launch the v2 dashboard (port 8502)
make app-v2

# Or launch in background
make app-v2-bg

# Submit jobs from the command line
make jobs-list           # see queued/running/done jobs
make jobs-run-once       # process all queued jobs once

# Run handoff smoke tests
bash scripts/test_handoff.sh
```

The v2 dashboard has a **Pipeline Jobs** page where you can:
- Submit summarize / generate_content / ping jobs
- Watch live status (queued → running → done/failed)
- Read results without ever blocking the UI

If Ollama is slow, missing, or crashes, the UI keeps working and shows
the job status. The worker retries with exponential backoff and falls
back to smaller models (`qwen2.5-coder:7b`, `llama3.2:3b`) if the
primary model hangs.

---

## Free-Tool Stack

| Layer | Tool | Cost |
|---|---|---|
| LLM | **Ollama** + `qwen3-coder` (local) | $0 |
| LLM fallback | Groq free tier / Anthropic free tier | $0 |
| Scraping | `requests` + `BeautifulSoup4` | $0 |
| RSS | `xml.etree.ElementTree` (stdlib) | $0 |
| Scheduling | In-process Python loop (no cron needed) | $0 |
| Desktop alerts | macOS `osascript` | $0 |
| Email alerts | Gmail SMTP + App Password | $0 |
| Webhook alerts | Slack/Discord incoming webhook (free tier) | $0 |
| Telegram alerts | Telegram Bot API (free) | $0 |
| Workflows | n8n (self-host) / Make.com (free tier) / Cline / Owl Alpha | $0 |

**Total monthly cost: $0.**

---

## Compliance Rules (Critical)

- Always enable TikTok's **AI/synthetic content label** on every post.
- No real-person deepfakes or non-consensual content.
- Disclose AI generation clearly where needed.
- Follow all TikTok Community Guidelines — no spam, excessive automation, prohibited topics.
- Hashtags: `#Afilla #SyntheticSeduction #AIMuse #MiamiVibes #NSFWTease` (research trending ones safely).

Rules are defined in `config.yaml` → `compliance` — edit there, no code changes needed.

---

## Configuration

All behavior is driven by `config.yaml`:

- **Sources** — add/remove URLs under `sources.guidelines`, `sources.reddit`, `sources.rss`
- **Compliance rules** — `compliance.banned_terms`, `compliance.risky_terms`, `compliance.required_hashtags`
- **Alert channels** — `alerting.email`, `alerting.desktop`, `alerting.webhook`
- **LLM provider** — `llm.provider` (`ollama` | `groq_free` | `anthropic_free` | `none`)
- **Schedule** — `schedule.scrape_cron`, `schedule.summarize_cron`

Optional credentials go in `.env` (copy from `.env.example`). Everything works offline with just Ollama.

---

## Posting Strategy

- 3–5 posts/week: mix trends + original.
- Engage replies thoughtfully to build community.
- Cross-promote to Fanvue without aggressive selling on TikTok.
- Track: views, saves, shares, follower growth.

---

## Notes

- The empty file at `~/afillia.ledger` (home directory) is leftover — the real project lives here on the Desktop.
- All Python deps are free: `pyyaml`, `requests`, `beautifulsoup4`. No paid API keys required.
- The scheduler is cron-free — it runs as a background process and checks daily.