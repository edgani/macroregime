"""app.py — MacroRegime Pro Streamlit Dashboard v3.2
Fixes v3.2:
 • Error boundary: kalau build_snapshot gagal, tampilkan error + tombol retry (tidak infinite loop)
 • fast_refresh=True selalu dipakai di first load (bukan False)
 • Cooldown 30 detik antar retry untuk hindari rate limit
 • Safe import data.loader dengan try/except
"""
import streamlit as st
st.set_page_config(page_title="MacroRegime Pro v3.2", page_icon="📊", layout="wide")

import os, sys, json, time
from datetime import datetime, timezone

# ── Safe import data.loader ──────────────────────────────────────────────────
try:
    from data.loader import snapshot_age_str, load_snapshot
    _LOADER_OK = True
except Exception as _e:
    st.error(f"Loader import failed: {_e}")
    _LOADER_OK = False
    def snapshot_age_str(): return "No snapshot"
    def load_snapshot(max_age_hours=12.0): return None

# ── Session state init ───────────────────────────────────────────────────────
for k, v in {
    "snap": None,
    "loading": False,
    "build_error": None,
    "last_build_time": 0,
    "inc_us": True, "inc_fx": True, "inc_commodities": True,
    "inc_crypto": True, "inc_ihsg": True,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 MacroRegime Pro v3.2")
st.markdown('<div style="font-size:12px;color:#8B949E;">Hedgeye GIP · PVV · Options Overlay</div>', unsafe_allow_html=True)
st.divider()

st.caption(f"Last update: {snapshot_age_str()}")

c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.loading = True
        st.session_state.build_error = None
        st.rerun()
with c2:
    if st.button("⚡ Rebuild (Full)", use_container_width=True):
        st.session_state.loading = True
        st.session_state.build_error = None
        st.session_state.last_build_time = 0
        st.rerun()

# ── Error display ────────────────────────────────────────────────────────────
if st.session_state.build_error:
    st.error(f"❌ Build failed: {st.session_state.build_error}")
    st.info("Tips: Tunggu 30–60 detik lalu klik Refresh. Jika terus gagal, cek log di Manage app → Logs.")
    if st.button("🔄 Coba Lagi"):
        st.session_state.build_error = None
        st.session_state.loading = True
        st.rerun()
    st.stop()

# ── Cooldown check ─────────────────────────────────────────────────────────────
now = time.time()
elapsed = now - st.session_state.last_build_time
if st.session_state.loading and elapsed < 30:
    st.warning(f"⏳ Cooldown: tunggu {30 - int(elapsed)} detik sebelum retry (hindari rate limit Yahoo Finance).")
    st.stop()

# ── Load cached snapshot ──────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None and _LOADER_OK:
    try:
        snap = load_snapshot(max_age_hours=12.0)
        if snap and snap.get("ok"):
            st.session_state.snap = snap
    except Exception:
        pass

# ── Build snapshot ────────────────────────────────────────────────────────────
if snap is None or not snap.get("ok") or st.session_state.loading:
    if now - st.session_state.last_build_time < 30:
        st.warning("⏳ Build cooldown aktif. Gunakan snapshot cache atau tunggu.")
        st.stop()

    try:
        from orchestrator import build_snapshot
    except Exception as _e:
        st.session_state.build_error = f"Cannot import orchestrator: {_e}"
        st.session_state.loading = False
        st.rerun()

    _msg = "🔄 Refreshing data..." if st.session_state.loading else "🏗️ Building snapshot..."
    with st.spinner(_msg):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m, f): pb.progress(min(f, 0.99)); pt.caption(f"⏳ {m}")

        try:
            snap = build_snapshot(
                progress_cb=prog,
                include_us_stocks   = st.session_state.get("inc_us", True),
                include_forex       = st.session_state.get("inc_fx", True),
                include_commodities = st.session_state.get("inc_commodities", True),
                include_crypto      = st.session_state.get("inc_crypto", True),
                include_ihsg        = st.session_state.get("inc_ihsg", True),
                fast_refresh=True,
            )
            if snap and snap.get("ok"):
                st.session_state.snap = snap
                st.session_state.build_error = None
                st.session_state.last_build_time = time.time()
            else:
                st.session_state.build_error = "Snapshot returned ok=False"
        except Exception as _e:
            st.session_state.build_error = str(_e)
        finally:
            st.session_state.loading = False
            pb.empty(); pt.empty()

    st.rerun()

# ── Main dashboard ─────────────────────────────────────────────────────────
if st.session_state.snap and st.session_state.snap.get("ok"):
    snap = st.session_state.snap
    gip = snap.get("gip")
    sq = gip.structural_quad if gip else "Q3"
    mq = gip.monthly_quad if gip else "Q2"

    st.success(f"✅ Data loaded | Structural: **{sq}** | Monthly: **{mq}** | Build: {snap.get("build_time_s", "?")}s")

    tabs = st.tabs([
        "📈 Dashboard", "🎯 Alpha Center", "🇺🇸 US Stocks", "🌐 Forex",
        "🪙 Crypto", "📊 Commodities", "🇮🇩 IHSG", "⚙️ Settings"
    ])

    with tabs[0]:
        st.header("Dashboard")
        col1, col2, col3 = st.columns(3)
        col1.metric("Structural Quad", sq)
        col2.metric("Monthly Quad", mq)
        col3.metric("Build Time", f"{snap.get("build_time_s", "?")}s")

        st.subheader("Daily Signals Summary")
        ds = snap.get("daily_signals_summary", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Strong Longs", ds.get("strong_longs", 0))
        c2.metric("Longs", ds.get("longs", 0))
        c3.metric("Strong Shorts", ds.get("strong_shorts", 0))
        c4.metric("Shorts", ds.get("shorts", 0))

        st.subheader("Top 5 Alpha Ideas (Long)")
        alpha = snap.get("alpha", {})
        longs = alpha.get("longs", [])
        if longs:
            for item in longs[:5]:
                st.markdown(f"**{item.get("ticker")}** — {item.get("signal")} | Entry: {item.get("entry")} | TP1: {item.get("target_1")} | Stop: {item.get("stop_loss")} | R/R: {item.get("rr")}")
                st.caption(item.get("thesis", ""))
        else:
            st.info("No long signals.")

    with tabs[1]:
        st.header("🎯 Alpha Center")
        ac = snap.get("alpha_center", {})
        meta = ac.get("meta", {})
        st.write(f"Total items: {meta.get("total_items", 0)} | L1: {meta.get("level_1_count", 0)} | L2: {meta.get("level_2_count", 0)} | Watch: {meta.get("watch_count", 0)}")

        for level, label in [("level_1", "🔴 Level 1"), ("level_2", "🟡 Level 2"), ("alpha_long", "🟢 Alpha Long"), ("alpha_short", "🔴 Alpha Short"), ("watch", "⚪ Watch")]:
            items = ac.get(level, [])
            if items:
                with st.expander(f"{label} ({len(items)})"):
                    for it in items[:10]:
                        st.markdown(f"**{it.get("ticker")}** | {it.get("direction")} | Score: {it.get("priority_score", 0):.1f} | {it.get("frontrun_status", "")}")
                        st.caption(f"Entry: {it.get("entry")} | TP1: {it.get("target_1")} | Stop: {it.get("stop_loss")} | Advice: {it.get("entry_advice", "")}")

    with tabs[2]:
        st.header("🇺🇸 US Stocks")
        ds = snap.get("daily_signals", [])
        us_signals = [s for s in ds if not any(x in s.get("ticker", "") for x in [".JK", "=X", "=F", "-USD", "^JKSE", "EIDO"])]
        if us_signals:
            for s in us_signals[:15]:
                emoji = "🟢" if "LONG" in s.get("signal", "") else ("🔴" if "SHORT" in s.get("signal", "") else "⚪")
                st.markdown(f"{emoji} **{s.get("ticker")}** | {s.get("signal")} | Grade {s.get("grade")} | Price: {s.get("price")} | Entry: {s.get("entry")} | TP1: {s.get("target_1")} | Stop: {s.get("stop_loss")}")
                st.caption(s.get("thesis", ""))
        else:
            st.info("No US stock signals.")

    with tabs[3]:
        st.header("🌐 Forex")
        fx = [s for s in snap.get("daily_signals", []) if "=X" in s.get("ticker", "") or s.get("ticker") == "DX-Y.NYB"]
        if fx:
            for s in fx[:15]:
                st.markdown(f"**{s.get("ticker")}** | {s.get("signal")} | Price: {s.get("price")} | 1M: {s.get("momentum_1m", "—")}")
        else:
            st.info("No forex signals.")

    with tabs[4]:
        st.header("🪙 Crypto")
        crypto = [s for s in snap.get("daily_signals", []) if "-USD" in s.get("ticker", "") or s.get("ticker") in ["IBIT", "MSTR"]]
        if crypto:
            for s in crypto[:10]:
                st.markdown(f"**{s.get("ticker")}** | {s.get("signal")} | Price: {s.get("price")}")
        else:
            st.info("No crypto signals.")

    with tabs[5]:
        st.header("📊 Commodities")
        comm = [s for s in snap.get("daily_signals", []) if "=F" in s.get("ticker", "") or s.get("ticker") in ["GLD", "SLV", "USO", "UNG", "BNO", "GDX", "GDXJ"]]
        if comm:
            for s in comm[:15]:
                st.markdown(f"**{s.get("ticker")}** | {s.get("signal")} | Price: {s.get("price")}")
        else:
            st.info("No commodity signals.")

    with tabs[6]:
        st.header("🇮🇩 IHSG")
        ihsg = [s for s in snap.get("daily_signals", []) if ".JK" in s.get("ticker", "") or s.get("ticker") in ["^JKSE", "EIDO"]]
        if ihsg:
            for s in ihsg[:20]:
                st.markdown(f"**{s.get("ticker")}** | {s.get("signal")} | Price: {s.get("price")}")
        else:
            st.info("No IHSG signals.")

        st.subheader("Sector Momentum")
        sm = snap.get("ihsg_sector_momentum", {})
        if sm:
            for sector, data in sm.items():
                st.markdown(f"**{sector}**: {data.get("bias")} | 1M avg: {data.get("avg_1m", 0):.2%}")
        else:
            st.info("No sector momentum data.")

    with tabs[7]:
        st.header("⚙️ Settings")
        st.session_state["inc_us"] = st.checkbox("Include US Stocks", st.session_state.get("inc_us", True))
        st.session_state["inc_fx"] = st.checkbox("Include Forex", st.session_state.get("inc_fx", True))
        st.session_state["inc_commodities"] = st.checkbox("Include Commodities", st.session_state.get("inc_commodities", True))
        st.session_state["inc_crypto"] = st.checkbox("Include Crypto", st.session_state.get("inc_crypto", True))
        st.session_state["inc_ihsg"] = st.checkbox("Include IHSG", st.session_state.get("inc_ihsg", True))
        if st.button("💾 Save & Rebuild"):
            st.session_state.loading = True
            st.session_state.snap = None
            st.rerun()

else:
    st.error("❌ Snapshot tidak tersedia. Klik Refresh atau Rebuild.")
