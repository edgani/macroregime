"""engines/ai_engine.py — Autonomous Intelligence Layer

Uses Claude API (claude-haiku-4-5) to continuously discover:
  - New investment narratives from latest macro data + news
  - New supply chain bottlenecks
  - Fresh alpha ideas aligned with current Quad regime
  - Scenario updates based on geopolitical/economic developments

ARCHITECTURE:
  1. Collect context: Quad regime + FRED signals + price performance + yfinance news headlines
  2. Call Claude API with structured prompt (JSON output)
  3. Parse + validate output
  4. Cache for 6 hours (same TTL as snapshot)
  5. If API unavailable → fall back to regex NLP engine (no crash)

RELIABILITY ON STREAMLIT CLOUD:
  - Always works when ANTHROPIC_API_KEY set in Streamlit Secrets
  - Set via: App Settings → Secrets → ANTHROPIC_API_KEY = "sk-ant-..."
  - Automatic 6h refresh = new analysis every time snapshot rebuilds
  - If API call fails → graceful degradation to fallback content
  - Rate limit: ~2-4 calls per rebuild = well within Haiku limits

TOKEN USAGE (estimated per rebuild):
  - Input: ~2000-3000 tokens (context + prompt)
  - Output: ~1000-1500 tokens (JSON analysis)
  - Cost at claude-haiku-4-5: ~$0.002-0.004 per rebuild
  - 6h refresh × 30 days = ~120 calls/month ≈ $0.25-0.50/month
"""
from __future__ import annotations

import json
import math
import logging
import os
import time
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Cache ──────────────────────────────────────────────────────────────────────
_AI_CACHE: Dict = {}
_AI_CACHE_TS: float = 0.0
_AI_CACHE_TTL: float = 6 * 3600  # 6 hours

# ── Model config ──────────────────────────────────────────────────────────────
MODEL        = "claude-haiku-4-5-20251001"  # Fast + cheap for batch analysis
MAX_TOKENS   = 2500
TIMEOUT_SEC  = 45  # Long enough for structured output

# ── News tickers to monitor ───────────────────────────────────────────────────
NEWS_TICKERS = [
    # Macro bellwethers
    "SPY","QQQ","TLT","GLD","SLV","DX-Y.NYB","^VIX",
    # Q2/Q3 key plays
    "XLE","OIH","GDX","GDXJ","SLV","IBIT","JPXN","EIS",
    # Bottleneck proxies
    "LITE","COHR","WOLF","ON","VST","CEG","ETN","VRT",
    # Indonesia
    "EIDO",
    # Defense
    "ITA","LMT","KTOS",
    # Energy
    "BNO","CL=F","BZ=F",
    # Broad macro
    "IWM","HYG","EEM",
]
MAX_HEADLINES = 40  # Cap total headlines sent to Claude


def _get_api_key() -> Optional[str]:
    """Get Claude API key from Streamlit secrets or environment."""
    # Try Streamlit secrets first
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
        if key: return str(key)
    except Exception:
        pass
    # Fall back to environment variable
    return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("anthropic_api_key")


def _fetch_news_headlines(tickers: List[str], max_per_ticker: int = 3) -> List[str]:
    """
    Fetch recent news headlines from yfinance.
    Returns list of clean headline strings.
    Free, no API key needed.
    """
    headlines = []
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                yt = yf.Ticker(ticker)
                news = yt.news or []
                for item in news[:max_per_ticker]:
                    title = item.get("title","") or item.get("headline","")
                    if title and len(title) > 10:
                        headlines.append(f"[{ticker}] {title}")
                    if len(headlines) >= max_per_ticker * len(tickers):
                        break
            except Exception:
                continue
            if len(headlines) >= MAX_HEADLINES:
                break
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
    return headlines[:MAX_HEADLINES]


def _price_performance(prices: Dict[str, pd.Series], tickers: List[str]) -> Dict[str, Dict]:
    """Compute recent price performance for context."""
    result = {}
    for ticker in tickers:
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 5: continue
        try:
            r5  = float(s.iloc[-1]/s.iloc[-6]-1)  if len(s)>=6 else None
            r21 = float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else None
            r63 = float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
            result[ticker] = {
                "5d":  f"{r5:+.1%}"  if r5  is not None else "—",
                "1m":  f"{r21:+.1%}" if r21 is not None else "—",
                "3m":  f"{r63:+.1%}" if r63 is not None else "—",
                "px":  f"{float(s.iloc[-1]):.2f}",
            }
        except Exception:
            continue
    return result


def _build_prompt(
    sq: str, mq: str, gq: str,
    gip_features: Dict,
    headlines: List[str],
    perf: Dict[str, Dict],
) -> str:
    """Build the Claude prompt for autonomous macro analysis."""

    QUAD_CONTEXT = {
        "Q1":"Goldilocks (Growth↑ Inflation↓) — Tech, Small Caps, Crypto win",
        "Q2":"Reflation (Growth↑ Inflation↑) — Energy, Commodities, International win",
        "Q3":"Stagflation (Growth↓ Inflation↑) — Gold, Silver, Defensives win. Tech loses.",
        "Q4":"Deflation (Growth↓ Inflation↓) — Bonds, Gold, Utilities win. Everything else loses.",
    }

    gm = gip_features.get("growth_momentum",0)
    im = gip_features.get("inflation_momentum",0)
    ps = gip_features.get("policy_score",0)

    # Format price performance for prompt
    perf_lines = []
    for t, d in sorted(perf.items(), key=lambda x: x[0]):
        perf_lines.append(f"  {t}: 5d={d.get('5d','—')} 1m={d.get('1m','—')} 3m={d.get('3m','—')}")
    perf_str = "\n".join(perf_lines[:25]) if perf_lines else "  No price data"

    news_str = "\n".join(f"  {h}" for h in headlines) if headlines else "  No recent news available"

    prompt = f"""You are a Hedgeye-style quantitative macro research analyst. Analyze the current environment and identify actionable investment opportunities.

CURRENT MACRO REGIME:
  Structural (Quarterly): {sq} — {QUAD_CONTEXT.get(sq,sq)}
  Monthly (3-6 weeks):    {mq} — {QUAD_CONTEXT.get(mq,mq)}
  Global (50 countries):  {gq} — {QUAD_CONTEXT.get(gq,gq)}

KEY ECONOMIC SIGNALS:
  Growth momentum:     {gm:+.2%} ({'accelerating' if gm>0 else 'decelerating'})
  Inflation momentum:  {im:+.2%} ({'rising' if im>0 else 'cooling'})
  Central bank stance: {'Dovish' if (ps or 0)>0.05 else 'Hawkish' if (ps or 0)<-0.05 else 'Neutral'}

RECENT PRICE PERFORMANCE (key assets):
{perf_str}

RECENT NEWS HEADLINES (last 24-48 hours):
{news_str}

TASK: Based on the regime, price action, and latest news, generate a JSON analysis with FOUR sections.

RULES:
1. Only recommend assets that make sense in the current Quad ({sq} structural, {mq} monthly).
2. In Q3: Tech/XLK/MAGS are WORST. Gold/Silver/Defensives are BEST.
3. In Q2 monthly overlay: Energy offense (OIH/BNO/XOP), International (JPXN/EIS/TUR), Commodities OK.
4. Bitcoin: Long in Q1/Q2/Q3. Exit ONLY in Q4.
5. Every narrative must have a clear invalidation condition.
6. Bottlenecks = supply constraint + rising demand. Must have real scarcity.
7. Alpha ideas = specific, actionable, with clear thesis tied to regime.
8. Confidence scores must be realistic (0.5-0.95 range).

OUTPUT: Return ONLY valid JSON in this exact format:

{{
  "narratives": [
    {{
      "name": "Theme name (4-6 words)",
      "score": 0.0,
      "stage": "active|building|brewing",
      "thesis": "2 sentences max. What is happening and why does it matter?",
      "regime_bias": "Q1|Q2|Q3|Q4|ALL",
      "tickers": ["TICK1","TICK2","TICK3"],
      "best": ["TICK1","TICK2"],
      "worst": ["TICK3"],
      "invalidators": ["Condition that breaks this thesis"],
      "news_catalyst": "Specific recent headline driving this"
    }}
  ],
  "bottlenecks": [
    {{
      "name": "Bottleneck name",
      "constraint": 0.0,
      "sector": "ai_optics|energy_infra|precious_metals|defense|etc",
      "thesis": "What is scarce and why?",
      "beneficiary_tickers": ["TICK1","TICK2"],
      "fade_tickers": ["TICK3"],
      "time_horizon": "months",
      "confidence": 0.0,
      "stage": "active|building|brewing"
    }}
  ],
  "alpha_ideas": [
    {{
      "ticker": "TICK",
      "name": "Company/ETF name",
      "direction": "long|short",
      "confidence": 0.0,
      "stage": "active|building|brewing",
      "thesis": "2 sentences. Why now, why this regime?",
      "regime_fit": "Explain why this works in current {sq}/{mq} regime",
      "category": "Bottleneck|Macro Rotation|Options Flow|Narrative|Technical",
      "invalidators": ["What breaks the thesis"]
    }}
  ],
  "scenario_update": {{
    "headline_risk": "Describe the biggest near-term risk from recent news in 1 sentence",
    "opportunity": "Describe the biggest near-term opportunity in 1 sentence",
    "regime_change_signal": "What data point would trigger a regime shift?",
    "base_case_intact": true
  }}
}}

Generate 3-5 narratives, 2-4 bottlenecks, 3-5 alpha ideas. Make them specific and actionable.
Prioritize ideas that are directly driven by recent news headlines above."""

    return prompt


def _call_claude(prompt: str, api_key: str) -> Optional[Dict]:
    """Call Claude API and parse JSON response."""
    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role":"user","content": prompt}],
            "temperature": 0.3,  # Low temperature for factual analysis
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Extract text from response
        raw = ""
        for block in data.get("content",[]):
            if block.get("type") == "text":
                raw += block.get("text","")

        # Parse JSON
        raw = raw.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Claude JSON parse error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Claude API call failed: {e}")
        return None


def _validate_output(data: Dict) -> Dict:
    """Validate and clean Claude's output. Ensure all required fields present."""
    clean = {}

    # Narratives
    narr = []
    for n in (data.get("narratives") or []):
        if not isinstance(n, dict): continue
        if not n.get("name") or not n.get("thesis"): continue
        narr.append({
            "name": str(n.get("name",""))[:60],
            "score": max(0.0, min(1.0, float(n.get("score",0.7)))),
            "stage": str(n.get("stage","brewing")) if n.get("stage") in ("active","building","brewing") else "brewing",
            "thesis": str(n.get("thesis",""))[:300],
            "regime_bias": str(n.get("regime_bias","ALL")),
            "tickers": [str(t) for t in (n.get("tickers") or [])[:10]],
            "best": [str(t) for t in (n.get("best") or [])[:6]],
            "worst": [str(t) for t in (n.get("worst") or [])[:4]],
            "invalidators": [str(i) for i in (n.get("invalidators") or [])[:3]],
            "news_catalyst": str(n.get("news_catalyst",""))[:200],
            "ai_generated": True,
        })
    clean["narratives"] = narr[:6]

    # Bottlenecks
    btks = []
    for b in (data.get("bottlenecks") or []):
        if not isinstance(b, dict): continue
        if not b.get("name"): continue
        btks.append({
            "name": str(b.get("name",""))[:60],
            "constraint": max(0.0, min(1.0, float(b.get("constraint",0.7)))),
            "sector": str(b.get("sector","generic")),
            "thesis": str(b.get("thesis",""))[:300],
            "beneficiary_tickers": [str(t) for t in (b.get("beneficiary_tickers") or [])[:8]],
            "fade_tickers": [str(t) for t in (b.get("fade_tickers") or [])[:4]],
            "time_horizon": str(b.get("time_horizon","weeks")),
            "confidence": max(0.0, min(1.0, float(b.get("confidence",0.7)))),
            "stage": str(b.get("stage","brewing")) if b.get("stage") in ("active","building","brewing") else "brewing",
            "ai_generated": True,
        })
    clean["bottlenecks"] = btks[:5]

    # Alpha ideas
    ideas = []
    for a in (data.get("alpha_ideas") or []):
        if not isinstance(a, dict): continue
        if not a.get("ticker") or not a.get("thesis"): continue
        ideas.append({
            "name": str(a.get("name",a.get("ticker","")))[:60],
            "ticker": str(a.get("ticker","")).upper(),
            "direction": "short" if str(a.get("direction","long")).lower()=="short" else "long",
            "confidence": max(0.0, min(1.0, float(a.get("confidence",0.7)))),
            "stage": str(a.get("stage","brewing")) if a.get("stage") in ("active","building","brewing") else "brewing",
            "thesis": str(a.get("thesis",""))[:300],
            "regime_fit": str(a.get("regime_fit",""))[:200],
            "category": str(a.get("category","Macro Rotation")),
            "invalidators": [str(i) for i in (a.get("invalidators") or [])[:3]],
            "ai_generated": True,
        })
    clean["alpha_ideas"] = ideas[:6]

    # Scenario update
    su = data.get("scenario_update") or {}
    clean["scenario_update"] = {
        "headline_risk":      str(su.get("headline_risk",""))[:300],
        "opportunity":        str(su.get("opportunity",""))[:300],
        "regime_change_signal": str(su.get("regime_change_signal",""))[:300],
        "base_case_intact":   bool(su.get("base_case_intact",True)),
    }

    return clean


class AIEngine:
    """
    Autonomous macro intelligence engine.
    Calls Claude API every 6 hours to generate fresh:
      - Investment narratives (from news + regime)
      - Bottleneck alerts (supply constraint detection)
      - Alpha ideas (regime-aligned trade setups)
      - Scenario updates (geopolitical/macro developments)

    Usage:
        engine = AIEngine()
        result = engine.run(
            sq="Q3", mq="Q2", gq="Q3",
            gip_features={...},
            prices={...},
        )

    Always returns a dict. Never raises an exception.
    Falls back to {"ok": False, "reason": "..."} if API unavailable.
    """

    def __init__(self, cache_ttl: float = _AI_CACHE_TTL):
        self.cache_ttl = cache_ttl

    def run(
        self,
        sq: str,
        mq: str,
        gq: str,
        gip_features: Dict,
        prices: Dict[str, pd.Series],
        force_refresh: bool = False,
    ) -> Dict:
        """
        Main entry point. Returns dict with narratives, bottlenecks, alpha_ideas, scenario_update.
        Cached for 6 hours. Thread-safe for Streamlit.
        """
        global _AI_CACHE, _AI_CACHE_TS

        # Check cache
        if not force_refresh and _AI_CACHE and (time.time() - _AI_CACHE_TS) < self.cache_ttl:
            logger.info("AIEngine: serving from cache")
            return {**_AI_CACHE, "from_cache": True}

        # Get API key
        api_key = _get_api_key()
        if not api_key:
            logger.warning("AIEngine: ANTHROPIC_API_KEY not set. Add to Streamlit Secrets.")
            return {
                "ok": False,
                "reason": "ANTHROPIC_API_KEY not configured. Add to Streamlit Secrets.",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        logger.info("AIEngine: fetching fresh analysis from Claude...")
        t0 = time.time()

        # 1. Collect news headlines
        headlines = _fetch_news_headlines(NEWS_TICKERS, max_per_ticker=3)
        logger.info(f"AIEngine: fetched {len(headlines)} headlines")

        # 2. Compute price performance for context
        perf = _price_performance(prices, NEWS_TICKERS)

        # 3. Build prompt
        prompt = _build_prompt(sq, mq, gq, gip_features, headlines, perf)

        # 4. Call Claude
        raw = _call_claude(prompt, api_key)
        if raw is None:
            logger.warning("AIEngine: Claude call failed or returned unparseable response")
            return {
                "ok": False,
                "reason": "Claude API call failed. Check logs.",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        # 5. Validate + clean
        result = _validate_output(raw)
        result["ok"] = True
        result["elapsed"] = round(time.time() - t0, 1)
        result["headlines_used"] = len(headlines)
        result["generated_at"] = time.time()
        result["model"] = MODEL

        # 6. Cache
        _AI_CACHE = result
        _AI_CACHE_TS = time.time()

        logger.info(f"AIEngine: generated {len(result.get('narratives',[]))} narratives, "
                    f"{len(result.get('bottlenecks',[]))} bottlenecks, "
                    f"{len(result.get('alpha_ideas',[]))} alpha ideas "
                    f"in {result['elapsed']}s")

        return result
