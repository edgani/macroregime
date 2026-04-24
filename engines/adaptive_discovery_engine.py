"""engines/adaptive_discovery_engine.py

TRUE Adaptive Discovery — uses Claude API (Anthropic) to generate
novel bottleneck/narrative hypotheses from current market data.

This is the core "adaptivity" mechanism:
- Input: current macro regime + top price movers + known narratives
- Process: calls Claude to generate hypotheses NOT in hardcoded list
- Output: novel plays with tickers, thesis, conviction, confirmation signals

Like discovering transformer/switchgear BEFORE it's consensus.
Runs on refresh, results cached for 4 hours.
"""
from __future__ import annotations
import json, math, time, logging
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DISCOVERY_CACHE: Dict[str, object] = {}
_CACHE_TS: float = 0.0
_CACHE_TTL = 4 * 3600  # 4 hours

def _ret(s, n):
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n+1: return None
    base = float(s.iloc[-n-1])
    if not math.isfinite(base) or abs(base) < 1e-10: return None
    r = float(s.iloc[-1]/base - 1)
    return r if math.isfinite(r) else None

def _build_market_context(
    prices: Dict[str, pd.Series],
    structural_quad: str,
    monthly_quad: str,
    gip_features: Dict[str, float],
    known_narrative_names: List[str],
) -> str:
    """Build a rich prompt context from current market data."""
    # Top/bottom performers 3M
    performers = []
    for t, s in prices.items():
        if t in ("SPY","QQQ","IWM","TLT","DX-Y.NYB","^VIX"): continue
        r3 = _ret(s, 63)
        if r3 is not None and math.isfinite(r3):
            performers.append((t, r3))
    performers.sort(key=lambda x: x[1], reverse=True)
    top5  = [(t, f"{r:+.1%}") for t,r in performers[:5]]
    bot5  = [(t, f"{r:+.1%}") for t,r in performers[-5:]]

    vix_raw = _ret(prices.get("^VIX"), 0)
    gold_3m = _ret(prices.get("GLD"), 63)
    usd_3m  = _ret(prices.get("DX-Y.NYB"), 63) or _ret(prices.get("UUP"), 63)
    oil_3m  = _ret(prices.get("CL=F"), 63)
    tlt_3m  = _ret(prices.get("TLT"), 63)

    g_mom = gip_features.get("growth_momentum", 0)
    i_mom = gip_features.get("inflation_momentum", 0)
    cov   = gip_features.get("data_coverage", 0)

    from config.settings import QUAD_ASSET_PERFORMANCE
    q_desc = {"Q1":"Goldilocks (Growth↑ Inflation↓)","Q2":"Reflation (Growth↑ Inflation↑)",
              "Q3":"Stagflation (Growth↓ Inflation↑)","Q4":"Deflation (Growth↓ Inflation↓)"}

    context = f"""CURRENT MACRO STATE (April 2026):
Structural Quad: {structural_quad} — {q_desc.get(structural_quad,'')}
Monthly Quad: {monthly_quad} — {q_desc.get(monthly_quad,'')}
Growth momentum: {g_mom:+.3f} ({'decelerating' if g_mom < 0 else 'accelerating'})
Inflation momentum: {i_mom:+.3f} ({'rising' if i_mom > 0 else 'falling'})
FRED coverage: {cov:.0%}

MARKET SIGNALS:
Gold 3M: {f'{gold_3m:+.1%}' if gold_3m else 'N/A'}
USD 3M: {f'{usd_3m:+.1%}' if usd_3m else 'N/A'}
Oil 3M: {f'{oil_3m:+.1%}' if oil_3m else 'N/A'}
TLT 3M: {f'{tlt_3m:+.1%}' if tlt_3m else 'N/A'}

TOP PERFORMERS (3M, outperforming SPY):
{chr(10).join(f'  {t}: {r}' for t,r in top5)}

WORST PERFORMERS (3M):
{chr(10).join(f'  {t}: {r}' for t,r in bot5)}

ALREADY TRACKED NARRATIVES (DO NOT duplicate):
{chr(10).join(f'  - {n}' for n in known_narrative_names[:15])}

TASK: Generate 4 NEW adaptive market hypotheses that:
1. Are NOT in the already tracked list above
2. Fit {structural_quad} structural + {monthly_quad} monthly regime
3. Are grounded in the specific price signals above (explain which signal activates it)
4. Have concrete beneficiary tickers tradeable via US markets (include ETFs, ADRs, futures)
5. Range from "already happening" to "brewing/early stage"

For each hypothesis return:
{{
  "name": "Short memorable name (max 6 words)",
  "stage": "active|building|brewing",
  "thesis": "2-3 sentence thesis grounded in current data",
  "regime_fit": 0.0-1.0,
  "beneficiary_tickers": ["T1","T2","T3"],
  "fade_tickers": ["F1","F2"],
  "confirmation_signal": "What price/data confirms this is real",
  "conviction": 0.0-1.0,
  "pump_risk": 0.0-1.0,
  "category": "technology|geopolitical|policy|commodity|cycle"
}}

Return ONLY a JSON array of 4 objects, no other text."""
    return context


async def _call_claude_api(prompt: str) -> Optional[List[dict]]:
    """Call Anthropic API to generate novel hypotheses."""
    try:
        import requests
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=25,
        )
        if response.status_code != 200:
            logger.warning(f"Claude API error: {response.status_code}")
            return None

        data = response.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # Clean JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```")

        result = json.loads(text)
        if isinstance(result, list):
            return result
        return None

    except Exception as e:
        logger.warning(f"Claude API call failed: {e}")
        return None


def _call_claude_sync(prompt: str) -> Optional[List[dict]]:
    """Synchronous wrapper for Claude API call."""
    try:
        import requests
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=25,
        )
        if response.status_code != 200:
            logger.warning(f"Claude API {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        text = text.strip()
        # Strip markdown code blocks
        if "```" in text:
            parts = text.split("```")
            for p in parts:
                p2 = p.strip().lstrip("json").strip()
                if p2.startswith("["):
                    text = p2
                    break

        result = json.loads(text)
        return result if isinstance(result, list) else None

    except Exception as e:
        logger.warning(f"Claude sync call failed: {e}")
        return None


class AdaptiveDiscoveryEngine:
    """
    Calls Claude API with current market context to discover
    novel bottleneck/narrative plays NOT in our hardcoded lists.
    Results cached 4 hours to avoid repeated API calls.
    """

    def run(
        self,
        prices: Dict[str, pd.Series],
        structural_quad: str,
        monthly_quad: str,
        gip_features: Dict[str, float],
        force_refresh: bool = False,
    ) -> Dict[str, object]:

        global _DISCOVERY_CACHE, _CACHE_TS

        # Cache check
        cache_key = f"{structural_quad}_{monthly_quad}"
        if not force_refresh and _DISCOVERY_CACHE.get("key") == cache_key:
            if time.time() - _CACHE_TS < _CACHE_TTL:
                return _DISCOVERY_CACHE

        from config.narrative_universe import get_all_narratives
        known_names = [n.name for n in get_all_narratives()]

        # Build context
        prompt = _build_market_context(prices, structural_quad, monthly_quad, gip_features, known_names)

        # Call Claude
        raw = _call_claude_sync(prompt)

        if raw is None:
            # Fallback: return empty with message
            result = dict(
                discoveries=[],
                status="api_unavailable",
                message="Claude API not reachable. Set ANTHROPIC_API_KEY or check network.",
                key=cache_key,
            )
            return result

        # Validate and clean each discovery
        discoveries = []
        for item in raw[:5]:
            if not isinstance(item, dict): continue
            if not item.get("name") or not item.get("thesis"): continue
            discoveries.append(dict(
                name=str(item.get("name","Unknown"))[:60],
                stage=str(item.get("stage","brewing")),
                thesis=str(item.get("thesis",""))[:300],
                regime_fit=float(item.get("regime_fit",0.5)),
                beneficiary_tickers=list(item.get("beneficiary_tickers",[])),
                fade_tickers=list(item.get("fade_tickers",[])),
                confirmation_signal=str(item.get("confirmation_signal",""))[:150],
                conviction=float(item.get("conviction",0.5)),
                pump_risk=float(item.get("pump_risk",0.5)),
                category=str(item.get("category","cycle")),
                adaptive=True,  # Flag: generated by AI, not hardcoded
            ))

        result = dict(
            discoveries=discoveries,
            status="ok",
            message=f"Generated {len(discoveries)} novel hypotheses for {structural_quad}/{monthly_quad}",
            key=cache_key,
            generated_at=time.strftime("%Y-%m-%d %H:%M"),
        )

        _DISCOVERY_CACHE = result
        _CACHE_TS = time.time()
        return result
