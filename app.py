from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
CURRENT = OUTPUTS / "current"
DISCOVERY = OUTPUTS / "discovery"
LOCKBOX = OUTPUTS / "lockbox"
PROSPECTIVE = OUTPUTS / "prospective"
CONFIG = ROOT / "config"
DOCS = ROOT / "docs"

SHORTLIST_PATH = CURRENT / "US_TOP20_SHADOW_SHORTLIST.csv"
SHORTLIST_RECEIPT_PATH = CURRENT / "US_TOP20_SHADOW_RECEIPT.json"
PANEL_PATH = PROCESSED / "us_monthly_research_panel.parquet"
PRICE_PATH = PROCESSED / "prices_sp500_pit.parquet"
ENTITY_MASTER_PATH = PROCESSED / "entity_master.parquet"
QUARANTINE_CANDIDATES = [
    PROCESSED / "entity_mapping_quarantine.csv",
    OUTPUTS / "entity_mapping_quarantine.csv",
    OUTPUTS / "discovery" / "entity_mapping_quarantine.csv",
]
PIPELINE_LOCK = OUTPUTS / ".streamlit_pipeline_running.lock"

st.set_page_config(
    page_title="War Room US Alpha Foundry",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# File helpers
# -----------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@st.cache_data(show_spinner=False)
def read_csv(path_string: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    return pd.read_csv(path_string)


@st.cache_data(show_spinner=False)
def read_json(path_string: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    return json.loads(Path(path_string).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def read_parquet_sample(path_string: str, modified_ns: int, columns: tuple[str, ...] | None = None) -> pd.DataFrame:
    del modified_ns
    if columns:
        return pd.read_parquet(path_string, columns=list(columns))
    return pd.read_parquet(path_string)


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return read_csv(str(path), path.stat().st_mtime_ns)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Gagal membaca {path.relative_to(ROOT)}: {exc}")
        return None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return read_json(str(path), path.stat().st_mtime_ns)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Gagal membaca {path.relative_to(ROOT)}: {exc}")
        return None


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "file": str(path.relative_to(ROOT)),
            "status": "MISSING",
            "size_mb": np.nan,
            "modified": "",
        }
    stat = path.stat()
    return {
        "file": str(path.relative_to(ROOT)),
        "status": "READY",
        "size_mb": round(stat.st_size / 1024 / 1024, 3),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def format_pct(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(number):
        return "—"
    return f"{number:.{digits}%}"


def format_number(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(number):
        return "—"
    return f"{number:,.{digits}f}"


def run_command(command: list[str], environment: dict[str, str] | None = None) -> tuple[int, str]:
    """Run a command synchronously and expose grouped logs in Streamlit."""
    if PIPELINE_LOCK.exists():
        return 2, f"Runner lain sedang aktif. Lock: {PIPELINE_LOCK}"

    PIPELINE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_LOCK.write_text(
        json.dumps({"started_at_utc": utc_now(), "command": command}, indent=2),
        encoding="utf-8",
    )
    output_lines: list[str] = []
    placeholder = st.empty()
    try:
        process = subprocess.Popen(  # noqa: S603
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=environment or os.environ.copy(),
        )
        assert process.stdout is not None
        for line in process.stdout:
            output_lines.append(line.rstrip())
            placeholder.code("\n".join(output_lines[-120:]), language="text")
        return_code = process.wait()
        placeholder.code("\n".join(output_lines[-200:]), language="text")
        st.cache_data.clear()
        return return_code, "\n".join(output_lines)
    except Exception as exc:  # noqa: BLE001
        output_lines.append(f"ERROR: {exc}")
        placeholder.code("\n".join(output_lines), language="text")
        return 1, "\n".join(output_lines)
    finally:
        PIPELINE_LOCK.unlink(missing_ok=True)


def available_tournament_periods() -> list[str]:
    periods: list[str] = []
    for period, directory in [("discovery", DISCOVERY), ("validation", DISCOVERY), ("lockbox", LOCKBOX)]:
        path = directory / f"COMPONENT_SELECTOR_TOURNAMENT__{period.upper()}.csv"
        if path.exists():
            periods.append(period)
    return periods


def tournament_path(period: str) -> Path:
    directory = LOCKBOX if period == "lockbox" else DISCOVERY
    return directory / f"COMPONENT_SELECTOR_TOURNAMENT__{period.upper()}.csv"


# -----------------------------------------------------------------------------
# Header and sidebar
# -----------------------------------------------------------------------------
st.title("War Room OS — US Alpha Foundry")
st.caption("Operational research & prospective-shadow dashboard · fail-closed · bukan auto-trading")

with st.sidebar:
    st.subheader("Permission state")
    st.error("LIVE: BLOCKED", icon="⛔")
    st.warning("PAPER: BLOCKED", icon="⚠️")
    st.info("Maximum current claim: HISTORICAL CANDIDATE / PROSPECTIVE SHADOW")

    receipt = load_json(SHORTLIST_RECEIPT_PATH)
    if receipt:
        st.metric("Shortlist decision date", receipt.get("decision_date", "—"))
        st.caption(f"Model hash: `{str(receipt.get('model_hash', ''))[:16]}…`")
        st.caption(f"Panel hash: `{str(receipt.get('panel_sha256', ''))[:16]}…`")
    else:
        st.caption("Shortlist belum dibuat. Jalankan pipeline dari tab Runner.")

    st.divider()
    st.caption("Frozen rules")
    st.markdown(
        "- Tidak ada fuzzy entity join\n"
        "- Missing tidak diisi nol\n"
        "- Semua trial masuk graveyard\n"
        "- Tidak retune setelah lockbox\n"
        "- Positive WFA belum berarti proven"
    )


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
tabs = st.tabs(
    [
        "Mission Control",
        "Top-20 Shadow",
        "Tournament",
        "Prospective",
        "Data Health",
        "Runner",
        "Governance",
    ]
)


# Mission Control
with tabs[0]:
    shortlist = load_csv(SHORTLIST_PATH)
    periods = available_tournament_periods()
    validation_results = load_csv(tournament_path("validation")) if "validation" in periods else None
    trial_ledger = load_csv(DISCOVERY / "TRIAL_GRAVEYARD.csv")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current shortlist", 0 if shortlist is None else len(shortlist))
    col2.metric("Registered trials", 0 if trial_ledger is None else len(trial_ledger))
    historical_candidates = 0
    if validation_results is not None and "promotion_pass" in validation_results.columns:
        historical_candidates = int(validation_results["promotion_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
    col3.metric("Historical candidates", historical_candidates)
    col4.metric("Proven components/selectors", "0 / 0")

    st.subheader("Pipeline readiness")
    readiness_paths = [
        PANEL_PATH,
        PRICE_PATH,
        ENTITY_MASTER_PATH,
        SHORTLIST_PATH,
        SHORTLIST_RECEIPT_PATH,
        DISCOVERY / "COMPONENT_SELECTOR_TOURNAMENT__VALIDATION.csv",
        DISCOVERY / "TRIAL_GRAVEYARD.csv",
        LOCKBOX / "LOCKBOX_OPENED.json",
    ]
    readiness = pd.DataFrame([file_state(path) for path in readiness_paths])
    st.dataframe(readiness, use_container_width=True, hide_index=True)

    if shortlist is None:
        st.warning(
            "Real-market shortlist belum tersedia di folder outputs/current. "
            "Gunakan tab **Runner** untuk menjalankan Quick Pipeline."
        )
    else:
        st.success("Operational shadow shortlist tersedia. Status tetap research-only.")
        display_columns = [column for column in [
            "overall_rank", "ticker", "company_name", "sic2", "selector_score",
            "sector_rank_pct", "momentum_252_21", "revenue_growth_yoy", "accrual_quality", "why_in"
        ] if column in shortlist.columns]
        st.dataframe(shortlist[display_columns], use_container_width=True, hide_index=True)

    st.subheader("Current legal verdict")
    verdict_rows = [
        {"Object": "Data/runner", "Status": "READY", "Use": "Historical research and shadow logging"},
        {"Object": "Historical WFA", "Status": "CANDIDATE MAX", "Use": "Discovery, not proof"},
        {"Object": "Ticker selector", "Status": "UNPROVEN", "Use": "Shadow shortlist only"},
        {"Object": "PAPER/LIVE", "Status": "BLOCKED", "Use": "No capital permission"},
    ]
    st.dataframe(pd.DataFrame(verdict_rows), use_container_width=True, hide_index=True)


# Top-20 Shadow
with tabs[1]:
    shortlist = load_csv(SHORTLIST_PATH)
    receipt = load_json(SHORTLIST_RECEIPT_PATH)
    if shortlist is None:
        st.info("Belum ada shortlist nyata. Jalankan pipeline pada tab Runner.")
    else:
        if receipt:
            left, middle, right = st.columns(3)
            left.metric("Decision date", receipt.get("decision_date", "—"))
            middle.metric("Top-K", receipt.get("top_k", len(shortlist)))
            right.metric("Claim ceiling", "SHADOW ONLY")
            st.caption(receipt.get("warning", ""))

        numeric_features = [
            column for column in [
                "selector_score", "sector_rank_pct", "revenue_growth_yoy", "operating_margin",
                "operating_margin_change_yoy", "cash_conversion", "accrual_quality", "leverage",
                "shares_growth_yoy", "momentum_252_21", "volatility_63", "drawdown_252",
                "dollar_volume_63",
            ] if column in shortlist.columns
        ]
        query = st.text_input("Filter ticker/company", placeholder="NVDA atau Nvidia")
        filtered = shortlist.copy()
        if query:
            mask = filtered.astype(str).apply(
                lambda column: column.str.contains(query, case=False, na=False)
            ).any(axis=1)
            filtered = filtered[mask]

        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.download_button(
            "Download shortlist CSV",
            data=shortlist.to_csv(index=False).encode("utf-8"),
            file_name="US_TOP20_SHADOW_SHORTLIST.csv",
            mime="text/csv",
        )

        if not shortlist.empty:
            ticker = st.selectbox("Inspect ticker", shortlist["ticker"].astype(str).tolist())
            row = shortlist[shortlist["ticker"].astype(str).eq(ticker)].iloc[0]
            st.subheader(f"{ticker} — {row.get('company_name', '')}")
            rank_col, score_col, sector_col = st.columns(3)
            rank_col.metric("Overall rank", row.get("overall_rank", "—"))
            score_col.metric("Selector score", format_number(row.get("selector_score"), 4))
            sector_col.metric("Sector rank percentile", format_pct(row.get("sector_rank_pct")))
            st.write("**Why in:**", row.get("why_in", "—"))
            if numeric_features:
                profile = pd.DataFrame(
                    {
                        "feature": numeric_features,
                        "value": [pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").iloc[0] for feature in numeric_features],
                    }
                ).dropna()
                st.bar_chart(profile.set_index("feature"))


# Tournament
with tabs[2]:
    periods = available_tournament_periods()
    if not periods:
        st.info("Tournament output belum ada. Jalankan pipeline pada tab Runner.")
    else:
        period = st.selectbox("Tournament period", periods, index=periods.index("validation") if "validation" in periods else 0)
        results = load_csv(tournament_path(period))
        if results is None or results.empty:
            st.warning("Tournament file kosong atau tidak terbaca.")
        else:
            for column in [
                "months", "mean_rank_ic", "rank_ic_positive_fraction", "mean_top20_excess",
                "top20_positive_fraction", "q_value", "incremental_rank_ic_vs_momentum",
                "incremental_top20_vs_momentum",
            ]:
                if column in results.columns:
                    results[column] = pd.to_numeric(results[column], errors="coerce")

            passes = 0
            if "promotion_pass" in results.columns:
                passes = int(results["promotion_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
            a, b, c, d = st.columns(4)
            a.metric("Registered tests", len(results))
            b.metric("Historical candidates", passes)
            c.metric("Best q-value", format_number(results.get("q_value", pd.Series(dtype=float)).min(), 4))
            d.metric("Proven", 0)

            target_options = sorted(results["target_id"].dropna().astype(str).unique()) if "target_id" in results else []
            selected_targets = st.multiselect("Target", target_options, default=target_options)
            candidate_families = sorted(results["candidate_family"].dropna().astype(str).unique()) if "candidate_family" in results else []
            selected_families = st.multiselect("Candidate family", candidate_families, default=candidate_families)
            view = results.copy()
            if selected_targets:
                view = view[view["target_id"].astype(str).isin(selected_targets)]
            if selected_families:
                view = view[view["candidate_family"].astype(str).isin(selected_families)]

            sort_column = "q_value" if "q_value" in view.columns else view.columns[0]
            st.dataframe(view.sort_values(sort_column, na_position="last"), use_container_width=True, hide_index=True)

            chart_columns = [column for column in ["mean_rank_ic", "mean_top20_excess", "q_value"] if column in view.columns]
            if "candidate" in view.columns and chart_columns:
                chart_frame = view[["candidate", *chart_columns]].dropna(subset=[chart_columns[0]]).set_index("candidate")
                st.subheader("Candidate comparison")
                st.bar_chart(chart_frame[chart_columns[:2]])

            st.caption(
                "`promotion_pass=True` maksimal berarti HISTORICAL_CANDIDATE. "
                "Ia belum menjadi proven component/selector sebelum lockbox dan prospective pass."
            )


# Prospective
with tabs[3]:
    if not PROSPECTIVE.exists():
        st.info("Belum ada prospective receipts.")
    else:
        date_dirs = sorted([path for path in PROSPECTIVE.iterdir() if path.is_dir()], reverse=True)
        if not date_dirs:
            st.info("Belum ada prospective receipts. Seal shortlist dari tab Runner.")
        else:
            date = st.selectbox("Decision date", [path.name for path in date_dirs])
            directory = PROSPECTIVE / date
            seal = load_json(directory / "PROSPECTIVE_SEAL.json")
            source_receipt = load_json(directory / "US_TOP20_SHADOW_RECEIPT.json")
            sealed_shortlist = load_csv(directory / "US_TOP20_SHADOW_SHORTLIST.csv")

            x, y, z = st.columns(3)
            x.metric("Seal status", "SEALED" if seal else "MISSING")
            y.metric("Tickers", 0 if sealed_shortlist is None else len(sealed_shortlist))
            z.metric("Retrospective edit", "NO" if seal else "UNKNOWN")
            if seal:
                st.json(seal)
            if source_receipt:
                with st.expander("Source receipt"):
                    st.json(source_receipt)
            if sealed_shortlist is not None:
                st.dataframe(sealed_shortlist, use_container_width=True, hide_index=True)

            outcome_files = sorted(directory.glob("OUTCOME_T*.csv"))
            if outcome_files:
                outcome = st.selectbox("Outcome file", [path.name for path in outcome_files])
                outcome_frame = load_csv(directory / outcome)
                if outcome_frame is not None:
                    st.dataframe(outcome_frame, use_container_width=True, hide_index=True)
                    if "return" in outcome_frame.columns:
                        values = pd.to_numeric(outcome_frame["return"], errors="coerce")
                        st.metric("Mean unlocked return", format_pct(values.mean()))
            else:
                st.caption("Outcome belum di-score atau horizon belum unlock.")


# Data Health
with tabs[4]:
    st.subheader("Core data objects")
    paths = [
        DATA / "reference" / "sp500_ticker_start_end.csv",
        DATA / "reference" / "current_us_universe_2026-07-17.csv",
        ENTITY_MASTER_PATH,
        PROCESSED / "sec_fundamental_features.parquet",
        PRICE_PATH,
        PANEL_PATH,
    ]
    st.dataframe(pd.DataFrame([file_state(path) for path in paths]), use_container_width=True, hide_index=True)

    if PANEL_PATH.exists():
        try:
            panel = read_parquet_sample(
                str(PANEL_PATH),
                PANEL_PATH.stat().st_mtime_ns,
                columns=("decision_date", "ticker", "sic2"),
            )
            panel["decision_date"] = pd.to_datetime(panel["decision_date"], errors="coerce")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Panel rows", f"{len(panel):,}")
            p2.metric("Unique tickers", f"{panel['ticker'].nunique():,}")
            p3.metric("Decision months", f"{panel['decision_date'].nunique():,}")
            p4.metric("Latest decision", str(panel["decision_date"].max().date()) if panel["decision_date"].notna().any() else "—")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Panel metadata tidak dapat dibaca: {exc}")

    quarantine_path = next((path for path in QUARANTINE_CANDIDATES if path.exists()), None)
    if quarantine_path:
        quarantine = load_csv(quarantine_path)
        st.subheader("Entity mapping quarantine")
        st.caption("Rows ini sengaja tidak dipaksa join.")
        if quarantine is not None:
            st.metric("Quarantined rows", len(quarantine))
            st.dataframe(quarantine.head(500), use_container_width=True, hide_index=True)
    else:
        st.caption("Entity mapping quarantine belum dihasilkan atau kosong.")

    source_registry = load_json(CONFIG / "source_registry.json")
    if source_registry:
        st.subheader("Registered sources")
        st.json(source_registry)


# Runner
with tabs[5]:
    st.warning(
        "Runner dapat mengunduh data besar dan memerlukan internet. Jangan tutup jendela sampai proses selesai. "
        "Hasil tetap berstatus research/shadow."
    )

    mode = st.selectbox(
        "Pipeline mode",
        ["quick", "full", "build-only", "test"],
        help="Quick memakai SEC mulai 2020; full mulai 2016; build-only memakai raw data lokal; test hanya unit tests.",
    )
    email = st.text_input(
        "SEC contact email",
        placeholder="nama@email.com",
        help="Wajib untuk quick/full/build-only yang perlu SEC fair-access user agent.",
    )

    run_col, selector_col, seal_col = st.columns(3)
    with run_col:
        if st.button("Run pipeline", type="primary", use_container_width=True):
            if mode != "test" and "@" not in email:
                st.error("Masukkan email valid untuk SEC fair-access policy.")
            else:
                env = os.environ.copy()
                if email:
                    env["SEC_USER_AGENT"] = f"Edward Gani {email.strip()}"
                code, _ = run_command([sys.executable, "run_pipeline.py", "--mode", mode], env)
                if code == 0:
                    st.success("Pipeline selesai.")
                else:
                    st.error(f"Pipeline gagal dengan exit code {code}.")

    with selector_col:
        target = st.selectbox("Current selector target", ["T20", "T63", "T126", "T252"], index=1)
        top_k = st.number_input("Top K", min_value=5, max_value=100, value=20, step=5)
        if st.button("Generate shortlist", use_container_width=True):
            code, _ = run_command(
                [sys.executable, "-m", "src.run_current_selector", "--target", target, "--top-k", str(top_k)]
            )
            if code == 0:
                st.success("Shortlist dan receipt berhasil dibuat.")
            else:
                st.error(f"Selector gagal dengan exit code {code}.")

    with seal_col:
        st.caption("Seal tidak dapat ditimpa pada tanggal yang sama.")
        confirm_seal = st.checkbox("Saya paham receipt immutable", key="confirm_seal")
        if st.button("Seal prospective", disabled=not confirm_seal, use_container_width=True):
            code, _ = run_command([sys.executable, "-m", "src.prospective", "seal"])
            if code == 0:
                st.success("Prospective receipt berhasil disegel.")
            else:
                st.error("Seal gagal—kemungkinan receipt tanggal tersebut sudah ada atau shortlist belum dibuat.")

    st.divider()
    st.subheader("Lockbox — one shot")
    sentinel = load_json(LOCKBOX / "LOCKBOX_OPENED.json")
    if sentinel:
        st.error(f"Lockbox sudah dibuka pada {sentinel.get('opened_at_utc', 'unknown')}. Rerun dilarang.")
        st.json(sentinel)
    else:
        st.caption("Jangan buka sebelum discovery/validation specification benar-benar selesai.")
        phrase = st.text_input("Ketik OPEN LOCKBOX ONCE untuk mengaktifkan tombol")
        if st.button("Open historical lockbox", disabled=phrase != "OPEN LOCKBOX ONCE"):
            code, _ = run_command([sys.executable, "-m", "src.open_lockbox"])
            if code == 0:
                st.success("Lockbox dibuka satu kali dan hasil disimpan.")
            else:
                st.error(f"Lockbox gagal dengan exit code {code}.")


# Governance
with tabs[6]:
    st.subheader("Claim ladder")
    claim_ladder = load_csv(DOCS / "CLAIM_LADDER.csv")
    if claim_ladder is not None:
        st.dataframe(claim_ladder, use_container_width=True, hide_index=True)

    st.subheader("Data-gap impact")
    gaps = load_csv(DOCS / "DATA_GAP_IMPACT.csv")
    if gaps is not None:
        st.dataframe(gaps, use_container_width=True, hide_index=True)

    st.subheader("Frozen contract")
    freeze_contract = load_json(CONFIG / "freeze_contract.json")
    if freeze_contract:
        st.json(freeze_contract)

    st.error(
        "Dashboard ini sengaja tidak memiliki tombol order, leverage, position sizing, atau label PROVEN. "
        "Capital permission tetap terpisah sampai lockbox dan future prospective receipts lolos."
    )
