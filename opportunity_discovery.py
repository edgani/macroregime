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
    market = str(row.get("market", ""))
    arch: List[str] = []
    rg, eg, gm, fcf = map(_f, [row.get("revenue_growth_yoy"),row.get("eps_growth_yoy"),row.get("gross_margin_change"),row.get("fcf_growth_yoy")])
    capex = _f(row.get("capex_to_revenue")); gap = _f(row.get("expectation_gap")); tx = _f(row.get("transaction_score"))
    if math.isfinite(rg) and rg > 0.12: arch.append("REVENUE_INFLECTION")
    if math.isfinite(gm) and gm > 0.015: arch.append("MARGIN_INFLECTION")
    if math.isfinite(capex) and capex > 0.10 and math.isfinite(rg) and rg > 0: arch.append("CAPEX_BENEFICIARY")
    if math.isfinite(gap) and gap >= 0.20: arch.append("VALUATION_DISLOCATION")
    if market == "IHSG" and math.isfinite(tx) and tx >= 65: arch.append("POSITIONING_SQUEEZE")
    if market == "Crypto":
        rr = _f(row.get("revenue_growth_30d")); hc = _f(row.get("holder_capture_ratio")); fdv = _f(row.get("fdv_premium"))
        if math.isfinite(rr) and rr > 0.15: arch.append("TOKEN_REVENUE_INFLECTION")
        if math.isfinite(hc) and hc > 0: arch.append("STRUCTURAL_COMPOUNDER")
        if math.isfinite(fdv) and fdv < 0.25: arch.append("SUPPLY_SCARCITY")
    if market == "FX": arch.append("FX_POLICY_DISLOCATION")
    if market == "Commodity": arch.append("COMMODITY_SUPPLY_SHOCK")
    if not arch and (math.isfinite(rg) or math.isfinite(eg) or math.isfinite(fcf)):
        arch.append("UNDEROWNED_GROWTH")
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
            "invalidation":"backlog/order growth decelerates; capacity catches up; capex cycle rolls over",
        }
    if any(k in notes for k in ["memory", "storage", "ssd", "nand"]):
        return {
            "theme":"MEMORY / STORAGE SUPPLY-DEMAND INFLECTION","driver":"AI/cloud storage demand + disciplined supply",
            "first_order_effect":"NAND/DRAM demand tightens relative to available bits",
            "second_order_effect":"pricing and producer gross margin improve",
            "bottleneck":"memory supply / qualified capacity","beneficiary":symbol,
            "revenue_link":"higher bit shipments / ASP","margin_link":"pricing operating leverage",
            "catalyst":"pricing, inventory normalization, earnings guidance","invalidation":"supply response outruns demand or inventory rebuild stalls",
        }
    if any(k in notes for k in ["cpo", "plantation", "palm"]):
        return {
            "theme":"CPO SUPPLY / POLICY DISLOCATION","driver":"CPO supply, biodiesel demand, policy",
            "first_order_effect":"CPO balance tightens/loosens","second_order_effect":"realized pricing changes producer cash flow",
            "bottleneck":"plantation supply response / inventories","beneficiary":symbol,
            "revenue_link":"realized CPO price x volume","margin_link":"price-cost spread",
            "catalyst":"production data, export policy, biodiesel mandate, earnings","invalidation":"supply recovery / policy reversal / demand destruction",
        }
    if market == "Crypto":
        return {
            "theme":"CRYPTO VALUE-CAPTURE INFLECTION","driver":"protocol usage / fee generation",
            "first_order_effect":"fees/revenue change","second_order_effect":"holder capture vs dilution determines net accrual",
            "bottleneck":"real usage / tokenholder capture / supply overhang","beneficiary":symbol,
            "revenue_link":"protocol fees/revenue","margin_link":"not applicable; tokenholder capture substitutes",
            "catalyst":"revenue acceleration, buyback/burn/distribution, supply change","invalidation":"usage/revenue fades or dilution overwhelms capture",
        }
    if market == "FX":
        return {"theme":"FX RELATIVE-MACRO / POLICY DISLOCATION","driver":"relative rates / policy / BoP / positioning","first_order_effect":"relative carry and policy expectations shift","second_order_effect":"valuation/positioning reprices","bottleneck":"causal FX data currently required","beneficiary":symbol,"revenue_link":"N/A","margin_link":"N/A","catalyst":"central-bank / intervention / macro release","invalidation":"relative macro reverses"}
    if market == "Commodity":
        return {"theme":"PHYSICAL COMMODITY DISLOCATION","driver":"physical supply/demand / inventory / curve","first_order_effect":"balance tightens or loosens","second_order_effect":"spot/curve reprices","bottleneck":"physical balance evidence required","beneficiary":symbol,"revenue_link":"N/A","margin_link":"N/A","catalyst":"inventory / production / policy / weather","invalidation":"physical balance reverses"}
    return {
        "theme": f"{sector.upper() if sector else market.upper()} FUNDAMENTAL INFLECTION",
        "driver":"observable fundamental / earnings / policy change",
        "first_order_effect":"revenue/earnings expectations change",
        "second_order_effect":"valuation and capital allocation reprice",
        "bottleneck":"economic capture must be verified",
        "beneficiary":symbol,"revenue_link":"revenue growth / segment exposure",
        "margin_link":"margin / FCF inflection","catalyst":"earnings / guidance / estimate revisions",
        "invalidation":"fundamental inflection reverses or was already priced",
    }


def component_scores(row: Mapping[str, Any], macro_context: Mapping[str, Any]) -> Dict[str, Any]:
    rg = _score_signed_change(row.get("revenue_growth_yoy"), 0.20)
    eg = _score_signed_change(row.get("eps_growth_yoy"), 0.35)
    gm = _score_signed_change(row.get("gross_margin_change"), 0.04)
    fcf = _score_signed_change(row.get("fcf_growth_yoy"), 0.50)
    change = _f(row.get("change_score"))
    inf_vals=[x for x in [rg,eg,gm,fcf,change] if math.isfinite(x)]
    inflection=float(np.median(inf_vals)) if inf_vals else math.nan

    # Capture intentionally depends on direct economics, not narrative mentions.
    rev_exp = 75.0 if math.isfinite(_f(row.get("revenue_growth_yoy"))) else math.nan
    margin_exp = gm
    cash_quality = 70.0 if math.isfinite(_f(row.get("fcf_growth_yoy"))) else math.nan
    capture_vals=[x for x in [rev_exp,margin_exp,cash_quality] if math.isfinite(x)]
    capture=float(np.mean(capture_vals)) if capture_vals else math.nan

    chain = infer_theme_chain(row)
    bottleneck = 70.0 if "required" not in chain["bottleneck"].lower() else math.nan
    if any(k in chain["theme"] for k in ["BOTTLENECK","SUPPLY","MEMORY","CPO"]): bottleneck = 80.0

    gap=_f(row.get("expectation_gap")); expectation=_clip(50+100*gap) if math.isfinite(gap) else math.nan
    val_conf=str(row.get("valuation_confidence","")).upper()
    valuation = expectation if val_conf in {"HIGH","MEDIUM"} and math.isfinite(expectation) else math.nan

    catalyst=65.0 if chain.get("catalyst") else math.nan
    tx=_f(row.get("transaction_score")); pos = tx if math.isfinite(tx) else math.nan
    macro_label=str(macro_context.get("action_label") or macro_context.get("regime") or "").upper()
    macro = 50.0
    if "RISK-ON" in macro_label: macro=70.0
    elif any(k in macro_label for k in ["DEFENSIVE","CRISIS"]): macro=30.0
    elif "GATED" in macro_label: macro=math.nan

    cash=_f(row.get("total_cash")); debt=_f(row.get("total_debt")); capex_ratio=_f(row.get("capex_to_revenue")); fin=str(row.get("financing_risk","")).upper()
    balance_sheet=math.nan
    if math.isfinite(cash) or math.isfinite(debt):
        c=0.0 if not math.isfinite(cash) else max(cash,0.0); d=0.0 if not math.isfinite(debt) else max(debt,0.0)
        balance_sheet=_clip(50+50*math.tanh((c-d)/max(c+d,1.0)))
    capital_intensity=_clip(100-250*capex_ratio) if math.isfinite(capex_ratio) else math.nan
    execution_risk=30.0 if fin=="HIGH" else (50.0 if fin in {"MEDIUM","DATA GATED"} else 70.0)
    theme_revenue_exposure=75.0 if math.isfinite(_f(row.get("revenue_growth_yoy"))) and "required" not in chain["bottleneck"].lower() else math.nan
    competitive_position=75.0 if math.isfinite(bottleneck) and bottleneck>=75 else (60.0 if math.isfinite(capture) else math.nan)
    valuation_risk=(100.0-valuation) if math.isfinite(_f(valuation)) else math.nan
    scores={
        "inflection_score":inflection,"capture_score":capture,"bottleneck_score":bottleneck,
        "expectation_gap_score":expectation,"catalyst_score":catalyst,"valuation_score":valuation,
        "positioning_score":pos,"macro_alignment":macro,
        "theme_revenue_exposure":theme_revenue_exposure,
        "incremental_revenue_sensitivity":rg,
        "incremental_margin_sensitivity":gm,
        "balance_sheet_quality":balance_sheet,
        "capital_intensity_score":capital_intensity,
        "execution_quality_score":execution_risk,
        "competitive_position":competitive_position,
        "valuation_risk":valuation_risk,
        "score_method":"transparent heuristic research components; not calibrated probability",
    }
    weighted=[]; total_w=0.0
    for key,w in WEIGHTS.items():
        v=scores.get(key if key!="expectation_gap" else "expectation_gap_score")
        if math.isfinite(_f(v)):
            weighted.append(w*float(v)); total_w += w
    scores["opportunity_score"] = sum(weighted)/total_w if total_w >= 0.55 else math.nan
    scores["score_coverage"] = total_w
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
    opp=_f(scores.get("opportunity_score")); crowd=_f(row.get("crowding_score")); det=_f(row.get("deterioration_families"))
    if any(k in action for k in ["SELL","AVOID"]) or (math.isfinite(det) and det>=3 and "DETERIOR" in stage): return "INVALIDATED"
    if math.isfinite(crowd) and crowd>=80: return "CROWDED"
    if "HIGH-CONVICTION" in stage or (math.isfinite(opp) and opp>=78): return "HIGH_CONVICTION"
    if "CONFIRMED" in stage or "EXPECTATION INFLECTION" in stage or (math.isfinite(opp) and opp>=68): return "PROVING"
    if "WATCH" in stage or "EMERGING" in ch or "UNUSUAL" in ch or (math.isfinite(opp) and opp>=58): return "EMERGING"
    return "DISCOVERED"


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
