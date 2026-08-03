"""Research governance, proof, failures, and data-health interface."""

from __future__ import annotations

import base64
import binascii
import json
from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from PIL import Image, UnidentifiedImageError

from eros.app.components import bullet_list, section_header
from eros.app.state import DashboardState
from eros.research.crashmeter import load_crashmeter_evidence

MAX_EXHIBIT_BYTES = 2 * 1024 * 1024
MAX_EXHIBIT_BASE64_LENGTH = 4 * ((MAX_EXHIBIT_BYTES + 2) // 3)


def _validated_jpeg(encoded: str) -> tuple[bytes, int, int]:
    """Decode a bounded JPEG claim exhibit without trusting registry metadata."""

    try:
        encoded.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("Backtest claim exhibit must be ASCII base64") from exc
    if len(encoded) > MAX_EXHIBIT_BASE64_LENGTH:
        raise ValueError("Backtest claim exhibit exceeds the encoded-size limit")
    image_bytes = base64.b64decode(encoded, validate=True)
    if (
        len(image_bytes) > MAX_EXHIBIT_BYTES
        or not image_bytes.startswith(b"\xff\xd8\xff")
        or not image_bytes.endswith(b"\xff\xd9")
    ):
        raise ValueError("Backtest claim exhibit is not a bounded JPEG")
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
            if image.format != "JPEG" or width <= 0 or height <= 0:
                raise ValueError("Backtest claim exhibit has invalid JPEG metadata")
            if width * height > 20_000_000:
                raise ValueError("Backtest claim exhibit exceeds the 20 megapixel limit")
            image.verify()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
        raise ValueError("Backtest claim exhibit is an invalid JPEG") from exc
    return image_bytes, width, height


def render(state: DashboardState) -> None:
    section_header(
        "Proof center",
        "Research Lab",
        "What is known, what failed, and what must be learned next?",
    )
    section_header(
        "Evidence inventory",
        "RESEARCH EVIDENCE MAP",
        "Status distribution by research object; missing proof stays visible.",
    )
    evidence_rows = [
        {"Domain": "Thesis", "Status": item.evidence_label} for item in state.theses
    ] + [
        {"Domain": "Mechanism", "Status": str(item.get("status", "UNKNOWN"))}
        for item in state.mechanisms
    ]
    evidence_counts = (
        pd.DataFrame(evidence_rows)
        .groupby(["Domain", "Status"], dropna=False)
        .size()
        .reset_index(name="Objects")
    )
    st.bar_chart(evidence_counts, x="Domain", y="Objects", color="Status", height=290)

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
            "Public benchmark outcome view",
            "LIVE 5-DAY MARKET PATHS",
            "Normalized provider closes shown only as monitored outcomes, never as "
            "technical signals.",
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
            "Source: each instrument's labelled public provider. This outcome path does not "
            "establish a causal signal, target, entry, or exit."
        )

    legacy_dir = Path(__file__).parents[3] / "data" / "macro_investigation"
    section_header(
        "Frozen legacy research",
        "LEGACY CRASHMETER V3 SCORE TIMELINE",
        "The actual 2023-2026 score path retained from the pre-redesign repository.",
    )
    st.warning(
        "LEGACY CLAIM ARTIFACT — NOT POINT-IN-TIME AUDITED — NOT CAUSAL EVIDENCE — "
        "NOT EXECUTION ELIGIBLE"
    )
    try:
        evidence = load_crashmeter_evidence(legacy_dir)
        legacy_frame = evidence.score_frame
        section_header(
            "Fixed article thresholds",
            "LEGACY CRASHMETER THRESHOLD BANDS",
            "0-1 monitor · 2 caution · 3 exit claim · 4-5 critical claim.",
        )
        band_frame = pd.DataFrame(
            [
                {
                    "start": legacy_frame["date"].min(),
                    "end": legacy_frame["date"].max(),
                    "lower": 0,
                    "upper": 2,
                    "band": "Monitor 0-1",
                },
                {
                    "start": legacy_frame["date"].min(),
                    "end": legacy_frame["date"].max(),
                    "lower": 2,
                    "upper": 3,
                    "band": "Caution 2",
                },
                {
                    "start": legacy_frame["date"].min(),
                    "end": legacy_frame["date"].max(),
                    "lower": 3,
                    "upper": 4,
                    "band": "Exit claim 3",
                },
                {
                    "start": legacy_frame["date"].min(),
                    "end": legacy_frame["date"].max(),
                    "lower": 4,
                    "upper": 5,
                    "band": "Critical claim 4-5",
                },
            ]
        )
        bands = (
            alt.Chart(band_frame)
            .mark_rect(opacity=0.16)
            .encode(
                x=alt.X("start:T", title="Date"),
                x2="end:T",
                y=alt.Y("lower:Q", title="Legacy score", scale=alt.Scale(domain=[0, 5])),
                y2="upper:Q",
                color=alt.Color(
                    "band:N",
                    scale=alt.Scale(
                        domain=[
                            "Monitor 0-1",
                            "Caution 2",
                            "Exit claim 3",
                            "Critical claim 4-5",
                        ],
                        range=["#3fb950", "#d29922", "#f85149", "#a371f7"],
                    ),
                ),
            )
        )
        score_line = (
            alt.Chart(legacy_frame)
            .mark_line(color="#f0f6fc", strokeWidth=2)
            .encode(x="date:T", y=alt.Y("score:Q", scale=alt.Scale(domain=[0, 5])))
        )
        st.altair_chart((bands + score_line).properties(height=320), width="stretch")
        st.caption(
            "Artifact identity: data/macro_investigation/crashmeter_v3_daily.csv · "
            f"frozen rows: {len(legacy_frame)} · "
            f"window: {legacy_frame['date'].min().date()} to "
            f"{legacy_frame['date'].max().date()}. Thresholds are article rules, not validated "
            "execution gates."
        )

        section_header(
            "Score-derived windows",
            "DERIVED RISK WINDOWS",
            "Contiguous stored observations with legacy score ≥2; no market outcome is implied.",
        )
        st.dataframe(evidence.risk_windows, width="stretch", hide_index=True)

        section_header(
            "Outcome proof",
            "REPRODUCIBLE SPX DRAWDOWN OVERLAP",
            "SPX drawdown is independently derived only where stored score and SPX dates overlap.",
        )
        st.line_chart(
            evidence.outcome_frame,
            x="date",
            y="drawdown_pct",
            height=300,
        )
        st.caption(
            "This overlap starts after the historical crisis claims. It can test recent behavior "
            "but cannot validate Dotcom, GFC, or COVID timing."
        )

        section_header(
            "Legacy score decomposition",
            "LEGACY CRASHMETER V3 DRIVER ATTRIBUTION",
            "Binary component contributions retained from the source dataset.",
        )
        attribution_frame = legacy_frame.rename(
            columns={
                "a1": "A1 Curve ≤0.5",
                "a2": "A2 Post-inversion",
                "b1": "B1 HY range >150bps",
                "b2": "B2 HY OAS >550bps",
                "c": "C CAPE >35",
            }
        )
        driver_columns = [
            "A1 Curve ≤0.5",
            "A2 Post-inversion",
            "B1 HY range >150bps",
            "B2 HY OAS >550bps",
            "C CAPE >35",
        ]
        st.area_chart(
            attribution_frame,
            x="date",
            y=driver_columns,
            height=320,
        )
        st.caption(
            "Attribution is a faithful view of stored binary flags, not proof that any driver "
            "caused a market outcome."
        )

        section_header(
            "Fail-closed historical validation",
            "REPLICATION VERDICT",
            evidence.replication_verdict,
        )
        if evidence.claims_replicable:
            st.success("Historical source coverage is sufficient for claim replay.")
        else:
            st.error(
                "Claims remain UNREPLICABLE because source coverage and/or consistency checks "
                "failed. Execution permission remains LOCKED."
            )
        st.dataframe(evidence.claim_ledger, width="stretch", hide_index=True)

        section_header(
            "Raw-to-derived consistency",
            "SOURCE CONSISTENCY CHECKS",
            "Every ancillary artifact is parsed; exact-date value mismatches remain blocking.",
        )
        st.dataframe(evidence.source_validation, width="stretch", hide_index=True)
        st.caption("Validation issues: " + "; ".join(evidence.validation_issues))

        section_header(
            "Outcome maturity",
            "FORWARD VALIDATION LEDGER",
            "A 12-month result stays pending until the full forward window exists.",
        )
        st.dataframe(evidence.false_alarm_ledger, width="stretch", hide_index=True)

        section_header(
            "Artifact identity",
            "SOURCE CHECKSUMS",
            "SHA-256 digests establish file identity only; they do not prove provenance or truth.",
        )
        st.dataframe(
            [
                {"Artifact": name, "SHA-256": digest}
                for name, digest in sorted(evidence.checksums.items())
            ],
            width="stretch",
            hide_index=True,
        )
    except (OSError, ValueError, json.JSONDecodeError, pd.errors.ParserError) as exc:
        st.error(f"Legacy Crashmeter v3 artifact unavailable: {type(exc).__name__}")

    backtests_path = (
        Path(__file__).parents[3]
        / "assets"
        / "crashmeter_v3"
        / "backtests_b64.json"
    )
    section_header(
        "Frozen visual claims",
        "LEGACY BACKTEST CLAIM EXHIBITS",
        "Screenshots retained for comparison only; they are not replayable backtest evidence.",
    )
    st.warning(
        "CLAIM EXHIBITS ONLY — SOURCE DATA, POINT-IN-TIME VINTAGES, COSTS, AND "
        "REPLICATION CHECKSUMS ARE NOT PRESENT"
    )
    st.error(
        "ARITHMETIC DISCREPANCY — the metric exhibit says five binary components produce a "
        "0-4 score, but five independent binary values mathematically permit 0-5. The stored "
        "series is displayed as-is and is not promoted to a validated BCM."
    )
    try:
        exhibits = json.loads(backtests_path.read_text(encoding="utf-8"))
        if not isinstance(exhibits, list):
            raise ValueError("Backtest exhibit registry must be a list")
        for exhibit in exhibits:
            if not isinstance(exhibit, dict):
                raise ValueError("Backtest exhibit entry must be an object")
            title = str(exhibit.get("title") or "Untitled legacy claim")
            source = str(exhibit.get("src") or "")
            header, encoded = source.split(",", maxsplit=1)
            if header != "data:image/jpeg;base64":
                raise ValueError("Only embedded JPEG claim exhibits are accepted")
            image_bytes, width, height = _validated_jpeg(encoded)
            st.image(
                image_bytes,
                caption=f"{title} · {width}x{height}px",
                width="stretch",
            )
        st.caption(
            f"Repository artifact: assets/crashmeter_v3/backtests_b64.json · "
            f"exhibits: {len(exhibits)} · status: frozen legacy claims."
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        st.error(f"Legacy backtest claim exhibits unavailable: {type(exc).__name__}")

    sections = st.tabs(
        (
            "Thesis Discovery",
            "Evidence Firewall",
            "Mechanisms",
            "Experiments",
            "Prediction Journal",
            "Failures",
            "Data Health",
            "Coverage Gaps",
            "Models",
            "Agent IQ",
        )
    )
    with sections[0]:
        st.write("Every material observation requires 3-7 competing hypotheses including a null.")
        st.dataframe(
            [
                {
                    "Thesis": item.thesis_id,
                    "Status": item.status,
                    "Posterior": f"{item.posterior:.0%}",
                    "Interval": item.interval,
                    "Permission": item.decision_permission,
                }
                for item in state.theses
            ],
            width="stretch",
            hide_index=True,
        )
    with sections[1]:
        st.info("Narratives open research tickets; they cannot change score, sizing, or action.")
    with sections[2]:
        st.dataframe(state.mechanisms, width="stretch", hide_index=True)
    with sections[3]:
        st.warning("No experiment is eligible for PROVEN_SCOPE_LIMITED promotion in this snapshot.")
    with sections[4]:
        st.info("No matured sealed prospective forecast. Capital remains locked.")
    with sections[5]:
        st.write("Busted as tested: debt/GDP-to-gold shortcut and price-derived direction rules.")
    with sections[6]:
        feed_rows = [item.model_dump() for item in state.data_health.feeds]
        st.dataframe(feed_rows, width="stretch", hide_index=True)
    with sections[7]:
        bullet_list(state.unknowns)
    with sections[8]:
        st.info(
            "Every model requires owner, scope, assumptions, challenger, review date, "
            "and kill switch."
        )
    with sections[9]:
        st.dataframe(
            [
                {"Metric": "Calibration", "Status": "UNKNOWN"},
                {"Metric": "Replication rate", "Status": "UNKNOWN"},
                {"Metric": "Blind-spot score", "Status": "DATA_DEBT"},
                {"Metric": "Model decay", "Status": "UNKNOWN"},
            ],
            width="stretch",
            hide_index=True,
        )

    section_header("Governance", "Acceptance Battery", "Code running is not proof")
    st.dataframe(state.acceptance_gates, width="stretch", hide_index=True)
