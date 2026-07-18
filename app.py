"""War Room OS v5 — resilient intraday-quote + daily-model dashboard.

The app never substitutes synthetic data. It uses a provider cascade and persistent last-known-good
cache. If current providers fail, the latest verified desk/cache remains visible with an explicit stale
badge. External networks can still fail; the application isolates failures rather than crashing or
blanking the entire dashboard.
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = Path(__file__).resolve().parent

import streamlit as st
import streamlit.components.v1 as components

from alpha_foundry_adapter import attach_alpha_foundry, load_alpha_foundry_state, minimal_desk
from consistency_guard import enforce_desk
from data.resilient_market_data import attach_quotes_to_desk, read_health

st.set_page_config(page_title="War Room OS", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
  .stApp{background:#0a0d12}
  header[data-testid="stHeader"]{background:transparent}
  .block-container{padding:0 !important;max-width:100% !important}
  #MainMenu,footer{visibility:hidden}
  section[data-testid="stSidebar"]{width:250px !important}
</style>""", unsafe_allow_html=True)

DASH_PATH = HERE / "dashboard.html"
DESK_CACHE = HERE / ".cache" / "desk_v5.pkl"
DESK_CACHE.parent.mkdir(parents=True, exist_ok=True)


def _inject(desk):
    html = DASH_PATH.read_text(encoding="utf-8")
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk, default=str) + ";"
    if "/*__INJECT_DATA__*/" in html:
        return html.replace("/*__INJECT_DATA__*/", payload)
    return html.replace("<body>", "<body>\n<script>" + payload + "</script>", 1)


def _save_desk_lkg(desk: dict) -> None:
    try:
        tmp = DESK_CACHE.with_suffix(".pkl.tmp")
        with tmp.open("wb") as file:
            pickle.dump(desk, file, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, DESK_CACHE)
    except Exception:
        pass


def _load_desk_lkg(reason: str) -> dict | None:
    if not DESK_CACHE.exists():
        return None
    try:
        with DESK_CACHE.open("rb") as file:
            desk = pickle.load(file)
        desk = dict(desk)
        desk["meta"] = dict(desk.get("meta") or {})
        desk["meta"]["source"] = "RESILIENT_DESK_LKG"
        desk["meta"]["data_mode"] = "LAST_KNOWN_GOOD_DESK"
        desk["meta"]["lkg_reason"] = reason
        desk["meta"]["trading_permission"] = "RESEARCH_ONLY_PAPER_AND_LIVE_BLOCKED"
        return desk
    except Exception:
        return None


def _approved_source(source: str) -> bool:
    return source.startswith("RESILIENT_") or source.startswith("DAILY_SNAPSHOT")


@st.cache_data(ttl=300, show_spinner="Refreshing providers, last-known-good cache, and War Room engines…")
def _run(markets: tuple[str, ...], refresh_nonce: int):
    import data_layer as data_layer
    from run import build_desk

    force = refresh_nonce > 0
    try:
        data = data_layer.load_all(markets=list(markets), allow_live=True, force_refresh=force)
        source = str(data.get("overall_source") or "")
        if not _approved_source(source):
            cached = _load_desk_lkg("all current providers unavailable")
            if cached is not None:
                return cached
            return enforce_desk(minimal_desk(
                "No real provider or previous cache is available yet. Connect once to seed the last-known-good cache."
            ))
        desk = build_desk(data, top_per_market=12)
        desk = attach_alpha_foundry(desk)
        desk = attach_quotes_to_desk(desk, force_refresh=force)
        desk = enforce_desk(desk)
        if str(desk.get("meta", {}).get("source", "")).startswith("RESILIENT_"):
            _save_desk_lkg(desk)
        return desk
    except Exception as exc:
        cached = _load_desk_lkg(f"current refresh failed: {type(exc).__name__}: {exc}")
        if cached is not None:
            return cached
        raise


if "refresh_nonce" not in st.session_state:
    st.session_state.refresh_nonce = 0

with st.sidebar:
    st.markdown("**War Room OS · RESILIENT FEEDS**")
    markets = st.multiselect(
        "Markets", ["us", "idx", "crypto", "commodity", "fx"],
        default=["us", "idx", "crypto", "commodity", "fx"],
    )
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_minutes = st.select_slider("Refresh interval", options=[2, 5, 10, 15, 30], value=5)
    if st.button("↻ Refresh all providers now"):
        st.session_state.refresh_nonce += 1
        st.cache_data.clear()
        st.rerun()
    st.caption(
        "Provider cascade + persistent last-known-good cache. Intraday quotes may be delayed; "
        "models use daily OHLCV. PAPER/LIVE permissions remain separate."
    )
    health = read_health()
    if health.get("markets"):
        with st.expander("Feed health", expanded=False):
            for market, info in health["markets"].items():
                st.caption(
                    f"{market}: {info.get('status')} · live {info.get('live',0)} · "
                    f"fresh cache {info.get('cache_fresh',0)} · stale {info.get('cache_stale',0)} · "
                    f"missing {info.get('missing',0)}"
                )
    st.divider()
    st.markdown("**US Alpha Foundry · integrated backend**")
    foundry = load_alpha_foundry_state()
    counts = foundry.get("counts", {})
    st.caption(
        f"Status: {foundry.get('status')} · shortlist {counts.get('shortlist',0)} · "
        f"trials {counts.get('registered_trials',0)}"
    )
    st.caption("PAPER/LIVE tetap blocked sampai lockbox + prospective pass.")
    with st.expander("Run free-data research pipeline", expanded=False):
        sec_contact = st.text_input(
            "SEC contact email", value=os.environ.get("SEC_CONTACT_EMAIL", ""), key="sec_contact"
        )
        if st.button("Run US Alpha Foundry — Quick", key="run_af_quick"):
            if "@" not in sec_contact:
                st.error("Masukkan email kontak yang valid untuk SEC fair-access policy.")
            else:
                alpha_root = HERE / "alpha_foundry"
                env = os.environ.copy()
                env["SEC_USER_AGENT"] = f"Edward Gani {sec_contact}"
                with st.spinner("Running free-data Alpha Foundry. Ini dapat memakan waktu..."):
                    proc = subprocess.run(
                        [sys.executable, "run_pipeline.py", "--mode", "quick"],
                        cwd=alpha_root, env=env, text=True, capture_output=True,
                    )
                if proc.returncode == 0:
                    st.success("Pipeline selesai. Dashboard akan memakai output terbaru.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Pipeline gagal. Log terakhir:")
                    st.code((proc.stdout + "\n" + proc.stderr)[-6000:])

if auto_refresh:
    components.html(
        f"""<script>
        const wait={int(refresh_minutes)*60*1000};
        setTimeout(()=>window.parent.location.reload(), wait);
        </script>""",
        height=0,
    )

try:
    desk = _run(tuple(markets), int(st.session_state.refresh_nonce))
    # A manual refresh is forceful only once; subsequent reruns use normal cache policy.
    st.session_state.refresh_nonce = 0
    html = _inject(desk)
    meta = desk.get("meta") or {}
    source = str(meta.get("source") or "")
    mode = str(meta.get("data_mode") or "")
    count = sum(len(m.get("setups") or []) for m in (desk.get("markets") or {}).values())
    audit = desk.get("consistency_audit") or {}
    quarantined = int(audit.get("quarantined_count") or 0)
    if source == "RESILIENT_DESK_LKG":
        st.warning(
            "Current providers failed, so the dashboard loaded the last-known-good verified desk. "
            "No panel was fabricated; inspect data-as-of labels before acting."
        )
    elif source.startswith("RESILIENT_"):
        quote_text = f" · quotes {meta.get('quote_fresh',0)}/{meta.get('quote_total',0)} fresh" if meta.get("quote_total") else ""
        st.toast(f"{mode or source} · {count} displayed setups{quote_text} · RESEARCH ONLY")
        if quarantined:
            st.warning(f"{quarantined} malformed row(s) were quarantined; unaffected markets remain loaded.")
    elif source == "DATA_UNAVAILABLE":
        st.warning(
            "First-run data is unavailable and no last-known-good cache exists. Connect once, then the app can survive temporary provider outages."
        )
    else:
        st.info(f"Research state loaded with source={source}. No trading permission is implied.")
except Exception as exc:
    st.error(f"No current provider and no previous verified desk were available: {type(exc).__name__}: {exc}")
    desk = minimal_desk(str(exc))
    html = _inject(desk)

components.html(html, height=1150, scrolling=True)
