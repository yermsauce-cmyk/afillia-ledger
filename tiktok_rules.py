"""
TikTok Rules & Regulations — quick reference for @afillia.

A plain, readable summary of TikTok's Community Guidelines as they apply
to a synthetic AI creator account. No scraping, no LLM, no pipeline —
just the rules you need to know before posting.

Sources:
- https://www.tiktok.com/community-guidelines
- https://support.tiktok.com/en/using-tiktok
- https://newsroom.tiktok.com/en-us
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="TikTok Rules — Afillia",
    page_icon="📋",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background: #0a0a0f; color: #ffffff; }
    .rule-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .rule-card h3 { margin-top: 0; color: #ff006e; }
    .ok { color: #06d6a0; font-weight: bold; }
    .warn { color: #ffbe0b; font-weight: bold; }
    .no { color: #ff006e; font-weight: bold; }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-right: 0.4rem;
    }
    .badge-ok { background: #06d6a0; color: black; }
    .badge-warn { background: #ffbe0b; color: black; }
    .badge-no { background: #ff006e; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("# 📋 TikTok Rules & Regulations — Quick Reference")
st.markdown("Everything you need to know before posting as **@afillia**. "
            "No scraping, no LLM — just the rules.")
st.markdown("---")


# ---------- The Big Picture ----------

st.markdown("## 🎯 The Big Picture")

st.markdown(
    """
<div class="rule-card">
<h3>What TikTok cares about</h3>
<p>TikTok's Community Guidelines are built around <strong>four pillars</strong>:</p>
<ul>
<li><strong>Safety</strong> — no harm to people (especially minors)</li>
<li><strong>Authenticity</strong> — no deception, no spam, no fake engagement</li>
<li><strong>Privacy</strong> — no doxxing, no non-consensual imagery</li>
<li><strong>IP & legality</strong> — no copyright violations, no illegal activity</li>
</ul>
<p>If your post violates any of these, it gets removed. Repeat violations = shadowban or ban.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- AI / Synthetic Content ----------

st.markdown("## 🤖 AI & Synthetic Content (Most Important for @afillia)")

st.markdown(
    """
<div class="rule-card">
<h3>AI-generated content MUST be labeled</h3>
<p><span class="badge badge-warn">REQUIRED</span> TikTok requires you to <strong>turn on the AI-generated content label</strong> on every post that contains realistic AI images, video, or audio.</p>
<ul>
<li>Use the in-app toggle when uploading: <em>"AI-generated content"</em></li>
<li>If you use a third-party tool (Grok, Stable Diffusion, etc.), still label it</li>
<li>Realistic deepfakes of real people are <span class="no">BANNED</span></li>
<li>Synthetic faces (like Afillia) are allowed <strong>only with the label on</strong></li>
</ul>
<p><strong>For @afillia:</strong> Every single post must have the AI label enabled. No exceptions.</p>
</div>

<div class="rule-card">
<h3>What counts as "realistic" AI</h3>
<ul>
<li><span class="no">BANNED:</span> Deepfakes of real, identifiable people without consent</li>
<li><span class="warn">REQUIRES LABEL:</span> Realistic AI faces that could be mistaken for a real person</li>
<li><span class="ok">OK:</span> Clearly stylized AI art, animation, obvious synthetic characters</li>
<li><span class="ok">OK:</span> AI-assisted editing (color grading, effects) on real footage</li>
</ul>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- NSFW / Adult Content ----------

st.markdown("## 🔞 NSFW & Adult Content")

st.markdown(
    """
<div class="rule-card">
<h3>What's allowed vs. banned</h3>
<ul>
<li><span class="no">BANNED:</span> Nudity, sexual acts, explicit pornographic content</li>
<li><span class="no">BANNED:</span> Sexually suggestive content involving minors (zero tolerance)</li>
<li><span class="warn">RESTRICTED (18+ only):</span> Suggestive content — must be age-gated</li>
<li><span class="warn">RESTRICTED:</span> Content that "depicts sexual activities" even without nudity</li>
<li><span class="ok">OK:</span> Dance, fitness, fashion, lifestyle content with sensual aesthetic</li>
</ul>
<p><strong>For @afillia:</strong> Tease aesthetic is fine. Actual nudity or explicit sexual content will get you banned immediately. Keep it suggestive, not explicit.</p>
</div>

<div class="rule-card">
<h3>The "tease" line</h3>
<p>TikTok's policy is roughly: <strong>"suggestive is OK, explicit is not."</strong></p>
<ul>
<li>✅ Outfit reveals, dance transitions, fitness glow-ups, dark/luxury aesthetic</li>
<li>⚠️ Lingering shots of cleavage/bottoms, simulated acts, "accidental" exposure</li>
<li>❌ Nudity, sexual acts, genitals, explicit text describing sex</li>
</ul>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Hashtags ----------

st.markdown("## #️⃣ Hashtags")

st.markdown(
    """
<div class="rule-card">
<h3>Hashtag rules</h3>
<ul>
<li><span class="no">BANNED:</span> Using banned/shadowbanned hashtags tanks your reach</li>
<li><span class="warn">RISKY:</span> Overly generic tags like #fyp, #foryou are deprioritized</li>
<li><span class="ok">BEST:</span> 3–5 niche-specific hashtags per post</li>
<li><span class="ok">OK:</span> Branded hashtags (#Afilla) build community</li>
</ul>
<p><strong>For @afillia:</strong> Always include <code>#Afilla</code>. Rotate from
<code>#SyntheticSeduction</code>, <code>#AIMuse</code>, <code>#MiamiVibes</code>,
<code>#NSFWTease</code>. Research trending tags weekly — never reuse banned ones.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Automation ----------

st.markdown("## ⚙️ Automation & Bots")

st.markdown(
    """
<div class="rule-card">
<h3>What gets you flagged</h3>
<ul>
<li><span class="no">BANNED:</span> Automated posting, bot followers, fake engagement</li>
<li><span class="no">BANNED:</span> Buying likes, views, followers, or comments</li>
<li><span class="warn">RISKY:</span> Posting more than 3–5x/day looks bot-like</li>
<li><span class="warn">RISKY:</span> Copy-pasting the same comment across many videos</li>
<li><span class="ok">OK:</span> Scheduling tools (Later, Buffer) for manual review posts</li>
<li><span class="ok">OK:</span> Replying to comments within an hour (boosts reach)</li>
</ul>
<p><strong>For @afillia:</strong> 3–5 posts/week is the sweet spot. Engage replies within 1 hour. Never use bots.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Monetization ----------

st.markdown("## 💰 Monetization & Commercial Content")

st.markdown(
    """
<div class="rule-card">
<h3>If you make money from TikTok</h3>
<ul>
<li><span class="warn">REQUIRED:</span> Disclose paid partnerships, gifted content, affiliate links</li>
<li><span class="warn">REQUIRED:</span> Use TikTok's "Branded Content" toggle when promoting</li>
<li><span class="no">BANNED:</span> Promoting other adult platforms (OnlyFans, Fansly) directly in TikTok bio/posts</li>
<li><span class="warn">RISKY:</span> Linking to Fanvue/OnlyFans in bio is tolerated but can limit reach</li>
<li><span class="ok">OK:</span> Soft teasers ("exclusive content on my page") without direct links</li>
</ul>
<p><strong>For @afillia:</strong> Cross-promote to Fanvue max 1x/week. Never put a direct link in every post. Use the "exclusive content" tease pattern.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- LIVE ----------

st.markdown("## 🔴 LIVE Streaming")

st.markdown(
    """
<div class="rule-card">
<h3>Going LIVE</h3>
<ul>
<li>Must be <strong>16+</strong> to go LIVE (18+ for gifts/monetization)</li>
<li><span class="warn">RESTRICTED:</span> LIVE content is held to a <strong>higher standard</strong> than regular posts</li>
<li><span class="no">BANNED:</span> Nudity, sexual content, violence on LIVE</li>
<li><span class="ok">OK:</span> Q&A, behind-the-scenes, dance, fitness sessions</li>
</ul>
<p><strong>For @afillia:</strong> LIVE is high-risk for a synthetic creator. If you go LIVE, keep it PG-13 — no suggestive content that would be borderline on a regular post.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Bans & Shadowbans ----------

st.markdown("## 🚫 Bans & Shadowbans")

st.markdown(
    """
<div class="rule-card">
<h3>How TikTok enforces</h3>
<ul>
<li><strong>Strike 1:</strong> Post removed, warning issued</li>
<li><strong>Strike 2:</strong> Temporary feature restriction (can't comment, can't go LIVE)</li>
<li><strong>Strike 3:</strong> Permanent ban</li>
<li><strong>Shadowban:</strong> Not officially communicated — your content just stops reaching anyone</li>
</ul>
<p><strong>Common shadowban triggers:</strong></p>
<ul>
<li>Sudden spike in activity (posting 10x in an hour)</li>
<li>Mass following/unfollowing</li>
<li>Using banned hashtags</li>
<li>Reposting flagged content</li>
<li>Reports from other users (even false ones)</li>
</ul>
<p><strong>Recovery:</strong> Shadowbans usually lift in 1–2 weeks if you stop the triggering behavior. Permanent bans can be appealed once.</p>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Quick Checklist ----------

st.markdown("## ✅ Pre-Post Checklist (Save This)")

st.markdown(
    """
<div class="rule-card">
<h3>Before you hit "Post"</h3>
<ul>
<li>☐ AI-generated content label is <strong>ON</strong></li>
<li>☐ Caption includes <code>#Afilla</code></li>
<li>☐ No banned terms (deepfake, real person, revenge, minor, underage, non-consensual)</li>
<li>☐ No risky terms without context (nsfw, onlyfans, fanvue, leaked)</li>
<li>☐ Caption is under 2200 characters</li>
<li>☐ Content is suggestive, not explicit</li>
<li>☐ No real-person deepfakes</li>
<li>☐ No copyrighted music you don't have rights to</li>
<li>☐ Hashtags are 3–5, niche-specific, not banned</li>
<li>☐ You're not posting more than 1x today</li>
</ul>
</div>
    """,
    unsafe_allow_html=True,
)


# ---------- Footer ----------

st.markdown("---")
st.markdown(
    """
**Sources:**
- [TikTok Community Guidelines](https://www.tiktok.com/community-guidelines)
- [TikTok Help Center](https://support.tiktok.com/en/using-tiktok)
- [TikTok Newsroom](https://newsroom.tiktok.com/en-us)

*Last reviewed: 2026-07-11. TikTok updates these rules frequently — check the official sources monthly.*
    """
)
