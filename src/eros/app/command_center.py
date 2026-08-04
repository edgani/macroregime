"""Decision-first Command Center.

Layout order follows the sealed product contract: the operator must be able to
read the page top-down in 30 seconds and know what to do. Evidence and raw data
live below the decision panels, never above them.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from eros.app.components import bullet_list, evidence_badge, section_header, status_card
from eros.app.opportunity_engine import _valid_qualified_packets
from eros.app.state import DashboardState
from eros.meters.snapshot import MetersSnapshot


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _command_center_qualified_packets(state: DashboardState) -> list[dict[str, object]]:
    """Return packets currently presented by the Command Center."""

    return _valid_qualified_packets(state)


def _feed_root_cause_rows(state: DashboardState) -> list[dict[str, str]]:
    """Expose exact symbol-level reasons a feed group is not live."""

    return [
        {
            "Feed group": feed.name,
            "Status": feed.status,
            "Expected": ", ".join(feed.expected_symbols) or "UNSPECIFIED",
            "Live": ", ".join(feed.live_symbols) or "NONE",
            "Stale": ", ".join(feed.stale_symbols) or "NONE",
            "Absent": ", ".join(feed.missing_symbols) or "NONE",
            "Blocking": ", ".join(feed.blocking_symbols) or "NONE",
            "Disabled consequence": ", ".join(feed.disabled_components) or "NONE",
        }
        for feed in state.data_health.feeds
    ]


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


@st.cache_data(ttl=1800, show_spinner="Menghitung meter proven dari sumber publik...")
def _compute_meters() -> MetersSnapshot:
    """Live computation first; committed precomputed snapshot as fallback.

    FRED blocks Streamlit Cloud egress, so the public deploy computes meters
    from the committed snapshot (clearly labelled PRECOMPUTED with its as-of
    dates) while local runs stay live. Cached only on success.
    """

    from eros.meters.snapshot import compute_meters_snapshot, load_precomputed

    try:
        live = compute_meters_snapshot()
    except Exception:
        live = None
    if live is not None and live.bcm.value is not None:
        return live
    precomputed = load_precomputed()
    if precomputed is not None:
        return precomputed
    if live is not None:
        return live
    raise RuntimeError("meter engine unavailable and no precomputed snapshot")


def _load_meters() -> tuple[MetersSnapshot | None, str | None]:
    """Return (meters, error). error is the engine failure signature, if any.

    A failed computation is deliberately NOT cached, so a transient outage does
    not extend itself across the full TTL.
    """

    try:
        return _compute_meters(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _zone(value: float | None) -> str:
    if value is None:
        return "NO_DATA"
    if value >= 0.8:
        return "MERAH"
    if value >= 0.5:
        return "KUNING"
    return "HIJAU"


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "NO_DATA"


def _headline_action(meters: MetersSnapshot | None, qualified_count: int) -> tuple[str, str]:
    """One plain-Indonesian headline plus its reason, derived only from machine state."""

    if meters is None:
        return (
            "DATA METER TIDAK TERSEDIA — tahan semua keputusan baru.",
            "Engine tidak dapat menjangkau sumber publik; sistem fail-closed, bukan menebak.",
        )
    exposure = meters.exposure
    bcm = meters.bcm.value
    frag = meters.fragility_reading.value
    if bcm is None or frag is None or exposure is None:
        return (
            "GATE TIDAK LENGKAP — tahan keputusan baru sampai BCM/FRAGILITY terisi.",
            (
                f"BCM {_fmt(bcm)}, FRAGILITY {_fmt(frag)}, exposure belum dapat dihitung. "
                "Sistem fail-closed: tanpa gate lengkap tidak ada headline aksi."
            ),
        )
    if exposure == 0.0:
        return (
            "GATE MERAH — ekuitas 0%. Jangan tambah posisi saham; fokus lindungi modal.",
            (
                f"BCM {bcm:.2f} dan FRAGILITY {frag:.2f}: stress sistemik di atas valuasi "
                "ekstrem. Rule R2 memaksa keluar."
            ),
        )
    if meters.fear_entry:
        return (
            "FEAR-ENTRY AKTIF — nyicil posisi secara bertahap sesuai rule, bukan sekaligus.",
            (
                "VIX di zona ekstrem sementara inflasi rendah: secara historis ini titik "
                "akumulasi terbaik, bukan momen panik."
            ),
        )
    if exposure == 0.5:
        return (
            "TRANSISI — ekuitas maksimal 50%. Tambah hanya lewat re-entry rule R2.",
            (
                f"BCM {bcm:.2f} sedang turun dari zona merah; sistem masuk kembali "
                "bertahap, bukan langsung penuh."
            ),
        )
    actions: list[str] = []
    if meters.gold.value is not None and meters.gold.value >= 0.85:
        actions.append("TRIM emas bertahap")
    if exposure == 1.0:
        actions.append("pertahankan ekuitas")
    if qualified_count == 0:
        actions.append("belum ada conviction play baru yang lolos bukti")
    headline = "; ".join(actions).upper() + "."
    reason = (
        f"BCM {bcm:.2f} (gate terbuka), FRAGILITY {frag:.2f} (valuasi ekstrem), "
        f"GOLD {_fmt(meters.gold.value)}. Mesin membolehkan posisi, tetapi zona ekstrem "
        "adalah area panen, bukan entry baru."
    )
    return headline, reason


def _scenario_rows(meters: MetersSnapshot | None) -> list[dict[str, str]]:
    """Deterministic 1-week / 1-month / 1-year+ guidance from machine state only."""

    if meters is None:
        return [
            {"Horizon": "1 MINGGU", "Sikap": "TAHAN",
             "Dasar": "Data meter tidak tersedia; fail-closed."},
            {"Horizon": "1 BULAN", "Sikap": "TAHAN",
             "Dasar": "Data meter tidak tersedia; fail-closed."},
            {
                "Horizon": "1 TAHUN+",
                "Sikap": "TAHAN",
                "Dasar": "Data meter tidak tersedia; fail-closed.",
            },
        ]
    gold = meters.gold.value
    bcm = meters.bcm.value
    frag = meters.fragility_reading.value
    exposure = meters.exposure

    if bcm is None or frag is None or exposure is None:
        return [
            {"Horizon": "1 MINGGU", "Sikap": "TAHAN",
             "Dasar": "Gate tidak lengkap; fail-closed."},
            {"Horizon": "1 BULAN", "Sikap": "TAHAN",
             "Dasar": "Gate tidak lengkap; fail-closed."},
            {"Horizon": "1 TAHUN+", "Sikap": "TAHAN",
             "Dasar": "Gate tidak lengkap; fail-closed."},
        ]

    if exposure == 0.0:
        week = (
            "DEFENSIF",
            "Gate merah: tanpa posisi ekuitas baru. Siapkan daftar beli untuk re-entry "
            "R2 (BCM < 0.60).",
        )
    elif meters.fear_entry:
        week = (
            "NYICIL",
            "FEAR-ENTRY menyala: akumulasi bertahap sesuai rule, jangan langsung penuh.",
        )
    else:
        parts = ["Pertahankan posisi inti"]
        if gold is not None and gold >= 0.85:
            parts.append("trim emas bertahap di zona ekstrem")
        parts.append("tidak ada sinyal keluar dari mesin")
        week = ("HOLD + PANEN ZONA EKSTREM", "; ".join(parts) + ".")

    tilt = meters.tilt
    if tilt:
        top = max(tilt, key=lambda name: tilt[name])
        month = (
            f"REBALANCE SESUAI TILT — porsi terbesar: {top} {tilt[top]:.0%}",
            (
                f"Tilt bulan ini: SPX {tilt.get('SPX', 0):.0%} / TLT {tilt.get('TLT', 0):.0%} "
                f"/ COMM {tilt.get('COMM', 0):.0%} / GLD {tilt.get('GLD', 0):.0%}. "
                "Rebalance hanya lewat mesin, bukan feeling."
            ),
        )
    else:
        month = ("TAHAN", "Tilt tidak dapat dihitung; tidak ada rebalance tanpa data.")

    if frag is not None and frag >= 0.8 and (bcm is not None and bcm < 0.65):
        year = (
            "BARBELL — bangun cash dari panen, siapkan dry powder.",
            (
                f"FRAGILITY {frag:.2f} berarti valuasi historis ekstrem, tetapi BCM {bcm:.2f} "
                "berarti belum ada stress sistemik. Secara historis ini fase 'mahal tapi "
                "belum pecah': panen zona ekstrem, simpan mesin FEAR-ENTRY untuk momen "
                "crash, jangan all-in baru."
            ),
        )
    elif exposure == 0.0:
        year = (
            "DEFENSIF PENUH",
            "Gate merah aktif: modal dilindungi dulu, opportunity dicari di sisi "
            "short/defensif yang lolos bukti.",
        )
    else:
        year = (
            "NORMAL",
            "Valuasi tidak ekstrem dan gate terbuka: posture risk-on biasa dengan sizing standar.",
        )
    return [
        {"Horizon": "1 MINGGU", "Sikap": week[0], "Dasar": week[1]},
        {"Horizon": "1 BULAN", "Sikap": month[0], "Dasar": month[1]},
        {"Horizon": "1 TAHUN+", "Sikap": year[0], "Dasar": year[1]},
    ]


def _action_rows(
    meters: MetersSnapshot | None, qualified_count: int, execution_enabled: bool
) -> list[dict[str, str]]:
    """Action queue with explicit ACTION pills and machine-readable reasons."""

    rows: list[dict[str, str]] = []
    if meters is None:
        return [
            {
                "Aset": "SEMUA",
                "Aksi": "VETO",
                "Alasan": "Meter engine NO_DATA — tidak ada aksi baru tanpa data.",
                "Bukti": "fail-closed",
            }
        ]
    gold = meters.gold.value
    if gold is not None:
        if gold >= 0.85:
            rows.append(
                {
                    "Aset": "Emas (GLD)",
                    "Aksi": "TRIM",
                    "Alasan": (
                        f"Gold Meter {gold:.2f} di zona ekstrem historis — area panen "
                        "bertahap, bukan entry baru."
                    ),
                    "Bukti": "PROVEN meter v2",
                }
            )
        elif gold <= 0.35:
            rows.append(
                {
                    "Aset": "Emas (GLD)",
                    "Aksi": "WAIT",
                    "Alasan": (
                        f"Gold Meter {gold:.2f} zona akumulasi — tunggu konfirmasi thesis "
                        "sebelum tambah."
                    ),
                    "Bukti": "PROVEN meter v2",
                }
            )
        else:
            rows.append(
                {
                    "Aset": "Emas (GLD)",
                    "Aksi": "HOLD",
                    "Alasan": f"Gold Meter {gold:.2f} zona tengah — tidak ada aksi dari mesin.",
                    "Bukti": "PROVEN meter v2",
                }
            )
    dollar = meters.dollar.value
    if dollar is not None and dollar >= 0.70:
        rows.append(
            {
                "Aset": "Dollar / EM / Komoditas",
                "Aksi": "WATCH",
                "Alasan": (
                    f"Dollar Meter {dollar:.2f} mendekati zona top (kondisi paling tight) — "
                    "tekanan ke EM dan komoditas."
                ),
                "Bukti": "PROVEN meter v1",
            }
        )
    exposure = meters.exposure
    bcm_value = meters.bcm.value
    if exposure is None or bcm_value is None:
        rows.append(
            {
                "Aset": "Ekuitas (SPX)",
                "Aksi": "VETO",
                "Alasan": "Gate tidak dapat dihitung lengkap — fail-closed.",
                "Bukti": "PROVEN_SCOPE_LIMITED BCM v3.2",
            }
        )
    elif exposure == 1.0:
        rows.append(
            {
                "Aset": "Ekuitas (SPX)",
                "Aksi": "HOLD",
                "Alasan": (
                    f"Gate terbuka: BCM {bcm_value:.2f} < 0.65. Porsi maksimal 100% "
                    "sesuai R2."
                ),
                "Bukti": "PROVEN_SCOPE_LIMITED BCM v3.2",
            }
        )
    elif exposure == 0.5:
        rows.append(
            {
                "Aset": "Ekuitas (SPX)",
                "Aksi": "WAIT",
                "Alasan": "Re-entry bertahap: penuh hanya setelah BCM < 0.50.",
                "Bukti": "PROVEN_SCOPE_LIMITED BCM v3.2",
            }
        )
    else:
        rows.append(
            {
                "Aset": "Ekuitas (SPX)",
                "Aksi": "SKIP",
                "Alasan": "Gate merah: tanpa posisi ekuitas.",
                "Bukti": "PROVEN_SCOPE_LIMITED BCM v3.2",
            }
        )
    if meters.fear_entry:
        rows.append(
            {
                "Aset": "Ekuitas (akumulasi)",
                "Aksi": "ENTER BERTAHAP",
                "Alasan": (
                    "FEAR-ENTRY aktif: VIX ekstrem + inflasi rendah — sinyal nyicil "
                    "historis terkuat."
                ),
                "Bukti": "PROVEN fear-entry",
            }
        )
    if qualified_count == 0:
        rows.append(
            {
                "Aset": "Saham individual",
                "Aksi": "WAIT",
                "Alasan": (
                    "Belum ada packet conviction yang lolos evidence gate — bukan berarti "
                    "tidak ada peluang, berarti belum terbukti."
                ),
                "Bukti": "canonical admission",
            }
        )
    if not execution_enabled:
        rows.append(
            {
                "Aset": "Eksekusi",
                "Aksi": "VETO",
                "Alasan": (
                    "Execution locked: anti-contamination policy dan human approval belum "
                    "lengkap."
                ),
                "Bukti": "policy gate",
            }
        )
    return rows


def _decision_brief(state: DashboardState, meters: MetersSnapshot | None) -> None:
    qualified_count = len(_command_center_qualified_packets(state))
    headline, reason = _headline_action(meters, qualified_count)
    st.markdown(
        f"""
        <div class="brief">
          <h3>HARI INI: {headline}</h3>
          <p><b>Kenapa:</b> {reason}</p>
          <p><b>Aturan mainnya:</b> aksi hanya boleh berubah kalau data berubah — bukan
          karena berita,
          bukan karena feeling. Semua angka di halaman ini bisa ditelusuri ke sumbernya di bagian
          DATA &amp; BUKTI di bawah.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _gate_strip(meters: MetersSnapshot | None) -> None:
    section_header(
        "Satpam ekuitas",
        "CRASH GATE (BCM v3.2)",
        "Boleh main atau tidak. Dua sumbu: STRESS harian x FRAGILITY valuasi.",
    )
    if meters is None:
        st.error("METER ENGINE: NO_DATA — gate tidak dapat dihitung, fail-closed.")
        return
    col_bcm, col_frag, col_expo, col_fear = st.columns(4)
    bcm = meters.bcm.value
    frag = meters.fragility_reading.value
    with col_bcm:
        st.metric(
            "BCM STRESS",
            f"{bcm:.2f}" if bcm is not None else "NO_DATA",
            help="0-1 percentile historis; >=0.65 bersama FRAGILITY>=0.8 = exit",
        )
        if bcm is not None:
            st.progress(min(max(bcm, 0.0), 1.0))
        st.caption(f"Zona: {_zone(bcm)} · exit di ≥0.65")
    with col_frag:
        st.metric(
            "FRAGILITY",
            f"{frag:.2f}" if frag is not None else "NO_DATA",
            help="Buffett x CAPE; valuasi ekstrem = kondisi rapuh",
        )
        if frag is not None:
            st.progress(min(max(frag, 0.0), 1.0))
        status_note = (
            "PARTIAL — CAPE unavailable"
            if "CAPE" in meters.fragility_reading.missing
            else "LIVE"
        )
        st.caption(f"Zona: {_zone(frag)} · rapuh di ≥0.80 · {status_note}")
    with col_expo:
        exposure = meters.exposure
        label = "NO_DATA" if exposure is None else {1.0: "100%", 0.5: "50%", 0.0: "0%"}[exposure]
        st.metric(
            "PORSI MAKSIMAL EKUITAS (R2)",
            label,
            help="Output state machine R2: exit / 50% re-entry / 100% / re-exit",
        )
        st.caption("Angka ini satu-satunya penentu porsi ekuitas hari ini.")
    with col_fear:
        fear = meters.fear_entry
        st.metric(
            "FEAR-ENTRY",
            "AKTIF" if fear else "STANDBY",
            help="Nyicil saat VIX ekstrem + inflasi rendah (hit historis 100%, n=29)",
        )
        st.caption("Pemicu: pct(VIX)>0.80 dan INFL≤0.50")
    if meters.blocks:
        st.caption(
            "Blok BCM: "
            + " · ".join(f"{name} {value:.2f}" for name, value in sorted(meters.blocks.items()))
        )
    if meters.source == "PRECOMPUTED":
        st.warning(
            f"METER PRECOMPUTED — dihitung {meters.fetched_at} dari lingkungan yang dapat "
            "menjangkau FRED; refresh live dari cloud sedang tidak tersedia. Angka tetap "
            "berlabel as-of per meter."
        )
    st.caption(
        f"Checksum port vs referensi riset: {meters.checksum_status} — {meters.checksum_note}"
    )


def _meters_row(meters: MetersSnapshot | None) -> None:
    section_header(
        "Kondisi tiap kelas aset",
        "ASSET METERS",
        "0-1 percentile historis per aset. Slot abu-abu = jujur belum ada bukti.",
    )
    if meters is None:
        st.info("Meters tidak tersedia — NO_DATA.")
        return
    readings = [meters.gold, meters.dollar, meters.duration]
    cols = st.columns(len(readings) + 2)
    for col, reading in zip(cols, readings, strict=False):
        with col:
            st.metric(
                reading.label,
                f"{reading.value:.2f}" if reading.value is not None else "NO_DATA",
            )
            if reading.value is not None:
                st.progress(min(max(reading.value, 0.0), 1.0))
            missing = f" · missing: {', '.join(reading.missing)}" if reading.missing else ""
            st.caption(f"{reading.status} · as of {reading.as_of}{missing}")
    with cols[-2]:
        st.metric("CRYPTO", "NO PROVEN SIGNAL")
        st.caption(
            "Belum ada meter crypto yang lolos promotion bar — jangan disentuh dari dashboard ini."
        )
    with cols[-1]:
        st.metric("IHSG", "NO PROVEN SIGNAL")
        st.caption("Butuh broker summary + fundamental PIT IDX — terdaftar sebagai data debt.")


def _tilt_card(meters: MetersSnapshot | None) -> None:
    section_header(
        "Rotasi makro bulanan",
        "TILT ENGINE",
        "Bobot baseline 4 aset dari INFL dan GROWTH. Rebalance hanya dari sini.",
    )
    if meters is None or not meters.tilt:
        st.info("Tilt tidak dapat dihitung — NO_DATA.")
        return
    for asset, weight in meters.tilt.items():
        label, bar = st.columns([0.18, 0.82])
        with label:
            st.markdown(f"**{asset}** {weight:.0%}")
        with bar:
            st.progress(min(max(weight, 0.0), 1.0))


def _scenario_panel(meters: MetersSnapshot | None) -> None:
    section_header(
        "Harus ngapain",
        "SKENARIO & SIKAP",
        "Jawaban mesin untuk tiga horizon. Berubah hanya kalau data berubah.",
    )
    st.dataframe(_scenario_rows(meters), width="stretch", hide_index=True)


def _action_queue(state: DashboardState, meters: MetersSnapshot | None) -> None:
    section_header(
        "Antrian keputusan",
        "ACTION QUEUE",
        "ENTER/WAIT/SKIP/TRIM/VETO — setiap baris punya alasan dan label bukti.",
    )
    qualified_count = len(_command_center_qualified_packets(state))
    rows = _action_rows(meters, qualified_count, state.execution_enabled)
    st.dataframe(rows, width="stretch", hide_index=True)


def render(state: DashboardState) -> None:
    meters, meters_error = _load_meters()
    if meters is None and meters_error is not None:
        st.error(f"METER ENGINE GAGAL (fail-closed): {meters_error}")
    _decision_brief(state, meters)
    _gate_strip(meters)
    _meters_row(meters)
    _tilt_card(meters)
    _scenario_panel(meters)
    _action_queue(state, meters)

    qualified_packets = _command_center_qualified_packets(state)
    section_header(
        "Decision surface",
        "Command Center — status mesin",
        "Ringkasan teknis; keputusan sudah dijawab panel di atas.",
    )

    columns = st.columns(4)
    execution_status = "APPROVED" if state.execution_enabled else "LOCKED"
    cards = (
        (
            "Data health",
            state.data_health.overall_status,
            f"{state.data_health.live_feeds}/{state.data_health.total_feeds} feeds live",
            state.data_health.overall_status,
        ),
        (
            "Qualified opportunities",
            str(len(qualified_packets)),
            "Conservative net-EV gate",
            "UNKNOWN",
        ),
        (
            "Execution",
            execution_status,
            "Human approval and anti-contamination gates are mandatory",
            execution_status,
        ),
        ("Material unknowns", str(len(state.unknowns)), "Visible, never imputed", "DATA_DEBT"),
    )
    for column, card in zip(columns, cards, strict=True):
        with column:
            status_card(*card)

    section_header(
        "Evidence",
        "DATA & BUKTI",
        "Semua angka di atas ditelusuri di sini. Monitoring bukan sinyal.",
    )

    if state.market_snapshot:
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
        "Failure decomposition",
        "FEED ROOT CAUSE MATRIX",
        "Expected, live, stale, absent, and decision-blocking symbols by feed contract.",
    )
    st.dataframe(_feed_root_cause_rows(state), width="stretch", hide_index=True)

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
        if not qualified_packets:
            st.warning("NO QUALIFIED OPPORTUNITY")
        else:
            st.dataframe(qualified_packets, width="stretch", hide_index=True)
    with action:
        section_header("Human gate", "Execution Gate", "Actions remain reviewable and reversible")
        execution_status = "APPROVED" if state.execution_enabled else "LOCKED"
        execution_reason = state.execution.reason
        if state.execution.permission == "APPROVED" and not state.execution_enabled:
            execution_reason = "Anti-contamination policy blocks live-capital promotion."
        st.error(f"{execution_status} — {execution_reason}")

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
