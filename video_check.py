"""
Video Compliance Checker — run any video through TikTok's rules before posting.

Upload a video file, answer a few questions about it, and get a risk score
plus a list of specific issues that could get it flagged or taken down.

Rules are loaded from `tiktok_rules.json` so they can be updated without
touching code. Push the JSON to GitHub and Streamlit auto-redeploys.

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
    .rules-meta { background: rgba(100,100,255,0.08); border: 1px solid rgba(100,100,255,0.3); padding: 0.6rem 1rem; border-radius: 6px; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Load rules from JSON ----------

RULES_PATH = Path(__file__).resolve().parent / "tiktok_rules.json"


@st.cache_data(ttl=300)  # cache for 5 minutes; refresh button bypasses cache
def load_rules(path_str: str) -> dict:
    """Load TikTok rules from JSON. Cached briefly so the UI stays snappy."""
    p = Path(path_str)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def refresh_rules_from_tiktok() -> dict:
    """
    Attempt to fetch TikTok's Community Guidelines page and extract rule text.
    NOTE: This violates TikTok's Terms of Service. Use at your own risk.
    Returns a partial rules dict — manual review still required.
    """
    import urllib.request
    import urllib.error

    url = "https://www.tiktok.com/community-guidelines"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {
            "ok": False,
            "error": f"Could not fetch TikTok guidelines: {e}",
            "html_length": 0,
        }

    # Strip HTML tags for a rough text dump. This is NOT a structured parse —
    # TikTok's page is JS-rendered so we usually only get the shell.
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "ok": True,
        "html_length": len(html),
        "text_length": len(text),
        "preview": text[:1500],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "warning": (
            "TikTok's guidelines page is JavaScript-rendered. The text above is "
            "likely just the page shell, not the actual rules. You still need to "
            "manually review and update tiktok_rules.json."
        ),
    }


# Load rules (cached)
try:
    rules = load_rules(str(RULES_PATH))
except (FileNotFoundError, json.JSONDecodeError) as e:
    st.error(f"❌ Could not load tiktok_rules.json: {e}")
    st.stop()


# ---------- Header ----------

st.markdown("# 🎬 Video Compliance Checker")
st.markdown("Run any video through TikTok's rules **before** you post. "
            "Get a risk score and a list of specific issues that could get it flagged or taken down.")

# Rules metadata banner
rules_meta_html = (
    f'<div class="rules-meta">'
    f'📋 <strong>Rules version:</strong> {rules.get("version", "?")} · '
    f'<strong>Last updated:</strong> {rules.get("last_updated", "?")} · '
    f'<strong>Source:</strong> '
    f'<a href="{rules.get("source_url", "#")}" target="_blank">TikTok Community Guidelines</a>'
    f'</div>'
)
st.markdown(rules_meta_html, unsafe_allow_html=True)

with st.expander("🔄 Refresh rules from TikTok (advanced — read warning first)"):
    st.warning(
        "⚠️ **TikTok's Terms of Service prohibit automated scraping.** "
        "This button attempts to fetch their guidelines page for reference only. "
        "It will likely return a JavaScript shell, not the actual rules. "
        "You should still manually review and update `tiktok_rules.json`."
    )
    if st.button("🌐 Attempt to fetch TikTok guidelines page"):
        with st.spinner("Fetching…"):
            result = refresh_rules_from_tiktok()
        if result.get("ok"):
            st.info(
                f"Fetched {result['html_length']} bytes of HTML, "
                f"{result['text_length']} chars of text after stripping tags."
            )
            st.caption(result["warning"])
            with st.expander("Raw text preview (first 1500 chars)"):
                st.code(result["preview"], language="text")
        else:
            st.error(result["error"])

st.markdown("---")


# ---------- Step 1: Upload ----------

st.markdown("## Step 1 — Upload your video")

uploaded = st.file_uploader(
    "Choose a video file",
    type=["mp4", "mov", "webm", "avi", "mkv"],
    help="The video stays on your machine. We just read its metadata.",
)

size_limits = rules.get("size_limits", {})
MAX_MB = size_limits.get("max_mb", 287)
WARN_MB = size_limits.get("warn_mb", 72)
MAX_CAPTION = size_limits.get("max_caption_chars", 2200)
WARN_CAPTION = size_limits.get("warn_caption_chars", 1500)

video_meta = {}
if uploaded is not None:
    file_bytes = uploaded.read()
    size_mb = len(file_bytes) / (1024 * 1024)

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
        if size_mb > MAX_MB:
            st.error(f"❌ Over {MAX_MB} MB TikTok limit")
        elif size_mb > WARN_MB:
            st.warning(f"⚠️ Over {WARN_MB} MB (slower upload)")
        else:
            st.success(f"✅ Under TikTok size limit")

    st.info(f"📁 File ready: **{uploaded.name}** ({size_mb:.1f} MB). "
            "Answer the questions below to check compliance.")

st.markdown("---")


# ---------- Step 2: Answer questions ----------

st.markdown("## Step 2 — Answer these questions about the video")

content_rules = rules.get("content_rules", {})
audio_ip_rules = rules.get("audio_ip_rules", {})

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🎥 Content")

    rp = content_rules.get("real_person", {})
    has_real_person = st.radio(
        rp.get("question", "Does this video show a **real, identifiable person**?"),
        rp.get("options", ["No — fully synthetic/animated", "Yes — but with consent", "Yes — no consent"]),
        help=rp.get("help", "Deepfakes of real people without consent are banned."),
    )

    nud = content_rules.get("nudity", {})
    is_nudity = st.radio(
        nud.get("question", "Does this video contain **nudity or explicit sexual content**?"),
        nud.get("options", ["No", "Suggestive only (tease aesthetic)", "Yes — partial nudity", "Yes — explicit"]),
    )

    vio = content_rules.get("violence", {})
    is_violence = st.radio(
        vio.get("question", "Does this video contain **violence, gore, or weapons**?"),
        vio.get("options", ["No", "Mild (fitness, dance)", "Yes"]),
    )

with col2:
    st.markdown("### 🎵 Audio & IP")

    mus = audio_ip_rules.get("music_source", {})
    music_source = st.radio(
        mus.get("question", "Where is the **music/audio** from?"),
        mus.get("options", ["TikTok's licensed library", "My own original audio", "Third-party (not licensed)"]),
        help=mus.get("help", "Using unlicensed music = copyright strike."),
    )

    brd = audio_ip_rules.get("uses_brand", {})
    uses_brand = st.radio(
        brd.get("question", "Does this video promote a **brand, product, or paid partnership**?"),
        brd.get("options", ["No", "Yes — disclosed with Branded Content toggle", "Yes — not disclosed"]),
    )

    adp = audio_ip_rules.get("mentions_adult_platform", {})
    mentions_adult_platform = st.radio(
        adp.get("question", "Does the caption mention **OnlyFans, Fansly, or similar**?"),
        adp.get("options", ["No", "Soft tease only", "Direct link or explicit mention"]),
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

def run_checks(meta: dict, answers: dict, caption: str, hashtags: list[str], rules: dict) -> dict:
    issues = []
    warnings = []
    passed = []

    content_rules = rules.get("content_rules", {})
    audio_ip_rules = rules.get("audio_ip_rules", {})
    caption_rules = rules.get("caption_rules", {})

    def apply_outcome(answer: str, section: dict):
        """Look up the outcome for an answer in a rule section and append to the right list."""
        outcomes = section.get("outcomes", {})
        outcome = outcomes.get(answer)
        if not outcome:
            return
        sev = outcome.get("severity")
        if sev == "issue":
            issues.append({
                "rule": outcome["rule"],
                "detail": outcome["detail"],
                "fix": outcome["fix"],
            })
        elif sev == "warning":
            warnings.append({
                "rule": outcome["rule"],
                "detail": outcome["detail"],
                "fix": outcome["fix"],
            })
            if outcome.get("pass_message"):
                passed.append(outcome["pass_message"])
        elif sev == "pass":
            passed.append(outcome.get("message", "OK"))

    # --- Content checks ---
    apply_outcome(answers["has_real_person"], content_rules.get("real_person", {}))
    apply_outcome(answers["is_nudity"], content_rules.get("nudity", {}))
    apply_outcome(answers["is_violence"], content_rules.get("violence", {}))

    # --- Audio / IP checks ---
    apply_outcome(answers["music_source"], audio_ip_rules.get("music_source", {}))
    apply_outcome(answers["uses_brand"], audio_ip_rules.get("uses_brand", {}))
    apply_outcome(answers["mentions_adult_platform"], audio_ip_rules.get("mentions_adult_platform", {}))

    # --- Caption text checks ---
    caption_lower = (caption + " " + " ".join(hashtags)).lower()

    banned_terms = caption_rules.get("banned_terms", [])
    risky_terms = caption_rules.get("risky_terms", [])
    required_hashtags = caption_rules.get("required_hashtags", [])

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

    for req_tag in required_hashtags:
        if req_tag.lower() not in caption_lower and req_tag.lower() not in [h.lower() for h in hashtags]:
            warnings.append({
                "rule": f"Missing {req_tag} hashtag",
                "detail": f"Your branded hashtag {req_tag} is missing. This hurts community building and tracking.",
                "fix": f"Add {req_tag} to every post.",
            })
        else:
            passed.append(f"Branded {req_tag} hashtag present")

    if len(caption) > MAX_CAPTION:
        issues.append({
            "rule": "Caption too long",
            "detail": f"Caption is {len(caption)} characters. TikTok's limit is {MAX_CAPTION}.",
            "fix": f"Trim the caption to under {MAX_CAPTION} characters.",
        })
    elif len(caption) > WARN_CAPTION:
        warnings.append({
            "rule": "Caption is long",
            "detail": f"Caption is {len(caption)} characters. Very long captions get truncated in the feed.",
            "fix": f"Consider trimming to under {WARN_CAPTION} for better readability.",
        })

    # --- AI label check ---
    if caption_rules.get("ai_label_required", True) and not answers.get("ai_label_on", True):
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
        "rules_version": rules.get("version", "?"),
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
        result = run_checks(video_meta, answers, caption, hashtags, rules)

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

**Keeping rules current:** Rules live in `tiktok_rules.json` in the repo.
Edit that file and push to GitHub — Streamlit auto-redeploys in ~30 seconds.
The version banner at the top shows when rules were last updated.

**Not a guarantee:** TikTok's enforcement is partly automated and partly
human. A clean check here doesn't mean the video is 100% safe, and a
flagged check doesn't mean it will definitely be removed. Use this as
a pre-flight checklist, not a legal review.

**Sources:** [TikTok Community Guidelines](https://www.tiktok.com/community-guidelines) ·
[TikTok Help Center](https://support.tiktok.com/en/using-tiktok)
    """
)
