"""engines/ai_engine.py — Autonomous Intelligence Layer (GEMINI VERSION)"""
from __future__ import annotations

import json
import math
import logging
import os
import time
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

_AI_CACHE: Dict = {}
_AI_CACHE_TS: float = 0.0
_AI_CACHE_TTL: float = 6 * 3600

MODEL = "gemini-2.5-pro-preview-03-25"
MAX_TOKENS = 8192
TIMEOUT_SEC = 60

NEWS_TICKERS = [
    "SPY","QQQ","TLT","GLD","SLV","DX-Y.NYB","^VIX",
    "XLE","OIH","GDX","GDXJ","SLV","IBIT","JPXN","EIS",
    "LITE","COHR","WOLF","ON","VST","CEG","ETN","VRT",
    "EIDO","ITA","LMT","KTOS","BNO","CL=F","BZ=F",
    "IWM","HYG","EEM",
]
MAX_HEADLINES = 40

def _get_api_key() -> Optional[str]:
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("gemini_api_key")
        if key:
            logger.info(f"AIEngine: GEMINI_API_KEY found in Streamlit secrets (len={len(str(key))})")
            return str(key)
    except Exception as e:
        logger.warning(f"AIEngine: Streamlit secrets error: {e}")
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("gemini_api_key")
    if env_key:
        logger.info(f"AIEngine: GEMINI_API_KEY found in env (len={len(str(env_key))})")
    else:
        logger.warning("AIEngine: GEMINI_API_KEY NOT found in secrets or env")
    return env_key

def _fetch_news_headlines(tickers: List[str], max_per_ticker: int = 3) -> List[str]:
    headlines = []
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                yt = yf.Ticker(ticker)
                news = yt.news or []
                for item in news[:max_per_ticker]:
                    title = item.get("title", "") or item.get("headline", "")
                    if title and len(title) > 10:
                        headlines.append(f"[{ticker}] {title}")
                    if len(headlines) >= MAX_HEADLINES:
                        break
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
    logger.info(f"AIEngine: fetched {len(headlines)} headlines")
    return headlines[:MAX_HEADLINES]

def _price_performance(prices: Dict[str, pd.Series], tickers: List[str]) -> Dict[str, Dict]:
    result = {}
    for ticker in tickers:
        s = prices.get(ticker)
        if s is None:
            continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 5:
            continue
        try:
            r5 = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else None
            r21 = float(s.iloc[-1] / s.iloc[-22] - 1) if len(s) >= 22 else None
            r63 = float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else None
            result[ticker] = {
                "5d": f"{r5:+.1%}" if r5 is not None else "—",
                "1m": f"{r21:+.1%}" if r21 is not None else "—",
                "3m": f"{r63:+.1%}" if r63 is not None else "—",
                "px": f"{float(s.iloc[-1]):.2f}",
            }
        except Exception:
            continue
    return result

def _build_prompt(sq: str, mq: str, gq: str, gip_features: Dict, headlines: List[str], perf: Dict) -> str:
    QUAD_CONTEXT = {
        "Q1": "Goldilocks (Growth↑ Inflation↓) — Tech, Small Caps, Crypto win",
        "Q2": "Reflation (Growth↑ Inflation↑) — Energy, Commodities, International win",
        "Q3": "Stagflation (Growth↓ Inflation↑) — Gold, Silver, Defensives win. Tech loses.",
        "Q4": "Deflation (Growth↓ Inflation↓) — Bonds, Gold, Utilities win. Everything else loses.",
    }
    gm = gip_features.get("growth_momentum", 0)
    im = gip_features.get("inflation_momentum", 0)
    ps = gip_features.get("policy_score", 0)

    perf_lines = []
    for t, d in sorted(perf.items(), key=lambda x: x[0]):
        perf_lines.append(f" {t}: 5d={d.get('5d','—')} 1m={d.get('1m','—')} 3m={d.get('3m','—')}")
    perf_str = "\n".join(perf_lines[:25]) if perf_lines else " No price data"

    news_str = "\n".join(f" {h}" for h in headlines) if headlines else " No recent news"

    prompt = f"""You are a Hedgeye-style quantitative macro research analyst. Analyze the current environment and identify actionable investment opportunities.

CURRENT MACRO REGIME:
 Structural (Quarterly): {sq} — {QUAD_CONTEXT.get(sq,sq)}
 Monthly (3-6 weeks): {mq} — {QUAD_CONTEXT.get(mq,mq)}
 Global (50 countries): {gq} — {QUAD_CONTEXT.get(gq,gq)}

KEY ECONOMIC SIGNALS:
 Growth momentum: {gm:+.2%} ({'accelerating' if gm>0 else 'decelerating'})
 Inflation momentum: {im:+.2%} ({'rising' if im>0 else 'cooling'})
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

def _call_gemini(prompt: str, api_key: str) -> Optional[Dict]:
    try:
        import google.generativeai as genai
        logger.info("AIEngine: google-generativeai imported successfully")
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            MODEL,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=MAX_TOKENS,
                response_mime_type="application/json",
            ),
        )

        logger.info(f"AIEngine: calling Gemini model={MODEL}...")
        response = model.generate_content(prompt)
        raw = response.text.strip()
        logger.info(f"AIEngine: Gemini raw response length={len(raw)}")

        if raw.startswith("```"):
            raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except ImportError as e:
        logger.error(f"AIEngine: FAILED to import google-generativeai: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"AIEngine: Gemini JSON parse error: {e}")
        return None
    except Exception as e:
        logger.warning(f"AIEngine: Gemini API call failed: {e}")
        return None

def _validate_output(data: Dict) -> Dict:
    clean = {}
    narr = []
    for n in (data.get("narratives") or []):
        if not isinstance(n, dict):
            continue
        if not n.get("name") or not n.get("thesis"):
            continue
        narr.append({
            "name": str(n.get("name", ""))[:60],
            "score": max(0.0, min(1.0, float(n.get("score", 0.7)))),
            "stage": str(n.get("stage", "brewing")) if n.get("stage") in ("active", "building", "brewing") else "brewing",
            "thesis": str(n.get("thesis", ""))[:300],
            "regime_bias": str(n.get("regime_bias", "ALL")),
            "tickers": [str(t) for t in (n.get("tickers") or [])[:10]],
            "best": [str(t) for t in (n.get("best") or [])[:6]],
            "worst": [str(t) for t in (n.get("worst") or [])[:4]],
            "invalidators": [str(i) for i in (n.get("invalidators") or [])[:3]],
            "news_catalyst": str(n.get("news_catalyst", ""))[:200],
            "ai_generated": True,
        })
    clean["narratives"] = narr[:6]

    btks = []
    for b in (data.get("bottlenecks") or []):
        if not isinstance(b, dict):
            continue
        if not b.get("name"):
            continue
        btks.append({
            "name": str(b.get("name", ""))[:60],
            "constraint": max(0.0, min(1.0, float(b.get("constraint", 0.7)))),
            "sector": str(b.get("sector", "generic")),
            "thesis": str(b.get("thesis", ""))[:300],
            "beneficiary_tickers": [str(t) for t in (b.get("beneficiary_tickers") or [])[:8]],
            "fade_tickers": [str(t) for t in (b.get("fade_tickers") or [])[:4]],
            "time_horizon": str(b.get("time_horizon", "weeks")),
            "confidence": max(0.0, min(1.0, float(b.get("confidence", 0.7)))),
            "stage": str(b.get("stage", "brewing")) if b.get("stage") in ("active", "building", "brewing") else "brewing",
            "ai_generated": True,
        })
    clean["bottlenecks"] = btks[:5]

    ideas = []
    for a in (data.get("alpha_ideas") or []):
        if not isinstance(a, dict):
            continue
        if not a.get("ticker") or not a.get("thesis"):
            continue
        ideas.append({
            "name": str(a.get("name", a.get("ticker", "")))[:60],
            "ticker": str(a.get("ticker", "")).upper(),
            "direction": "short" if str(a.get("direction", "long")).lower() == "short" else "long",
            "confidence": max(0.0, min(1.0, float(a.get("confidence", 0.7)))),
            "stage": str(a.get("stage", "brewing")) if a.get("stage") in ("active", "building", "brewing") else "brewing",
            "thesis": str(a.get("thesis", ""))[:300],
            "regime_fit": str(a.get("regime_fit", ""))[:200],
            "category": str(a.get("category", "Macro Rotation")),
            "invalidators": [str(i) for i in (a.get("invalidators") or [])[:3]],
            "ai_generated": True,
        })
    clean["alpha_ideas"] = ideas[:6]

    su = data.get("scenario_update") or {}
    clean["scenario_update"] = {
        "headline_risk": str(su.get("headline_risk", ""))[:300],
        "opportunity": str(su.get("opportunity", ""))[:300],
        "regime_change_signal": str(su.get("regime_change_signal", ""))[:300],
        "base_case_intact": bool(su.get("base_case_intact", True)),
    }

    return clean

class AIEngine:
    def __init__(self, cache_ttl: float = _AI_CACHE_TTL):
        self.cache_ttl = cache_ttl

    def run(self, sq: str, mq: str, gq: str, gip_features: Dict, prices: Dict[str, pd.Series], force_refresh: bool = False) -> Dict:
        global _AI_CACHE, _AI_CACHE_TS

        logger.info("AIEngine.run() called")

        if not force_refresh and _AI_CACHE and (time.time() - _AI_CACHE_TS) < self.cache_ttl:
            logger.info("AIEngine: serving from cache")
            return {**_AI_CACHE, "from_cache": True}

        api_key = _get_api_key()
        if not api_key:
            logger.warning("AIEngine: GEMINI_API_KEY not set")
            return {
                "ok": False,
                "reason": "GEMINI_API_KEY not configured. Add GEMINI_API_KEY to Streamlit Secrets.",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        logger.info("AIEngine: fetching fresh analysis from Gemini...")
        t0 = time.time()

        try:
            headlines = _fetch_news_headlines(NEWS_TICKERS, max_per_ticker=3)
            logger.info(f"AIEngine: fetched {len(headlines)} headlines")
        except Exception as e:
            logger.error(f"AIEngine: news fetch crashed: {e}")
            headlines = []

        try:
            perf = _price_performance(prices, NEWS_TICKERS)
            logger.info(f"AIEngine: perf computed for {len(perf)} tickers")
        except Exception as e:
            logger.error(f"AIEngine: perf computation crashed: {e}")
            perf = {}

        try:
            prompt = _build_prompt(sq, mq, gq, gip_features, headlines, perf)
            logger.info(f"AIEngine: prompt built, length={len(prompt)}")
        except Exception as e:
            logger.error(f"AIEngine: prompt build crashed: {e}")
            return {
                "ok": False,
                "reason": f"Prompt build error: {e}",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        raw = _call_gemini(prompt, api_key)
        if raw is None:
            logger.warning("AIEngine: Gemini call returned None")
            return {
                "ok": False,
                "reason": "Gemini API call failed. Check logs for details.",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        try:
            result = _validate_output(raw)
            result["ok"] = True
            result["elapsed"] = round(time.time() - t0, 1)
            result["headlines_used"] = len(headlines)
            result["generated_at"] = time.time()
            result["model"] = MODEL
            logger.info(
                f"AIEngine: SUCCESS — {len(result.get('narratives', []))} narratives, "
                f"{len(result.get('bottlenecks', []))} bottlenecks, "
                f"{len(result.get('alpha_ideas', []))} alpha ideas "
                f"in {result['elapsed']}s"
            )
        except Exception as e:
            logger.error(f"AIEngine: validation crashed: {e}")
            return {
                "ok": False,
                "reason": f"Output validation error: {e}",
                "narratives": [], "bottlenecks": [], "alpha_ideas": [],
                "scenario_update": {},
            }

        _AI_CACHE = result
        _AI_CACHE_TS = time.time()

        return result