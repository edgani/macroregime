from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from opportunity_longitudinal import OpportunityMemory


EQUITY_MARKETS = {"US", "IHSG", "HK", "Hong Kong", "China", "Europe", "Taiwan"}
SUPPORTED_MARKETS = sorted(EQUITY_MARKETS | {"Crypto", "FX", "Commodity", "Index"})

BENCHMARKS = {
    "US": "SPY", "IHSG": "^JKSE", "HK": "^HSI", "Hong Kong": "^HSI",
    "China": "000300.SS", "Europe": "^STOXX50E", "Taiwan": "^TWII",
    "Crypto": "BTC-USD", "FX": "DXY / relative pair context", "Commodity": "asset-specific physical/commodity benchmark",
    "Index": "market-specific index",
}

FAILURE_CODES = {
    "GOOD_NARRATIVE_BAD_ECONOMICS", "REVENUE_EXPOSURE_TOO_SMALL", "VALUATION_TOO_EXPENSIVE",
    "CATALYST_DELAYED", "MACRO_REGIME_CHANGED", "POSITIONING_TOO_CROWDED", "EARNINGS_DISAPPOINTED",
    "MARGIN_FAILED_TO_EXPAND", "CAPEX_OVERRUN", "SUPPLY_RESPONSE_ARRIVED", "COMPETITOR_TOOK_SHARE", "POLICY_REVERSED",
}

WEIGHTS = {
    "inflection": 0.20,
    "capture": 0.20,
    "bottleneck": 0.15,
    "expectation_gap": 0.15,
    "catalyst": 0.10,
    "valuation": 0.10,
    "positioning": 0.05,
    "macro_alignment": 0.05,
}


def _f(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _clip(x: Any, lo: float = 0.0, hi: float = 100.0) -> float:
    v = _f(x)
    return max(lo, min(hi, v)) if math.isfinite(v) else math.nan


def _score_signed_change(x: Any, scale: float) -> float:
    v = _f(x)
    if not math.isfinite(v):
        return math.nan
    return _clip(50.0 + 50.0 * math.tanh(v / max(scale, 1e-9)))


def classify_archetypes(row: Mapping[str, Any]) -> List[str]:
    """Evidence-gated archetypes; market membership alone is never an archetype."""
    market = str(row.get("market", "")); arch: List[str] = []
    rg, gm = map(_f, [row.get("revenue_growth_yoy"),row.get("gross_margin_change")])
    gap = _f(row.get("expectation_gap")); tx = _f(row.get("transaction_score"))
    ch=str(row.get("change_state","")).upper(); accel=_f(row.get("change_acceleration"))
    inflect = ch in {"UNUSUAL","EMERGING","ACCELERATING"} or (math.isfinite(accel) and accel>0.10)
    if math.isfinite(rg) and rg > 0.12 and inflect: arch.append("REVENUE_INFLECTION")
    if math.isfinite(gm) and gm > 0.015 and inflect: arch.append("MARGIN_INFLECTION")
    # High company capex means the company spends capex; it does not prove it benefits
    # economically from somebody else's capex boom.
    if bool(row.get("capex_beneficiary_evidence")): arch.append("CAPEX_BENEFICIARY")
    if math.isfinite(gap) and gap >= 0.20: arch.append("VALUATION_DISLOCATION")
    if market == "IHSG" and math.isfinite(tx) and tx >= 65: arch.append("POSITIONING_SQUEEZE")
    if market == "Crypto":
        rr = _f(row.get("revenue_growth_30d")); hc = _f(row.get("holder_capture_ratio"))
        if math.isfinite(rr) and rr > 0.15: arch.append("TOKEN_REVENUE_INFLECTION")
        if math.isfinite(hc) and hc > 0 and math.isfinite(rr) and rr>=0: arch.append("STRUCTURAL_COMPOUNDER")
        if bool(row.get("supply_scarcity_evidence")): arch.append("SUPPLY_SCARCITY")
    if market == "FX" and bool(row.get("fx_policy_dislocation_evidence")): arch.append("FX_POLICY_DISLOCATION")
    if market == "Commodity" and bool(row.get("commodity_supply_shock_evidence")): arch.append("COMMODITY_SUPPLY_SHOCK")
    if not arch and market in EQUITY_MARKETS and inflect and math.isfinite(rg): arch.append("UNDEROWNED_GROWTH")
    return list(dict.fromkeys(arch))


def infer_theme_chain(row: Mapping[str, Any]) -> Dict[str, str]:
    market = str(row.get("market", "")); notes = str(row.get("notes", "") or "").lower(); sector = str(row.get("sector", "") or "")
    symbol = str(row.get("symbol", ""))
    if any(k in notes for k in ["data-center power", "grid", "electrical"]):
        return {
            "theme":"DATA CENTER POWER / GRID BOTTLENECK","driver":"AI / data-center capex",
            "first_order_effect":"electrical load and grid interconnection demand rises",
            "second_order_effect":"transformer / switchgear / generation capacity tightens",
            "bottleneck":"power equipment / interconnection / generation capacity",
            "beneficiary":symbol,"revenue_link":"orders / backlog / equipment demand",
            "margin_link":"scarcity + pricing power can improve mix/margins",
            "catalyst":"earnings, backlog, order wins, capacity expansion",
            "invalidation":"backlog/order growth decelerates; capacity catches up; capex cycle rolls over","chain_evidence":"MAPPED",
        }
    if any(k in notes for k in ["memory", "storage", "ssd", "nand"]):
        return {
            "theme":"MEMORY / STORAGE SUPPLY-DEMAND INFLECTION","driver":"AI/cloud storage demand + disciplined supply",
            "first_order_effect":"NAND/DRAM demand tightens relative to available bits",
            "second_order_effect":"pricing and producer gross margin improve",
            "bottleneck":"memory supply / qualified capacity","beneficiary":symbol,
            "revenue_link":"higher bit shipments / ASP","margin_link":"pricing operating leverage",
            "catalyst":"pricing, inventory normalization, earnings guidance","invalidation":"supply response outruns demand or inventory rebuild stalls","chain_evidence":"MAPPED",
        }
    if any(k in notes for k in ["cpo", "plantation", "palm"]):
        return {
            "theme":"CPO SUPPLY / POLICY DISLOCATION","driver":"CPO supply, biodiesel demand, policy",
            "first_order_effect":"CPO balance tightens/loosens","second_order_effect":"realized pricing changes producer cash flow",
            "bottleneck":"plantation supply response / inventories","beneficiary":symbol,
            "revenue_link":"realized CPO price x volume","margin_link":"price-cost spread",
            "catalyst":"production data, export policy, biodiesel mandate, earnings","invalidation":"supply recovery / policy reversal / demand destruction","chain_evidence":"MAPPED",
        }
    if market == "Crypto":
        return {
            "theme":"CRYPTO VALUE-CAPTURE INFLECTION","driver":"protocol usage / fee generation",
            "first_order_effect":"fees/revenue change","second_order_effect":"holder capture vs dilution determines net accrual",
            "bottleneck":"real usage / tokenholder capture / supply overhang","beneficiary":symbol,
            "revenue_link":"protocol fees/revenue","margin_link":"not applicable; tokenholder capture substitutes",
            "catalyst":"revenue acceleration, buyback/burn/distribution, supply change","invalidation":"usage/revenue fades or dilution overwhelms capture","chain_evidence":"UNVERIFIED",
        }
    if market == "FX":
        return {"theme":"FX RELATIVE-MACRO / POLICY DISLOCATION","driver":"relative rates / policy / BoP / positioning","first_order_effect":"relative carry and policy expectations shift","second_order_effect":"valuation/positioning reprices","bottleneck":"causal FX data currently required","beneficiary":symbol,"revenue_link":"N/A","margin_link":"N/A","catalyst":"central-bank / intervention / macro release","invalidation":"relative macro reverses","chain_evidence":"UNVERIFIED"}
    if market == "Commodity":
        return {"theme":"PHYSICAL COMMODITY DISLOCATION","driver":"physical supply/demand / inventory / curve","first_order_effect":"balance tightens or loosens","second_order_effect":"spot/curve reprices","bottleneck":"physical balance evidence required","beneficiary":symbol,"revenue_link":"N/A","margin_link":"N/A","catalyst":"inventory / production / policy / weather","invalidation":"physical balance reverses","chain_evidence":"UNVERIFIED"}
    return {
        "theme": f"{sector.upper() if sector else market.upper()} FUNDAMENTAL INFLECTION",
        "driver":"observable fundamental / earnings / policy change",
        "first_order_effect":"revenue/earnings expectations change",
        "second_order_effect":"valuation and capital allocation reprice",
        "bottleneck":"economic capture must be verified",
        "beneficiary":symbol,"revenue_link":"revenue growth / segment exposure",
        "margin_link":"margin / FCF inflection","catalyst":"earnings / guidance / estimate revisions",
        "invalidation":"fundamental inflection reverses or was already priced","chain_evidence":"UNVERIFIED",
    }


def component_scores(row: Mapping[str, Any], macro_context: Mapping[str, Any]) -> Dict[str, Any]:
    # Inflection prioritises change/acceleration. Absolute growth can support it but
    # cannot by itself manufacture a high score.
    rg = _score_signed_change(row.get("revenue_growth_yoy"), 0.20)
    eg = _score_signed_change(row.get("eps_growth_yoy"), 0.35)
    gm = _score_signed_change(row.get("gross_margin_change"), 0.04)
    fcf = _score_signed_change(row.get("fcf_growth_yoy"), 0.50)
    change = _f(row.get("change_score")); accel=_f(row.get("change_acceleration"))
    level_vals=[x for x in [rg,eg,gm,fcf] if math.isfinite(x)]
    level=float(np.median(level_vals)) if level_vals else math.nan
    if math.isfinite(change):
        inflection=0.70*change + 0.30*level if math.isfinite(level) else change
    elif math.isfinite(accel):
        inflection=_clip(50+30*math.tanh(accel))
    else:
        inflection=math.nan

    chain = infer_theme_chain(row); chain_verified=str(chain.get("chain_evidence","")).upper()=="MAPPED"
    # Economic capture must be causal, not just 'revenue exists'.  Explicit exposure
    # fields win; a mapped chain + observed revenue/margin change is a weaker fallback.
    rev_direct=_f(row.get("theme_revenue_exposure_score")); margin_direct=_f(row.get("margin_capture_score"))
    if not math.isfinite(rev_direct) and chain_verified and math.isfinite(rg): rev_direct=rg
    if not math.isfinite(margin_direct) and chain_verified and math.isfinite(gm): margin_direct=gm
    capture_vals=[x for x in [rev_direct,margin_direct] if math.isfinite(x)]
    capture=float(np.mean(capture_vals)) if capture_vals else math.nan

    explicit_bneck=_f(row.get("bottleneck_evidence_score"))
    bottleneck=explicit_bneck if math.isfinite(explicit_bneck) else (75.0 if chain_verified else math.nan)

    gap=_f(row.get("expectation_gap")); expectation=_clip(50+100*gap) if math.isfinite(gap) else math.nan
    val_conf=str(row.get("valuation_confidence","")).upper()
    valuation = expectation if val_conf in {"HIGH","MEDIUM"} and math.isfinite(expectation) else math.nan

    # Generic text 'next earnings' is not a catalyst-quality observation.
    catalyst=_f(row.get("catalyst_quality_score"))
    tx=_f(row.get("transaction_score")); pos = tx if math.isfinite(tx) else math.nan
    # Macro is timing/risk context unless opportunity-specific alignment evidence exists.
    macro=_f(row.get("macro_alignment_score"))

    cash=_f(row.get("total_cash")); debt=_f(row.get("total_debt")); capex_ratio=_f(row.get("capex_to_revenue")); fin=str(row.get("financing_risk","")).upper()
    balance_sheet=math.nan
    if math.isfinite(cash) and math.isfinite(debt):
        c=max(cash,0.0); d=max(debt,0.0); balance_sheet=_clip(50+50*math.tanh((c-d)/max(c+d,1.0)))
    capital_intensity=_clip(100-250*capex_ratio) if math.isfinite(capex_ratio) else math.nan
    execution_quality=30.0 if fin=="HIGH" else (60.0 if fin=="MEDIUM" else (70.0 if fin=="LOW" else math.nan))
    competitive_position=_f(row.get("competitive_position_score"))
    valuation_risk=(100.0-valuation) if math.isfinite(valuation) else math.nan
    scores={
        "inflection_score":inflection,"capture_score":capture,"bottleneck_score":bottleneck,
        "expectation_gap_score":expectation,"catalyst_score":catalyst,"valuation_score":valuation,
        "positioning_score":pos,"macro_alignment":macro,
        "theme_revenue_exposure":rev_direct,
        "incremental_revenue_sensitivity":rg,
        "incremental_margin_sensitivity":gm,
        "balance_sheet_quality":balance_sheet,
        "capital_intensity_score":capital_intensity,
        "execution_quality_score":execution_quality,
        "competitive_position":competitive_position,
        "valuation_risk":valuation_risk,
        "score_method":"transparent evidence-gated research components; not calibrated probability",
    }
    weighted=[]; total_w=0.0
    for key,w in WEIGHTS.items():
        v=scores.get(key if key!="expectation_gap" else "expectation_gap_score")
        if math.isfinite(_f(v)):
            weighted.append(w*float(v)); total_w += w
    # Economic capture is mandatory.  Without it, an attractive narrative/valuation
    # cannot become a numerical Opportunity Score.
    scores["opportunity_score"] = (sum(weighted)/total_w if total_w>=0.55 and math.isfinite(capture) else math.nan)
    scores["score_coverage"] = total_w
    scores["capture_required_pass"] = bool(math.isfinite(capture))
    return scores


def expectation_state(row: Mapping[str, Any]) -> str:
    gap=_f(row.get("expectation_gap")); crowd=_f(row.get("crowding_score")); action=str(row.get("research_action","")).upper()
    if math.isfinite(crowd) and crowd >= 80: return "CROWDED"
    if math.isfinite(gap):
        if gap >= 0.25: return "UNDERPRICED"
        if gap <= -0.20: return "OVERPRICED"
        return "FAIRLY_PRICED"
    if "GATED" in action: return "UNKNOWN"
    return "UNKNOWN"


def lifecycle_from_row(row: Mapping[str, Any], scores: Mapping[str, Any]) -> str:
    action=str(row.get("research_action","")).upper(); stage=str(row.get("stage","")).upper(); ch=str(row.get("change_state","")).upper()
    opp=_f(scores.get("opportunity_score")); crowd=_f(row.get("crowding_score")); det=_f(row.get("deterioration_families")); readiness=str(row.get("vertical_status","GATED")).upper()
    if any(k in action for k in ["SELL","AVOID"]) or (math.isfinite(det) and det>=3 and "DETERIOR" in stage): return "INVALIDATED"
    if math.isfinite(crowd) and crowd>=80: return "CROWDED"
    candidate="DISCOVERED"
    if "HIGH-CONVICTION" in stage or (math.isfinite(opp) and opp>=78): candidate="HIGH_CONVICTION"
    elif "CONFIRMED" in stage or "EXPECTATION INFLECTION" in stage or (math.isfinite(opp) and opp>=68): candidate="PROVING"
    elif "WATCH" in stage or "EMERGING" in ch or "UNUSUAL" in ch or (math.isfinite(opp) and opp>=58): candidate="EMERGING"
    # Readiness is a hard lifecycle ceiling; incomplete core data cannot be described as
    # high conviction merely because other features are strong.
    if readiness=="GATED": return "DISCOVERED"
    if readiness=="PARTIAL" and candidate in {"HIGH_CONVICTION","PRICING_IN","MATURE"}: return "PROVING"
    return candidate


def meaningful_detection(row: Mapping[str, Any], scores: Mapping[str, Any]) -> bool:
    market=str(row.get("market","")); ev=_f(row.get("evidence_families")); ch=_f(row.get("change_score")); opp=_f(scores.get("opportunity_score"))
    if market in {"FX","Commodity"} and "GATED" in str(row.get("market_model_status","")).upper():
        return False
    return bool((math.isfinite(ev) and ev>=2) or (math.isfinite(ch) and ch>=62) or (math.isfinite(opp) and opp>=58))


def build_event_payload(row: Mapping[str, Any], macro_context: Mapping[str, Any], now: Any = None) -> Dict[str, Any]:
    chain=infer_theme_chain(row); arch=classify_archetypes(row); scores=component_scores(row,macro_context)
    fundamentals={k:row.get(k) for k in [
        "revenue_growth_yoy","eps_growth_yoy","gross_margin","gross_margin_change","net_margin","net_margin_change","fcf_ttm","fcf_growth_yoy",
        "capex_ttm","capex_to_revenue","rd_to_revenue","shares_change_yoy","revenue_growth_30d","holder_capture_ratio","fdv_premium","circulating_ratio",
    ]}
    expectation={k:row.get(k) for k in [
        "expectation_gap","valuation_confidence","valuation_basis","valuation_mode","forward_pe","trailing_pe","eps_estimate_next_year",
        "eps_estimate_next_year_30d_ago","eps_revisions_up_30d","eps_revisions_down_30d","transaction_score","transaction_state",
        "upside_case_value","base_case_value","downside_case_value",
    ]}
    px=_f(row.get("price")); bull=_f(row.get("upside_case_value")); bear=_f(row.get("downside_case_value"))
    expectation["expected_upside"]=(bull/px-1) if math.isfinite(px) and px>0 and math.isfinite(bull) else math.nan
    expectation["expected_downside"]=(bear/px-1) if math.isfinite(px) and px>0 and math.isfinite(bear) else math.nan
    if math.isfinite(_f(expectation["expected_upside"])) and math.isfinite(_f(expectation["expected_downside"])) and _f(expectation["expected_downside"])<0:
        expectation["asymmetry_ratio"]=_f(expectation["expected_upside"])/abs(_f(expectation["expected_downside"]))
    else:
        expectation["asymmetry_ratio"]=math.nan
    expectation["expectation_state"]=expectation_state(row)
    thesis=(f"{chain['driver']} → {chain['first_order_effect']} → {chain['second_order_effect']} → "
            f"{chain['bottleneck']} → {chain['beneficiary']}. Economic capture must be visible in revenue/margin or value-capture data.")
    return {
        "first_seen_time": now or row.get("refreshed_at_utc") or pd.Timestamp.utcnow(),
        "first_unusual_time": now or row.get("refreshed_at_utc") if str(row.get("change_state","")).upper() in {"UNUSUAL","EMERGING","ACCELERATING"} else None,
        "asset":row.get("name") or row.get("symbol"),"symbol":row.get("symbol"),"market":row.get("market"),
        "asset_class":"Equity" if str(row.get("market")) in EQUITY_MARKETS else row.get("market"),
        "country":row.get("country") or row.get("market"),"sector":row.get("sector"),"industry":row.get("industry"),
        "benchmark":BENCHMARKS.get(str(row.get("market")),"market-specific benchmark"),
        "theme":chain["theme"],"archetypes":arch,"time_horizon":row.get("time_horizon") or "1–2Q / archetype-dependent",
        "price":row.get("price"),"market_cap":row.get("market_cap"),
        **chain,"thesis":thesis,"macro_context":dict(macro_context),"fundamental_change":fundamentals,"expectation":expectation,
        "scores":scores,"snapshot":dict(row),"source_quality":row.get("data_quality"),
    }


def sync_opportunities(scan: pd.DataFrame, memory: OpportunityMemory, macro_context: Mapping[str, Any], now: Any = None) -> pd.DataFrame:
    if scan is None or scan.empty:
        return memory.events_frame(active_only=True)
    ts=now or pd.Timestamp.utcnow()
    for _,row in scan.iterrows():
        payload=build_event_payload(row,macro_context,ts)
        scores=payload["scores"]
        if not meaningful_detection(row,scores):
            continue
        event=memory.create_event(payload)
        event_id=event.get("event_id")
        if not event_id: continue
        lifecycle=lifecycle_from_row(row,scores)
        memory.record_state(event_id,lifecycle,observed_at_utc=ts,price=row.get("price"),market_cap=row.get("market_cap"),reason=f"live scan: {row.get('research_action','')} / {row.get('stage','')}",snapshot=dict(row))
        # Conservative automatic failure taxonomy: only label what current evidence directly shows.
        if lifecycle=="INVALIDATED":
            if _f(row.get("gross_margin_change")) < -0.03: memory.label_failure(event_id,"MARGIN_FAILED_TO_EXPAND","gross margin deterioration observed",ts)
            if _f(row.get("expectation_gap")) < -0.25: memory.label_failure(event_id,"VALUATION_TOO_EXPENSIVE","expectation gap materially negative",ts)
    return memory.events_frame(active_only=True)
