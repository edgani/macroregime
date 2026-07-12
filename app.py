from __future__ import annotations

import hmac
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("WARROOM_ROOT") or Path(__file__).resolve().parent).resolve()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from warroom_v3.evaluation import build_evaluation_report
from warroom_v3.runtime import (
    bootstrap_binance_scope,
    build_asset_snapshot,
    collect_binance_scope,
    get_scope_bars,
    get_scope_dashboard_payload,
    import_canonical_csv,
    system_status,
)
from warroom_v3.sensors import compute_mqa_benchmarks, compute_momentum_axes, true_ranges
from warroom_v3.storage import atomic_write, load_jsonl
from warroom_v3.trading import (
    PaperTradeStatus,
    TradeDirection,
    build_structural_template,
    calculate_manual_trade_plan,
    cancel_paper_trade,
    close_paper_trade,
    list_paper_trades,
    open_paper_trade,
    paper_journal_summary,
    verify_paper_journal,
)

BINANCE_ASSETS = ("BTCUSDT", "ETHUSDT")
FRAMES = ("15m", "1h", "4h", "1d")

def configured_assets() -> tuple[str, ...]:
    path = ROOT / "validation/market_matrix.json"
    if not path.exists():
        return BINANCE_ASSETS
    payload = json.loads(path.read_text(encoding="utf-8"))
    found = sorted({str(row["asset"]).upper() for row in payload.get("scopes", [])})
    ordered = [a for a in BINANCE_ASSETS if a in found]
    ordered.extend(a for a in found if a not in ordered)
    return tuple(ordered)

ASSETS = configured_assets()
ROLE_BY_FRAME = {"1d": "Structural", "4h": "Trend", "1h": "Tactical", "15m": "Execution"}

st.set_page_config(
    page_title="War Room OS v3",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1600px;}
[data-testid="stMetric"] {background: rgba(128,128,128,.08); border: 1px solid rgba(128,128,128,.16); padding: .8rem; border-radius: .7rem;}
.wr-card {padding: .9rem 1rem; border: 1px solid rgba(128,128,128,.22); border-radius: .75rem; background: rgba(128,128,128,.055); margin-bottom: .55rem;}
.wr-ok {border-left: 5px solid #2ca02c;}
.wr-warn {border-left: 5px solid #ff9f1a;}
.wr-stop {border-left: 5px solid #d62728;}
.wr-muted {opacity: .75; font-size: .92rem;}
code {font-size: .86rem;}
</style>
""",
    unsafe_allow_html=True,
)


def fmt(value: Any, digits: int = 4, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 1000:
        text = f"{number:,.2f}"
    else:
        text = f"{number:.{digits}f}"
    return text + suffix


def authenticate() -> None:
    expected = os.environ.get("WARROOM_OPERATOR_PIN", "").strip()
    if not expected:
        return
    if st.session_state.get("authenticated"):
        return
    st.title("War Room OS v3")
    supplied = st.text_input("Operator PIN", type="password")
    if st.button("Unlock", type="primary"):
        st.session_state["authenticated"] = hmac.compare_digest(supplied, expected)
        if st.session_state["authenticated"]:
            st.rerun()
        st.error("PIN salah")
    st.stop()


def scope_frame(asset: str, timeframe: str, limit: int = 400) -> pd.DataFrame:
    bars = get_scope_bars(ROOT, asset=asset, timeframe=timeframe)
    if not bars:
        return pd.DataFrame()
    rows = [
        {
            "time": b.observed_at,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "available_at": b.available_at,
        }
        for b in bars[-limit:]
    ]
    return pd.DataFrame(rows)


def state_series(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    if df.empty or len(df) < 100:
        return df, {}, {}
    high = df["high"].astype(float).tolist()
    low = df["low"].astype(float).tolist()
    close = df["close"].astype(float).tolist()
    tr = true_ranges(high, low, close)
    mqa = compute_mqa_benchmarks(high, low, close)
    momentum = compute_momentum_axes(close, tr)
    enriched = df.copy()
    enriched["fixed_lower"] = [x.fixed_lower for x in mqa]
    enriched["fixed_upper"] = [x.fixed_upper for x in mqa]
    enriched["conformal_lower"] = [x.conformal_lower for x in mqa]
    enriched["conformal_upper"] = [x.conformal_upper for x in mqa]
    enriched["trend_context"] = [x.trend_context for x in momentum]
    enriched["acceleration"] = [x.acceleration for x in momentum]
    enriched["release_rank"] = [x.release_rank for x in momentum]
    enriched["exhaustion_risk"] = [x.exhaustion_risk for x in momentum]
    return enriched, asdict(mqa[-1]), asdict(momentum[-1])


def price_chart(df: pd.DataFrame, asset: str, timeframe: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.78, 0.22],
    )
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=asset,
        ),
        row=1,
        col=1,
    )
    for column, name, dash in (
        ("fixed_lower", "ATR lower", "dot"),
        ("fixed_upper", "ATR upper", "dot"),
        ("conformal_lower", "Conformal lower", "dash"),
        ("conformal_upper", "Conformal upper", "dash"),
    ):
        if column in df and df[column].notna().any():
            fig.add_trace(
                go.Scatter(x=df["time"], y=df[column], mode="lines", name=name, line={"width": 1.2, "dash": dash}),
                row=1,
                col=1,
            )
    fig.add_trace(go.Bar(x=df["time"], y=df["volume"], name="Volume", opacity=0.45), row=2, col=1)
    fig.update_layout(
        title=f"{asset} · {timeframe}",
        height=680,
        margin={"l": 8, "r": 8, "t": 45, "b": 8},
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def context_label(snapshot: dict[str, Any]) -> tuple[str, str, str]:
    mtf = snapshot.get("mtf", {})
    conflicts = mtf.get("conflict_codes", [])
    states = [mtf.get(k) for k in ("structural", "trend", "tactical", "execution")]
    if "UNAVAILABLE" in states:
        return "UNAVAILABLE", "Belum semua timeframe punya warm-up yang cukup.", "wr-stop"
    if conflicts:
        return "WAIT / CONFLICT", ", ".join(conflicts), "wr-stop"
    directional = [v for v in states if v in ("BULLISH", "BEARISH")]
    if directional and all(v == "BULLISH" for v in directional):
        return "BULLISH CONTEXT", "Semua timeframe directional yang tersedia selaras bullish.", "wr-ok"
    if directional and all(v == "BEARISH" for v in directional):
        return "BEARISH CONTEXT", "Semua timeframe directional yang tersedia selaras bearish.", "wr-ok"
    return "MIXED / OBSERVE", "Belum ada alignment penuh; jangan paksa entry.", "wr-warn"


def run_scope_action(kind: str, asset: str, timeframe: str) -> None:
    try:
        with st.spinner(f"{kind.title()} {asset} {timeframe}..."):
            if kind == "bootstrap":
                result = bootstrap_binance_scope(ROOT, asset=asset, timeframe=timeframe)
            else:
                result = collect_binance_scope(ROOT, asset=asset, timeframe=timeframe)
        st.session_state["last_operation"] = result
        st.success(result.get("status", "DONE"))
        st.rerun()
    except Exception as exc:
        st.error(f"{type(exc).__name__}: {exc}")


def run_all(kind: str) -> None:
    results = []
    failures = 0
    progress = st.progress(0)
    total = len(BINANCE_ASSETS) * len(FRAMES)
    for i, asset in enumerate(BINANCE_ASSETS):
        for timeframe in FRAMES:
            try:
                fn = bootstrap_binance_scope if kind == "bootstrap" else collect_binance_scope
                results.append(fn(ROOT, asset=asset, timeframe=timeframe))
            except Exception as exc:
                failures += 1
                results.append({"asset": asset, "timeframe": timeframe, "status": "ERROR", "error": str(exc)})
            progress.progress((i * len(FRAMES) + FRAMES.index(timeframe) + 1) / total)
    st.session_state["last_operation"] = {"kind": kind, "failures": failures, "results": results}
    if failures:
        st.warning(f"Selesai dengan {failures} kegagalan. Lihat Operations.")
    else:
        st.success("Semua scope selesai.")
    st.rerun()


def system_header() -> None:
    status = system_status(ROOT)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Mode", status["mode"])
    c2.metric("Prospective batches", status["prospective_batches"])
    c3.metric("Observations", status["observations"])
    c4.metric("Outcomes", status["outcomes"])
    c5.metric("Store", "PASS" if not status["store_errors"] else "ERROR")
    if status["store_errors"]:
        st.error("Runtime store integrity error: " + "; ".join(status["store_errors"]))


def watchlist_table(timeframe: str) -> pd.DataFrame:
    rows = []
    for asset in ASSETS:
        payload = get_scope_dashboard_payload(ROOT, asset=asset, timeframe=timeframe)
        state = payload.get("component_states", {})
        mqa = state.get("mqa_benchmarks", {})
        momentum = state.get("momentum_axes", {})
        rows.append({
            "Asset": asset,
            "Status": payload.get("status", "UNAVAILABLE"),
            "Bars": payload.get("bars", 0),
            "Last": mqa.get("close"),
            "Vol state": mqa.get("volatility_state"),
            "Trend": momentum.get("trend_context"),
            "Release": momentum.get("release_rank"),
            "Exhaustion": momentum.get("exhaustion_risk"),
        })
    return pd.DataFrame(rows)


def market_desk(asset: str, timeframe: str) -> None:
    system_header()
    st.caption("Market state bersifat descriptive. Directional context bukan probabilitas dan bukan autonomous signal.")
    with st.expander(f"Watchlist · {timeframe}", expanded=False):
        st.dataframe(watchlist_table(timeframe), hide_index=True, width="stretch")
    snapshot = build_asset_snapshot(ROOT, asset=asset)
    label, detail, card_class = context_label(snapshot)
    st.markdown(
        f'<div class="wr-card {card_class}"><b>{asset}: {label}</b><br><span class="wr-muted">{detail}</span></div>',
        unsafe_allow_html=True,
    )

    df = scope_frame(asset, timeframe)
    enriched, mqa, momentum = state_series(df)
    if enriched.empty or len(enriched) < 100:
        st.warning(f"Data {asset} {timeframe} belum cukup. Bars tersedia: {len(enriched)}; minimum 100.")
        left, right = st.columns(2)
        if left.button("Bootstrap scope", width="stretch"):
            run_scope_action("bootstrap", asset, timeframe)
        if right.button("Collect scope", width="stretch"):
            run_scope_action("collect", asset, timeframe)
        return

    last = enriched.iloc[-1]
    prev = enriched.iloc[-2]
    delta = float(last["close"] / prev["close"] - 1) if float(prev["close"]) else 0.0
    a, b, c, d, e, f = st.columns(6)
    a.metric("Last", fmt(last["close"], 2), f"{delta * 100:+.2f}%")
    b.metric("ATR", fmt(mqa.get("atr"), 2))
    b.caption(mqa.get("volatility_state", "UNAVAILABLE"))
    c.metric("Range location", fmt(None if mqa.get("prior_range_location") is None else mqa["prior_range_location"] * 100, 1, "%"))
    d.metric("Trend context", fmt(momentum.get("trend_context"), 2))
    e.metric("Release rank", fmt(None if momentum.get("release_rank") is None else momentum["release_rank"] * 100, 1, "%"))
    f.metric("Exhaustion risk", fmt(None if momentum.get("exhaustion_risk") is None else momentum["exhaustion_risk"] * 100, 1, "%"))

    st.plotly_chart(price_chart(enriched.tail(260), asset, timeframe), width="stretch", config={"displaylogo": False})

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("MQA descriptive range")
        rows = [
            ("ATR lower", mqa.get("fixed_lower")),
            ("Current", mqa.get("close")),
            ("ATR upper", mqa.get("fixed_upper")),
            ("Conformal lower", mqa.get("conformal_lower")),
            ("Conformal upper", mqa.get("conformal_upper")),
            ("Volatility percentile", None if mqa.get("volatility_percentile") is None else mqa["volatility_percentile"] * 100),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["Metric", "Value"]), hide_index=True, width="stretch")
    with right:
        st.subheader("MTF state")
        mtf = snapshot.get("mtf", {})
        mtf_rows = [
            {"Role": ROLE_BY_FRAME[frame], "Timeframe": frame, "State": mtf.get(role.lower(), "UNAVAILABLE")}
            for frame, role in ROLE_BY_FRAME.items()
        ]
        st.dataframe(pd.DataFrame(mtf_rows), hide_index=True, width="stretch")
        st.caption(f"Alignment: {fmt(mtf.get('alignment_score'), 2)} · Risk ceiling: {fmt(mtf.get('risk_multiplier_ceiling'), 2)}×")

    st.subheader("Momentum axes — terpisah, tidak digabung menjadi score")
    momentum_rows = [
        {"Axis": "Trend context", "Value": momentum.get("trend_context")},
        {"Axis": "Acceleration", "Value": momentum.get("acceleration")},
        {"Axis": "Release rank", "Value": momentum.get("release_rank")},
        {"Axis": "Signed persistence", "Value": momentum.get("signed_persistence")},
        {"Axis": "Path efficiency", "Value": momentum.get("path_efficiency")},
        {"Axis": "Noise ratio", "Value": momentum.get("noise_ratio")},
        {"Axis": "Exhaustion risk", "Value": momentum.get("exhaustion_risk")},
    ]
    st.dataframe(pd.DataFrame(momentum_rows), hide_index=True, width="stretch")


def trade_planner(asset: str, timeframe: str) -> None:
    st.header("Execution Planner")
    st.warning("Operator menentukan arah. Template hanya aritmetika level/risk, bukan signal, probability, atau edge tervalidasi.")
    payload = get_scope_dashboard_payload(ROOT, asset=asset, timeframe=timeframe)
    if payload.get("status") == "UNAVAILABLE":
        st.error(" · ".join(payload.get("reason_codes", [])))
        return
    mqa = payload["component_states"]["mqa_benchmarks"]
    snapshot_hash = payload["source_snapshot_hash"]

    snapshot = build_asset_snapshot(ROOT, asset=asset)
    context, context_detail, context_class = context_label(snapshot)
    st.markdown(
        f'<div class="wr-card {context_class}"><b>MTF context: {context}</b><br><span class="wr-muted">{context_detail}</span></div>',
        unsafe_allow_html=True,
    )
    default_direction = TradeDirection.SHORT if context == "BEARISH CONTEXT" else TradeDirection.LONG
    direction = TradeDirection(st.radio(
        "Direction operator", [d.value for d in TradeDirection],
        index=0 if default_direction == TradeDirection.LONG else 1, horizontal=True,
    ))
    col1, col2 = st.columns([1, 2])
    if col1.button("Generate structural template", type="primary", width="stretch"):
        try:
            template = build_structural_template(
                asset=asset,
                timeframe=timeframe,
                direction=direction,
                source_snapshot_hash=snapshot_hash,
                mqa_state=mqa,
            )
            st.session_state["template"] = asdict(template)
            st.session_state["template"]["direction"] = template.direction.value
        except Exception as exc:
            st.error(str(exc))
    col2.caption("Template memakai current close + ATR/conformal boundaries. Lu tetap wajib review struktur chart dan invalidation.")

    template = st.session_state.get("template")
    if not template or template.get("asset") != asset or template.get("timeframe") != timeframe or template.get("direction") != direction.value:
        try:
            generated = build_structural_template(
                asset=asset,
                timeframe=timeframe,
                direction=direction,
                source_snapshot_hash=snapshot_hash,
                mqa_state=mqa,
            )
            template = asdict(generated)
            template["direction"] = generated.direction.value
        except Exception:
            template = None
    if not template:
        st.info("Generate template setelah ATR tersedia.")
        return

    defaults_targets = ", ".join(f"{x:.8f}" for x in template["targets"])
    with st.form("trade_plan_form"):
        a, b, c = st.columns(3)
        entry_low = a.number_input("Entry low", min_value=0.0, value=float(template["entry_zone"][0]), format="%.8f")
        entry_high = b.number_input("Entry high", min_value=0.0, value=float(template["entry_zone"][1]), format="%.8f")
        invalidation = c.number_input("Invalidation", min_value=0.0, value=float(template["invalidation_price"]), format="%.8f")
        targets_text = st.text_input("Targets, comma separated", value=defaults_targets)
        d, e, f, g = st.columns(4)
        equity = d.number_input("Account equity", min_value=1.0, value=float(st.session_state.get("equity", 10000.0)), step=100.0)
        risk_pct = e.number_input("Risk budget %", min_value=0.05, max_value=2.0, value=0.5, step=0.05)
        cost_bps = f.number_input("Round-trip costs bps", min_value=0.0, max_value=500.0, value=12.0, step=1.0)
        leverage = g.number_input("Max leverage", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        notes = st.text_area("Trade thesis / conditions", placeholder="Kenapa entry ini valid? Apa yang membatalkan thesis sebelum stop?")
        submitted = st.form_submit_button("Calculate operator plan", type="primary", width="stretch")
    if submitted:
        try:
            targets = tuple(float(x.strip()) for x in targets_text.split(",") if x.strip())
            plan = calculate_manual_trade_plan(
                asset=asset,
                timeframe=timeframe,
                direction=direction,
                source_snapshot_hash=snapshot_hash,
                entry_zone=(entry_low, entry_high),
                invalidation_price=invalidation,
                targets=targets,
                account_equity=equity,
                risk_budget_pct=risk_pct,
                estimated_roundtrip_cost_bps=cost_bps,
                max_leverage=leverage,
                notes=notes,
            )
            st.session_state["calculated_plan"] = plan
            st.session_state["equity"] = equity
        except Exception as exc:
            st.error(f"Plan ditolak: {exc}")

    plan = st.session_state.get("calculated_plan")
    if plan and plan.asset == asset and plan.timeframe == timeframe and plan.direction == direction:
        st.subheader("Operator ticket")
        x1, x2, x3, x4, x5 = st.columns(5)
        x1.metric("Quantity", fmt(plan.quantity, 6))
        x2.metric("Notional", fmt(plan.notional, 2))
        x3.metric("Margin", fmt(plan.margin_required, 2))
        x4.metric("Loss @ invalidation", fmt(plan.estimated_loss_at_invalidation, 2))
        x5.metric("Risk budget", fmt(plan.cash_risk_budget, 2))
        rr = pd.DataFrame({"Target": list(plan.targets), "Net R multiple": list(plan.reward_r_multiples)})
        st.dataframe(rr, hide_index=True, width="stretch")
        plan_payload = asdict(plan)
        plan_payload["direction"] = plan.direction.value
        st.download_button(
            "Download operator ticket JSON",
            data=json.dumps(plan_payload, indent=2, default=str),
            file_name=f"{plan.asset}_{plan.timeframe}_{plan.direction.value}_{plan.plan_id[:10]}.json",
            mime="application/json",
            width="stretch",
        )
        acknowledge = st.checkbox("Saya paham ini bukan signal tervalidasi dan journal yang dibuat adalah paper trade.")
        if st.button("Open paper trade", disabled=not acknowledge, type="primary", width="stretch"):
            try:
                event = open_paper_trade(ROOT, plan=plan)
                st.success(f"Paper trade dibuka: {event['trade_id'][:12]}")
                st.session_state.pop("calculated_plan", None)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def paper_journal_page() -> None:
    st.header("Paper Trade Journal")
    errors = verify_paper_journal(ROOT)
    if errors:
        st.error("Journal integrity error: " + "; ".join(errors))
        return
    summary = paper_journal_summary(ROOT)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", summary["total"])
    c2.metric("Open", summary["open"])
    c3.metric("Closed", summary["closed"])
    c4.metric("Realized P&L", fmt(summary["realized_pnl"], 2))
    c5.metric("Average R", fmt(summary["average_r"], 2))
    trades = list_paper_trades(ROOT)
    if not trades:
        st.info("Belum ada paper trade. Buat dari Execution Planner.")
        return
    rows = []
    for t in trades:
        plan = t.plan
        rows.append({
            "Trade ID": t.trade_id[:12],
            "Status": t.status.value,
            "Opened": t.opened_at,
            "Asset": plan["asset"],
            "TF": plan["timeframe"],
            "Direction": plan["direction"],
            "Entry mid": (plan["entry_zone"][0] + plan["entry_zone"][1]) / 2,
            "Stop": plan["invalidation_price"],
            "Qty": plan["quantity"],
            "P&L": t.realized_pnl,
            "R": t.realized_r,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    open_trades = [t for t in trades if t.status == PaperTradeStatus.OPEN]
    if open_trades:
        st.subheader("Close / cancel open trade")
        options = {f"{t.trade_id[:12]} · {t.plan['asset']} {t.plan['timeframe']} {t.plan['direction']}": t for t in open_trades}
        selected_label = st.selectbox("Open trade", list(options))
        selected = options[selected_label]
        current = get_scope_dashboard_payload(ROOT, asset=selected.plan["asset"], timeframe=selected.plan["timeframe"])
        last_price = current.get("component_states", {}).get("mqa_benchmarks", {}).get("close")
        with st.form("close_trade_form"):
            exit_price = st.number_input("Exit price", min_value=0.0, value=float(last_price or selected.plan["entry_zone"][0]), format="%.8f")
            reason = st.text_input("Reason", value="MANUAL_CLOSE")
            left, right = st.columns(2)
            close_it = left.form_submit_button("Close trade", type="primary", width="stretch")
            cancel_it = right.form_submit_button("Cancel trade", width="stretch")
        try:
            if close_it:
                close_paper_trade(ROOT, trade_id=selected.trade_id, exit_price=exit_price, reason=reason)
                st.success("Trade closed.")
                st.rerun()
            if cancel_it:
                cancel_paper_trade(ROOT, trade_id=selected.trade_id, reason=reason)
                st.success("Trade cancelled.")
                st.rerun()
        except Exception as exc:
            st.error(str(exc))

    closed = [t for t in reversed(trades) if t.status == PaperTradeStatus.CLOSED]
    if closed:
        curve = []
        total = 0.0
        for t in closed:
            total += float(t.realized_pnl or 0.0)
            curve.append({"time": t.closed_at, "Cumulative P&L": total})
        chart_df = pd.DataFrame(curve).set_index("time")
        st.line_chart(chart_df)


def operations_page(asset: str, timeframe: str) -> None:
    st.header("Operations & Evidence")
    status = system_status(ROOT)
    st.json(status, expanded=False)
    a, b, c, d = st.columns(4)
    selected_supported = asset in BINANCE_ASSETS
    if a.button("Bootstrap selected", width="stretch", disabled=not selected_supported):
        run_scope_action("bootstrap", asset, timeframe)
    if b.button("Collect selected", width="stretch", disabled=not selected_supported):
        run_scope_action("collect", asset, timeframe)
    if c.button("Bootstrap all", width="stretch"):
        run_all("bootstrap")
    if d.button("Collect all", width="stretch"):
        run_all("collect")

    if not selected_supported:
        st.caption("Selected asset tidak punya approved online adapter. Gunakan canonical PIT CSV import di bawah.")
    if "last_operation" in st.session_state:
        with st.expander("Last operation", expanded=False):
            st.json(st.session_state["last_operation"])

    st.subheader("Canonical PIT CSV import")
    st.caption("Required columns: asset,timeframe,observed_at,available_at,open,high,low,close,volume,source_record_id[,revision_id]")
    uploaded = st.file_uploader("Upload canonical CSV", type=["csv"])
    tier = st.selectbox("Import tier", ["bootstrap", "prospective"], help="Prospective requires post-seal timestamps and complete PIT semantics.")
    if uploaded is not None and st.button("Validate and import CSV", type="primary"):
        try:
            import hashlib
            raw = uploaded.getvalue()
            digest = hashlib.sha256(raw).hexdigest()
            upload_path = ROOT / f"runtime/uploads/{digest}.csv"
            upload_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(upload_path, raw)
            result = import_canonical_csv(ROOT, csv_path=upload_path, tier=tier)
            st.success(result.get("status", "IMPORTED"))
            st.json(result)
        except Exception as exc:
            st.error(f"Import ditolak: {exc}")

    st.subheader("Evidence evaluation")
    evaluation = build_evaluation_report(ROOT)
    st.json(evaluation, expanded=False)

    st.subheader("Runtime journals")
    journals = {
        "Prospective batches": ROOT / "runtime/prospective/journal.jsonl",
        "Observations": ROOT / "runtime/observations/journal.jsonl",
        "Outcomes": ROOT / "runtime/outcomes/journal.jsonl",
        "Paper events": ROOT / "runtime/trading/paper_events.jsonl",
    }
    selected = st.selectbox("Journal", list(journals))
    entries = load_jsonl(journals[selected])
    st.dataframe(pd.DataFrame(entries), hide_index=True, width="stretch")

    incident_files = sorted((ROOT / "runtime/incidents").glob("*.json")) if (ROOT / "runtime/incidents").exists() else []
    if incident_files:
        st.subheader("Incidents")
        incident_rows = [json.loads(p.read_text(encoding="utf-8")) for p in incident_files[-100:]]
        st.dataframe(pd.DataFrame(incident_rows), hide_index=True, width="stretch")


def about_page() -> None:
    st.header("System Contract")
    st.markdown(
        """
### Yang boleh dilakukan
- Memantau data finalized BTC/ETH pada 15m, 1H, 4H, dan Daily.
- Membaca MQA range/volatility state, Momentum axes, dan MTF alignment.
- Menghitung manual position size dan level geometry.
- Membuka, menutup, dan mengevaluasi paper trade secara append-only.
- Mengumpulkan prospective evidence tanpa mengganti formula.

### Yang sengaja diblokir
- Autonomous BUY/SELL.
- Probability yang belum calibrated.
- Auto execution ke exchange/broker.
- Mengubah research state menjadi PAPER/LIVE evidence.
- Menyebut structural template sebagai alpha.

Untuk actual manual trading, operator boleh memakai ticket sebagai kalkulator. Keputusan arah dan eksekusi tetap milik operator.
"""
    )
    release = ROOT / "artifacts/release_manifest_ready.json"
    seal = ROOT / "prospective/SEAL.json"
    if release.exists() and seal.exists():
        c1, c2 = st.columns(2)
        c1.json(json.loads(release.read_text(encoding="utf-8")), expanded=False)
        c2.json(json.loads(seal.read_text(encoding="utf-8")), expanded=False)


authenticate()

with st.sidebar:
    st.title("⚔️ War Room OS")
    st.caption("Streamlit Trading Workstation")
    page = st.radio("Workspace", ["Market Desk", "Execution Planner", "Paper Journal", "Operations", "System Contract"])
    st.divider()
    asset = st.selectbox("Asset", ASSETS)
    timeframe = st.selectbox("Timeframe", FRAMES, index=1)
    if st.button("Refresh view", width="stretch"):
        st.rerun()
    st.caption(f"Root: `{ROOT}`")
    st.caption("Mode: RESEARCH + DISCRETIONARY PAPER")

st.title("War Room OS v3")
st.caption("Live Streamlit workstation · fail-closed evidence · no broker execution")

try:
    if page == "Market Desk":
        market_desk(asset, timeframe)
    elif page == "Execution Planner":
        trade_planner(asset, timeframe)
    elif page == "Paper Journal":
        paper_journal_page()
    elif page == "Operations":
        operations_page(asset, timeframe)
    else:
        about_page()
except Exception as exc:
    st.error(f"{type(exc).__name__}: {exc}")
    with st.expander("Diagnostic"):
        st.exception(exc)
