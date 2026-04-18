"""regime_ticker_engine.py

Resolves the current regime → specific front-run ticker recommendations
with conviction scoring per market and explicit rationale.

Consumes:
- RegimePosterior (current/monthly quad, confidence, flip_hazard)
- RegimeTransitionOutput (transition paths, front_run_window, early warning)
- NewsEventEngine output (news state, Claude analysis)
- ScenarioFeatures (petrodollar_shock, em_importer_pain, etc.)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from config.regime_ticker_registry import (
    US_TICKERS, IHSG_TICKERS, FX_TICKERS, COMMODITY_TICKERS, CRYPTO_TICKERS,
    TRANSITION_FRONT_RUN,
)
from utils.math_utils import clamp01


@dataclass
class TickerRecommendation:
    ticker: str
    market: str           # us | ihsg | fx | commodities | crypto
    side: str             # long | short | buy | reduce | watch
    conviction: float     # 0-1
    quad_source: str      # which quad/regime drives this
    rationale: str
    front_run: bool       # True if this is a pre-confirmation front-run
    tags: List[str] = field(default_factory=list)


@dataclass
class RegimeTickerOutput:
    structural_quad: str
    monthly_quad: str
    front_run_window: str
    recommendations: List[TickerRecommendation]       # all recs sorted by conviction
    front_run_picks: List[TickerRecommendation]       # highest conviction front-run only
    transition_alert: str                              # plain language alert if transition near
    most_important_signal: str                         # what to watch NOW
    us_longs: List[str]
    us_shorts: List[str]
    ihsg_buys: List[str]
    fx_longs: List[str]
    fx_shorts: List[str]
    commodity_longs: List[str]
    commodity_shorts: List[str]
    crypto_longs: List[str]
    crypto_shorts: List[str]


class RegimeTickerEngine:
    """Converts macro regime state → specific actionable ticker list with conviction."""

    def run(
        self,
        regime_posterior,            # RegimePosterior dataclass
        transition_output=None,      # RegimeTransitionOutput (optional)
        news_state: Dict | None = None,
        scenario_features: Dict | None = None,
    ) -> RegimeTickerOutput:
        news_state = news_state or {}
        scenario_features = scenario_features or {}

        structural_quad = str(getattr(regime_posterior, "structural_quad", "Q?"))
        monthly_quad = str(getattr(regime_posterior, "monthly_quad", structural_quad))
        confidence = float(getattr(regime_posterior, "structural_confidence", 0.5))
        flip_hazard = float(getattr(regime_posterior, "flip_hazard", 0.3))
        divergence = str(getattr(regime_posterior, "divergence_state", "aligned"))

        # Transition signals
        front_run_window = "not yet"
        top_transition_to = ""
        ew_score = 0.0
        if transition_output:
            front_run_window = getattr(transition_output, "front_run_window", "not yet")
            paths = getattr(transition_output, "transition_paths", [])
            if paths:
                top_path = paths[0]
                top_transition_to = top_path.to_quad
                ew_score = float(top_path.early_warning_score)

        # News signals
        war_h = float(news_state.get("war_oil_hazard", 0.0))
        pol_h = float(news_state.get("policy_pressure_hazard", 0.0))
        credit_h = float(news_state.get("credit_stress_hazard", 0.0))
        relief_h = float(news_state.get("relief_hazard", 0.0))
        news_dominant = str(news_state.get("state", "quiet"))

        # Scenario flags
        petrodollar = float(scenario_features.get("petrodollar_shock", 0.0))
        em_pain = float(scenario_features.get("em_importer_pain", 0.0))
        carry_unwind = float(scenario_features.get("carry_unwind", 0.0))
        broadening = float(scenario_features.get("broadening_reflation", 0.0))

        recs: List[TickerRecommendation] = []

        # ------------------------------------------------------------------
        # 1. Current structural quad — base recommendations
        # ------------------------------------------------------------------
        base_conviction = clamp01(confidence * (1.0 - 0.5 * flip_hazard))

        def _add_us_recs(quad: str, conviction_mult: float = 1.0, front_run: bool = False):
            data = US_TICKERS.get(quad, {})
            rationale = data.get("long", {}).get("rationale", "")
            for etf in (data.get("long", {}).get("etfs") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=etf, market="us", side="long",
                    conviction=clamp01(base_conviction * conviction_mult * 0.90),
                    quad_source=quad, rationale=rationale, front_run=front_run,
                    tags=["etf", "us_long"],
                ))
            for stk in (data.get("long", {}).get("stocks") or [])[:8]:
                recs.append(TickerRecommendation(
                    ticker=stk, market="us", side="long",
                    conviction=clamp01(base_conviction * conviction_mult * 0.85),
                    quad_source=quad, rationale=rationale, front_run=front_run,
                    tags=["stock", "us_long"],
                ))
            short_data = data.get("short", {})
            short_rationale = short_data.get("rationale", "")
            for etf in (short_data.get("etfs") or [])[:3]:
                recs.append(TickerRecommendation(
                    ticker=etf, market="us", side="short",
                    conviction=clamp01(base_conviction * conviction_mult * 0.80),
                    quad_source=quad, rationale=short_rationale, front_run=front_run,
                    tags=["etf", "us_short"],
                ))
            for stk in (short_data.get("stocks") or [])[:5]:
                recs.append(TickerRecommendation(
                    ticker=stk, market="us", side="short",
                    conviction=clamp01(base_conviction * conviction_mult * 0.75),
                    quad_source=quad, rationale=short_rationale, front_run=front_run,
                    tags=["stock", "us_short"],
                ))

        def _add_ihsg_recs(quad: str, conviction_mult: float = 1.0, front_run: bool = False):
            data = IHSG_TICKERS.get(quad, {})
            buy_data = data.get("buy", {})
            rationale = buy_data.get("rationale", "")
            for t in (buy_data.get("core") or []):
                recs.append(TickerRecommendation(
                    ticker=t, market="ihsg", side="buy",
                    conviction=clamp01(base_conviction * conviction_mult * 0.90),
                    quad_source=quad, rationale=rationale, front_run=front_run,
                    tags=["ihsg", "core"],
                ))
            for t in (buy_data.get("tactical") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="ihsg", side="buy",
                    conviction=clamp01(base_conviction * conviction_mult * 0.75),
                    quad_source=quad, rationale=rationale, front_run=front_run,
                    tags=["ihsg", "tactical"],
                ))
            for t in (data.get("reduce") or [])[:3]:
                recs.append(TickerRecommendation(
                    ticker=t, market="ihsg", side="reduce",
                    conviction=clamp01(base_conviction * conviction_mult * 0.70),
                    quad_source=quad, rationale=f"Reduce/avoid in {quad}", front_run=front_run,
                    tags=["ihsg", "reduce"],
                ))

        def _add_fx_recs(quad: str, conviction_mult: float = 1.0, front_run: bool = False):
            data = FX_TICKERS.get(quad, {})
            for t in (data.get("long", {}).get("pairs") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="fx", side="long",
                    conviction=clamp01(base_conviction * conviction_mult * 0.80),
                    quad_source=quad, rationale=data.get("long", {}).get("rationale", ""),
                    front_run=front_run, tags=["fx", "long"],
                ))
            for t in (data.get("short", {}).get("pairs") or [])[:3]:
                recs.append(TickerRecommendation(
                    ticker=t, market="fx", side="short",
                    conviction=clamp01(base_conviction * conviction_mult * 0.75),
                    quad_source=quad, rationale=data.get("short", {}).get("rationale", ""),
                    front_run=front_run, tags=["fx", "short"],
                ))

        def _add_commodity_recs(quad: str, conviction_mult: float = 1.0, front_run: bool = False):
            data = COMMODITY_TICKERS.get(quad, {})
            for t in (data.get("long", {}).get("tickers") or [])[:5]:
                recs.append(TickerRecommendation(
                    ticker=t, market="commodities", side="long",
                    conviction=clamp01(base_conviction * conviction_mult * 0.85),
                    quad_source=quad, rationale=data.get("long", {}).get("rationale", ""),
                    front_run=front_run, tags=["commodity", "long"],
                ))
            for t in (data.get("long", {}).get("etfs") or [])[:3]:
                recs.append(TickerRecommendation(
                    ticker=t, market="commodities", side="long",
                    conviction=clamp01(base_conviction * conviction_mult * 0.80),
                    quad_source=quad, rationale=data.get("long", {}).get("rationale", ""),
                    front_run=front_run, tags=["commodity", "etf", "long"],
                ))
            for t in (data.get("short", {}).get("tickers") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="commodities", side="short",
                    conviction=clamp01(base_conviction * conviction_mult * 0.75),
                    quad_source=quad, rationale=data.get("short", {}).get("rationale", ""),
                    front_run=front_run, tags=["commodity", "short"],
                ))

        def _add_crypto_recs(quad: str, conviction_mult: float = 1.0, front_run: bool = False):
            data = CRYPTO_TICKERS.get(quad, {})
            for key in ["tier1", "tier2"]:
                for t in (data.get("long", {}).get(key) or [])[:4]:
                    recs.append(TickerRecommendation(
                        ticker=t, market="crypto", side="long",
                        conviction=clamp01(base_conviction * conviction_mult * (0.85 if key == "tier1" else 0.70)),
                        quad_source=quad, rationale=data.get("long", {}).get("rationale", ""),
                        front_run=front_run, tags=["crypto", key, "long"],
                    ))
            for key in ["tier1", "speculative"]:
                for t in (data.get("short", {}).get(key) or [])[:4]:
                    recs.append(TickerRecommendation(
                        ticker=t, market="crypto", side="short",
                        conviction=clamp01(base_conviction * conviction_mult * (0.80 if key == "tier1" else 0.70)),
                        quad_source=quad, rationale=data.get("short", {}).get("rationale", ""),
                        front_run=front_run, tags=["crypto", key, "short"],
                    ))

        # Add base structural quad recs
        _add_us_recs(structural_quad)
        _add_ihsg_recs(structural_quad)
        _add_fx_recs(structural_quad)
        _add_commodity_recs(structural_quad)
        _add_crypto_recs(structural_quad)

        # ------------------------------------------------------------------
        # 2. Monthly divergence — blend in monthly quad recs at lower conviction
        # ------------------------------------------------------------------
        if divergence == "divergent" and monthly_quad != structural_quad:
            monthly_weight = 0.55
            _add_us_recs(monthly_quad, conviction_mult=monthly_weight)
            _add_ihsg_recs(monthly_quad, conviction_mult=monthly_weight)
            _add_commodity_recs(monthly_quad, conviction_mult=monthly_weight)
            _add_crypto_recs(monthly_quad, conviction_mult=monthly_weight)

        # ------------------------------------------------------------------
        # 3. Front-run transition tickers — if transition window is active
        # ------------------------------------------------------------------
        transition_alert = ""
        if front_run_window in ("now", "1-2w") and top_transition_to:
            path_key = f"{structural_quad}→{top_transition_to}"
            tr_data = TRANSITION_FRONT_RUN.get(path_key, {})
            tr_conviction = 0.85 if front_run_window == "now" else 0.65
            tr_desc = tr_data.get("description", "")

            for t in (tr_data.get("us_long") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="us", side="long",
                    conviction=clamp01(tr_conviction * ew_score),
                    quad_source=f"transition_{path_key}",
                    rationale=f"FRONT-RUN {path_key}: {tr_desc}",
                    front_run=True, tags=["front_run", "us", "long"],
                ))
            for t in (tr_data.get("us_short") or [])[:3]:
                recs.append(TickerRecommendation(
                    ticker=t, market="us", side="short",
                    conviction=clamp01(tr_conviction * ew_score * 0.90),
                    quad_source=f"transition_{path_key}",
                    rationale=f"FRONT-RUN {path_key}: {tr_desc}",
                    front_run=True, tags=["front_run", "us", "short"],
                ))
            for t in (tr_data.get("ihsg_buy") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="ihsg", side="buy",
                    conviction=clamp01(tr_conviction * ew_score * 0.90),
                    quad_source=f"transition_{path_key}",
                    rationale=f"FRONT-RUN {path_key}: {tr_desc}",
                    front_run=True, tags=["front_run", "ihsg"],
                ))
            for t in (tr_data.get("commodity_long") or [])[:4]:
                recs.append(TickerRecommendation(
                    ticker=t, market="commodities", side="long",
                    conviction=clamp01(tr_conviction * ew_score * 0.85),
                    quad_source=f"transition_{path_key}",
                    rationale=f"FRONT-RUN {path_key}: {tr_desc}",
                    front_run=True, tags=["front_run", "commodity", "long"],
                ))

            transition_alert = (
                f"⚡ TRANSITION ALERT: {path_key} — {tr_desc} | "
                f"EW Score: {int(ew_score*100)}% | Window: {front_run_window}"
            )

        # ------------------------------------------------------------------
        # 4. War/oil shock overlay — boost energy and gold conviction
        # ------------------------------------------------------------------
        if war_h >= 0.45 or petrodollar >= 0.55:
            war_boost = war_h + 0.5 * petrodollar
            war_tickers = ["XLE", "CL=F", "GC=F", "NEM", "LMT", "ADRO.JK", "PTBA.JK", "ANTM.JK"]
            for t in war_tickers:
                market = "ihsg" if t.endswith(".JK") else ("commodities" if "=F" in t else "us")
                recs.append(TickerRecommendation(
                    ticker=t, market=market, side="long" if market != "ihsg" else "buy",
                    conviction=clamp01(0.45 + 0.40 * war_boost),
                    quad_source="war_oil_overlay",
                    rationale=f"War/oil shock overlay active ({int(war_h*100)}%). Energy + defense + gold.",
                    front_run=False, tags=["war_oil", "overlay"],
                ))

        # ------------------------------------------------------------------
        # 5. EM importer pain — boost IDR hedge + IHSG defensive rotation
        # ------------------------------------------------------------------
        if em_pain >= 0.50:
            recs.append(TickerRecommendation(
                ticker="IDR=X", market="fx", side="short",  # short IDR = long USDIDR
                conviction=clamp01(0.40 + 0.40 * em_pain),
                quad_source="em_importer_overlay",
                rationale=f"EM importer pain ({int(em_pain*100)}%). Hedge IDR exposure. Rotate to IHSG exporters.",
                front_run=False, tags=["em_pain", "fx"],
            ))
            for t in ["ICBP.JK", "INDF.JK", "KLBF.JK"]:
                recs.append(TickerRecommendation(
                    ticker=t, market="ihsg", side="buy",
                    conviction=clamp01(0.50 + 0.30 * em_pain),
                    quad_source="em_importer_overlay",
                    rationale="IDR pressure → rotate IHSG to domestic defensives",
                    front_run=False, tags=["ihsg", "defensive", "em_pain"],
                ))

        # ------------------------------------------------------------------
        # 6. Credit stress — defensive overlay
        # ------------------------------------------------------------------
        if credit_h >= 0.45:
            for t in ["GLD", "TLT", "BIL", "XLP"]:
                recs.append(TickerRecommendation(
                    ticker=t, market="us", side="long",
                    conviction=clamp01(0.55 + 0.30 * credit_h),
                    quad_source="credit_stress_overlay",
                    rationale=f"Credit stress active ({int(credit_h*100)}%). Flight to quality.",
                    front_run=False, tags=["credit_stress", "defensive"],
                ))

        # ------------------------------------------------------------------
        # Sort by conviction, deduplicate (keep highest conviction per ticker+side)
        # ------------------------------------------------------------------
        seen: dict[str, float] = {}
        deduped: List[TickerRecommendation] = []
        for r in sorted(recs, key=lambda x: x.conviction, reverse=True):
            key = f"{r.ticker}|{r.side}"
            if key not in seen:
                seen[key] = r.conviction
                deduped.append(r)

        # ------------------------------------------------------------------
        # Build flat lists for easy UI consumption
        # ------------------------------------------------------------------
        us_longs    = [r.ticker for r in deduped if r.market == "us" and r.side == "long"][:10]
        us_shorts   = [r.ticker for r in deduped if r.market == "us" and r.side == "short"][:8]
        ihsg_buys   = [r.ticker for r in deduped if r.market == "ihsg" and r.side in ("buy",)][:10]
        fx_longs    = [r.ticker for r in deduped if r.market == "fx" and r.side == "long"][:6]
        fx_shorts   = [r.ticker for r in deduped if r.market == "fx" and r.side == "short"][:4]
        com_longs   = [r.ticker for r in deduped if r.market == "commodities" and r.side == "long"][:8]
        com_shorts  = [r.ticker for r in deduped if r.market == "commodities" and r.side == "short"][:5]
        cry_longs   = [r.ticker for r in deduped if r.market == "crypto" and r.side == "long"][:8]
        cry_shorts  = [r.ticker for r in deduped if r.market == "crypto" and r.side == "short"][:5]

        front_run_picks = [r for r in deduped if r.front_run][:6]

        # Most important signal to watch
        if transition_alert:
            most_important = transition_alert
        elif news_dominant in ("war_oil", "policy_pressure", "credit_stress"):
            most_important = f"Active {news_dominant} regime — overlay active on all recommendations"
        else:
            sq = US_TICKERS.get(structural_quad, {})
            fr_signal = sq.get("front_run", {}).get("signal", "")
            most_important = fr_signal or f"Stay positioned in {structural_quad} regime"

        return RegimeTickerOutput(
            structural_quad=structural_quad,
            monthly_quad=monthly_quad,
            front_run_window=front_run_window,
            recommendations=deduped,
            front_run_picks=front_run_picks,
            transition_alert=transition_alert,
            most_important_signal=most_important,
            us_longs=us_longs,
            us_shorts=us_shorts,
            ihsg_buys=ihsg_buys,
            fx_longs=fx_longs,
            fx_shorts=fx_shorts,
            commodity_longs=com_longs,
            commodity_shorts=com_shorts,
            crypto_longs=cry_longs,
            crypto_shorts=cry_shorts,
        )
