"""Decision-first Command Center."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from eros.app.components import bullet_list, evidence_badge, section_header, status_card
from eros.app.state import DashboardState
from eros.data.public_markets import EXPECTED_SYMBOLS_BY_GROUP, MARKET_GROUPS


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _capital_flow_dot(state: DashboardState) -> str:
    lines = [
        "digraph CapitalMap {",
        'graph [bgcolor="transparent", rankdir="LR", pad="0.2"];',
        'node [shape="box", style="rounded,filled", fillcolor="#161b22", '
        'color="#30363d", fontcolor="#e6edf3", fontname="Inter"];',
        'edge [fontcolor="#8b949e", fontname="Inter", fontsize="9"];',
    ]
    edge_colors = {
        "PROVEN_SCOPE_LIMITED": "#3fb950",
        "REPLICATED_OOS": "#3fb950",
        "CANDIDATE": "#d29922",
        "DATA_DEBT": "#f85149",
        "BUSTED_AS_TESTED": "#f85149",
    }
    for index, flow in enumerate(state.capital_flows):
        source = f"source_{index}"
        target = f"target_{index}"
        color = edge_colors.get(flow.status, "#8b949e")
        lines.append(f'{source} [label="{_dot_escape(flow.source)}"];')
        lines.append(f'{target} [label="{_dot_escape(flow.target)}"];')
        label = _dot_escape(f"{flow.mechanism} · {flow.status}")
        lines.append(f'{source} -> {target} [label="{label}", color="{color}"];')
    lines.append("}")
    return "\n".join(lines)


def _decision_brief(state: DashboardState) -> None:
    live_ratio = f"{state.data_health.live_feeds}/{state.data_health.total_feeds}"
    if state.market_snapshot:
        condition = (
            f"{len(state.market_snapshot)} public benchmark observations loaded; "
            "causal regime remains UNKNOWN until macro evidence passes admission."
        )
    else:
        condition = "UNKNOWN. Belum ada panel point-in-time global yang lolos."
    st.markdown(
        f"""
        <div class="brief">
          <h3>Ringkasan keputusan 30 detik</h3>
          <ul>
            <li><b>Kondisi global:</b> {condition}</li>
            <li><b>Peluang:</b> tidak ada qualified opportunity; kandidat masih gagal
            evidence gate.</li>
            <li><b>Tindakan:</b> WAIT / RESEARCH ONLY. Execution tetap dikunci.</li>
            <li><b>Data aktif:</b> {live_ratio} feed. Missing data tidak diganti neutral score.</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render(state: DashboardState) -> None:
    _decision_brief(state)
    section_header(
        "Decision surface",
        "Command Center",
        "What changed, what matters, and what should I do?",
    )

    columns = st.columns(4)
    cards = (
        (
            "Data health",
            state.data_health.overall_status,
            f"{state.data_health.live_feeds}/{state.data_health.total_feeds} feeds live",
            state.data_health.overall_status,
        ),
        (
            "Qualified opportunities",
            str(len(state.qualified_opportunities)),
            "Conservative net-EV gate",
            "UNKNOWN",
        ),
        (
            "Execution",
            state.execution.permission,
            "Human approval remains mandatory",
            "LOCKED" if state.execution.permission == "LOCKED" else "CANDIDATE",
        ),
        ("Material unknowns", str(len(state.unknowns)), "Visible, never imputed", "DATA_DEBT"),
    )
    for column, card in zip(columns, cards, strict=True):
        with column:
            status_card(*card)

    if state.market_snapshot:
        path_rows: list[dict[str, object]] = []
        for observation in state.market_snapshot:
            if len(observation.history) < 2 or observation.history[0].value == 0:
                continue
            base = float(observation.history[0].value)
            path_rows.extend(
                {
                    "Observed at": point.observed_at,
                    "Instrument": observation.instrument,
                    "Normalized return %": (float(point.value) / base - 1.0) * 100.0,
                }
                for point in observation.history
            )
        if path_rows:
            section_header(
                "Provider history",
                "LIVE 5-DAY MARKET PATHS",
                "Normalized provider closes; comparable direction without mixing price units.",
            )
            path_frame = pd.DataFrame(path_rows)
            path_frame["Observed at"] = pd.to_datetime(path_frame["Observed at"], utc=True)
            st.line_chart(
                path_frame,
                x="Observed at",
                y="Normalized return %",
                color="Instrument",
                height=390,
            )
            st.caption(
                "Source: each instrument's labelled public provider. "
                "This monitoring path does not establish a causal signal."
            )

        section_header(
            "Live provider observations",
            "LIVE CROSS-MARKET PULSE",
            "Which monitored benchmarks moved, when were they observed, and who supplied them?",
        )
        pulse_rows = [
            {
                "Instrument": item.instrument,
                "Change %": item.change_pct,
                "Market": item.market_group,
            }
            for item in state.market_snapshot
            if item.change_pct is not None
        ]
        if pulse_rows:
            st.bar_chart(
                pd.DataFrame(pulse_rows),
                x="Instrument",
                y="Change %",
                color="Market",
                height=340,
            )
        else:
            st.info("Live levels are available, but providers did not supply comparable changes.")

        section_header(
            "Coverage by contract",
            "MARKET COVERAGE MAP",
            "Observed symbols versus the expected benchmark contract for every market group.",
        )
        coverage_rows = []
        for group in MARKET_GROUPS:
            expected = EXPECTED_SYMBOLS_BY_GROUP[group]
            observed = {
                item.symbol
                for item in state.market_snapshot
                if item.market_group == group and item.status == "LIVE"
            }
            coverage_rows.extend(
                [
                    {
                        "Market group": group,
                        "Metric": "Observed live",
                        "Symbols": len(expected & observed),
                    },
                    {
                        "Market group": group,
                        "Metric": "Expected",
                        "Symbols": len(expected),
                    },
                ]
            )
        st.bar_chart(
            pd.DataFrame(coverage_rows),
            x="Market group",
            y="Symbols",
            color="Metric",
            height=300,
            stack=False,
        )

        section_header(
            "Observed data",
            "PUBLIC MARKET SNAPSHOT",
            "Provider-labelled benchmarks across US, IHSG, crypto, FX, commodities, and rates.",
        )
        market_rows = [
            {
                "Market": item.market_group,
                "Instrument": item.instrument,
                "Symbol": item.symbol,
                "Value": item.value,
                "Currency": item.currency,
                "Change %": item.change_pct,
                "Observed at": item.observed_at,
                "Provider": item.provider,
                "Status": item.status,
            }
            for item in state.market_snapshot
        ]
        st.dataframe(market_rows, width="stretch", hide_index=True)
        st.caption(
            "Monitoring data only. Public benchmark prices do not establish causal regime state "
            "or execution permission."
        )
    if state.feed_failures:
        failed = ", ".join(sorted(state.feed_failures))
        st.warning(f"Provider failures isolated: {failed}")

    section_header(
        "World state", "Global Regime", "Eight dimensions, each with evidence and uncertainty"
    )
    rows = [
        {
            "Dimension": item.name,
            "State": item.state,
            "Evidence": item.evidence_label,
            "Uncertainty": item.uncertainty,
            "Interpretation": item.interpretation,
        }
        for item in state.regime_dimensions
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    left, right = st.columns([1.15, 0.85])
    with left:
        section_header(
            "Flow graph",
            "MECHANISM MAP",
            "How capital could transmit; edge color preserves evidence status.",
        )
        st.graphviz_chart(_capital_flow_dot(state), width="stretch")
        flow_rows = [
            {
                "From": flow.source,
                "To": flow.target,
                "Mechanism": flow.mechanism,
                "Evidence": flow.status,
            }
            for flow in state.capital_flows
        ]
        st.dataframe(flow_rows, width="stretch", hide_index=True)
    with right:
        section_header("Delta", "What Changed", "Only verified updates may move decisions")
        for change in state.changes:
            st.markdown(
                f"**{change.title}** {evidence_badge(change.evidence_label)}  \n"
                f"{change.delta}  \n*Decision impact:* {change.decision_impact}",
                unsafe_allow_html=True,
            )

    section_header(
        "Competing explanations", "Thesis Board", "Probability is separate from confidence"
    )
    for thesis in state.theses:
        with st.expander(
            f"{thesis.thesis_id} · {thesis.status} · posterior {thesis.posterior:.0%}"
        ):
            st.markdown(f"**Claim:** {thesis.claim}")
            st.write(f"Credible interval: {thesis.interval} · Change: {thesis.change:+.0%}")
            st.write(
                f"Evidence: {thesis.evidence_label} · Permission: {thesis.decision_permission}"
            )
            st.write(f"Next discriminating observation: {thesis.next_observation}")
            st.write("Missing evidence:")
            bullet_list(thesis.missing_evidence)

    opportunity, action = st.columns(2)
    with opportunity:
        section_header(
            "Conservative EV", "Opportunity Board", "No candidate is promoted by narrative"
        )
        if not state.qualified_opportunities:
            st.warning("NO QUALIFIED OPPORTUNITY")
        else:
            st.dataframe(state.qualified_opportunities, width="stretch", hide_index=True)
    with action:
        section_header("Human gate", "Action Queue", "Actions remain reviewable and reversible")
        st.error(f"{state.execution.permission} — {state.execution.reason}")

    risks, unknowns = st.columns(2)
    with risks:
        section_header("Downside", "Top Risks", "What can make the system or portfolio wrong?")
        bullet_list(state.risks)
    with unknowns:
        section_header("Blind spots", "Top Unknowns", "Missing evidence is a first-class output")
        bullet_list(state.unknowns)

    section_header(
        "Calendar", "Upcoming Catalysts", "A catalyst matters only if it changes a decision"
    )
    st.dataframe(
        [item.model_dump() for item in state.catalysts],
        width="stretch",
        hide_index=True,
    )
