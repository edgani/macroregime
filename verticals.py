from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
import pandas as pd

from opportunity_kernel import FeatureSpec, aggregate_change, robust_change_reading, sequence_signature, vertical_readiness


MARKET_TO_VERTICAL = {
    "US": "US",
    "IHSG": "IHSG",
    "HK": "HK",
    "Hong Kong": "Hong Kong",
    "China": "China",
    "Europe": "Europe",
    "Taiwan": "Taiwan",
    "Crypto": "Crypto",
    "FX": "FX",
    "Commodity": "Commodity",
    "Index": "Index",
}


def feature_specs_for_market(market: str) -> List[FeatureSpec]:
    if market in {"US","HK","Hong Kong","China","Europe","Taiwan"}:
        return [FeatureSpec("revenue_growth_yoy",1,"fundamentals"), FeatureSpec("eps_growth_yoy",1,"fundamentals"), FeatureSpec("fcf_growth_yoy",1,"fundamentals"), FeatureSpec("gross_margin_change",1,"fundamentals")]
    if market == "IHSG":
        return [FeatureSpec("revenue_growth_yoy",1,"fundamentals"), FeatureSpec("eps_growth_yoy",1,"fundamentals"), FeatureSpec("transaction_score",1,"broker_flow"), FeatureSpec("foreign_net_adv_ratio",1,"foreign_flow")]
    if market == "Crypto":
        return [FeatureSpec("revenue_growth_30d",1,"usage"), FeatureSpec("holder_capture_ratio",1,"value_capture"), FeatureSpec("fdv_premium",-1,"dilution"), FeatureSpec("circulating_ratio",1,"supply")]
    # FX/commodities are intentionally not fed price-only pseudo-alpha features.
    return []


def available_families_from_row(row: Mapping[str, Any]) -> List[str]:
    market = str(row.get("market", ""))
    out = {"memory"}
    if market in {"US", "IHSG", "HK", "Hong Kong", "China", "Europe", "Taiwan"}:
        if any(pd.notna(row.get(k)) for k in ["revenue_growth_yoy", "eps_growth_yoy", "fcf_growth_yoy"]): out.add("fundamentals")
        if pd.notna(row.get("expectation_gap")): out.add("valuation")
    if market in {"US", "HK", "Hong Kong", "China", "Europe", "Taiwan"}:
        if str(row.get("expectation_revision_state", "")) != "DATA GATED": out.add("estimate_revisions")
        if pd.notna(row.get("expectation_optionality_score")): out.add("expectation_optionality")
    if market == "IHSG":
        if "READY" in str(row.get("transaction_status", "")).upper() or pd.notna(row.get("transaction_score")): out.add("broker_flow")
        if pd.notna(row.get("foreign_net_adv_ratio")): out.add("foreign_flow")
        if pd.notna(row.get("story_optionality_score")): out.add("narrative_optionality")
    if market == "Crypto":
        # Protocol economics are useful confirmation, but they are not spot flow, OI, funding or liquidation data.
        if pd.notna(row.get("revenue_growth_30d")) or pd.notna(row.get("holder_capture_ratio")): out.add("onchain_confirmation")
    return sorted(out)


def enrich_with_memory(df: pd.DataFrame, memory: Any) -> pd.DataFrame:
    """Attach descriptive change states using only snapshots that existed before/at refresh time."""
    if df.empty:
        return df
    out = df.copy()
    rows = []
    for _, r in out.iterrows():
        market, entity = str(r.get("market","")), str(r.get("symbol",""))
        specs = feature_specs_for_market(market)
        hist = memory.history(entity, market, limit=90) if specs else pd.DataFrame()
        readings = []
        for spec in specs:
            vals = hist.get(spec.name, pd.Series(dtype=float)).tolist() if not hist.empty and spec.name in hist else []
            vals.append(r.get(spec.name))
            readings.append(robust_change_reading(vals, spec))
        agg = aggregate_change(readings)
        states = memory.states(entity, market, limit=12)
        available = available_families_from_row(r)
        ready = vertical_readiness(market, available)
        d = dict(r)
        d.update(agg)
        d.update({
            "sequence_signature": sequence_signature(states + [agg.get("change_state","")]),
            "memory_observations": int(len(hist)),
            "vertical_status": ready["status"],
            "vertical_core_coverage": ready["core_coverage"],
            "vertical_missing_core": ", ".join(ready["missing_core"]),
        })
        rows.append(d)
    return pd.DataFrame(rows)


def snapshot_features(row: Mapping[str, Any]) -> Dict[str, Any]:
    keys = {
        "US": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","story_optionality_score","expectation_optionality_score","expectation_revision_score","evidence_families","deterioration_families","expectation_gap"],
        "HK": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","evidence_families","deterioration_families","expectation_gap"],
        "Hong Kong": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","evidence_families","deterioration_families","expectation_gap"],
        "China": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","evidence_families","deterioration_families","expectation_gap"],
        "Europe": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","evidence_families","deterioration_families","expectation_gap"],
        "Taiwan": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","gross_margin_change","net_margin_change","evidence_families","deterioration_families","expectation_gap"],
        "IHSG": ["price","revenue_growth_yoy","eps_growth_yoy","fcf_growth_yoy","net_margin_change","story_optionality_score","story_credibility_score","transaction_score","foreign_net_adv_ratio","evidence_families","deterioration_families","expectation_gap"],
        "Crypto": ["price","market_cap","revenue_growth_30d","holder_capture_ratio","fdv_premium","circulating_ratio","evidence_families","deterioration_families"],
        "FX": ["price"],
        "Commodity": ["price"],
        "Index": ["price"],
    }.get(str(row.get("market","")), ["price"])
    return {k: row.get(k) for k in keys}
