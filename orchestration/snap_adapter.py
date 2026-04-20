"""snap_adapter.py

Converts the new build_snapshot() output (modular pipeline) into
the legacy snap dict format that all UI code expects.

This is the bridge that makes the rebuild transparent to UI.

Old format (monolith): snap['q']['quad'], snap['f']['vix_last'], etc.
New format (modular):  snap['shared_core']['regime']['current_quad'], etc.

All UI code (command_center_page.py, pages_redesigned.py) reads OLD format.
This adapter = zero UI changes needed during migration.
"""
from __future__ import annotations
import math
from typing import Any, Dict
import pandas as pd


def _g(d: Any, *keys, default=None):
    """Safe nested get."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d if d is not None else default


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def adapt_snap(new_snap: dict) -> dict:
    """
    Convert build_snapshot() output to legacy snap format.
    Returns a dict that all existing UI code can read unchanged.
    """
    sc = new_snap.get("shared_core", {})
    regime = sc.get("regime", {})
    rs = sc.get("regime_stack", {})
    weather = sc.get("weather", {})
    shock = sc.get("shock", {})
    news_state = sc.get("news_state", {})
    risk_summary = sc.get("risk_summary", {})
    rotation_raw = sc.get("rotation", {})
    analog_list = sc.get("analog", [])
    exec_mode = sc.get("execution_mode", {})

    # ── q: regime / quad state ────────────────────────────────────────────────
    s_quad = _g(rs, "structural", "quad") or regime.get("current_quad", "Q?")
    m_quad = _g(rs, "monthly", "quad") or regime.get("monthly_quad", s_quad)
    s_probs = _g(rs, "structural", "probs") or regime.get("probs", {})
    m_probs = _g(rs, "monthly", "probs") or {}
    s_conf = float(_g(rs, "structural", "confidence") or regime.get("confidence", 0.0) or 0.0)
    m_conf = float(_g(rs, "monthly", "confidence") or 0.0)
    s_next = _g(rs, "structural", "next_quad") or "Q?"
    m_next = _g(rs, "monthly", "next_quad") or s_next
    g_core = float(_g(rs, "structural", "g_core") or 0.0)
    i_core = float(_g(rs, "structural", "i_core") or 0.0)
    p_core = float(_g(rs, "structural", "p_core") or 0.0)
    div = "divergent" if s_quad != m_quad else "aligned"

    # Derived fields for UI
    flip_hazard = float(regime.get("flip_hazard", 0.0) or 0.0)
    deepness = float(regime.get("deepness", 0.3) or 0.3)
    duration_mat = float(regime.get("duration_maturity", 0.3) or 0.3)
    g_acc = bool(g_core > 0)
    i_acc = bool(i_core > 0)
    slowdown = float(regime.get("slowdown_flags", 0.0) or 0.0)
    inf_shock = float(shock.get("override_strength", 0.0) or 0.0)

    # Confidence band
    def conf_band(c):
        if c >= 0.55: return "High-Conviction"
        if c >= 0.35: return "Moderate-Conviction"
        return "Low-Conviction"

    # Transitional
    q_ordered = sorted(s_probs.items(), key=lambda x: -x[1]) if s_probs else []
    top_spread = (q_ordered[0][1] - q_ordered[1][1]) if len(q_ordered) >= 2 else 1.0
    is_transitional = s_conf < 0.20 and top_spread < 0.08
    t_label = f"Transitional ({q_ordered[0][0]}/{q_ordered[1][0]})" if is_transitional and len(q_ordered) >= 2 else s_quad

    q = {
        "quad": s_quad,
        "monthly_quad": m_quad,
        "probs": s_probs,
        "monthly_probs": m_probs,
        "next_quad": s_next,
        "monthly_next": m_next,
        "confidence": _clamp(s_conf),
        "monthly_conf": _clamp(m_conf),
        "conf_band": conf_band(s_conf),
        "divergence": div,
        "operating": f"Aligned {s_quad}" if div == "aligned" else f"Monthly {m_quad} inside Structural {s_quad}",
        "flip_hazard": _clamp(flip_hazard),
        "deepness": _clamp(deepness),
        "duration_mat": _clamp(duration_mat),
        "g_core": g_core,
        "i_core": i_core,
        "p_core": p_core,
        "g_level": g_core,
        "i_level": i_core,
        "growth_acc": g_acc,
        "infl_acc": i_acc,
        "slowdown_flags": _clamp(slowdown),
        "inf_shock": _clamp(inf_shock),
        "transitional": is_transitional,
        "transitional_label": t_label,
    }

    # ── f: macro features ─────────────────────────────────────────────────────
    # Get from shared_core's macro features
    macro = sc.get("macro_features", {})  # raw macro features
    mkt = sc.get("market_features", {})  # raw market features

    # Pull all the signals UI expects
    f = {
        # Growth
        "indpro_yoy": _g(macro, "indpro_yoy"),
        "indpro_acc": _g(macro, "indpro_acc"),
        "payrolls_yoy": _g(macro, "payrolls_yoy"),
        "payrolls_acc": _g(macro, "payrolls_acc"),
        "retail_yoy": _g(macro, "retail_yoy"),
        "retail_acc": _g(macro, "retail_acc"),
        "unrate": _g(macro, "unrate"),
        "unrate_3m_delta": _g(macro, "unrate_3m_delta"),
        "ism_last": _g(macro, "ism_last"),
        "ism_3m_delta": _g(macro, "ism_3m_delta"),
        "lei_3m": _g(macro, "lei_3m"),
        "lei_acc": _g(macro, "lei_acc"),
        "housing_yoy": _g(macro, "housing_yoy"),
        "claims_13w_delta": _g(macro, "claims_13w_delta"),
        # RoC second derivatives (NEW — from macro_features.py)
        "indpro_roc_3m": _g(macro, "indpro_roc_3m"),
        "cpi_roc_3m": _g(macro, "cpi_roc_3m"),
        "payrolls_roc_3m": _g(macro, "payrolls_roc_3m"),
        "ism_3m": _g(macro, "ism_3m"),
        "core_cpi_roc_3m": _g(macro, "core_cpi_roc_3m"),
        "leading_indicator_composite": _g(macro, "leading_indicator_composite"),
        # Inflation
        "cpi_yoy": _g(macro, "cpi_yoy"),
        "cpi_acc": _g(macro, "cpi_acc"),
        "corepce_yoy": _g(macro, "corepce_yoy"),
        "corepce_acc": _g(macro, "corepce_acc"),
        "breakeven": _g(macro, "breakeven"),
        "breakeven_1m": _g(macro, "breakeven_1m"),
        "headline_core_gap": _g(macro, "headline_core_gap"),
        "m_shock": _g(macro, "m_shock", default=inf_shock),
        "inflation_shock": inf_shock,
        # Policy & Rates
        "policy_rate": _g(macro, "policy_rate"),
        "policy_rate_3m": _g(macro, "policy_rate_3m"),
        "policy_score": _g(macro, "policy_score", default=0.0),
        "liq_score": _g(macro, "liq_score", default=0.0),
        "spread_2s10s": _g(macro, "spread_2s10s"),
        "spread_10s30s": _g(macro, "spread_10s30s"),
        "spread_2s10s_3m": _g(macro, "spread_2s10s_3m"),
        "yield_curve_state": _g(macro, "yield_curve_state", default=""),
        "yield_curve_uninverting": bool(_g(macro, "yield_curve_uninverting", default=False)),
        # Credit & Vol
        "hy_oas": _g(macro, "hy_oas", default=float("nan")),
        "hy_oas_1m": _g(macro, "hy_oas_1m", default=float("nan")),
        "ig_oas": _g(macro, "ig_oas", default=float("nan")),
        "ig_oas_1m": _g(macro, "ig_oas_1m", default=float("nan")),
        "vix_last": _g(mkt, "vix_last", default=float(_g(sc, "vix_bucket", "vix_spot") or 20.0)),
        "vix_vxv_ratio": _g(macro, "vix_vxv_ratio", default=float("nan")),
        "vix_term_state": _g(macro, "vix_term_state", default=""),
        # Market returns
        "spy_1m": _g(mkt, "spy_1m"),
        "spy_3m": _g(mkt, "spy_3m"),
        "uup_1m": _g(mkt, "uup_1m", default=_g(mkt, "dxy_1m")),
        "uup_3m": _g(mkt, "uup_3m"),
        "clf_1m": _g(mkt, "clf_1m", default=_g(mkt, "oil_1m")),
        "clf_3m": _g(mkt, "clf_3m", default=_g(mkt, "oil_3m")),
        "gld_1m": _g(mkt, "gld_1m", default=_g(mkt, "gold_1m")),
        "gld_3m": _g(mkt, "gld_3m", default=_g(mkt, "gold_3m")),
        "tlt_1m": _g(mkt, "tlt_1m"),
        "iwm_1m": _g(mkt, "iwm_1m"),
        "iwm_3m": _g(mkt, "iwm_3m"),
        "xli_1m": _g(mkt, "xli_1m"),
        "xly_1m": _g(mkt, "xly_1m"),
        "eem_1m": _g(mkt, "eem_1m"),
        "rsp_1m": _g(mkt, "rsp_1m"),
        # Data quality
        "data_coverage": _g(macro, "data_coverage", default=0.5),
        "macro_source_quality": _g(macro, "macro_source_quality", default=0.5),
        "_proxy_share": _g(macro, "macro_proxy_share", default=0.5),
        "_fred_loaded": _g(macro, "_fred_loaded", default=0),
        "_fred_total": _g(macro, "_fred_total", default=20),
        "fred_real_share": _g(macro, "fred_real_share", default=0.5),
        "data_source_mode": _g(macro, "data_source_mode", default="Hybrid"),
        # Tariff headwind (new)
        "tariff_growth_headwind": _g(macro, "tariff_growth_headwind", default=0.0),
        # g/i struct internals (for regime intel)
        "g_struct_climate": _g(macro, "g_struct_climate", default=g_core),
        "structural_obs_reliability": _g(macro, "structural_obs_reliability", default=0.5),
    }

    # ── h: market health ──────────────────────────────────────────────────────
    weather_score = float(weather.get("score", 0.5) or 0.5)
    h = {
        "weather": weather_score,
        "weather_state": weather.get("weather_bias", "mixed").title(),
        "trade_state": weather.get("trade_state", "balanced"),
        "tail_state": weather.get("tail_state", "neutral"),
        "verdict": weather.get("verdict", "Mixed"),
        "breadth": float(weather.get("breadth", 0.5) or 0.5),
        "sec_support": float(weather.get("sec_support", 0.5) or 0.5),
        "sec_above50": int(weather.get("sec_above50", 5) or 5),
        "spy_trend": float(weather.get("spy_trend", 0.5) or 0.5),
        "iwm_trend": float(weather.get("iwm_trend", 0.5) or 0.5),
        "narrow_leadership": float(weather.get("narrow_leadership", 0.5) or 0.5),
        "eqw_vs_cw": float(weather.get("eqw_vs_cw", 0.0) or 0.0),
        "tail": float(weather.get("tail", 0.5) or 0.5),
        "bank_health": float(weather.get("bank_health", 0.5) or 0.5),
        "trade": float(weather.get("trade", 0.5) or 0.5),
    }

    # ── crash ─────────────────────────────────────────────────────────────────
    crash_raw = sc.get("crash", {}) or risk_summary
    crash_score = float(crash_raw.get("crash_score", 0.0) or 0.0)
    risk_off = float(crash_raw.get("risk_off", 0.0) or 0.0)
    exec_score = float(exec_mode.get("score", 0.5) or 0.5)
    exec_label = exec_mode.get("label", "🟢 Add on Reset")

    crash = {
        "crash_score": _clamp(crash_score),
        "risk_off": _clamp(risk_off),
        "state": "🔴 ELEVATED" if crash_score >= 0.65 else ("🟡 WATCH" if crash_score >= 0.42 else "🟢 CALM"),
        "div_state": "aligned" if abs(crash_score - risk_off) < 0.08 else ("tail_heavier" if crash_score > risk_off else "broad_defensive"),
        "vol_stress": float(crash_raw.get("vol_stress", 0.0) or 0.0),
        "credit_stress": float(crash_raw.get("credit_stress", 0.0) or 0.0),
        "breadth_dmg": float(crash_raw.get("breadth_dmg", 0.3) or 0.3),
        "exec_score": _clamp(exec_score),
        "exec_mode": exec_label,
        "reasons": crash_raw.get("reasons", [])[:5],
        "crash_reasons": crash_raw.get("crash_reasons", [])[:4],
        # CNN + IWM (from v8 crash engine enhancements)
        "cnn_fear_greed": crash_raw.get("cnn_fear_greed"),
        "cnn_crash_signal": float(crash_raw.get("cnn_crash_signal", 0.0) or 0.0),
        "iwm_ath_distance": float(crash_raw.get("iwm_ath_distance", 0.0) or 0.0),
    }

    # ── rotation ──────────────────────────────────────────────────────────────
    em_rot = sc.get("em_rotation", {}) or {}
    rotation = {
        "em_score": float(em_rot.get("em_score", 0.5) or 0.5),
        "petro_score": float(em_rot.get("petro_score", 0.0) or 0.0),
        "top_ben": rotation_raw.get("top_beneficiary", "?"),
        "top_safe": rotation_raw.get("top_safe_harbor", "?"),
        "top_us_bucket": rotation_raw.get("top_us_bucket", "?"),
        "spill_us": rotation_raw.get("spillover_us", []),
        "spill_ihsg": rotation_raw.get("spillover_ihsg", []),
        "ben_rows": rotation_raw.get("beneficiary_rows", []),
        "safe_rows": rotation_raw.get("safe_harbor_rows", []),
        "best_meta": rotation_raw.get("best_meta", {}),
        "safe_meta": rotation_raw.get("safe_meta", {}),
        "us_breadth": float(weather.get("breadth", 0.5) or 0.5),
    }

    # ── ihsg ──────────────────────────────────────────────────────────────────
    ihsg_raw = new_snap.get("ihsg", {}) or {}
    ihsg_hub = ihsg_raw.get("market_hub", {}) or {}
    ihsg = {
        "ihsg_score": float(ihsg_hub.get("composite_score", 0.5) or 0.5),
        "exec_mode": ihsg_hub.get("exec_mode", "WATCH"),
        "jkse_1m": float(ihsg_hub.get("jkse_1m", float("nan")) or float("nan")),
        "jkse_3m": float(ihsg_hub.get("jkse_3m", float("nan")) or float("nan")),
        "usd_idr_1m": float(ihsg_hub.get("usd_idr_1m", float("nan")) or float("nan")),
        "usd_idr_pressure": float(ihsg_hub.get("usd_idr_pressure", 0.5) or 0.5),
        "foreign_flow": float(ihsg_hub.get("foreign_flow", 0.5) or 0.5),
        "flow_state": ihsg_hub.get("flow_state", "Neutral"),
        "bi_path": float(ihsg_hub.get("bi_path", 0.5) or 0.5),
        "bi_state": ihsg_hub.get("bi_state", "Neutral"),
        "em_regime": float(ihsg_hub.get("em_regime", 0.5) or 0.5),
        "bank_health": float(ihsg_hub.get("bank_health", 0.5) or 0.5),
        "comm_spill": float(ihsg_hub.get("comm_spill", 0.5) or 0.5),
        "breadth_ihsg": float(ihsg_hub.get("breadth_ihsg", 0.5) or 0.5),
        "top_sector": ihsg_hub.get("top_sector", "Banks"),
        "spill_ihsg": ihsg_hub.get("spillover_chain", []),
        "stock_rows": ihsg_raw.get("setups_now", {}).get("rows", []),
    }

    # ── analog ────────────────────────────────────────────────────────────────
    analog_item = analog_list[0] if analog_list else {}
    analog = {
        "label": analog_item.get("label", "No analog"),
        "similarity": float(analog_item.get("similarity", 0.5) or 0.5),
        "path_1m": analog_item.get("path_1m", "—"),
        "path_3m": analog_item.get("path_3m", "—"),
        "path_6m": analog_item.get("path_6m", "—"),
        "next_bias": analog_item.get("next_bias", ""),
        "impacts": analog_item.get("impacts", {}),
    }

    # ── scenarios ────────────────────────────────────────────────────────────
    scenarios_raw = new_snap.get("scenarios", {})
    scenarios = scenarios_raw.get("what_if_matrix", {}) if isinstance(scenarios_raw, dict) else {}

    # ── playbooks ────────────────────────────────────────────────────────────
    playbooks = sc.get("playbooks", []) or []

    # ── checklists ────────────────────────────────────────────────────────────
    cl_raw = sc.get("global_checklist", [])
    ihsg_cl = sc.get("asset_checklists", {}).get("ihsg", [])
    # Convert to tuple format (label, score, note) for backward compat
    def _to_tuples(items):
        out = []
        for item in (items or []):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append(tuple(item))
            elif isinstance(item, dict):
                out.append((item.get("label","?"), float(item.get("score",0.5) or 0.5), item.get("note","")))
        return out
    checklists = {"global": _to_tuples(cl_raw), "ihsg": _to_tuples(ihsg_cl)}

    # ── news_overlay ─────────────────────────────────────────────────────────
    events_raw = sc.get("event_bubble", []) or []
    news_events = [
        {"label": e.get("title","")[:40], "impact": e.get("impact","watch"), "countdown": e.get("countdown",""), "score": float(e.get("score",0.5) or 0.5), "type": e.get("type","EVENT")}
        for e in events_raw[:5]
    ]
    war_oil = float(news_state.get("war_oil", 0.0) or 0.0)
    policy_p = float(news_state.get("policy_pressure", 0.0) or 0.0)
    relief = float(news_state.get("relief", 0.0) or 0.0)
    dominant = max({"war_oil": war_oil, "policy_pressure": policy_p, "relief": relief}.items(), key=lambda x: x[1])
    if dominant[0] == "war_oil" and war_oil >= 0.55:
        news_label = "⚔️ Event-Lite: War/Oil Shock"; news_cls = "bad"
    elif dominant[0] == "policy_pressure" and policy_p >= 0.55:
        news_label = "📋 Event-Lite: Policy Pressure"; news_cls = "warn"
    elif relief >= 0.50:
        news_label = "🕊️ Event-Lite: Relief / De-escalation"; news_cls = "good"
    else:
        news_label = "😶 Event-Lite: Quiet"; news_cls = "neu"

    news_overlay = {
        "state": dominant[0],
        "label": news_label,
        "desc": news_state.get("description", "")[:100],
        "cls": news_cls,
        "war_oil": war_oil,
        "policy_pressure": policy_p,
        "relief": relief,
        "events": news_events,
    }

    # ── route ─────────────────────────────────────────────────────────────────
    master_routes = new_snap.get("master_routes", {}) or {}
    active_route = master_routes.get("active_route", {}) or {}
    route = {
        "primary": active_route.get("route_id", "growth_scare"),
        "primary_meta": active_route.get("meta", {}),
        "alt_meta": master_routes.get("alt_route_meta", {}),
        "long_allowed": True,
        "short_allowed": s_quad in ("Q3", "Q4"),
        "position_cap": 0.85 if crash_score < 0.42 else (0.60 if crash_score < 0.65 else 0.35),
        "route_bias": active_route.get("bias", "long"),
        "crash_score": crash_score,
    }

    # ── most_hated_rally ──────────────────────────────────────────────────────
    mhr = sc.get("most_hated_rally", {}) or {}
    most_hated_rally = {
        "clear_count": int(mhr.get("clear_count", 0) or 0),
        "hard_clear_count": int(mhr.get("hard_clear_count", 0) or 0),
        "stage": mhr.get("stage", "monitor"),
        "action": mhr.get("action", "Selective"),
        "posture": mhr.get("posture", ""),
        "branch_state": mhr.get("branch_state", "dormant"),
    }

    # ── top_drivers ──────────────────────────────────────────────────────────
    top_drivers_raw = sc.get("top_drivers", []) or []
    top_drivers = [
        {"label": d if isinstance(d, str) else d.get("label",""), 
         "score": 0.5, "tone": "neu", "why": "", "tag": ""}
        for d in top_drivers_raw[:6]
    ]

    # ── Build final snap (legacy format) ─────────────────────────────────────
    return {
        # Core regime + features
        "q": q,
        "f": f,
        "h": h,
        "crash": crash,
        "rotation": rotation,
        "ihsg": ihsg,
        "analog": analog,
        "scenarios": scenarios,
        "playbooks": playbooks,
        "checklists": checklists,
        "news_overlay": news_overlay,
        "route": route,
        "most_hated_rally": most_hated_rally,
        "top_drivers": top_drivers,
        "family": sc.get("rotation_family", "reflation"),

        # Prices and raw data (pass through)
        "prices": new_snap.get("_raw", {}).get("prices", {}),
        "fred": new_snap.get("_raw", {}).get("fred", {}),
        "price_meta": {},

        # Forward-looking engines (already in new format)
        "regime_transition": sc.get("regime_transition", {}),
        "regime_tickers": sc.get("regime_tickers", {}),
        "options_regime": sc.get("options_regime", {}),
        "narrative_discovery": sc.get("narrative_discovery", {}),
        "bei_flow": sc.get("bei_flow", {}),
        "broker_flow": sc.get("broker_flow", {}),
        "broker_confirm": sc.get("broker_confirm", {}),
        "data_freshness": sc.get("data_freshness", {}),
        "backtest_data": sc.get("backtest_data", {}),
        "intraday": sc.get("intraday", {}),
        "positions": sc.get("positions", {}),

        # Market sections (new format, UI reads via snap.get())
        "us": new_snap.get("us", {}),
        "ihsg_section": new_snap.get("ihsg", {}),
        "fx": new_snap.get("fx", {}),
        "commodities": new_snap.get("commodities", {}),
        "crypto": new_snap.get("crypto", {}),

        # Misc
        "position_sizing": {},
        "risk_ranges": {},
        "signal_strength": {},
        "asset_checklists": sc.get("asset_checklists", {}),
        "strong_weak_all": {},
        "macro_impact": sc.get("macro_impact_global", {}),
        "opportunities": new_snap.get("master_opportunities", {}),
        "forward_radar": sc.get("next_path", {}),
        "asset_translation": sc.get("asset_translation", {}),
        "decision_context": {
            "route_primary": route["primary"],
            "route_bias": route["route_bias"],
            "long_allowed": route["long_allowed"],
            "short_allowed": route["short_allowed"],
            "position_cap": route["position_cap"],
            "crash_score": crash_score,
        },
        "ts": new_snap.get("meta", {}).get("generated_at", "")[:16],
        "build_meta": new_snap.get("meta", {}),
        "_new_snap": new_snap,  # full new snap available if UI needs it
    }
