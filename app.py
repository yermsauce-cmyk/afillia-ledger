"""
Afillia.ledger — Streamlit Dashboard

A free, local web app for monitoring TikTok policy changes and running
pre-post compliance checks for the @afillia synthetic creator account.

Run:
    streamlit run app.py
    # or
    make app
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Make scripts/ importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import CONFIG, project_path  # noqa: E402
from compliance_check import check as compliance_check  # noqa: E402
from performance import (  # noqa: E402
    log_post, summary as perf_summary, goal_progress,
    load_goals, set_goals, load_entries,
)
from content_generator import generate as generate_content, PILLARS  # noqa: E402

# ---------- Page config ----------
st.set_page_config(
    page_title="Afillia Ledger",
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
        <h1>🌙 Afillia Ledger</h1>
        <p>TikTok Policy Monitor + Compliance Gate for @afillia</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 🎛️ Navigation")
    page = st.radio(
        "Go to",
        ["🏠 Dashboard", "✅ Compliance Check", "🎬 Content Studio", "📈 Performance", "🎯 Goals", "📰 Policy Feed", "📊 Summaries", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🎭 Mode")
    agent_mode = st.toggle("AGENT MODE", value=False, help="Switch from in-character Afilla to analytical operations mode")
    if agent_mode:
        st.caption("🔧 Analytical mode active — structured JSON output")

    st.markdown("---")
    st.markdown("### 📡 System Status")

    # Ollama status
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        st.success(f"✅ Ollama online\n\nModels: {', '.join(models) if models else 'none'}")
    except Exception:
        st.error("❌ Ollama offline\n\nRun: `ollama serve`")

    # Last pipeline run
    last_run_file = project_path("logs", ".last_run")
    if last_run_file.exists():
        last_run = last_run_file.read_text().strip()
        st.info(f"🕐 Last run: {last_run}")
    else:
        st.warning("🕐 Pipeline never run")

    st.markdown("---")
    st.markdown("### 🔗 Quick Actions")
    if st.button("🔄 Run Pipeline Now", use_container_width=True):
        with st.spinner("Running scrape → summarize → alert..."):
            result = subprocess.run(
                ["bash", str(ROOT / "scripts" / "run_pipeline.sh")],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                st.success("✅ Pipeline complete!")
                st.rerun()
            else:
                st.error(f"❌ Pipeline failed:\n{result.stderr}")


# ---------- Helper functions ----------
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


def risk_badge(level: str) -> str:
    return f'<span class="risk-{level}">{level.upper()}</span>'


# ---------- Pages ----------
if page == "🏠 Dashboard":
    st.markdown("## 📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    log_entries = load_compliance_log()
    summaries = load_summaries()
    raw_scrapes = load_raw_scrapes()

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
        blocked = sum(1 for e in log_entries if not e.get("approved"))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Blocked Posts", blocked)
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Policy Summaries", len(summaries))
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
            st.info("No compliance checks yet. Try the Compliance Check page.")

    with col_right:
        st.markdown("### 📰 Latest Policy Summary")
        if summaries:
            latest = summaries[0]
            content = latest.read_text(encoding="utf-8")
            with st.expander(f"📄 {latest.name}", expanded=True):
                st.markdown(content[:2000] + ("..." if len(content) > 2000 else ""))
        else:
            st.info("No summaries yet. Run the pipeline to generate one.")

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
        caption = st.text_area(
            "Caption",
            height=150,
            placeholder="Write your TikTok caption here...",
        )
        hashtags = st.text_input(
            "Hashtags",
            value="#Afilla #SyntheticSeduction #MiamiVibes",
        )
        submitted = st.form_submit_button("🔍 Check Compliance", type="primary", use_container_width=True)

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
                st.error("🚫 This post would be blocked. Review the issues above.")
            elif result.get("needs_review"):
                st.warning("⚠️ Approved with review — check risky terms carefully.")
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


elif page == "📰 Policy Feed":
    st.markdown("## 📰 Raw Policy Feed")
    st.markdown("Latest scraped content from TikTok guidelines, Reddit, and news sources.")

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
                preview = content[:3000]
                st.text(preview + ("\n\n... (truncated)" if len(content) > 3000 else ""))
                if st.button(f"View full file", key=f"view_{scrape_file.name}"):
                    st.text(content)


elif page == "📊 Summaries":
    st.markdown("## 📊 AI-Generated Policy Summaries")
    st.markdown("Summaries generated by local Ollama LLM (free, private).")

    summaries = load_summaries()

    if not summaries:
        st.info("No summaries yet. Run the pipeline to generate one.")
        if st.button("🚀 Generate First Summary", type="primary"):
            with st.spinner("Scraping + summarizing... (may take 1-2 minutes)"):
                result = subprocess.run(
                    ["bash", str(ROOT / "scripts" / "run_pipeline.sh")],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    st.success("✅ Summary generated!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed:\n{result.stderr}")
    else:
        for summary_file in summaries:
            with st.expander(f"📄 {summary_file.name}", expanded=(summary_file == summaries[0])):
                content = summary_file.read_text(encoding="utf-8")
                st.markdown(content)


elif page == "🎬 Content Studio":
    st.markdown("## 🎬 Content Studio")
    st.markdown("Generate captions, hooks, and hashtag sets in-character as Afilla — powered by local Ollama LLM.")

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

    if st.button("✨ Generate Content", type="primary", use_container_width=True):
        with st.spinner("Afillia is creating... (1-2 minutes via local LLM)"):
            try:
                result = generate_content(pillar, trend, topic, agent_mode)
                st.session_state["last_content"] = result
                st.success("✅ Content generated!")
            except Exception as e:
                st.error(f"❌ Generation failed: {e}")

    if "last_content" in st.session_state:
        result = st.session_state["last_content"]
        st.markdown("---")
        st.markdown(f"### 📝 Generated Content — {result['pillar']}")

        with st.expander("🎭 Raw Output", expanded=True):
            st.markdown(result["raw_output"])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🏷️ Extracted Hashtags**")
            st.code(" ".join(result["extracted_hashtags"]) if result["extracted_hashtags"] else "(none)")

        with col2:
            if result["compliance_check"]:
                cc = result["compliance_check"]
                risk = cc["risk_level"]
                st.markdown(f"**🛡️ Compliance: {risk_badge(risk)}**")
                if cc["approved"]:
                    st.success("✅ Safe to post")
                else:
                    st.error("❌ Needs fixes")

        st.markdown(f"💾 Saved to: `{result['saved_to']}`")

    st.markdown("---")
    st.markdown("### 📚 Past Content Ideas")
    ideas_dir = project_path("logs", "content_ideas")
    if ideas_dir.exists():
        ideas = sorted(ideas_dir.glob("*.md"), reverse=True)
        for idea in ideas[:10]:
            with st.expander(f"📄 {idea.name}"):
                st.markdown(idea.read_text(encoding="utf-8")[:2000])


elif page == "📈 Performance":
    st.markdown("## 📈 Performance Tracking")
    st.markdown("Log post metrics and track progress toward your goals.")

    with st.expander("➕ Log New Post Metrics", expanded=False):
        with st.form("perf_form"):
            col1, col2 = st.columns(2)
            with col1:
                post_id = st.text_input("Post ID / URL slug", placeholder="afilla_2026_07_11_dance")
                pillar = st.selectbox("Pillar", ["dance", "fitness", "lifestyle", "fan_cta"])
                views = st.number_input("Views", min_value=0, value=1000)
            with col2:
                saves = st.number_input("Saves", min_value=0, value=30)
                shares = st.number_input("Shares", min_value=0, value=10)
                new_followers = st.number_input("New Followers", min_value=0, value=50)
            notes = st.text_input("Notes (optional)")
            submitted = st.form_submit_button("📊 Log Metrics", type="primary")

            if submitted and post_id:
                entry = log_post(post_id, views, saves, shares, new_followers, pillar, notes)
                st.success(f"✅ Logged: {entry['save_rate']*100:.1f}% save rate, {entry['share_rate']*100:.1f}% share rate")

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
    st.markdown("### 📅 Weekly Breakdown")
    weeks = s.get("weeks", {})
    if weeks:
        for week, data in sorted(weeks.items(), reverse=True):
            st.markdown(f"**{week}** — {data['posts']} posts, {data['views']:,} views, +{data['followers']} followers")
    else:
        st.info("No posts logged yet. Use the form above to start tracking.")

    st.markdown("---")
    st.markdown("### 📜 Recent Entries")
    entries = load_entries()
    if entries:
        for entry in reversed(entries[-10:]):
            with st.expander(f"{entry['timestamp'][:10]} — {entry['post_id']} ({entry['pillar']})"):
                st.json(entry)


elif page == "🎯 Goals":
    st.markdown("## 🎯 Goal Tracker")
    st.markdown("Track progress toward 10k followers and Fanvue conversion targets.")

    current = st.number_input(
        "Current TikTok Followers",
        min_value=0,
        value=int(st.session_state.get("current_followers", 0)),
        step=100,
        help="Update this as your account grows",
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
    st.markdown("### 💎 Fanvue Conversion Target")
    fanvue_target = progress["fanvue_subs_target"]
    st.markdown(f"At **{goals['fanvue_conversion_target']*100:.1f}%** conversion, you should aim for **{fanvue_target:,}** Fanvue subscribers.")

    st.markdown("---")
    st.markdown("### ⚙️ Adjust Goals")
    with st.form("goals_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_followers_target = st.number_input("Followers Target", value=goals["followers_target"])
            new_weekly_growth = st.number_input("Weekly Growth Target", value=goals["weekly_follower_growth_target"])
            new_views_target = st.number_input("Views per Post Target", value=goals["views_per_post_target"])
        with col2:
            new_save_rate = st.number_input("Save Rate Target", value=goals["save_rate_target"], step=0.01, format="%.2f")
            new_share_rate = st.number_input("Share Rate Target", value=goals["share_rate_target"], step=0.01, format="%.2f")
            new_fanvue_conv = st.number_input("Fanvue Conversion Target", value=goals["fanvue_conversion_target"], step=0.01, format="%.2f")

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


elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Configuration")

    st.markdown("### 📋 Current Config")
    st.json(CONFIG)

    st.markdown("---")
    st.markdown("### 🔧 Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh All Data", use_container_width=True):
            with st.spinner("Running full pipeline..."):
                result = subprocess.run(
                    ["bash", str(ROOT / "scripts" / "run_pipeline.sh")],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    st.success("✅ Refresh complete!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed:\n{result.stderr}")

    with col2:
        if st.button("🧹 Clear Logs", use_container_width=True):
            log_file = project_path("logs", "compliance_checks.log")
            if log_file.exists():
                log_file.unlink()
                st.success("✅ Logs cleared")
                st.rerun()

    st.markdown("---")
    st.markdown("### 📁 File Locations")
    st.code(f"""
Config:     {project_path('config.yaml')}
Prompts:    {project_path('prompts')}
Logs:       {project_path('logs')}
Scripts:    {project_path('scripts')}
Workflows:  {project_path('workflows')}
    """)
