"""
Video Compliance Checker — run any video through TikTok's rules before posting.

Upload a video file, answer a few questions about it, and get a risk score
plus a list of specific issues that could get it flagged or taken down.

No LLM, no scraping — just rule-based checks against TikTok's
Community Guidelines as they apply to @afillia.

Run:
    streamlit run video_check.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Video Compliance Check — Afillia",
    page_icon="🎬",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #0a0a0f; color: #ffffff; }
    .risk-high { background: #ff006e; color: white; padding: 0.5rem 1rem; border-radius: 8px; font-weight: bold; font-size: 1.1rem; }
    .risk-medium { background: #ffbe0b; color: black; padding: 0.5rem 1rem; border-radius: 8px; font-weight: bold; font-size: 1.1rem; }
    .risk-low { background: #06d6a0; color: black; padding: 0.5rem 1rem; border-radius: 8px; font-weight: bold; font-size: 1.1rem; }
    .issue-block { background: rgba(255,0,110,0.1); border-left: 4px solid #ff006e; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; }
    .warn-block { background: rgba(255,190,11,0.1); border-left: 4px solid #ffbe0b; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; }
    .ok-block { background: rgba(6,214,160,0.1); border-left: 4px solid #06d6a0; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("# 🎬 Video Compliance Checker")
st.markdown("Run any video through TikTok's rules **before** you post. "
            "Get a risk score and a list of specific issues that could get it flagged or taken down.")
st.markdown("---")


# ---------- Step 1: Upload ----------

st.markdown("## Step 1 — Upload your video")

uploaded = st.file_uploader(
    "Choose a video file",
    type=["mp4", "mov", "webm", "avi", "mkv"],
    help="The video stays on your machine. We just read its metadata.",
)

video_meta = {}
if uploaded is not None:
    file_bytes = uploaded.read()
    size_mb = len(file_bytes) / (1024 * 1024)

    # Try to extract basic metadata from the filename and size
    video_meta = {
        "filename": uploaded.name,
        "size_mb": round(size_mb, 2),
        "type": uploaded.type or "video/mp4",
    }

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filename", uploaded.name)
    with col2:
        st.metric("Size", f"{size_mb:.1f} MB")
    with col3:
        # TikTok upload limit is 287 MB / 10 min for most accounts
        if size_mb > 287:
            st.error("❌ Over 287 MB TikTok limit")
        elif size_mb > 72:
            st.warning("⚠️ Over 72 MB (slower upload)")
        else:
            st.success("✅ Under TikTok size limit")

    st.info(f"📁 File ready: **{uploaded.name}** ({size_mb:.1f} MB). "
            "Answer the questions below to check compliance.")

st.markdown("---")


# ---------- Step 2: Answer questions ----------

st.markdown("## Step 2 — Answer these questions about the video")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🎥 Content")
    has_real_person = st.radio(
        "Does this video show a **real, identifiable person**?",
        ["No — fully synthetic/animated", "Yes — but with consent", "Yes — no consent"],
        help="Deepfakes of real people without consent are banned.",
    )
    is_nudity = st.radio(
        "Does this video contain **nudity or explicit sexual content**?",
        ["No", "Suggestive only (tease aesthetic)", "Yes — partial nudity", "Yes — explicit"],
    )
    is_violence = st.radio(
        "Does this video contain **violence, gore, or weapons**?",
        ["No", "Mild (fitness, dance)", "Yes"],
    )

with col2:
    st.markdown("### 🎵 Audio & IP")
    music_source = st.radio(
        "Where is the **music/audio** from?",
        ["TikTok's licensed library", "My own original audio", "Third-party (not licensed)"],
        help="Using unlicensed music = copyright strike.",
    )
    uses_brand = st.radio(
        "Does this video promote a **brand, product, or paid partnership**?",
        ["No", "Yes — disclosed with Branded Content toggle", "Yes — not disclosed"],
    )
    mentions_adult_platform = st.radio(
        "Does the caption mention **OnlyFans, Fansly, or similar**?",
        ["No", "Soft tease only", "Direct link or explicit mention"],
    )

st.markdown("---")

st.markdown("### 📝 Caption & hashtags")
caption = st.text_area(
    "Caption (paste what you plan to post)",
    height=100,
    placeholder="Tonight's Miami vibe ✨ #Afilla #SyntheticSeduction #MiamiVibes",
)
hashtags_raw = st.text_input(
    "Hashtags (space-separated)",
    value="#Afilla #SyntheticSeduction #MiamiVibes",
)

st.markdown("---")


# ---------- Step 3: Run checks ----------

def run_checks(meta: dict, answers: dict, caption: str, hashtags: list[str]) -> dict:
    issues = []      # hard fails — will get taken down
    warnings = []    # soft flags — might get flagged
    passed = []      # things you did right

    # --- Content checks ---
    if answers["has_real_person"] == "Yes — no consent":
        issues.append({
            "rule": "Non-consensual deepfake",
            "detail": "Real-person deepfakes without consent are banned. This video will be removed and your account may be permanently suspended.",
            "fix": "Remove the video. Only use synthetic faces or get written consent from the person depicted.",
        })
    elif answers["has_real_person"] == "Yes — but with consent":
        warnings.append({
            "rule": "Real person depicted",
            "detail": "TikTok may still flag this. Keep evidence of consent ready in case of an appeal.",
            "fix": "Have written consent on file. Consider adding a disclaimer in the caption.",
        })
    else:
        passed.append("Fully synthetic content — no real-person deepfake risk")

    if answers["is_nudity"] == "Yes — explicit":
        issues.append({
            "rule": "Explicit sexual content",
            "detail": "Explicit nudity or sexual acts are banned. This will be removed immediately.",
            "fix": "Remove or heavily edit the video. Suggestive tease aesthetic is OK; explicit is not.",
        })
    elif answers["is_nudity"] == "Yes — partial nudity":
        issues.append({
            "rule": "Partial nudity",
            "detail": "Partial nudity is restricted and likely to be removed or age-restricted (which kills reach).",
            "fix": "Crop, blur, or reshoot. Keep the tease aesthetic without actual skin exposure.",
        })
    elif answers["is_nudity"] == "Suggestive only (tease aesthetic)":
        warnings.append({
            "rule": "Suggestive content",
            "detail": "Suggestive content is allowed but held to a higher standard. Avoid lingering shots of cleavage/bottoms or simulated acts.",
            "fix": "Keep transitions fast, focus on outfit/dance/aesthetic rather than body parts.",
        })
        passed.append("Suggestive (not explicit) — within TikTok's tease line")
    else:
        passed.append("No nudity or explicit content")

    if answers["is_violence"] == "Yes":
        issues.append({
            "rule": "Violence or weapons",
            "detail": "Violent content or weapons are banned or heavily restricted.",
            "fix": "Remove violent elements or reshoot without weapons/injury.",
        })
    elif answers["is_violence"] == "Mild (fitness, dance)":
        passed.append("Mild physical activity — within guidelines")
    else:
        passed.append("No violence or weapons")

    # --- Audio / IP checks ---
    if answers["music_source"] == "Third-party (not licensed)":
        issues.append({
            "rule": "Unlicensed music",
            "detail": "Using music you don't have rights to = automatic copyright strike. The video will be muted or removed, and repeat strikes can ban your account.",
            "fix": "Use TikTok's in-app music library, or upload your own original audio.",
        })
    elif answers["music_source"] == "My own original audio":
        passed.append("Original audio — no copyright risk")
    else:
        passed.append("Using TikTok's licensed music library")

    # --- Monetization / disclosure ---
    if answers["uses_brand"] == "Yes — not disclosed":
        issues.append({
            "rule": "Undisclosed paid partnership",
            "detail": "Failing to disclose paid partnerships violates FTC and TikTok rules. Video will be removed and you may lose monetization.",
            "fix": "Turn on TikTok's 'Branded Content' toggle before posting, or add #ad / #sponsored in the caption.",
        })
    elif answers["uses_brand"] == "Yes — disclosed with Branded Content toggle":
        passed.append("Paid partnership properly disclosed")
    else:
        passed.append("No commercial content — no disclosure needed")

    if answers["mentions_adult_platform"] == "Direct link or explicit mention":
        issues.append({
            "rule": "Direct promotion of adult platform",
            "detail": "Directly promoting OnlyFans/Fansly in TikTok posts is against guidelines. The video will likely be removed and reach limited.",
            "fix": "Use soft teasers like 'exclusive content on my page' without naming the platform or linking directly.",
        })
    elif answers["mentions_adult_platform"] == "Soft tease only":
        warnings.append({
            "rule": "Adult platform tease",
            "detail": "Soft teasers are tolerated but can limit reach. Don't do this on every post.",
            "fix": "Max 1x/week. Vary the tease language. Never put a direct link in the caption.",
        })
    else:
        passed.append("No adult platform promotion")

    # --- Caption text checks ---
    caption_lower = (caption + " " + " ".join(hashtags)).lower()

    banned_terms = ["deepfake", "real person", "revenge", "minor", "underage", "non-consensual"]
    risky_terms = ["nsfw", "onlyfans", "fansly", "leaked"]

    banned_hits = [t for t in banned_terms if t in caption_lower]
    risky_hits = [t for t in risky_terms if t in caption_lower]

    if banned_hits:
        issues.append({
            "rule": "Banned terms in caption",
            "detail": f"Caption contains banned terms: {', '.join(banned_hits)}. These trigger automatic flagging.",
            "fix": "Remove these terms. Rephrase without them.",
        })

    if risky_hits:
        warnings.append({
            "rule": "Risky terms in caption",
            "detail": f"Caption contains risky terms: {', '.join(risky_hits)}. These may limit reach or trigger review.",
            "fix": "Consider removing or rephrasing. Use softer language.",
        })

    if "#afilla" not in caption_lower and "#afilla" not in [h.lower() for h in hashtags]:
        warnings.append({
            "rule": "Missing #Afilla hashtag",
            "detail": "Your branded hashtag is missing. This hurts community building and tracking.",
            "fix": "Add #Afilla to every post.",
        })
    else:
        passed.append("Branded #Afilla hashtag present")

    if len(caption) > 2200:
        issues.append({
            "rule": "Caption too long",
            "detail": f"Caption is {len(caption)} characters. TikTok's limit is 2200.",
            "fix": "Trim the caption to under 2200 characters.",
        })
    elif len(caption) > 1500:
        warnings.append({
            "rule": "Caption is long",
            "detail": f"Caption is {len(caption)} characters. Very long captions get truncated in the feed.",
            "fix": "Consider trimming to under 1500 for better readability.",
        })

    # --- AI label check ---
    if not answers.get("ai_label_on", True):
        issues.append({
            "rule": "AI label not enabled",
            "detail": "AI-generated content must be labeled. Without the label, the video will be removed.",
            "fix": "Turn on the 'AI-generated content' toggle in TikTok's upload screen.",
        })
    else:
        passed.append("AI-generated content label assumed ON (verify in upload screen)")

    # --- Score ---
    if issues:
        risk = "high"
        verdict = "❌ DO NOT POST — will likely be taken down"
    elif len(warnings) >= 3:
        risk = "medium"
        verdict = "⚠️ POST WITH CAUTION — may be flagged or reach-limited"
    elif warnings:
        risk = "low"
        verdict = "✅ SAFE TO POST — minor flags only"
    else:
        risk = "low"
        verdict = "✅ SAFE TO POST — all checks passed"

    return {
        "risk": risk,
        "verdict": verdict,
        "issues": issues,
        "warnings": warnings,
        "passed": passed,
        "video_meta": meta,
        "answers": answers,
        "caption_length": len(caption),
        "hashtags": hashtags,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# AI label checkbox (separate so it doesn't get lost)
ai_label_on = st.checkbox(
    "✅ I will turn ON the **AI-generated content label** when uploading",
    value=True,
    help="This is required for every post as @afillia. If unchecked, the check will fail.",
)

if st.button("🔍 Run Compliance Check", type="primary", use_container_width=True):
    if not caption.strip():
        st.warning("Please paste your caption first.")
    else:
        hashtags = re.findall(r"#\w+", hashtags_raw)
        answers = {
            "has_real_person": has_real_person,
            "is_nudity": is_nudity,
            "is_violence": is_violence,
            "music_source": music_source,
            "uses_brand": uses_brand,
            "mentions_adult_platform": mentions_adult_platform,
            "ai_label_on": ai_label_on,
        }
        result = run_checks(video_meta, answers, caption, hashtags)

        st.markdown("---")
        st.markdown("## Step 3 — Results")

        risk = result["risk"]
        st.markdown(
            f'<div class="risk-{risk}">{result["verdict"]}</div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Risk Level", risk.upper())
        with col2:
            st.metric("Issues (will be taken down)", len(result["issues"]))
        with col3:
            st.metric("Warnings (may be flagged)", len(result["warnings"]))

        if result["issues"]:
            st.markdown("### 🚨 Issues — must fix before posting")
            for issue in result["issues"]:
                st.markdown(
                    f'<div class="issue-block">'
                    f'<strong>{issue["rule"]}</strong><br>'
                    f'{issue["detail"]}<br>'
                    f'<em>Fix: {issue["fix"]}</em>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if result["warnings"]:
            st.markdown("### ⚠️ Warnings — review before posting")
            for warn in result["warnings"]:
                st.markdown(
                    f'<div class="warn-block">'
                    f'<strong>{warn["rule"]}</strong><br>'
                    f'{warn["detail"]}<br>'
                    f'<em>Fix: {warn["fix"]}</em>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if result["passed"]:
            st.markdown("### ✅ What you did right")
            for p in result["passed"]:
                st.markdown(
                    f'<div class="ok-block">✓ {p}</div>',
                    unsafe_allow_html=True,
                )

        # Save the check to a log (best-effort — read-only filesystems skip silently)
        try:
            log_dir = Path(__file__).resolve().parent / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "video_checks.jsonl"
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            st.markdown("---")
            st.markdown(f"💾 Check saved to `logs/video_checks.jsonl`")
        except OSError:
            # Read-only filesystem (e.g. Streamlit Community Cloud) — skip silently
            pass

        with st.expander("📋 Full JSON report"):
            st.json(result)


# ---------- Footer ----------

st.markdown("---")
st.markdown(
    """
**How this works:** Rule-based checks against TikTok's Community Guidelines
as they apply to a synthetic AI creator account. No LLM, no scraping —
just the rules.

**Not a guarantee:** TikTok's enforcement is partly automated and partly
human. A clean check here doesn't mean the video is 100% safe, and a
flagged check doesn't mean it will definitely be removed. Use this as
a pre-flight checklist, not a legal review.

**Sources:** [TikTok Community Guidelines](https://www.tiktok.com/community-guidelines) ·
[TikTok Help Center](https://support.tiktok.com/en/using-tiktok)
    """
)
