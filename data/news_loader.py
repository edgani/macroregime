from __future__ import annotations
from typing import Dict, List
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus
from datetime import datetime, timezone
import json
import os
import requests

from config.settings import LIVE_FETCH_ENABLED, NEWS_CACHE_TTL_SECONDS
from utils.streamlit_compat import st

# ---------------------------------------------------------------------------
# News search queries — expanded for better geopolitical/macro coverage
# ---------------------------------------------------------------------------
_NEWS_QUERIES = [
    ("war_oil",        "Iran OR Hormuz OR oil shock OR Middle East war site:reuters.com"),
    ("ceasefire",      "ceasefire OR truce OR de-escalation OR peace talks OR pause in strikes site:reuters.com"),
    ("trade_policy",   "tariff OR trade war OR sanctions OR export controls site:reuters.com"),
    ("rates_treasury", "Treasury yields OR refunding OR long-end pressure OR bond selloff site:reuters.com"),
    ("fed_inflation",  "Fed OR inflation OR CPI OR PCE OR rate decision site:reuters.com"),
    ("china_macro",    "China stimulus OR PBOC OR yuan OR China growth OR China recession site:reuters.com"),
    ("credit_stress",  "credit spread OR IG spread OR HY spread OR default risk OR bankruptcy site:reuters.com"),
]


def _parse_rss(xml_text: str) -> List[Dict[str, str]]:
    root = ET.fromstring(xml_text)
    out: List[Dict[str, str]] = []
    for item in root.findall(".//item")[:10]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title:
            out.append({"title": title, "link": link, "published": pub})
    return out


def _get_anthropic_api_key() -> str | None:
    """Try multiple sources for the Anthropic API key."""
    # 1. Environment variable (preferred for production)
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    # 2. Streamlit secrets
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", "").strip()
        if key:
            return key
    except Exception:
        pass
    return None


def _analyze_with_claude(headlines: List[Dict[str, str]], api_key: str) -> Dict[str, object]:
    """Use Claude to semantically analyze headlines for macro regime implications.

    Returns a structured assessment of event type, macro variable impacts,
    regime shift probability, and front-run signal quality.
    """
    if not headlines:
        return {}

    headline_text = "\n".join(f"- {h['title']}" for h in headlines[:15])

    system_prompt = (
        "You are a macro economist and quantitative analyst specializing in "
        "macro regime analysis. Your job is to assess how current news affects "
        "growth and inflation trajectories and regime transition probabilities. "
        "Be concise, quantitative, and regime-focused. Never speculate beyond what "
        "the headlines support. Respond ONLY with valid JSON — no markdown, no preamble."
    )

    user_prompt = f"""Analyze these financial news headlines for macro regime implications.

Headlines:
{headline_text}

Respond with EXACTLY this JSON structure (all fields required):
{{
  "dominant_event_type": "geopolitical|policy|commodity|credit|growth|inflation|currency|mixed",
  "regime_impact": {{
    "growth_direction": "accelerating|decelerating|neutral",
    "inflation_direction": "accelerating|decelerating|neutral",
    "growth_magnitude": 0.0,
    "inflation_magnitude": 0.0
  }},
  "quad_shift_risk": {{
    "toward": "Q1|Q2|Q3|Q4|none",
    "probability": 0.0,
    "timeframe_weeks": 4
  }},
  "event_specific": {{
    "oil_shock_active": false,
    "war_escalation": false,
    "policy_pivot": false,
    "credit_stress": false,
    "supply_chain_disruption": false,
    "ceasefire_or_relief": false,
    "china_stimulus": false,
    "tariff_escalation": false
  }},
  "front_run_signal": {{
    "action_window_days": 7,
    "confidence": 0.0,
    "what_to_watch": "brief description of next catalyst to confirm or deny this scenario"
  }},
  "news_dominant_state": "war_oil|policy_pressure|deescalation_watch|deescalation_confirmed|oil_shock_fading|credit_stress|quiet",
  "summary": "1-2 sentence summary of macro regime implications"
}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",   # fast and cheap for news scan
                "max_tokens": 800,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"].strip()
        # Strip potential markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {}


def _keyword_fallback(all_items: List[Dict[str, str]]) -> Dict[str, object]:
    """Keyword-based fallback when Claude API is unavailable.
    More comprehensive than original — added more signal words.
    """
    text_blob = " || ".join(x["title"].lower() for x in all_items)

    escalation_words = ["strike", "attack", "war", "escalat", "threat", "retaliat", "sanction", "tariff", "surge", "spike", "bomb", "missile", "invad"]
    relief_words = ["ceasefire", "de-escalat", "talk", "truce", "pause", "withdraw", "moderat", "deal", "peace", "cooling", "easing", "agreement"]
    oil_words = ["oil", "hormuz", "energy", "opec", "crude", "petroleum", "brent", "wti"]
    rates_words = ["yield", "treasury", "refunding", "long-end", "bond selloff", "rate hike", "basis points", "fed funds"]
    dollar_words = ["dollar", "usd", "dxy", "greenback"]
    china_words = ["china", "pboc", "yuan", "renminbi", "beijing", "chinese economy"]
    credit_words = ["credit spread", "hy spread", "default", "bankruptcy", "distress", "cds"]

    esc = sum(w in text_blob for w in escalation_words)
    rel = sum(w in text_blob for w in relief_words)
    oil = sum(w in text_blob for w in oil_words)
    rates = sum(w in text_blob for w in rates_words)
    usd = sum(w in text_blob for w in dollar_words)
    china = sum(w in text_blob for w in china_words)
    credit = sum(w in text_blob for w in credit_words)

    if esc >= 3 and esc > rel:
        state = "escalating"
    elif rel >= 2 and rel >= esc:
        state = "de_escalating"
    elif all_items:
        state = "active"
    else:
        state = "quiet"

    return {
        "counts": {
            "escalation": esc,
            "relief": rel,
            "oil": oil,
            "rates": rates,
            "usd": usd,
            "china": china,
            "credit": credit,
        },
        "state": state,
        "claude_analysis": None,
    }


@st.cache_data(ttl=NEWS_CACHE_TTL_SECONDS, show_spinner=False)
def load_news_signals(*, force_refresh: bool = False) -> Dict[str, object]:
    """Load and analyze news signals.

    Pipeline:
    1. Fetch RSS headlines from Google News for each topic query
    2. Attempt Claude semantic analysis (requires ANTHROPIC_API_KEY)
    3. Fall back to keyword counting if Claude unavailable
    4. Return structured news state for NewsEventEngine consumption
    """
    if not LIVE_FETCH_ENABLED:
        return {
            "state": "quiet",
            "counts": {"escalation": 0, "relief": 0, "oil": 0, "rates": 0, "usd": 0, "china": 0, "credit": 0},
            "groups": {k: [] for k, _ in _NEWS_QUERIES},
            "top_headlines": [],
            "claude_analysis": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ----------------------------------------------------------------
    # Step 1: Fetch RSS headlines
    # ----------------------------------------------------------------
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    grouped: Dict[str, List[Dict[str, str]]] = {k: [] for k, _ in _NEWS_QUERIES}
    for key, query in _NEWS_QUERIES:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = session.get(url, timeout=5)
            resp.raise_for_status()
            grouped[key] = _parse_rss(resp.text)
        except Exception:
            grouped[key] = []

    all_items = [x for items in grouped.values() for x in items]
    top_headlines = all_items[:12]

    # ----------------------------------------------------------------
    # Step 2: Keyword fallback (always computed — baseline)
    # ----------------------------------------------------------------
    fallback = _keyword_fallback(all_items)
    counts = fallback["counts"]
    state = fallback["state"]

    # ----------------------------------------------------------------
    # Step 3: Claude semantic analysis (upgrade when API key available)
    # ----------------------------------------------------------------
    claude_analysis: Dict[str, object] | None = None
    api_key = _get_anthropic_api_key()
    if api_key and top_headlines:
        claude_analysis = _analyze_with_claude(top_headlines, api_key)
        # If Claude succeeded, use its dominant state (more accurate)
        if claude_analysis and isinstance(claude_analysis.get("news_dominant_state"), str):
            state = claude_analysis["news_dominant_state"]

    return {
        "state": state,
        "counts": counts,
        "groups": grouped,
        "top_headlines": top_headlines,
        "claude_analysis": claude_analysis,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
