"""engines/supply_chain_light_engine.py v1 — Lightweight Supply Chain Discovery

No heavy EDGAR parsing. Uses:
  1. yfinance .info business summary → keyword mining
  2. News headline co-mention with supply chain keywords
  3. Earnings date proximity → recent fundamental event
"""
from __future__ import annotations
import re
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class SupplyChainLightEngine:
    """
    Auto-detects bottleneck signals from lightweight sources.
    Constraint score derived from:
      - business_summary keywords (dominant market position)
      - news supply chain mentions
      - earnings surprise recency
    """

    CONSTRAINT_KEYWORDS = [
        "sole source", "only supplier", "only provider", "dominant market share",
        "market leader", "monopoly", "duopoly", "oligopoly", "near-monopoly",
        "industry leader", "leading provider", "largest supplier", "primary supplier",
        "exclusive supplier", "critical supplier", "single source", "limited suppliers",
        "supply constrained", "capacity constrained", "tight supply", "supply shortage",
        "bottleneck", "chokepoint", "indispensable", "irreplaceable",
    ]

    RISK_KEYWORDS = [
        "shortage", "supply chain disruption", "constrained", "lead times extended",
        "backlog", "order backlog", "demand exceeds supply", "unable to meet demand",
        "capacity expansion", "ramping production", "supply crunch",
    ]

    def __init__(self, news_engine=None):
        self.news_engine = news_engine

    def run(
        self,
        tickers: List[str],
        prices=None,
        news_results: Optional[Dict] = None,
    ) -> Dict[str, object]:
        import yfinance as yf
        
        results = {}
        for t in tickers:
            try:
                info = yf.Ticker(t).info or {}
            except Exception as e:
                logger.warning(f"yfinance error for {t}: {e}")
                info = {}

            summary = info.get("longBusinessSummary", "") or ""
            industry = info.get("industry", "") or ""
            sector = info.get("sector", "") or ""

            # ── 1. Business Summary Constraint Mining ────────────────────
            summary_lower = summary.lower()
            constraint_hits = [kw for kw in self.CONSTRAINT_KEYWORDS if kw in summary_lower]
            risk_hits = [kw for kw in self.RISK_KEYWORDS if kw in summary_lower]

            # Score: more hits = higher constraint
            constraint_score = min(len(constraint_hits) * 0.15 + len(risk_hits) * 0.10, 1.0)

            # ── 2. News Supply Chain Co-mention ─────────────────────────
            news_supply_score = 0.0
            news_supply_hits = []
            if news_results and "ticker_specific" in news_results:
                t_news = news_results["ticker_specific"].get(t, [])
                for ni in t_news:
                    if hasattr(ni, 'supply_chain_mentions') and len(ni.supply_chain_mentions) > 0:
                        news_supply_hits.extend(ni.supply_chain_mentions)
                news_supply_score = min(len(news_supply_hits) * 0.12, 0.6)

            # ── 3. Market Cap / Float Proxy (smaller = more explosive if bottleneck) ──
            mcap = info.get("marketCap", 0) or 0
            float_proxy = 0.3 if mcap < 5e9 else 0.15 if mcap < 50e9 else 0.05

            # ── 4. Combine ──────────────────────────────────────────────
            final_constraint = min(constraint_score + news_supply_score + float_proxy, 1.0)

            # ── 5. Auto-generate thesis ─────────────────────────────────
            thesis = self._auto_thesis(t, summary, industry, constraint_hits, risk_hits, news_supply_hits)

            results[t] = {
                "ticker": t,
                "sector": sector,
                "industry": industry,
                "constraint_score": round(final_constraint, 2),
                "business_summary_hits": constraint_hits,
                "news_supply_hits": list(set(news_supply_hits)),
                "market_cap": mcap,
                "thesis": thesis,
                "is_bottleneck_candidate": final_constraint >= 0.65,
            }

        # Rank
        ranked = sorted(results.values(), key=lambda x: x["constraint_score"], reverse=True)
        return {
            "candidates": ranked,
            "strong_candidates": [r for r in ranked if r["is_bottleneck_candidate"]],
            "meta": {"tickers_scanned": len(tickers), "strong_count": len([r for r in ranked if r["is_bottleneck_candidate"]])}
        }

    def _auto_thesis(self, ticker, summary, industry, constraint_hits, risk_hits, news_hits):
        parts = []
        if constraint_hits:
            parts.append(f"Business summary indicates {'; '.join(constraint_hits[:2])}.")
        if risk_hits:
            parts.append(f"Recent risk language: {'; '.join(risk_hits[:2])}.")
        if news_hits:
            parts.append(f"News confirms supply pressure: {', '.join(set(news_hits)[:2])}.")
        if not parts:
            parts.append(f"{ticker} operates in {industry} with no explicit constraint language detected.")
        
        return " ".join(parts)[:250]