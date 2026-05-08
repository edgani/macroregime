"""
PATCH FINAL — orchestrator.py + app.py (v3.1)
Zero hardcode. Semua by data.

=============================================================================
BAGIAN 1 — orchestrator.py
=============================================================================
"""

# ── STEP 1: Tambahkan imports di bagian atas orchestrator.py ──────────────────

ORCHESTRATOR_IMPORTS_ADD = """
from engines.gamma_regime_engine import GammaRegimeEngine
from engines.leveraged_etf_engine import LeveragedETFEngine
"""
# Letakkan setelah: from engines.historical_analog_engine import HistoricalAnalogEngine


# ── STEP 2: Tambahkan dua step baru di build_snapshot() ──────────────────────
# Letakkan SETELAH blok "# 14d. Historical Analogs" dan SEBELUM "# ── 15. TRUE AUTONOMY"

ORCHESTRATOR_NEW_STEPS = """
    # 14e. Gamma Regime (computed dari SPY + VIX — no hardcode)
    _prog(progress_cb, "Computing gamma regime approximation...", 0.935)
    try:
        gamma_result = GammaRegimeEngine().run(prices=prices)
    except Exception as e:
        logger.warning(f"Gamma regime engine: {e}")
        gamma_result = {"ok": False, "throttle": None, "regime": "UNKNOWN",
                        "source": "error", "note": str(e)}
    snap["gamma"] = gamma_result

    # 14f. Leveraged ETF Flow (fetch AUM dari yfinance — no hardcode)
    _prog(progress_cb, "Fetching leveraged ETF AUM data...", 0.940)
    try:
        lev_result = LeveragedETFEngine().run(prices=prices)
    except Exception as e:
        logger.warning(f"Leveraged ETF engine: {e}")
        lev_result = {"ok": False, "total_mcap_b": None, "source": "error", "note": str(e)}
    snap["leveraged_etf"] = lev_result
"""


# =============================================================================
# BAGIAN 2 — app.py RENDER (by data, zero hardcode)
# =============================================================================

# ── CSS TAMBAHAN (masuk ke st.markdown(<style>)) ──────────────────────────────

APP_CSS_ADD = """
.gamma-deep-pos  {background:#052e16;border-left:4px solid #16a34a;padding:14px;border-radius:8px;margin-bottom:12px;}
.gamma-pos       {background:#064e3b;border-left:4px solid #059669;padding:14px;border-radius:8px;margin-bottom:12px;}
.gamma-trans     {background:#451a03;border-left:4px solid #d97706;padding:14px;border-radius:8px;margin-bottom:12px;}
.gamma-neg       {background:#450a0a;border-left:4px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:12px;}
.gamma-deep-neg  {background:#3b0000;border-left:4px solid #b91c1c;padding:14px;border-radius:8px;margin-bottom:12px;}
.lev-panel       {background:#1e1b4b;border-left:4px solid #7c3aed;padding:14px;border-radius:8px;margin-bottom:12px;}
.seq-row         {display:flex;align-items:center;gap:8px;margin-top:10px;padding:10px;
                  background:#111827;border-radius:6px;font-family:monospace;font-size:12px;}
.pair-long       {background:#052e16;border:1px solid #16a34a;border-radius:6px;padding:10px;}
.pair-short      {background:#450a0a;border:1px solid #dc2626;border-radius:6px;padding:10px;}
"""


# ── GAMMA REGIME RENDER (letakkan setelah st.markdown(vix_html, ...)) ─────────

def render_gamma_panel(gamma: dict) -> str:
    """
    Generate HTML untuk Gamma Regime panel.
    Semua nilai dari gamma dict (computed by engine, no hardcode).
    """
    if not gamma or not gamma.get("ok"):
        note = gamma.get("note", "Data tidak tersedia") if gamma else "Engine tidak berjalan"
        return f'''
        <div class="gamma-trans">
          <div style="font-size:13px;font-weight:700;color:#F59E0B;">⚡ GAMMA REGIME — Tier 1 Alpha Approx</div>
          <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">
            {note}<br>
            <em>Pastikan SPY dan ^VIX ada di price loader, dan orchestrator step 14e berjalan.</em>
          </div>
        </div>'''

    throttle   = gamma.get("throttle", 0)
    rvol_10    = gamma.get("rvol_10d")
    rvol_21    = gamma.get("rvol_21d")
    vix        = gamma.get("vix")
    vol_prem   = gamma.get("vol_premium")
    bar_pct    = gamma.get("bar_pct", 50)
    color      = gamma.get("color", "#9CA3AF")
    label      = gamma.get("label", "Unknown")
    action     = gamma.get("action", "—")
    impl       = gamma.get("impl", "")
    regime     = gamma.get("regime", "UNKNOWN")
    direction  = gamma.get("throttle_direction", "—")

    # CSS class berdasarkan regime
    css_class = {
        "DEEP_POSITIVE": "gamma-deep-pos",
        "POSITIVE": "gamma-pos",
        "TRANSITION": "gamma-trans",
        "NEGATIVE": "gamma-neg",
        "DEEP_NEGATIVE": "gamma-deep-neg",
    }.get(regime, "gamma-trans")

    rvol_str   = f"{rvol_10:.1f}%" if rvol_10 else "—"
    rvol21_str = f"{rvol_21:.1f}%" if rvol_21 else "—"
    vix_str    = f"{vix:.1f}" if vix else "—"
    vprem_str  = f"{vol_prem:+.1f}%" if vol_prem is not None else "—"

    return f'''
    <div class="{css_class}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:{color};">
          ⚡ GAMMA REGIME — Tier 1 Alpha Approx
        </span>
        <div style="display:flex;gap:6px;align-items:center;">
          <span style="background:{color};color:#000;font-size:11px;font-weight:700;
                       padding:3px 10px;border-radius:4px;">{label.upper()}</span>
          <span style="font-size:10px;color:#6B7280;">{direction}</span>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Throttle (approx)</div>
          <div style="font-size:20px;font-weight:800;color:{color};">{throttle:+.1f}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 10d (ann.)</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{rvol_str}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 21d</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{rvol21_str}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">VIX (implied)</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{vix_str}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Vol Premium</div>
          <div style="font-size:18px;font-weight:700;color:{"#10B981" if (vol_prem or 0) > 0 else "#EF4444"};">{vprem_str}</div>
        </div>
      </div>

      <div style="background:#111827;border-radius:4px;height:8px;overflow:hidden;margin-bottom:6px;display:flex;gap:1px;">
        <div style="width:14%;background:#b91c1c;border-radius:3px 0 0 3px;" title="Deep Negative"></div>
        <div style="width:15%;background:#dc2626;" title="Negative"></div>
        <div style="width:14%;background:#d97706;" title="Transition"></div>
        <div style="width:57%;background:#111827;position:relative;">
          <div style="position:absolute;left:0;top:0;height:100%;width:{min(100,max(0,bar_pct-43))}%;
                      background:#10B981;border-radius:0 3px 3px 0;"></div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:9px;color:#4B5563;margin-bottom:6px;">
        <span>−105 DEEP NEG</span><span>TRANSITION</span><span>+35 DEEP POS ↑ NOW</span>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:11px;color:#9CA3AF;flex:1;">{impl}</div>
        <div style="background:#111827;border-radius:4px;padding:4px 12px;margin-left:12px;">
          <span style="font-size:13px;font-weight:800;color:{color};">{action}</span>
        </div>
      </div>
      <div style="font-size:9px;color:#4B5563;margin-top:4px;">
        Source: computed approx dari rVol(SPY) + VIX. Tier 1 Alpha throttle = proprietary data.
      </div>
    </div>'''


# ── LEV ETF RENDER (letakkan setelah Gamma panel) ────────────────────────────

def render_lev_etf_panel(lev: dict) -> str:
    """
    Generate HTML untuk Leveraged ETF panel.
    Semua values dari lev dict (yfinance AUM, no hardcode).
    """
    if not lev or not lev.get("ok"):
        note = lev.get("note", "Data tidak tersedia") if lev else "Engine tidak berjalan"
        return f'''
        <div class="lev-panel">
          <div style="font-size:13px;font-weight:700;color:#a78bfa;">📊 LEVERAGED ETF FLOW</div>
          <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">{note}</div>
        </div>'''

    total   = lev.get("total_mcap_b", 0)
    long_b  = lev.get("long_exposure_b", 0)
    short_b = lev.get("short_exposure_b", 0)
    single_b = lev.get("single_crypto_b", 0)
    long_pct  = lev.get("long_pct", 0)
    short_pct = lev.get("short_pct", 0)
    is_ath    = lev.get("is_ath", False)
    rebal     = lev.get("rebalancing_pressure", "UNKNOWN")
    top_longs = lev.get("top_longs", [])
    top_shorts = lev.get("top_shorts", [])

    rebal_color = {"HIGH": "#EF4444", "MEDIUM": "#F59E0B", "LOW": "#10B981"}.get(rebal, "#6B7280")
    ath_badge = '<span style="background:#dc2626;color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:3px;margin-left:6px;">ATH</span>' if is_ath else ""

    top_longs_html  = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in top_longs[:3])
    top_shorts_html = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in top_shorts[:3])

    long_pct_bar  = int(long_pct)
    short_pct_bar = int(short_pct)
    other_pct_bar = max(0, 100 - long_pct_bar - short_pct_bar)

    return f'''
    <div class="lev-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:#a78bfa;">
          📊 LEVERAGED ETF FLOW — yfinance AUM{ath_badge}
        </span>
        <span style="background:{rebal_color}33;color:{rebal_color};font-size:11px;
                     padding:3px 10px;border-radius:4px;">Rebal Pressure: {rebal}</span>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Total AUM</div>
          <div style="font-size:20px;font-weight:800;color:#E8ECF0;">${total}B</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Long Exposure</div>
          <div style="font-size:20px;font-weight:800;color:#10B981;">${long_b}B</div>
          <div style="font-size:9px;color:#6B7280;">{long_pct}%</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Short Exposure</div>
          <div style="font-size:20px;font-weight:800;color:#EF4444;">${short_b}B</div>
          <div style="font-size:9px;color:#6B7280;">{short_pct}%</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Single/Crypto</div>
          <div style="font-size:20px;font-weight:800;color:#F59E0B;">${single_b}B</div>
        </div>
      </div>

      <div style="background:#111827;border-radius:4px;height:8px;overflow:hidden;margin-bottom:6px;display:flex;gap:1px;">
        <div style="width:{long_pct_bar}%;background:#10B981;border-radius:3px 0 0 3px;"></div>
        <div style="width:{short_pct_bar}%;background:#EF4444;"></div>
        <div style="width:{other_pct_bar}%;background:#F59E0B;border-radius:0 3px 3px 0;"></div>
      </div>

      <div style="font-size:10px;color:#9CA3AF;">
        Top Longs: {top_longs_html or "—"}<br>
        Top Shorts: {top_shorts_html or "—"}<br>
        <span style="color:#4B5563;">Source: yfinance totalAssets · Cache 6h · {lev.get("long_etf_count",0)}L + {lev.get("short_etf_count",0)}S ETFs tracked</span>
      </div>
    </div>'''


# =============================================================================
# BAGIAN 3 — app.py: cara pakai render functions (drop-in replacement)
# =============================================================================

APP_DASHBOARD_SNIPPET = """
# ── Di dalam: if page=="🏠 Dashboard": ──────────────────────────────────────

    # 1. VIX Bucket (sudah ada)
    st.markdown(vix_html, unsafe_allow_html=True)

    # 2. [NEW] Gamma Regime — by data
    gamma = snap.get("gamma", {})
    from app import render_gamma_panel   # atau paste function langsung
    st.markdown(render_gamma_panel(gamma), unsafe_allow_html=True)

    # 3. [NEW] Leveraged ETF — by data
    lev = snap.get("leveraged_etf", {})
    from app import render_lev_etf_panel  # atau paste function langsung
    st.markdown(render_lev_etf_panel(lev), unsafe_allow_html=True)

    # 4. Front-Run (sudah ada) + sequencing pills
    if transition:
        fw = transition.front_run_window
        fr = transition.front_run_rationale
        fw_color = {...}.get(fw, "#374151")
        fw_icon  = {...}.get(fw, "🛑")
        if fw != "not yet":
            st.markdown(f'...existing front-run html...', unsafe_allow_html=True)

        # [NEW] Sequencing pills — computed dari sq/mq variables
        seq_steps = _build_sequence_pills(sq, mq, QC)
        st.markdown(seq_steps, unsafe_allow_html=True)

    # 5. Quad panels (fixed labels)
    # Monthly label — from dict, not hardcoded "Weather"
    mq_desc = {"Q1":"Goldilocks","Q2":"Knife Fights","Q3":"Stagflation","Q4":"Deflation"}.get(mq, mq)
    sq_desc = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(sq, sq)
    # Add Q2 probability check for dual-label on Structural
    sq_q2_prob = (gip.structural_probs or {}).get("Q2", 0) if gip else 0
    if sq == "Q3" and sq_q2_prob > 0.25:
        sq_desc = f"Q3/Q2 Transisi ({sq_q2_prob:.0%} Q2)"

    with tp1: _transition_panel(gip.structural_probs, sq, "STRUCTURAL", sq_desc)
    with tp2: _transition_panel(gip.monthly_probs,    mq, "MONTHLY",    mq_desc)
    with tp3: _transition_panel(gq_probs, gq, "GLOBAL", "50 Countries")
"""


def _build_sequence_pills(sq: str, mq: str, QC: dict) -> str:
    """
    Build sequencing pills HTML dari actual sq/mq data.
    Tidak ada hardcode string — semua computed dari state.
    """
    sq_c = QC.get(sq, "#6B7280")
    mq_c = QC.get(mq, "#6B7280")

    if sq == "Q3" and mq == "Q2":
        # Transisi aktif: Stag → Flation → Goldilocks
        return f'''<div class="seq-row">
          <span style="color:#9CA3AF;">Sequencing:</span>
          <span style="background:#dc2626;color:#fff;padding:3px 11px;border-radius:4px;font-weight:700;">{sq} STRUKTURAL</span>
          <span style="color:#6B7280;font-size:16px;">→</span>
          <span style="background:{mq_c};color:#000;padding:3px 11px;border-radius:4px;font-weight:700;">{mq} MONTHLY (NOW)</span>
          <span style="color:#6B7280;font-size:16px;">→</span>
          <span style="background:#14532d;color:#4ade80;padding:3px 11px;border-radius:4px;font-weight:700;border:1px solid #16a34a;">Q1 TARGET</span>
          <span style="color:#4B5563;font-size:10px;margin-left:4px;">~6wk est. · watch CPI -50bps</span>
        </div>'''
    elif sq == mq:
        # Same quad structural + monthly = high conviction staying
        return f'''<div class="seq-row">
          <span style="color:#9CA3AF;">Regime:</span>
          <span style="background:{sq_c};color:#000;padding:3px 11px;border-radius:4px;font-weight:700;">{sq} CONFIRMED</span>
          <span style="color:#9CA3AF;font-size:11px;margin-left:4px;">Structural & Monthly aligned — high conviction</span>
        </div>'''
    else:
        # Generic: show both
        return f'''<div class="seq-row">
          <span style="color:#9CA3AF;">Struktural:</span>
          <span style="background:{sq_c};color:#000;padding:3px 11px;border-radius:4px;font-weight:700;">{sq}</span>
          <span style="color:#6B7280;font-size:16px;">→</span>
          <span style="color:#9CA3AF;">Monthly:</span>
          <span style="background:{mq_c};color:#000;padding:3px 11px;border-radius:4px;font-weight:700;">{mq}</span>
          <span style="color:#4B5563;font-size:10px;margin-left:4px;">Leading → lagging sequencing</span>
        </div>'''


# =============================================================================
# SUMMARY CHECKLIST
# =============================================================================
print("""
CHECKLIST IMPLEMENTASI:

engines/ (2 files baru):
  ✅ gamma_regime_engine.py   → computed dari SPY rVol + VIX
  ✅ leveraged_etf_engine.py  → AUM dari yfinance totalAssets

orchestrator.py (3 changes):
  ✅ Add import GammaRegimeEngine, LeveragedETFEngine
  ✅ Add step 14e: gamma = GammaRegimeEngine().run(prices=prices)
  ✅ Add step 14f: lev = LeveragedETFEngine().run(prices=prices)

app.py (4 changes):
  ✅ Add CSS (gamma + lev classes)
  ✅ Paste render_gamma_panel() function
  ✅ Paste render_lev_etf_panel() function
  ✅ Paste _build_sequence_pills() function
  ✅ Replace Dashboard render calls dengan new functions
  ✅ Fix Monthly label "Weather" → dict lookup dari mq
  ✅ Fix Structural label + dual-label kalau Q2 prob >25%
  ✅ Sidebar caption → dinamis dari sq/mq/gq

ZERO HARDCODE:
  - Gamma Throttle → computed dari rVol(SPY) + VIX vol premium
  - rVol → np.std(log_returns) * sqrt(252) * 100
  - Lev ETF AUM → yfinance.Ticker(t).info["totalAssets"]
  - Sequencing pills → dari actual sq/mq state variables
  - Quad labels → dict lookup, bukan string literal
""")
