"""app.py — MacroRegime Pro Streamlit Dashboard v4.0 (Hedgeye Edition)
v4.0 changes:
 • Hedgeye visual identity: navy + gold palette, Inter font, Q-colored badges
 • Quad badges (Q1 green / Q2 orange / Q3 red / Q4 purple) everywhere
 • GIP probability bars + flip_hazard + divergence prominent
 • Risk Range™ tab with Trade/Trend/Tail per asset
 • Risk disclosure on every alpha card per CLAUDE.md mandate
 • "Process output. Manage risk accordingly." footer
 • New tab order: Macro / Alpha Center / Risk Range™ / US / FX / Commodities / Crypto / IHSG / Settings
 • Refresh vs Rebuild visually differentiated
 • Stale-snapshot fallback when build fails
"""
import streamlit as st
st.set_page_config(page_title="MacroRegime Pro", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

import os, sys, json, time
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Hedgeye palette + Inter font + Quad badges
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stText, button, input, select, textarea {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.stApp { background: #0E1620; }
.block-container { padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1400px; }

/* Hide streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

/* Brand header */
.brand-row {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 4px 0 14px 0; border-bottom: 1px solid #2E4365; margin-bottom: 18px;
}
.brand-title { font-size: 24px; font-weight: 800; color: #E8ECF0; letter-spacing: 0.3px; }
.brand-gold { color: #C9A961; }
.brand-sub { font-size: 10px; color: #8B9AAB; text-transform: uppercase; letter-spacing: 2px; font-weight: 500; }
.brand-age { font-size: 11px; color: #8B9AAB; padding: 3px 10px; border: 1px solid #2E4365; border-radius: 12px; }

/* Quad badges */
.quad-badge {
  display: inline-block; padding: 5px 12px; border-radius: 3px;
  font-weight: 700; font-size: 12px; letter-spacing: 0.6px;
  color: white; text-transform: uppercase;
}
.quad-q1 { background: #2E9E5F; }
.quad-q2 { background: #E89B3C; }
.quad-q3 { background: #D14B5F; }
.quad-q4 { background: #8B5FBF; }

/* Macro banner */
.macro-banner {
  background: linear-gradient(135deg, #1B2A41 0%, #243553 100%);
  border: 1px solid #2E4365; border-left: 4px solid #C9A961;
  border-radius: 6px; padding: 18px 22px; margin-bottom: 18px;
}
.macro-row { display: flex; gap: 32px; align-items: center; flex-wrap: wrap; }
.macro-block-label { font-size: 10px; color: #8B9AAB; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
.macro-block-val { font-size: 14px; color: #E8ECF0; font-weight: 600; }

/* Probability bars */
.prob-bar-row { display: flex; align-items: center; gap: 10px; font-size: 12px; margin: 3px 0; }
.prob-label { width: 28px; font-weight: 600; color: #E8ECF0; font-size: 11px; }
.prob-track { flex: 1; height: 8px; background: #0E1620; border-radius: 4px; overflow: hidden; }
.prob-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.prob-pct { width: 42px; text-align: right; color: #8B9AAB; font-size: 11px; font-variant-numeric: tabular-nums; }

/* Signal pills */
.sig-long { color: #2E9E5F; font-weight: 700; }
.sig-strong-long { color: #2E9E5F; font-weight: 800; }
.sig-short { color: #D14B5F; font-weight: 700; }
.sig-strong-short { color: #D14B5F; font-weight: 800; }
.sig-neutral { color: #8B9AAB; font-weight: 500; }

/* Hedgeye card */
.he-card {
  background: #1B2A41; border: 1px solid #2E4365; border-radius: 6px;
  padding: 14px 18px; margin-bottom: 10px;
}
.he-card-header {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 6px;
}
.he-ticker { font-size: 16px; font-weight: 800; color: #E8ECF0; letter-spacing: 0.4px; }
.he-meta { font-size: 11px; color: #8B9AAB; }
.he-levels {
  display: flex; gap: 18px; font-size: 12px; margin: 6px 0;
  color: #C9D5E0; font-variant-numeric: tabular-nums;
}
.he-levels b { color: #C9A961; font-weight: 700; }
.he-thesis { font-size: 12px; color: #8B9AAB; line-height: 1.5; margin-top: 4px; }

/* Risk disclosure block */
.risk-disc {
  background: rgba(201, 169, 97, 0.07); border-left: 3px solid #C9A961;
  padding: 6px 10px; font-size: 11px; color: #C9D5E0;
  margin-top: 8px; border-radius: 0 3px 3px 0; line-height: 1.4;
}

/* Process footer */
.process-footer {
  text-align: center; font-size: 10px; color: #8B9AAB;
  padding: 14px 0; border-top: 1px solid #2E4365; margin-top: 28px;
  letter-spacing: 1.5px; text-transform: uppercase; font-weight: 500;
}

/* Risk Range table */
.rr-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rr-table th {
  background: #243553; color: #C9A961; padding: 8px 10px; text-align: left;
  text-transform: uppercase; letter-spacing: 1px; font-size: 10px; border-bottom: 2px solid #C9A961;
}
.rr-table td { padding: 8px 10px; border-bottom: 1px solid #2E4365; color: #E8ECF0; font-variant-numeric: tabular-nums; }
.rr-table tr:hover td { background: #243553; }
.rr-ticker { font-weight: 700; color: #C9A961; }

/* Progress bar */
.stProgress > div > div > div > div { background-color: #C9A961 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid #2E4365; }
.stTabs [data-baseweb="tab"] {
  background: transparent; color: #8B9AAB; border-radius: 4px 4px 0 0;
  padding: 8px 14px; font-weight: 500; font-size: 13px;
}
.stTabs [aria-selected="true"] {
  background: #1B2A41 !important; color: #C9A961 !important;
  border-bottom: 2px solid #C9A961; font-weight: 700;
}

/* Buttons */
.stButton button {
  border-radius: 4px; font-weight: 600; letter-spacing: 0.3px;
  border: 1px solid #2E4365; background: #1B2A41; color: #E8ECF0;
}
.stButton button:hover { border-color: #C9A961; color: #C9A961; }
.stButton button[kind="primary"] { background: #C9A961; color: #0E1620; border: 1px solid #C9A961; }
.stButton button[kind="primary"]:hover { background: #D9B971; color: #0E1620; }

/* Metrics */
[data-testid="stMetricValue"] { color: #C9A961; font-weight: 800; font-size: 24px; }
[data-testid="stMetricLabel"] { color: #8B9AAB; font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
[data-testid="stMetricDelta"] { font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ── Safe import data.loader ──────────────────────────────────────────────────
try:
    from data.loader import snapshot_age_str, load_snapshot
    _LOADER_OK = True
except Exception as _e:
    st.error(f"Loader import failed: {_e}")
    _LOADER_OK = False
    def snapshot_age_str(): return "No snapshot"
    def load_snapshot(max_age_hours=12.0): return None

# ══════════════════════════════════════════════════════════════════════════════
# Quad metadata + render helpers
# ══════════════════════════════════════════════════════════════════════════════
QUAD_META = {
    "Q1": {"name": "Growth↑ Inflation↓", "color": "#2E9E5F", "bias": "Bullish growth, sell vol"},
    "Q2": {"name": "Growth↑ Inflation↑", "color": "#E89B3C", "bias": "Reflation, own commodities/energy"},
    "Q3": {"name": "Stagflation",        "color": "#D14B5F", "bias": "Defensive: gold, utilities, staples"},
    "Q4": {"name": "Deflation",          "color": "#8B5FBF", "bias": "Bonds + USD, sell risk"},
}

def q_badge(q: str) -> str:
    q = q if q in QUAD_META else "Q3"
    return f'<span class="quad-badge quad-{q.lower()}">{q}</span>'

def sig_pill(signal: str) -> str:
    s = (signal or "").upper()
    if "STRONG LONG" in s: return f'<span class="sig-strong-long">{signal}</span>'
    if "STRONG SHORT" in s: return f'<span class="sig-strong-short">{signal}</span>'
    if "LONG" in s: return f'<span class="sig-long">{signal}</span>'
    if "SHORT" in s: return f'<span class="sig-short">{signal}</span>'
    return f'<span class="sig-neutral">{signal or "—"}</span>'

def prob_bars(probs: dict) -> str:
    if not probs: return ""
    rows = []
    for q in ("Q1", "Q2", "Q3", "Q4"):
        p = float(probs.get(q, 0) or 0)
        pct = max(0, min(1, p)) * 100
        color = QUAD_META[q]["color"]
        rows.append(
            f'<div class="prob-bar-row"><div class="prob-label">{q}</div>'
            f'<div class="prob-track"><div class="prob-fill" style="width:{pct:.1f}%;background:{color};"></div></div>'
            f'<div class="prob-pct">{pct:.0f}%</div></div>'
        )
    return "".join(rows)

def risk_disclosure_html(duration: str, quad: str, alt_quad: str = None) -> str:
    alt = alt_quad or {"Q1":"Q4","Q2":"Q3","Q3":"Q2","Q4":"Q1"}.get(quad, "Q1")
    return (f'<div class="risk-disc"><b>{duration}</b> idea within '
            f'<b>{quad}</b> ({QUAD_META.get(quad,{}).get("name","")}). '
            f'If Quad shifts to <b>{alt}</b>, thesis breaks.</div>')

def fmt_num(x, dp=2):
    try:
        x = float(x)
        if abs(x) >= 1e6: return f"{x/1e6:.{dp}f}M"
        if abs(x) >= 1e3: return f"{x/1e3:.{dp}f}K"
        return f"{x:.{dp}f}"
    except Exception:
        return "—"

def render_alpha_card(item: dict, quad: str, duration: str = "TREND"):
    t = item.get("ticker", "—")
    sig = item.get("signal", item.get("direction", "—"))
    entry = fmt_num(item.get("entry"))
    tp1 = fmt_num(item.get("target_1"))
    stop = fmt_num(item.get("stop_loss"))
    rr = item.get("rr", "—")
    score = item.get("priority_score", item.get("score", 0))
    fr = item.get("frontrun_status", "")
    thesis = item.get("thesis") or item.get("known_thesis") or item.get("entry_advice") or ""
    html = (
        f'<div class="he-card">'
        f'<div class="he-card-header">'
        f'<div><span class="he-ticker">{t}</span> &nbsp; {sig_pill(sig)}</div>'
        f'<div class="he-meta">Score {score:.1f} · {fr}</div>'
        f'</div>'
        f'<div class="he-levels">Entry <b>{entry}</b> · TP1 <b>{tp1}</b> · Stop <b>{stop}</b> · R/R <b>{rr}</b></div>'
        + (f'<div class="he-thesis">{thesis}</div>' if thesis else "")
        + risk_disclosure_html(duration, quad)
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_signal_row(s: dict, quad: str):
    t = s.get("ticker", "—")
    sig = s.get("signal", "—")
    grade = s.get("grade", "—")
    price = fmt_num(s.get("price"))
    entry = fmt_num(s.get("entry"))
    tp1 = fmt_num(s.get("target_1"))
    stop = fmt_num(s.get("stop_loss"))
    thesis = s.get("thesis", "")
    html = (
        f'<div class="he-card">'
        f'<div class="he-card-header">'
        f'<div><span class="he-ticker">{t}</span> &nbsp; {sig_pill(sig)} &nbsp; <span class="he-meta">Grade {grade}</span></div>'
        f'<div class="he-meta">Px {price}</div>'
        f'</div>'
        f'<div class="he-levels">Entry <b>{entry}</b> · TP1 <b>{tp1}</b> · Stop <b>{stop}</b></div>'
        + (f'<div class="he-thesis">{thesis}</div>' if thesis else "")
        + risk_disclosure_html("TRADE", quad)
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def render_risk_range_table(asset_ranges: dict, prices: dict, top_n: int = 40):
    """Render Risk Range™ three-duration table: Trade / Trend / Tail."""
    rows = []
    for tk, ranges in list(asset_ranges.items())[:top_n]:
        if not isinstance(ranges, dict): continue
        trade = ranges.get("trade") or ranges.get("TRADE") or {}
        trend = ranges.get("trend") or ranges.get("TREND") or {}
        tail  = ranges.get("tail")  or ranges.get("TAIL")  or {}
        px = "—"
        try:
            s = prices.get(tk)
            if s is not None and len(s) > 0:
                px = f"{float(s.iloc[-1]):.2f}"
        except Exception:
            pass
        def lo_hi(r):
            if not isinstance(r, dict): return "— / —"
            lo = r.get("low", r.get("lo"))
            hi = r.get("high", r.get("hi"))
            try: return f"{float(lo):.2f} / {float(hi):.2f}"
            except Exception: return "— / —"
        rows.append(
            f'<tr><td class="rr-ticker">{tk}</td><td>{px}</td>'
            f'<td>{lo_hi(trade)}</td><td>{lo_hi(trend)}</td><td>{lo_hi(tail)}</td></tr>'
        )
    if not rows:
        st.info("No Risk Range data available.")
        return
    table = (
        '<table class="rr-table">'
        '<thead><tr><th>Ticker</th><th>Last</th>'
        '<th>Trade ≤3wk (Lo/Hi)</th><th>Trend ≥3mo (Lo/Hi)</th><th>Tail ≤3yr (Lo/Hi)</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table>'
    )
    st.markdown(table, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Session state init
# ══════════════════════════════════════════════════════════════════════════════
for k, v in {
    "snap": None, "loading": False, "build_error": None, "last_build_time": 0,
    "inc_us": True, "inc_fx": True, "inc_commodities": True,
    "inc_crypto": True, "inc_ihsg": True,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# Brand header
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="brand-row">'
    f'<div>'
    f'<div class="brand-title">MacroRegime <span class="brand-gold">Pro</span></div>'
    f'<div class="brand-sub">Hedgeye GIP · Quad Model · Risk Range™ · Options Overlay</div>'
    f'</div>'
    f'<div class="brand-age">⏱ Last update · {snapshot_age_str()}</div>'
    f'</div>',
    unsafe_allow_html=True
)

# Refresh / Rebuild — visually differentiated
c1, c2, c3 = st.columns([1, 1, 3])
with c1:
    if st.button("🔄 Refresh", use_container_width=True, help="Reuse cache where possible (~30s)"):
        st.session_state.loading = True
        st.session_state.build_error = None
        st.rerun()
with c2:
    if st.button("⚡ Full Rebuild", use_container_width=True, type="primary", help="Force refetch all data (~2-4 min)"):
        st.session_state.loading = True
        st.session_state.build_error = None
        st.session_state.last_build_time = 0
        st.session_state.snap = None
        st.rerun()

# ── Error display ────────────────────────────────────────────────────────────
if st.session_state.build_error:
    st.error(f"❌ Build failed: {st.session_state.build_error}")
    st.info("Tunggu 30–60 detik lalu klik Refresh. Jika persistent, cek log.")
    if st.button("🔄 Coba Lagi"):
        st.session_state.build_error = None
        st.session_state.loading = True
        st.rerun()
    st.stop()

# ── Cooldown ─────────────────────────────────────────────────────────────────
now = time.time()
elapsed = now - st.session_state.last_build_time
if st.session_state.loading and elapsed < 30 and st.session_state.last_build_time > 0:
    st.warning(f"⏳ Cooldown: tunggu {30 - int(elapsed)} detik (hindari rate limit).")
    st.stop()

# ── Load cached snapshot ─────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None and _LOADER_OK:
    try:
        snap = load_snapshot(max_age_hours=12.0)
        if snap and snap.get("ok"):
            st.session_state.snap = snap
    except Exception:
        pass

# ── Build snapshot ───────────────────────────────────────────────────────────
if snap is None or not snap.get("ok") or st.session_state.loading:
    if st.session_state.last_build_time > 0 and now - st.session_state.last_build_time < 30:
        st.warning("⏳ Build cooldown aktif.")
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

        # Stale fallback
        if st.session_state.build_error and _LOADER_OK:
            try:
                stale = load_snapshot(max_age_hours=72.0)
                if stale and stale.get("ok"):
                    st.session_state.snap = stale
                    st.warning(f"⚠️ Build failed ({st.session_state.build_error}). Using stale snapshot (≤72h).")
                    st.session_state.build_error = None
            except Exception:
                pass

    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# Main dashboard
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.snap and st.session_state.snap.get("ok"):
    snap = st.session_state.snap
    gip = snap.get("gip")
    sq = gip.structural_quad if gip and hasattr(gip, "structural_quad") else "Q3"
    mq = gip.monthly_quad if gip and hasattr(gip, "monthly_quad") else "Q2"
    struct_probs = gip.structural_probs if gip and hasattr(gip, "structural_probs") else {}
    month_probs  = gip.monthly_probs    if gip and hasattr(gip, "monthly_probs")    else {}
    flip_hazard  = getattr(gip, "flip_hazard", 0.0) if gip else 0.0
    divergence   = getattr(gip, "divergence", "Unknown") if gip else "Unknown"
    data_cov     = getattr(gip, "data_coverage", 0.0) if gip else 0.0
    feats        = getattr(gip, "features", {}) if gip else {}

    health = snap.get("health") or {}
    vix = health.get("vix_bucket", {}).get("vix_last", "—")
    vix_bucket = health.get("vix_bucket", {}).get("bucket", "—")

    # ── MACRO BANNER ─────────────────────────────────────────────────────────
    growth_mom = feats.get("growth_momentum", 0)
    infl_mom = feats.get("inflation_momentum", 0)

    banner = f'''
<div class="macro-banner">
  <div class="macro-row">
    <div>
      <div class="macro-block-label">Structural Quad (TREND ≥3mo)</div>
      <div style="margin-top:4px;">{q_badge(sq)} <span class="macro-block-val">{QUAD_META.get(sq,{}).get("name","")}</span></div>
    </div>
    <div>
      <div class="macro-block-label">Monthly Quad (TRADE ≤3wk)</div>
      <div style="margin-top:4px;">{q_badge(mq)} <span class="macro-block-val">{QUAD_META.get(mq,{}).get("name","")}</span></div>
    </div>
    <div>
      <div class="macro-block-label">Flip Hazard</div>
      <div class="macro-block-val" style="color:{'#D14B5F' if flip_hazard>0.5 else '#E89B3C' if flip_hazard>0.3 else '#2E9E5F'};">{flip_hazard*100:.0f}%</div>
    </div>
    <div>
      <div class="macro-block-label">Divergence</div>
      <div class="macro-block-val">{divergence}</div>
    </div>
    <div>
      <div class="macro-block-label">VIX</div>
      <div class="macro-block-val">{fmt_num(vix,1)} · {vix_bucket}</div>
    </div>
    <div>
      <div class="macro-block-label">Data Coverage</div>
      <div class="macro-block-val">{data_cov*100:.0f}%</div>
    </div>
  </div>
  <div style="margin-top:14px; color:#C9A961; font-size:12px; font-weight:600;">PLAYBOOK · {QUAD_META.get(sq,{}).get("bias","")}</div>
</div>
'''
    st.markdown(banner, unsafe_allow_html=True)

    # ── A/B Test row + Probability bars ──────────────────────────────────────
    cA, cB = st.columns(2)
    with cA:
        st.markdown(
            f'<div class="he-card"><div class="hedgeye-card-title" style="color:#C9A961;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:10px;">Structural Quad Probability</div>'
            + prob_bars(struct_probs) +
            f'<div style="margin-top:10px;font-size:11px;color:#8B9AAB;">Growth momentum: <b style="color:{"#2E9E5F" if growth_mom>0 else "#D14B5F"};">{growth_mom:+.2%}</b> · Inflation momentum: <b style="color:{"#D14B5F" if infl_mom>0 else "#2E9E5F"};">{infl_mom:+.2%}</b></div></div>',
            unsafe_allow_html=True
        )
    with cB:
        st.markdown(
            f'<div class="he-card"><div class="hedgeye-card-title" style="color:#C9A961;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:10px;">Monthly Quad Probability</div>'
            + prob_bars(month_probs) +
            f'<div style="margin-top:10px;font-size:11px;color:#8B9AAB;">Build: {snap.get("build_time_s","?")}s · Prices: {snap.get("prices_loaded","?")} · Signals: {len(snap.get("daily_signals",[]))}</div></div>',
            unsafe_allow_html=True
        )

    # ── A/B Test summary card ────────────────────────────────────────────────
    st.markdown(
        f'<div class="he-card" style="border-left:3px solid #C9A961;">'
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
        f'<div style="flex:1;min-width:280px;"><div class="macro-block-label">Test A · Macro</div>'
        f'<div style="margin-top:6px;font-size:13px;color:#E8ECF0;line-height:1.5;">Quad: {q_badge(sq)} → {q_badge(mq)}. Optimal: <b style="color:#C9A961;">{QUAD_META.get(sq,{}).get("bias","")}</b></div></div>'
        f'<div style="flex:1;min-width:280px;"><div class="macro-block-label">Test B · Signal</div>'
        f'<div style="margin-top:6px;font-size:13px;color:#E8ECF0;line-height:1.5;">VIX <b>{fmt_num(vix,1)}</b> ({vix_bucket}). Flip hazard <b style="color:{"#D14B5F" if flip_hazard>0.5 else "#C9A961"};">{flip_hazard*100:.0f}%</b>. Market {"front-running" if flip_hazard>0.4 else "in regime"}.</div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📊 Macro",
        "🎯 Alpha Center",
        "📐 Risk Range™",
        "🇺🇸 US Stocks",
        "🌐 Forex",
        "📊 Commodities",
        "🪙 Crypto",
        "🇮🇩 IHSG",
        "⚙️ Settings",
    ])

    # ── Tab 0: Macro ─────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### Daily Signals Summary")
        ds_sum = snap.get("daily_signals_summary", {})
        col = st.columns(4)
        col[0].metric("Strong Longs", ds_sum.get("strong_longs", 0))
        col[1].metric("Longs", ds_sum.get("longs", 0))
        col[2].metric("Strong Shorts", ds_sum.get("strong_shorts", 0))
        col[3].metric("Shorts", ds_sum.get("shorts", 0))

        st.markdown("### Top 5 Alpha Ideas — Long")
        alpha = snap.get("alpha", {})
        longs = alpha.get("longs", [])
        if longs:
            for item in longs[:5]:
                render_alpha_card(item, sq, duration="TREND")
        else:
            st.info("No long signals.")

        st.markdown("### Top 5 Alpha Ideas — Short")
        shorts = alpha.get("shorts", [])
        if shorts:
            for item in shorts[:5]:
                render_alpha_card(item, sq, duration="TREND")
        else:
            st.info("No short signals.")

    # ── Tab 1: Alpha Center ──────────────────────────────────────────────────
    with tabs[1]:
        ac = snap.get("alpha_center", {})
        meta = ac.get("meta", {})
        col = st.columns(4)
        col[0].metric("Total", meta.get("total_items", 0))
        col[1].metric("Level 1", meta.get("level_1_count", 0))
        col[2].metric("Level 2", meta.get("level_2_count", 0))
        col[3].metric("Watch", meta.get("watch_count", 0))

        for level, label, icon in [
            ("level_1",      "Level 1 — High Conviction", "🔴"),
            ("level_2",      "Level 2 — Building",        "🟡"),
            ("alpha_long",   "Alpha Long",                "🟢"),
            ("alpha_short",  "Alpha Short",               "🔴"),
            ("watch",        "Watch List",                "⚪"),
        ]:
            items = ac.get(level, [])
            if items:
                with st.expander(f"{icon} {label} ({len(items)})", expanded=(level=="level_1")):
                    for it in items[:12]:
                        render_alpha_card(it, sq, duration="TREND")

    # ── Tab 2: Risk Range ────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### Risk Range™ — Trade / Trend / Tail")
        st.caption("Price × Volume × Volatility bounds. Trade = ≤3wk · Trend = ≥3mo · Tail = ≤3yr.")
        asset_ranges = (snap.get("risk_ranges") or {}).get("asset_ranges", {})
        prices = snap.get("prices") or {}
        render_risk_range_table(asset_ranges, prices, top_n=60)

    # ── Tab 3: US Stocks ─────────────────────────────────────────────────────
    with tabs[3]:
        ds = snap.get("daily_signals", [])
        us_signals = [s for s in ds if not any(x in s.get("ticker", "") for x in [".JK", "=X", "=F", "-USD", "^JKSE", "EIDO"])]
        st.markdown(f"### US Equities · {len(us_signals)} signals")
        if us_signals:
            for s in us_signals[:20]:
                render_signal_row(s, sq)
        else:
            st.info("No US stock signals.")

    # ── Tab 4: Forex ─────────────────────────────────────────────────────────
    with tabs[4]:
        fx = [s for s in snap.get("daily_signals", []) if "=X" in s.get("ticker", "") or s.get("ticker") == "DX-Y.NYB"]
        st.markdown(f"### Forex · {len(fx)} signals")
        if fx:
            for s in fx[:15]:
                render_signal_row(s, sq)
        else:
            st.info("No forex signals.")

    # ── Tab 5: Commodities ───────────────────────────────────────────────────
    with tabs[5]:
        comm = [s for s in snap.get("daily_signals", []) if "=F" in s.get("ticker", "") or s.get("ticker") in ["GLD","SLV","USO","UNG","BNO","GDX","GDXJ"]]
        st.markdown(f"### Commodities · {len(comm)} signals")
        if comm:
            for s in comm[:15]:
                render_signal_row(s, sq)
        else:
            st.info("No commodity signals.")

    # ── Tab 6: Crypto ────────────────────────────────────────────────────────
    with tabs[6]:
        crypto = [s for s in snap.get("daily_signals", []) if "-USD" in s.get("ticker", "") or s.get("ticker") in ["IBIT","MSTR"]]
        st.markdown(f"### Crypto · {len(crypto)} signals")
        if crypto:
            for s in crypto[:12]:
                render_signal_row(s, sq)
        else:
            st.info("No crypto signals.")

    # ── Tab 7: IHSG ──────────────────────────────────────────────────────────
    with tabs[7]:
        ihsg = [s for s in snap.get("daily_signals", []) if ".JK" in s.get("ticker", "") or s.get("ticker") in ["^JKSE","EIDO"]]
        st.markdown(f"### IHSG · {len(ihsg)} signals")
        if ihsg:
            for s in ihsg[:20]:
                render_signal_row(s, sq)
        else:
            st.info("No IHSG signals.")

        st.markdown("### Sector Momentum")
        sm = snap.get("ihsg_sector_momentum", {})
        if sm:
            rows = []
            for sector, data in sm.items():
                bias = data.get("bias", "—")
                avg_1m = data.get("avg_1m", 0)
                color = "#2E9E5F" if avg_1m > 0 else "#D14B5F"
                rows.append(
                    f'<tr><td><b>{sector}</b></td><td>{bias}</td>'
                    f'<td style="color:{color};font-weight:700;">{avg_1m:+.2%}</td></tr>'
                )
            st.markdown(
                '<table class="rr-table"><thead><tr><th>Sector</th><th>Bias</th><th>1M Avg</th></tr></thead><tbody>'
                + "".join(rows) + '</tbody></table>',
                unsafe_allow_html=True
            )
        else:
            st.info("No sector momentum data.")

    # ── Tab 8: Settings ──────────────────────────────────────────────────────
    with tabs[8]:
        st.markdown("### Universe Settings")
        st.session_state["inc_us"]          = st.checkbox("Include US Stocks", st.session_state.get("inc_us", True))
        st.session_state["inc_fx"]          = st.checkbox("Include Forex", st.session_state.get("inc_fx", True))
        st.session_state["inc_commodities"] = st.checkbox("Include Commodities", st.session_state.get("inc_commodities", True))
        st.session_state["inc_crypto"]      = st.checkbox("Include Crypto", st.session_state.get("inc_crypto", True))
        st.session_state["inc_ihsg"]        = st.checkbox("Include IHSG", st.session_state.get("inc_ihsg", True))
        st.markdown("---")
        if st.button("💾 Save & Rebuild", type="primary"):
            st.session_state.loading = True
            st.session_state.snap = None
            st.rerun()

    # ── Process output footer ────────────────────────────────────────────────
    st.markdown(
        '<div class="process-footer">This is a process output. Manage risk accordingly. · '
        f'Built {snap.get("build_time_s","?")}s · Prices {snap.get("prices_loaded","?")} · '
        f'Coverage {data_cov*100:.0f}%</div>',
        unsafe_allow_html=True
    )

else:
    st.error("❌ Snapshot tidak tersedia. Klik Refresh atau Rebuild di atas.")
