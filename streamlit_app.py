"""War Room OS v3 — Streamlit workstation.

Read-only research workstation over the fail-closed v3 kernel (src/warroom_v3).
Nothing on this UI promotes evidence: every payload stays DESCRIPTIVE_ONLY /
RESEARCH_ONLY and the planner emits OPERATOR_PLANNING_ONLY structural templates.

Run:  streamlit run streamlit_app.py
Root: WARROOM_ROOT env var, else the repository root (this file's directory).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_SRC = str(ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import streamlit as st

from warroom_v3.hashing import canonical_hash
from warroom_v3.runtime import get_scope_dashboard_payload, system_status
from warroom_v3.trading import (
    TradeDirection,
    build_structural_template,
    calculate_manual_trade_plan,
)

ASSETS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = ("15m", "1h", "4h", "1d")


def _root() -> Path:
    return Path(os.environ.get("WARROOM_ROOT") or ROOT)


def _load_status(root: Path) -> dict:
    try:
        return system_status(root)
    except Exception as exc:  # empty or partial store must never crash the UI
        return {"mode": "RESEARCH_ONLY", "seal_status": "UNAVAILABLE", "scopes": [],
                "store_errors": [f"{type(exc).__name__}: {exc}"]}


def _load_payload(root: Path, asset: str, timeframe: str) -> dict:
    try:
        return get_scope_dashboard_payload(root, asset=asset, timeframe=timeframe)
    except Exception as exc:
        return {"asset": asset, "timeframe": timeframe, "status": "UNAVAILABLE",
                "bars": 0, "reason_codes": [f"{type(exc).__name__}: {exc}"],
                "actionable": False, "claim_ceiling": "DESCRIPTIVE_ONLY"}


def page_market_overview(root: Path) -> None:
    st.header("Market Overview")
    status = _load_status(root)
    st.caption(
        f"mode={status.get('mode', 'UNKNOWN')} · seal={status.get('seal_status', 'UNKNOWN')} · "
        "claim ceiling: DESCRIPTIVE_ONLY — nothing here is a trade recommendation"
    )
    asset = st.selectbox("Asset", ASSETS, key="overview_asset")
    payloads = {tf: _load_payload(root, asset, tf) for tf in TIMEFRAMES}

    cols = st.columns(4)
    for col, tf in zip(cols, TIMEFRAMES):
        payload = payloads[tf]
        states = payload.get("component_states") or {}
        close = (states.get("mqa_benchmarks") or {}).get("close")
        with col:
            st.metric(f"{tf} finalized bars", payload.get("bars", 0))
            st.metric(f"{tf} last close", "N/A" if close is None else f"{close:,.2f}")

    for tf in TIMEFRAMES:
        payload = payloads[tf]
        if payload.get("status") == "UNAVAILABLE":
            st.warning(f"{asset} {tf}: UNAVAILABLE — {', '.join(payload.get('reason_codes', []))}")


def page_execution_planner(root: Path) -> None:
    st.header("Execution Planner")
    st.caption(
        "Operator-driven planning only. The kernel never infers direction; templates are "
        "UNVALIDATED_STRUCTURAL_TEMPLATE with claim ceiling OPERATOR_PLANNING_ONLY."
    )
    asset = st.selectbox("Asset", ASSETS, key="planner_asset")
    timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=TIMEFRAMES.index("1d"), key="planner_tf")
    direction = st.radio("Direction (operator decision)", ["LONG", "SHORT"], horizontal=True)

    payload = _load_payload(root, asset, timeframe)
    mqa_state = (payload.get("component_states") or {}).get("mqa_benchmarks") or {}
    data_ready = payload.get("status") != "UNAVAILABLE" and mqa_state.get("close") is not None
    if not data_ready:
        st.info(
            f"No finalized-bar observation available for {asset} {timeframe} "
            f"({', '.join(payload.get('reason_codes', ['NO_DATA']))}). "
            "Import finalized bars before planning."
        )

    if st.button("Generate structural template"):
        if not data_ready:
            st.error("Cannot generate a template without a finalized observation (fail-closed).")
        else:
            try:
                template = build_structural_template(
                    asset=asset,
                    timeframe=timeframe,
                    direction=TradeDirection(direction),
                    source_snapshot_hash=canonical_hash(payload),
                    mqa_state=mqa_state,
                )
                st.session_state["template"] = template
            except Exception as exc:
                st.error(f"Template rejected by kernel: {type(exc).__name__}: {exc}")

    template = st.session_state.get("template")
    if template is not None:
        st.subheader("Structural template")
        st.json({
            "asset": template.asset,
            "timeframe": template.timeframe,
            "direction": template.direction.value,
            "entry_zone": list(template.entry_zone),
            "invalidation_price": template.invalidation_price,
            "targets": list(template.targets),
            "template_label": template.template_label,
            "claim_ceiling": template.claim_ceiling,
        })
        st.subheader("Manual trade plan (paper only)")
        equity = st.number_input("Account equity", min_value=1.0, value=10_000.0, step=1_000.0)
        risk_pct = st.number_input("Risk budget %", min_value=0.1, max_value=2.0, value=1.0, step=0.1)
        if st.button("Calculate manual trade plan"):
            try:
                plan = calculate_manual_trade_plan(
                    asset=template.asset,
                    timeframe=template.timeframe,
                    direction=template.direction,
                    source_snapshot_hash=template.source_snapshot_hash,
                    entry_zone=template.entry_zone,
                    invalidation_price=template.invalidation_price,
                    targets=template.targets,
                    account_equity=equity,
                    risk_budget_pct=risk_pct,
                )
                st.json({
                    "plan_id": plan.plan_id,
                    "quantity": plan.quantity,
                    "notional": plan.notional,
                    "margin_required": plan.margin_required,
                    "estimated_loss_at_invalidation": plan.estimated_loss_at_invalidation,
                    "reward_r_multiples": list(plan.reward_r_multiples),
                    "mode": plan.mode,
                    "claim_ceiling": plan.claim_ceiling,
                })
            except Exception as exc:
                st.error(f"Plan rejected by kernel: {type(exc).__name__}: {exc}")


def main() -> None:
    st.set_page_config(page_title="War Room OS v3", layout="wide")
    st.title("War Room OS v3")
    root = _root()
    page = st.sidebar.radio("Page", ["Market Overview", "Execution Planner"])
    st.sidebar.caption(f"root: {root}")
    if page == "Market Overview":
        page_market_overview(root)
    else:
        page_execution_planner(root)


main()
