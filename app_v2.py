"""
Afillia.ledger — Streamlit Dashboard (v2, handoff-based)

This is a crash-resistant rewrite of app.py. The original called Ollama
synchronously with a 60-300s timeout, which crashed the UI when
qwen3-coder:latest (30.5B) took longer than that.

This version uses the **pipeline handoff** pattern:
  - LLM jobs are submitted to a queue (scripts/pipeline_handoff.py).
  - A background worker runs them with a 30-minute timeout, retries,
    and falls back to smaller models if needed.
  - The UI polls the queue and shows live status. It never blocks.

Run:
    streamlit run app_v2.py
    # or
    make app-v2
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import CONFIG, project_path  # noqa: E402
from compliance_check import check as compliance_check  # noqa: E402
from performance import (  # noqa: E402
    log_post, summary as perf_summary, goal_progress,
    load_goals, set_goals, load_entries,
)
from content_generator import PILLARS  # noqa: E402
from pipeline_handoff import submit_job, get_job, list_jobs  # noqa: E402

# ---------- Page config ----------
st.set_page_config(
    page_title="Afillia Ledger v2",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom CSS ----------
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #0a0a0f 0%, #1a0a1f 100%); }
    .afillia-header {
        background: linear-gradient(90deg, #8b0000 0%, #ff006e 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .afillia-header h1 { margin: 0; font-size: 2.2rem; }
    .afillia-header p { margin: 0.3rem 0 0 0; opacity: 0.9; }
    .risk-high { background: #ff006e; color: white; padding: 0.4rem 0.8rem; border-radius: 6px; font-weight: bold; }
    .risk-medium { background: #ffbe0b; color: black; padding: 0.4rem 0.8rem; border-radius: 6px; font-weight: bold; }
    .risk-low { background: #06d6a0; color: black; padding: 0.4rem 0.8rem; border-radius: 6px; font-weight: bold; }
    .job-queued { background: #6c757d; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; }
    .job-running { background: #0d6efd; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; }
    .job-done { background: #06d6a0; color: black; padding: 0.3rem 0.6rem; border-radius: 4px; }
    .job-failed { background: #ff006e; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; }
    .metric-card {
        background: rgba(255,255,255,0.05);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown(
    """
    <div class="afillia-header">
        <h1>🌙 Afillia Ledger v2</h1>
        <p>Crash-resistant pipeline handoff — TikTok Policy Monitor + Compliance Gate for @afillia</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Helpers ----------

def risk_badge(level: str) -> str:
    return f'<span class="risk-{level}">{level.upper()}</span>'


def job_badge(status: str) -> str:
    return f'<span class="job-{status}">{status.upper()}</span>'


def load_compliance_log() -> list[dict]:
    log_file = project_path("logs", "compliance_checks.log")
    if not log_file.exists():
        return []
    entries = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def load_summaries() -> list[Path]:
    summaries_dir = project_path("logs", "summaries")
    if not summaries_dir.exists():
        return []
    return sorted(summaries_dir.glob("summary_*.md"), reverse=True)


def load_raw_scrapes() -> list[Path]:
    raw_dir = project_path("logs", "raw")
    if not raw_dir.exists():
        return []
    return sorted(raw_dir.glob("*.txt"), reverse=True)


def worker_is_running() -> bool:
    """Check if the handoff worker process is alive."""
    try:
        out = subprocess.check_output(["pgrep", "-f", "pipeline_handoff.py"], text=True)
        return bool(out.strip())
    except subprocess.CalledProcessError:
        return False


def start_worker() -> bool:
    """Launch the handoff worker in the background."""
    log_path = project_path("logs", "worker.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "pipeline_handoff.py"), "--poll", "5"],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # Give it a moment to start
    time.sleep(1)
    return worker_is_running()


def ollama_online() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ---------- Sidebar ----------

with st.sidebar:
    st.markdown("### 🎛️ Navigation")
    page = st.radio(
        "Go to",
        ["🏠 Dashboard", "✅ Compliance Check", "🎬 Content Studio",
         "📈 Performance", "🎯 Goals", "📰 Policy Feed", "📊 Summaries",
         "⚙️ Pipeline Jobs", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🎭 Mode")
    agent_mode = st.toggle("AGENT MODE", value=False,
                           help="Switch from in-character Afilla to analytical operations mode")

    st.markdown("---")
    st.markdown("### 📡 System Status")

    if ollama_online():
        st.success("✅ Ollama online")
    else:
        st.error("❌ Ollama offline — run `ollama serve`")

    if worker_is_running():
        st.success("✅ Handoff worker running")
    else:
        st.warning("⚠️ Handoff worker NOT running")
        if st.button("▶ Start worker", use_container_width=True):
            if start_worker():
                st.success("Worker started")
                st.rerun()
            else:
                st.error("Failed to start worker")

    last_run_file = project_path("logs", ".last_run")
    if last_run_file.exists():
        st.info(f"🕐 Last run: {last_run_file.read_text().strip()}")
    else:
        st.warning("🕐 Pipeline never run")

    st.markdown("---")
    st.markdown("### 🔗 Quick Actions")
    if st.button("🔄 Run Pipeline Now", use_container_width=True,
                 help="Scrape → submit summarize job → alert"):
        with st.spinner("Submitting jobs to handoff queue..."):
            # Scrape synchronously (fast, no LLM)
            scrape = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "scrape_sources.py")],
                capture_output=True, text=True, timeout=120,
            )
            # Submit summarize job to the handoff queue (non-blocking)
            job_id = submit_job("summarize", {})
            st.success(f"✅ Scrape done. Summarize job queued: `{job_id}`")
            st.info("Worker will pick it up. Check the Pipeline Jobs page.")
            st.rerun()


# ---------- Pages ----------

if page == "🏠 Dashboard":
    st.markdown("## 📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    log_entries = load_compliance_log()
    summaries = load_summaries()
    raw_scrapes = load_raw_scrapes()
    jobs = list_jobs(limit=100)
    queued = sum(1 for j in jobs if j["status"] == "queued")
    running = sum(1 for j in jobs if j["status"] == "running")
    done = sum(1 for j in jobs if j["status"] == "done")
    failed = sum(1 for j in jobs if j["status"] == "failed")

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Compliance Checks", len(log_entries))
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        approved = sum(1 for e in log_entries if e.get("approved"))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Approved Posts", approved)
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Policy Summaries", len(summaries))
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Jobs (queued/running)", f"{queued}/{running}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🔥 Recent Compliance Checks")
        if log_entries:
            for entry in reversed(log_entries[-5:]):
                risk = entry.get("risk_level", "low")
                caption = entry.get("caption", "")[:80]
                ts = entry.get("timestamp", "")[:19]
                st.markdown(
                    f"{risk_badge(risk)} **{ts}**\n\n"
                    f"> {caption}{'...' if len(entry.get('caption', '')) > 80 else ''}",
                    unsafe_allow_html=True,
                )
                st.markdown("")
        else:
            st.info("No compliance checks yet.")

    with col_right:
        st.markdown("### 📰 Latest Policy Summary")
        if summaries:
            latest = summaries[0]
            content = latest.read_text(encoding="utf-8")
            with st.expander(f"📄 {latest.name}", expanded=True):
                st.markdown(content[:2000] + ("..." if len(content) > 2000 else ""))
        else:
            st.info("No summaries yet. Submit a job from the Pipeline Jobs page.")

    st.markdown("---")
    st.markdown("### 🎯 Quick Compliance Check")
    quick_caption = st.text_input("Test a caption:", placeholder="Tonight's Miami vibe ✨")
    quick_hashtags = st.text_input("Hashtags:", value="#Afilla #SyntheticSeduction #MiamiVibes")
    if st.button("Check Now", type="primary"):
        if quick_caption:
            hashtags = re.findall(r"#\w+", quick_hashtags)
            result = compliance_check(quick_caption, hashtags)
            risk = result["risk_level"]
            st.markdown(f"### Result: {risk_badge(risk)}", unsafe_allow_html=True)
            if result["approved"]:
                st.success("✅ Approved — safe to post")
            else:
                st.error("❌ Blocked — fix issues before posting")
            st.json(result)
        else:
            st.warning("Enter a caption first.")


elif page == "✅ Compliance Check":
    st.markdown("## ✅ Pre-Post Compliance Check")
    st.markdown("Test any caption against TikTok's rules before publishing.")

    with st.form("compliance_form"):
        caption = st.text_area("Caption", height=150,
                               placeholder="Write your TikTok caption here...")
        hashtags = st.text_input("Hashtags", value="#Afilla #SyntheticSeduction #MiamiVibes")
        submitted = st.form_submit_button("🔍 Check Compliance", type="primary",
                                          use_container_width=True)

    if submitted:
        if not caption:
            st.warning("Please enter a caption.")
        else:
            tag_list = re.findall(r"#\w+", hashtags)
            result = compliance_check(caption, tag_list)
            risk = result["risk_level"]
            st.markdown(f"## {risk_badge(risk)}", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Risk Level", risk.upper())
            with col2:
                st.metric("Status", "✅ Approved" if result["approved"] else "❌ Blocked")
            with col3:
                st.metric("Caption Length", f"{result['caption_length']} chars")
            st.markdown("### 📋 Detailed Report")
            st.json(result)
            if not result["approved"]:
                st.error("🚫 This post would be blocked.")
            elif result.get("needs_review"):
                st.warning("⚠️ Approved with review.")
            else:
                st.success("✅ All checks passed — safe to post!")

    st.markdown("---")
    st.markdown("### 📜 Recent Checks")
    log_entries = load_compliance_log()
    if log_entries:
        for entry in reversed(log_entries[-10:]):
            risk = entry.get("risk_level", "low")
            caption = entry.get("caption", "")[:100]
            ts = entry.get("timestamp", "")[:19]
            with st.expander(f"{risk_badge(risk)} {ts} — {caption}..."):
                st.json(entry)


elif page == "🎬 Content Studio":
    st.markdown("## 🎬 Content Studio")
    st.markdown("Generate captions via the **handoff queue** — UI never blocks on Ollama.")

    if agent_mode:
        st.info("🔧 AGENT MODE active — output will be structured JSON")

    col1, col2 = st.columns(2)
    with col1:
        pillar = st.selectbox(
            "Content Pillar",
            options=list(PILLARS.keys()),
            format_func=lambda k: f"{k} — {PILLARS[k]}",
        )
    with col2:
        trend = st.text_input("Trend to adapt (optional)", placeholder="e.g. viral sound name")

    topic = st.text_input("Specific topic (optional)", placeholder="e.g. Miami sunset workout")

    if st.button("✨ Submit Generation Job", type="primary", use_container_width=True):
        job_id = submit_job("generate_content", {
            "pillar": pillar,
            "trend": trend,
            "topic": topic,
            "agent_mode": agent_mode,
        })
        st.success(f"✅ Job queued: `{job_id}`")
        st.info("The worker will pick it up. Track it on the Pipeline Jobs page.")
        st.session_state["last_content_job"] = job_id

    # If we have a recent job, poll its status
    last_job_id = st.session_state.get("last_content_job")
    if last_job_id:
        st.markdown("---")
        st.markdown("### 🔄 Last Job Status")
        job = get_job(last_job_id)
        if job:
            st.markdown(f"{job_badge(job['status'])} **{job['kind']}** — `{job['id']}`")
            if job["status"] == "done" and job.get("result"):
                result = job["result"]
                st.markdown(f"### 📝 Generated Content — {result['pillar']}")
                with st.expander("🎭 Raw Output", expanded=True):
                    st.markdown(result["raw_output"])
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🏷️ Extracted Hashtags**")
                    st.code(" ".join(result["extracted_hashtags"]) or "(none)")
                with col2:
                    if result.get("compliance_check"):
                        cc = result["compliance_check"]
                        st.markdown(f"**🛡️ Compliance: {risk_badge(cc['risk_level'])}**")
                        if cc["approved"]:
                            st.success("✅ Safe to post")
                        else:
                            st.error("❌ Needs fixes")
                st.markdown(f"💾 Saved to: `{result['saved_to']}`")
                st.markdown(f"🤖 Model: `{result.get('model', '?')}`")
            elif job["status"] == "failed":
                st.error(f"❌ Failed: {job.get('error')}")
            elif job["status"] in ("queued", "running"):
                st.info("⏳ Still processing — refresh in a minute.")
                if st.button("🔄 Refresh status"):
                    st.rerun()


elif page == "📈 Performance":
    st.markdown("## 📈 Performance Tracking")

    with st.expander("➕ Log New Post Metrics", expanded=False):
        with st.form("perf_form"):
            col1, col2 = st.columns(2)
            with col1:
                post_id = st.text_input("Post ID / URL slug",
                                        placeholder="afilla_2026_07_11_dance")
                pillar = st.selectbox("Pillar",
                                      ["dance", "fitness", "lifestyle", "fan_cta"])
                views = st.number_input("Views", min_value=0, value=1000)
            with col2:
                saves = st.number_input("Saves", min_value=0, value=30)
                shares = st.number_input("Shares", min_value=0, value=10)
                new_followers = st.number_input("New Followers", min_value=0, value=50)
            notes = st.text_input("Notes (optional)")
            submitted = st.form_submit_button("📊 Log Metrics", type="primary")
            if submitted and post_id:
                entry = log_post(post_id, views, saves, shares, new_followers, pillar, notes)
                st.success(f"✅ Logged: {entry['save_rate']*100:.1f}% save rate")

    s = perf_summary()
    goals = s.get("goals", {})
    st.markdown("### 📊 Aggregate Stats")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Posts", s.get("total_posts", 0))
    with col2:
        st.metric("Total Views", f"{s.get('total_views', 0):,}")
    with col3:
        st.metric("Total Saves", f"{s.get('total_saves', 0):,}")
    with col4:
        st.metric("New Followers", f"{s.get('total_new_followers', 0):,}")

    col1, col2 = st.columns(2)
    with col1:
        avg_save = s.get("avg_save_rate", 0) * 100
        target_save = goals.get("save_rate_target", 0.03) * 100
        st.metric("Avg Save Rate", f"{avg_save:.2f}%", delta=f"target {target_save:.1f}%")
    with col2:
        avg_share = s.get("avg_share_rate", 0) * 100
        target_share = goals.get("share_rate_target", 0.01) * 100
        st.metric("Avg Share Rate", f"{avg_share:.2f}%", delta=f"target {target_share:.1f}%")

    st.markdown("---")
    st.markdown("### 📜 Recent Entries")
    entries = load_entries()
    if entries:
        for entry in reversed(entries[-10:]):
            with st.expander(f"{entry['timestamp'][:10]} — {entry['post_id']} ({entry['pillar']})"):
                st.json(entry)


elif page == "🎯 Goals":
    st.markdown("## 🎯 Goal Tracker")
    current = st.number_input(
        "Current TikTok Followers",
        min_value=0,
        value=int(st.session_state.get("current_followers", 0)),
        step=100,
    )
    st.session_state["current_followers"] = current
    progress = goal_progress(current)
    goals = load_goals()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Followers", f"{current:,}")
    with col2:
        st.metric("Target", f"{progress['target']:,}")
    with col3:
        st.metric("Progress", f"{progress['progress_pct']:.1f}%")
    st.progress(min(progress["progress_pct"] / 100, 1.0))

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Remaining", f"{progress['remaining']:,}")
    with col2:
        if progress["weeks_to_goal"]:
            st.metric("Est. Weeks to Goal", f"{progress['weeks_to_goal']:.1f}")
        else:
            st.metric("Est. Weeks to Goal", "— (log posts to estimate)")

    st.markdown("---")
    st.markdown("### ⚙️ Adjust Goals")
    with st.form("goals_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_followers_target = st.number_input("Followers Target",
                                                   value=goals["followers_target"])
            new_weekly_growth = st.number_input("Weekly Growth Target",
                                                value=goals["weekly_follower_growth_target"])
            new_views_target = st.number_input("Views per Post Target",
                                              value=goals["views_per_post_target"])
        with col2:
            new_save_rate = st.number_input("Save Rate Target",
                                            value=goals["save_rate_target"],
                                            step=0.01, format="%.2f")
            new_share_rate = st.number_input("Share Rate Target",
                                             value=goals["share_rate_target"],
                                             step=0.01, format="%.2f")
            new_fanvue_conv = st.number_input("Fanvue Conversion Target",
                                              value=goals["fanvue_conversion_target"],
                                              step=0.01, format="%.2f")
        if st.form_submit_button("💾 Save Goals", type="primary"):
            set_goals(
                followers_target=new_followers_target,
                weekly_follower_growth_target=new_weekly_growth,
                views_per_post_target=new_views_target,
                save_rate_target=new_save_rate,
                share_rate_target=new_share_rate,
                fanvue_conversion_target=new_fanvue_conv,
            )
            st.success("✅ Goals updated!")


elif page == "📰 Policy Feed":
    st.markdown("## 📰 Raw Policy Feed")
    raw_scrapes = load_raw_scrapes()
    if not raw_scrapes:
        st.info("No scraped data yet. Click 'Run Pipeline Now' in the sidebar.")
    else:
        source_filter = st.selectbox(
            "Filter by source:",
            ["All"] + sorted(set(p.name.split("_")[2] for p in raw_scrapes)),
        )
        for scrape_file in raw_scrapes:
            if source_filter != "All" and source_filter not in scrape_file.name:
                continue
            size_kb = scrape_file.stat().st_size / 1024
            with st.expander(f"📄 {scrape_file.name} ({size_kb:.1f} KB)"):
                content = scrape_file.read_text(encoding="utf-8")
                st.text(content[:3000] + ("\n\n... (truncated)" if len(content) > 3000 else ""))


elif page == "📊 Summaries":
    st.markdown("## 📊 AI-Generated Policy Summaries")
    summaries = load_summaries()
    if not summaries:
        st.info("No summaries yet. Submit a summarize job from the Pipeline Jobs page.")
    else:
        for summary_file in summaries:
            with st.expander(f"📄 {summary_file.name}",
                             expanded=(summary_file == summaries[0])):
                st.markdown(summary_file.read_text(encoding="utf-8"))


elif page == "⚙️ Pipeline Jobs":
    st.markdown("## ⚙️ Pipeline Handoff Queue")
    st.markdown("LLM jobs run asynchronously via `scripts/pipeline_handoff.py`. "
                "The UI never blocks on Ollama.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Submit Summarize Job", use_container_width=True):
            job_id = submit_job("summarize", {})
            st.success(f"Queued: `{job_id}`")
            st.rerun()
    with col2:
        if st.button("🏓 Submit Ping Job", use_container_width=True,
                     help="Quick health check — tests Ollama with a tiny prompt"):
            job_id = submit_job("ping", {})
            st.success(f"Queued: `{job_id}`")
            st.rerun()
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Recent Jobs")
    jobs = list_jobs(limit=50)
    if not jobs:
        st.info("No jobs yet. Submit one above.")
    else:
        for job in jobs:
            with st.expander(f"{job_badge(job['status'])} {job['kind']} — `{job['id']}`  "
                             f"({job['created_at'][:19]})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Status:** {job['status']}")
                    st.markdown(f"**Attempts:** {job['attempts']}")
                    st.markdown(f"**Created:** {job['created_at']}")
                with col2:
                    if job.get("started_at"):
                        st.markdown(f"**Started:** {job['started_at'][:19]}")
                    if job.get("finished_at"):
                        st.markdown(f"**Finished:** {job['finished_at'][:19]}")
                    if job.get("model_used"):
                        st.markdown(f"**Model:** `{job['model_used']}`")
                if job.get("error"):
                    st.error(f"❌ {job['error']}")
                if job.get("result"):
                    with st.expander("Result"):
                        st.json(job["result"])


elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Configuration")
    st.markdown("### 📋 Current Config")
    st.json(CONFIG)

    st.markdown("---")
    st.markdown("### 🔧 Worker Control")
    if worker_is_running():
        st.success("✅ Handoff worker is running")
        if st.button("🛑 Stop worker"):
            subprocess.run(["pkill", "-f", "pipeline_handoff.py"])
            st.rerun()
    else:
        st.warning("⚠️ Handoff worker is NOT running")
        if st.button("▶ Start worker"):
            if start_worker():
                st.success("Worker started")
                st.rerun()

    st.markdown("---")
    st.markdown("### 📁 File Locations")
    st.code(f"""
Config:     {project_path('config.yaml')}
Prompts:    {project_path('prompts')}
Logs:       {project_path('logs')}
Scripts:    {project_path('scripts')}
Workflows:  {project_path('workflows')}
Job Queue:  {project_path('logs', 'jobs')}
Worker Log: {project_path('logs', 'worker.log')}
    """)
