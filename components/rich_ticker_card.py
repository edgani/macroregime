"""rich_ticker_card.py — Comprehensive ticker rendering with narrative analysis

Per Edward's spec: setiap ticker card harus nampilin:
  • Ticker + harga saat ini
  • TRR/LRR (TRADE/TREND/TAIL)
  • **PHASE NARRATIVE** (trending bullish/bearish/sideways + reasoning)
  • **ENTRY ZONE** (di mana buy/short, take profit, R/R)
  • **OPTIONS + GREEKS narrative** (call/put walls, OI heatmap, MM positioning,
    expected move, volatility outlook, ACTIONABLE recommendation)
  • Market-specific layer (COT/on-chain/bandar) with NARRATIVE interpretation
"""
import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════
# NARRATIVE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def compute_signal_strength(rr: dict) -> dict:
    """Keith McCullough Signal Strength: HH across all 3 durations (TRADE/TREND/TAIL).
    HH = price breaking ABOVE the band (higher-high); LL = below the band (lower-low).
    For mid-range price, lean on MA trend (phase_code) so it stays CONSISTENT with Phase box.
    """
    if not rr:
        return {"score": 0, "label": "NEUTRAL", "detail": ""}
    px = rr.get("px", 0)
    phase_code = rr.get("phase_code", 0)
    hh = ll = 0
    states = []
    for d in ["trade", "trend", "tail"]:
        dd = rr.get(d, {})
        lrr = dd.get("lrr", 0) or 0
        trr = dd.get("trr", 0) or 0
        if trr and px >= trr:
            hh += 1; states.append("HH")
        elif lrr and px <= lrr:
            ll += 1; states.append("LL")
        else:
            states.append("mid")
    # Breakout extremes (Keith's true HH/LL across durations)
    if hh == 3:
        return {"score": 3, "label": "STRONGEST BULL", "detail": "Price > TRR on TRADE+TREND+TAIL - HH all 3 (Keith max strength)"}
    if ll == 3:
        return {"score": -3, "label": "STRONGEST BEAR", "detail": "Price < LRR on TRADE+TREND+TAIL - LL all 3 (max bearish)"}
    if hh >= 1 and ll == 0 and phase_code >= 0:
        return {"score": 2, "label": "STRONG BULL", "detail": f"Breaking out HH on {hh}/3 durations - bull trend intact"}
    if ll >= 1 and hh == 0 and phase_code <= 0:
        return {"score": -2, "label": "STRONG BEAR", "detail": f"Breaking down LL on {ll}/3 durations - bear trend"}
    # Mid-range: lean on MA trend so it agrees with the Phase box
    if phase_code == 1:
        return {"score": 1, "label": "BULL BIAS", "detail": "Mid-range, 21d>63d MA - bullish lean, wait for pullback/breakout"}
    if phase_code == -1:
        return {"score": -1, "label": "BEAR BIAS", "detail": "Mid-range, 21d<63d MA - bearish lean"}
    return {"score": 0, "label": "NEUTRAL", "detail": "Mid-range, no trend - no edge"}


def _render_oi_heatmap(snap, ticker, market_key):
    """OI heatmap (open interest by strike). Uses yfinance options OI when available.
    Futures (CL=F etc) → ETF proxy (USO etc). FX → currency ETF proxy."""
    import streamlit as st
    st.markdown("**📊 OI Heatmap (Open Interest by Strike)**")

    # Futures → ETF proxy mapping (futures have no yfinance options)
    FUT_PROXY = {
        "CL=F": "USO", "GC=F": "GLD", "SI=F": "SLV", "NG=F": "UNG", "HG=F": "CPER",
        "RB=F": "UGA", "HO=F": "USO", "ZC=F": "CORN", "ZW=F": "WEAT", "ZS=F": "SOYB",
    }
    FX_PROXY = {
        "EURUSD=X": "FXE", "EUR=X": "FXE", "JPY=X": "FXY", "USDJPY=X": "FXY",
        "GBPUSD=X": "FXB", "GBP=X": "FXB", "AUDUSD=X": "FXA", "DX-Y.NYB": "UUP",
        "USDCAD=X": "FXC",
    }

    # First try direct OI from snapshot options_data
    opts = (snap.get("options_data", {}) or {}).get(ticker, {})
    proxy = None
    if not opts:
        proxy = FUT_PROXY.get(ticker) or FX_PROXY.get(ticker)
        if proxy:
            opts = (snap.get("options_data", {}) or {}).get(proxy, {})

    if opts and (opts.get("total_call_oi") or opts.get("call_wall")):
        cw = opts.get("call_wall")
        pw = opts.get("put_wall")
        mp = opts.get("max_pain")
        tot_c = opts.get("total_call_oi", 0)
        tot_p = opts.get("total_put_oi", 0)
        src = f" (via {proxy} proxy)" if proxy else ""
        st.markdown(
            f"Call OI total: **{tot_c:,}** · Put OI total: **{tot_p:,}**{src}  \n"
            f"🧱 Call Wall (resistance): **\\${cw}** · Put Wall (support): **\\${pw}** · Max Pain: **\\${mp}**"
        )
        # Simple visual: call wall above, put wall below current
        spot = opts.get("spot", 0)
        if spot and cw and pw:
            st.caption(f"Price \\${spot} sits between Put Wall \\${pw} ↓ and Call Wall \\${cw} ↑ — "
                       f"dealers pin toward Max Pain \\${mp} into OPEX.")
    else:
        if market_key == "commodity":
            st.caption(f"OI heatmap untuk {ticker} butuh CME QuikStrike (sering ke-block server-side) "
                       f"atau ETF proxy options. Futures OI ga ada di yfinance — pakai proxy: "
                       f"{FUT_PROXY.get(ticker, 'N/A')}.")
        else:
            st.caption(f"OI data untuk {ticker} belum tersedia — pakai FX ETF proxy "
                       f"({FX_PROXY.get(ticker, 'N/A')}) atau CME QuikStrike.")


def _render_signal_boxes(rr, snap, market_key, show_options, ticker):
    """Tier1Alpha-style color-coded signal boxes per ticker."""
    import streamlit as st
    if not rr:
        return
    def _box(label, value, color):
        return (f"<div style='background:{color};color:white;padding:6px 4px;border-radius:6px;"
                f"text-align:center;font-weight:700;font-size:0.72rem;margin:2px 0;'>"
                f"{label}<br><span style='font-size:0.82rem;'>{value}</span></div>")
    GREEN, RED, AMBER, GREY = "#1a7f37", "#cf222e", "#bf8700", "#57606a"
    ss = compute_signal_strength(rr)
    ss_color = GREEN if ss["score"] > 0 else RED if ss["score"] < 0 else AMBER
    phase = rr.get("phase", "NEUTRAL")
    phase_color = GREEN if phase == "BULL" else RED if phase == "BEAR" else AMBER
    quality = rr.get("signals", {}).get("quality", "C")
    q_color = GREEN if quality.startswith("A") else RED if quality.startswith("short") else AMBER if quality == "B" else GREY
    hurst = rr.get("hurst", {}).get("interpretation", "RANDOM_WALK")
    hurst_short = {"TRENDING": "TREND", "MEAN_REVERTING": "MEAN-REV", "RANDOM_WALK": "RANDOM"}.get(hurst, "-")
    hurst_color = GREEN if hurst == "TRENDING" else AMBER if hurst == "MEAN_REVERTING" else GREY
    boxes = [
        _box("Signal Strength", ss["label"], ss_color),
        _box("Phase", phase, phase_color),
        _box("Quality", quality, q_color),
        _box("Hurst", hurst_short, hurst_color),
    ]
    if show_options:
        opts = (snap.get("options_data", {}) or {}).get(ticker, {})
        gex = opts.get("net_gex") or opts.get("gex")
        if gex is not None:
            try:
                g = float(gex)
                boxes.append(_box("Gamma", "LONG g" if g > 0 else "SHORT g", GREEN if g > 0 else RED))
            except (TypeError, ValueError):
                pass
    cols = st.columns(len(boxes))
    for c, b in zip(cols, boxes):
        c.markdown(b, unsafe_allow_html=True)
    if ss["detail"]:
        st.caption(f"Signal: {ss['detail']}")


def _phase_narrative(rr: dict) -> str:
    """Generate phase explanation in plain language."""
    if not rr:
        return "Phase data unavailable."

    phase = rr.get("phase", "NEUTRAL")
    formation = rr.get("signals", {}).get("formation", "NEUTRAL")
    trade_pos = rr.get("signals", {}).get("trade_position_pct", 50)
    hurst = rr.get("hurst", {}).get("interpretation", "RANDOM_WALK")

    parts = []

    # Trend direction
    if phase == "BULL":
        parts.append("**Trending BULLISH** (21d MA > 63d MA by +0.5%)")
    elif phase == "BEAR":
        parts.append("**Trending BEARISH** (21d MA < 63d MA by -0.5%)")
    else:
        parts.append("**Sideways** (21d MA ≈ 63d MA, no clear direction)")

    # Hurst behavior
    if hurst == "TRENDING":
        parts.append("Hurst > 0.6 → persistent trend regime, ride momentum")
    elif hurst == "MEAN_REVERTING":
        parts.append("Hurst < 0.4 → mean-reverting, fade extremes")
    else:
        parts.append("Hurst ≈ 0.5 → random walk, low signal")

    # Position in TRADE range
    if trade_pos < 25:
        parts.append(f"At **lower 25%** of TRADE range ({trade_pos:.0f}%) — kalo bullish → ADD zone")
    elif trade_pos > 75:
        parts.append(f"At **upper 25%** of TRADE range ({trade_pos:.0f}%) — kalo bullish → TRIM zone")
    else:
        parts.append(f"Mid TRADE range ({trade_pos:.0f}%) — no edge")

    # Formation
    if formation == "BULLISH":
        parts.append("Formation bullish (price > TREND TRR + TAIL TRR)")
    elif formation == "BEARISH":
        parts.append("Formation bearish (price < TREND LRR + TAIL LRR)")

    return " · ".join(parts)


def _entry_narrative(rr: dict) -> str:
    """Generate entry/exit zone explanation."""
    if not rr:
        return ""
    sig = rr.get("signals", {})
    action = sig.get("action", "HOLD")
    px = rr.get("px", 0)
    trade = rr.get("trade", {})
    trend = rr.get("trend", {})
    tail = rr.get("tail", {})

    trade_lrr = trade.get("lrr", 0) or 0
    trade_trr = trade.get("trr", 0) or 0
    trend_lrr = trend.get("lrr", 0) or 0
    trend_trr = trend.get("trr", 0) or 0
    rr_ratio = sig.get("rr_ratio", 0) or 0

    if action == "BUY_DIP":
        return (f"🎯 **BUY ZONE NOW** — price at LRR \\${trade_lrr:.2f}. "
                f"Take profit di TRR \\${trade_trr:.2f} (+{((trade_trr/px-1)*100):.1f}%). "
                f"Stop loss if breaks TAIL LRR \\${tail.get('lrr', 0) or 0:.2f}. R/R: {rr_ratio:.2f}")
    elif action == "ADD":
        return (f"🟢 **ADD ZONE** — lower 25% of TRADE range. "
                f"Entry up to \\${trade_lrr + (trade_trr-trade_lrr)*0.25:.2f}. "
                f"Trim di \\${trade_trr:.2f}. R/R: {rr_ratio:.2f}")
    elif action == "HOLD":
        return (f"⚪ **HOLD** — mid range. Wait. "
                f"Add jika turun ke \\${trade_lrr:.2f}, trim jika naik ke \\${trade_trr:.2f}.")
    elif action == "TRIM":
        return (f"🟡 **TRIM ZONE** — upper 25% of TRADE range. "
                f"Reduce exposure now. Re-add di \\${trade_lrr:.2f}.")
    elif action == "TRIM_RIP":
        return (f"🟠 **TAKE PROFIT** — price at/above TRR \\${trade_trr:.2f}. "
                f"Lock in gains. Wait pullback to \\${trade_lrr:.2f}.")
    elif action == "SHORT_RIP":
        return (f"🔴 **SHORT ZONE** — bearish trend, price at TRR \\${trade_trr:.2f}. "
                f"Cover di LRR \\${trade_lrr:.2f}. R/R: {rr_ratio:.2f}")
    elif action == "COVER":
        return (f"🟣 **COVER ZONE** — bearish, price at LRR \\${trade_lrr:.2f}. "
                f"Lock short gains.")
    elif action == "WATCH":
        return f"👀 **WATCH** — wait di sini. Setup unclear. LRR \\${trade_lrr:.2f} / TRR \\${trade_trr:.2f}"
    return ""


def _options_narrative(opts: dict, px: float, ticker: str) -> str:
    """Generate options + Greeks narrative."""
    if not opts:
        return ""

    parts = []

    # Walls
    call_wall = opts.get("call_wall") or opts.get("call_wall_strike")
    put_wall = opts.get("put_wall") or opts.get("put_wall_strike")
    max_pain = opts.get("max_pain")
    vol_trigger = opts.get("vol_trigger")
    gex = opts.get("gex") or opts.get("net_gex")

    if call_wall:
        dist_call = (float(call_wall) - px) / px * 100 if px else 0
        parts.append(f"**Call Wall \\${float(call_wall):.2f}** ({dist_call:+.1f}% away) — major resistance, MM short-gamma above")
    if put_wall:
        dist_put = (float(put_wall) - px) / px * 100 if px else 0
        parts.append(f"**Put Wall \\${float(put_wall):.2f}** ({dist_put:+.1f}% away) — major support, MM long-gamma below")
    if max_pain:
        parts.append(f"**Max Pain \\${float(max_pain):.2f}** — pinning target for OPEX week")
    if vol_trigger:
        dist_vt = (float(vol_trigger) - px) / px * 100 if px else 0
        parts.append(f"**Vol Trigger \\${float(vol_trigger):.2f}** ({dist_vt:+.1f}%) — gamma flip level")

    # GEX regime
    if gex is not None:
        try:
            gex_val = float(gex)
            if gex_val > 0:
                parts.append(f"GEX: **+\\${gex_val/1e9:.2f}B** (positive) → MM long gamma → **suppressed volatility**, mean-reverting")
            else:
                parts.append(f"GEX: **\\${gex_val/1e9:.2f}B** (negative) → MM short gamma → **amplified moves**, volatile breakouts")
        except (TypeError, ValueError):
            pass

    # IV
    iv_rank = opts.get("iv_rank")
    pc_ratio = opts.get("put_call_ratio") or opts.get("pc_ratio")
    if iv_rank is not None:
        try:
            ivr = float(iv_rank)
            if ivr > 70:
                parts.append(f"IV Rank **{ivr:.0f}** → vol expensive, sell premium")
            elif ivr < 30:
                parts.append(f"IV Rank **{ivr:.0f}** → vol cheap, buy options")
        except (TypeError, ValueError):
            pass
    if pc_ratio is not None:
        try:
            pc = float(pc_ratio)
            if pc > 1.0:
                parts.append(f"P/C ratio **{pc:.2f}** → put-heavy = hedging/bearish positioning")
            elif pc < 0.6:
                parts.append(f"P/C ratio **{pc:.2f}** → call-heavy = greed/squeeze risk")
        except (TypeError, ValueError):
            pass

    return "\n".join(f"• {p}" for p in parts) if parts else ""


def _mm_positioning(opts: dict, px: float) -> str:
    """Market maker positioning summary."""
    if not opts: return ""
    gex = opts.get("gex") or opts.get("net_gex")
    call_wall = opts.get("call_wall") or opts.get("call_wall_strike")
    put_wall = opts.get("put_wall") or opts.get("put_wall_strike")
    expected_move = opts.get("expected_move_pct") or opts.get("expected_move")

    summary_parts = []
    try:
        if gex is not None and float(gex) > 0 and call_wall and put_wall:
            summary_parts.append(
                f"**🟢 MM LONG GAMMA → BUY DIPS WORK.** Price kemungkinan pinball "
                f"antara Put Wall \\${float(put_wall):.2f} dan Call Wall \\${float(call_wall):.2f}. "
                f"Volatility supressed. Sell strangle/iron condor di range ini."
            )
        elif gex is not None and float(gex) < 0:
            summary_parts.append(
                f"**🔴 MM SHORT GAMMA → AMPLIFIED MOVES.** Break above Call Wall = "
                f"chase higher (MM buyback). Break below Put Wall = waterfall down. "
                f"Buy options, jangan sell premium."
            )
    except (TypeError, ValueError): pass

    if expected_move:
        try:
            em = float(expected_move)
            summary_parts.append(f"Expected move next week: **±{em:.2f}%** (implied by ATM straddle)")
        except (TypeError, ValueError): pass

    return "\n".join(summary_parts)


def _cot_narrative(cot: dict, ticker: str) -> str:
    """COT data interpretation for Forex/Commodities."""
    if not cot: return ""
    parts = []
    nc_net = cot.get("noncomm_net") or cot.get("non_commercial_net")
    nc_chg = cot.get("noncomm_change_wow") or cot.get("noncomm_change")
    extreme = cot.get("extreme_position") or cot.get("at_extreme")

    if nc_net is not None:
        try:
            nn = float(nc_net)
            if nn > 0:
                parts.append(f"**Non-commercial NET LONG: {nn:+,.0f}** contracts (large specs bullish)")
            else:
                parts.append(f"**Non-commercial NET SHORT: {nn:+,.0f}** contracts (large specs bearish)")
        except (TypeError, ValueError): pass

    if nc_chg is not None:
        try:
            ncc = float(nc_chg)
            if abs(ncc) > 5000:
                direction = "added longs" if ncc > 0 else "added shorts" if ncc < 0 else "flat"
                parts.append(f"WoW change: {ncc:+,.0f} ({direction}) — momentum {'building' if abs(ncc) > 10000 else 'modest'}")
        except (TypeError, ValueError): pass

    if extreme:
        parts.append("⚠️ **EXTREME POSITIONING** (>2σ from 1yr avg) — contrarian setup, watch for reversal")

    return "\n".join(f"• {p}" for p in parts) if parts else ""


def _onchain_narrative(oc: dict, ticker: str) -> str:
    """On-chain accumulation/distribution narrative for Crypto."""
    if not oc: return ""
    parts = []
    whale_7d = oc.get("whale_accum_7d") or oc.get("whale_accum")
    funding = oc.get("funding_rate") or oc.get("funding_8h")
    oi_chg = oc.get("oi_change_7d") or oc.get("oi_chg")
    exch_outflow = oc.get("exchange_outflow_pct") or oc.get("exch_outflow")
    sig = oc.get("signal") or ""

    if whale_7d is not None:
        try:
            wa = float(whale_7d) * 100 if abs(float(whale_7d)) < 1 else float(whale_7d)
            if wa > 5:
                parts.append(f"**Whale ACCUMULATION** +{wa:.1f}% (7d) — top 100 wallets adding")
            elif wa < -5:
                parts.append(f"**Whale DISTRIBUTION** {wa:.1f}% (7d) — top wallets dumping")
        except (TypeError, ValueError): pass

    if funding is not None:
        try:
            f = float(funding) * 100 if abs(float(funding)) < 1 else float(funding)
            if f > 0.05:
                parts.append(f"Funding +{f:.3f}% → longs paying shorts = overheated, squeeze risk")
            elif f < -0.05:
                parts.append(f"Funding {f:.3f}% → shorts paying longs = bottom signal, short squeeze setup")
        except (TypeError, ValueError): pass

    if oi_chg is not None:
        try:
            oc_val = float(oi_chg) * 100 if abs(float(oi_chg)) < 1 else float(oi_chg)
            if abs(oc_val) > 10:
                parts.append(f"OI {oc_val:+.1f}% (7d) — {'leverage building' if oc_val > 0 else 'deleveraging'}")
        except (TypeError, ValueError): pass

    if exch_outflow is not None:
        try:
            eo = float(exch_outflow) * 100 if abs(float(exch_outflow)) < 1 else float(exch_outflow)
            if eo > 2:
                parts.append(f"Exchange outflow +{eo:.1f}% → coins moving to self-custody = bullish HODL")
            elif eo < -2:
                parts.append(f"Exchange inflow {eo:.1f}% → coins moving to exchanges = sell pressure")
        except (TypeError, ValueError): pass

    if sig:
        parts.append(f"**On-chain signal: {sig}**")

    return "\n".join(f"• {p}" for p in parts) if parts else ""


def _bandar_narrative(b: dict, ticker: str) -> str:
    """IHSG bandar (Indonesian market maker) detailed narrative.

    Based on Hengky Adinata methodology + bandarmologi research:
    - Cornering supply detection
    - 4-phase goreng cycle (akumulasi → corp action → liquiditas → euforia)
    - Foreign vs domestic broker classification
    - Cross-trade detection (same broker buying + selling = wash trade)
    - Konglomerat group flow (Bakrie, Salim, Barito, Astra, Lippo)
    """
    if not b: return ""
    parts = []

    flow_signal = b.get("flow_signal", "UNCLEAR")
    confidence = b.get("confidence", 0)

    signal_explanations = {
        "ACCUMULASI_ASLI": (
            "🟢 **AKUMULASI ASLI** — bandar lokal aktif kumpulin posisi. "
            "Pattern: bid-offer frequency tinggi di bid, broker dominan (BRPT, MNCS, dll) jadi top buyer "
            "berhari-hari, harga konsolidasi (volatility menurun). Setup goreng phase 1."
        ),
        "DISTRIBUSI_ASLI": (
            "🔴 **DISTRIBUSI ASLI** — bandar sedang exit posisi. "
            "Pattern: top sellers = broker yang sebelumnya top buyer, harga di range tinggi tapi volume menurun, "
            "bid-offer asymmetric (lebih banyak offer). EXIT NOW."
        ),
        "FAKE_AKUM": (
            "🟡 **FAKE AKUMULASI** — kelihatan akumulasi tapi cross-trade detected. "
            "Same broker code muncul di top buyer DAN top seller = wash trade. "
            "Mereka coba narik retail, jangan kena."
        ),
        "FAKE_DISTR": (
            "🟡 **FAKE DISTRIBUSI** — kelihatan distribusi tapi cross-trade detected. "
            "Bandar coba scare retail biar jual murah, mereka beli balik. Hold."
        ),
        "FORCED_SELL": (
            "🔴 **FORCED SELL / MARGIN CALL** — broker likuidasi posisi nasabah. "
            "Volume spike + price drop tajam + concentrated seller. "
            "Bisa jadi bottom signal kalo udah selesai."
        ),
        "WINDOW_DRESSING": (
            "🟣 **WINDOW DRESSING** — biasanya akhir bulan/kuartal/tahun. "
            "Bandar/MI naikin harga buat appearance NAV. Setelah period close = balik turun."
        ),
        "UNCLEAR": "⚪ Flow signal belum jelas — observasi lebih lanjut.",
    }
    parts.append(signal_explanations.get(flow_signal, signal_explanations["UNCLEAR"]))
    if confidence:
        try:
            parts.append(f"Confidence: **{float(confidence)*100:.0f}%** (broker concentration + cross-trade analysis)")
        except (TypeError, ValueError): pass

    # Top brokers
    top_buy = b.get("top_brokers_buy") or b.get("top_buyers") or []
    top_sell = b.get("top_brokers_sell") or b.get("top_sellers") or []
    if top_buy:
        broker_explanations = _broker_codes_explained(top_buy[:5], side="buy")
        parts.append(f"\n**🟢 Top Buyers:** {broker_explanations}")
    if top_sell:
        broker_explanations = _broker_codes_explained(top_sell[:5], side="sell")
        parts.append(f"**🔴 Top Sellers:** {broker_explanations}")

    # Cornering signal
    cornering = b.get("cornering_signal") or b.get("cornering") or {}
    if isinstance(cornering, dict) and cornering.get("detected"):
        thesis = cornering.get("thesis", "Floating shares mengecil drastis")
        parts.append(
            f"\n⚠️ **CORNERING SUPPLY DETECTED**\n"
            f"• Floating shares yang available di market mengecil drastis (kemungkinan <15% free float)\n"
            f"• {thesis}\n"
            f"• Implikasi: harga bisa lompat tajam ke atas karena tidak ada supply. "
            f"Tapi juga risiko: ketika bandar exit, harga collapse karena retail panic."
        )

    # Goreng phase
    goreng = b.get("goreng_phase")
    if goreng:
        phase_explanations = {
            "PHASE_1_AKUMULASI": (
                "📦 **PHASE 1 — AKUMULASI** (3-12 bulan): "
                "Bandar diam-diam beli di harga murah. Volume rendah, range sempit. "
                "Retail belum aware. Best entry point."
            ),
            "PHASE_2_CORP_ACTION": (
                "📰 **PHASE 2 — CORPORATE ACTION** (1-3 bulan): "
                "Berita keluar (right issue / akuisisi / spin-off / pembagian dividen besar). "
                "Volume mulai naik, harga break range akumulasi. Retail mulai notice."
            ),
            "PHASE_3_LIQUIDITAS": (
                "💧 **PHASE 3 — LIQUIDITAS** (1-2 bulan): "
                "Bandar marik retail dengan candle bullish yang nyolok. Volume tinggi. "
                "Influencer/media coverage mulai banyak. Bandar mulai distribute pelan-pelan."
            ),
            "PHASE_4_EUFORIA": (
                "🔥 **PHASE 4 — EUFORIA** (2-4 minggu): "
                "Harga parabolik. Retail FOMO. Volume sangat tinggi. "
                "Bandar sudah hampir habis distribusi. CRASH IMMINENT — EXIT NOW."
            ),
        }
        parts.append(f"\n{phase_explanations.get(goreng, goreng)}")

    # Konglomerat group flow
    konglo = b.get("konglomerat_group") or b.get("conglomerate")
    if konglo:
        parts.append(f"\n🏢 **Group: {konglo}** — coordinated flow detected. "
                    f"Watch cross-correlation dengan ticker satu grup.")

    return "\n".join(parts)


def compute_optimal_entry(rr: dict, snap: dict, market_key: str, ticker: str) -> dict:
    """Synthesize the OPTIMAL ENTRY using ONLY data appropriate to this market.

    Data by market (Edward's rule — never use options/greeks for IHSG/forex):
      • us_equity / crypto : TRR/LRR + options(GEX/walls/max-pain) + vanna/charm timing
      • forex              : TRR/LRR + COT positioning (NO options/greeks)
      • commodity          : TRR/LRR + COT + OI heatmap walls (NO options/greeks for futures)
      • ihsg               : TRR/LRR + bandar accumulation (NO options/greeks/COT)
    """
    if not rr:
        return {}
    px = rr.get("px", 0) or 0
    phase = rr.get("phase", "NEUTRAL")
    trade = rr.get("trade", {})
    lrr = trade.get("lrr", 0) or 0
    trr = trade.get("trr", 0) or 0
    width = trr - lrr if (trr and lrr) else 0
    pos = (px - lrr) / width if width > 0 else 0.5

    bull = phase == "BULL" or rr.get("phase_code", 0) == 1
    bear = phase == "BEAR" or rr.get("phase_code", 0) == -1

    # ── KEITH OVERRIDE: markets follow Keith's actual public calls ───────
    # If Keith says BEARISH TRADE on this name, don't chase even if our phase is bull.
    keith_note = None
    try:
        from engines.keith_signal_sync import resolve_direction
        dash_dir = "LONG" if bull else "SHORT" if bear else "NEUTRAL"
        kd = resolve_direction(ticker, dash_dir)
        if kd.get("override") or kd.get("keith_trade") not in (None, "NEUTRAL", ""):
            kt = kd.get("keith_trade", "NEUTRAL")
            ktr = kd.get("keith_trend", "NEUTRAL")
            keith_note = f"🎯 **Keith ({ticker}):** TRADE {kt} · TREND {ktr} — {kd.get('basis','')}"
            # If Keith TRADE bearish but we're bull → flip framing to 'wait/don't chase'
            if kt == "BEARISH" and bull:
                bull = False  # don't show 'buy now'; treat as wait
    except Exception:
        pass

    # Base entry zone from TRR/LRR (universal)
    parts = []
    if keith_note:
        parts.append(keith_note)
    is_fx = market_key == "forex"
    fmt = ".4f" if is_fx else ",.2f"
    cur = "" if is_fx else "$"
    def _f(v): return f"{cur}{format(v, fmt)}"

    if bull:
        stop = lrr - width * 0.30
        target1 = trr
        target2 = (rr.get("trend", {}).get("trr", 0) or trr)
        direction = "LONG"
        # Frame entry RELATIVE to current price (Keith daily-actionable style)
        if pos < 0.25:
            parts.append(f"🟢 **BUY ZONE SEKARANG** — harga {_f(px)} udah di lower TRADE band ({pos:.0%}). Entry di sini, ini level yang Keith sebut 'buy-able now'.")
        elif pos < 0.55:
            dip = lrr + width * 0.10
            parts.append(f"🟡 **Bisa mulai sekarang** ({_f(px)}, mid-low {pos:.0%}) — atau tunggu dip ke {_f(dip)} buat add lebih bagus.")
        elif pos < 0.80:
            zone_top = lrr + width * 0.15
            parts.append(f"🟠 **Mid-high ({pos:.0%})** — jangan chase. Tunggu pullback ke {_f(lrr)}–{_f(zone_top)} ({((zone_top/px-1)*100):+.1f}% s/d {((lrr/px-1)*100):+.1f}%) buat entry optimal.")
        else:
            parts.append(f"🔴 **Extended ({pos:.0%}, dekat TRR)** — JANGAN kejar. Trim kalau udah punya, atau tunggu reset ke {_f(lrr)} ({((lrr/px-1)*100):+.1f}%).")
        parts.append(f"**Stop:** < {_f(stop)} · **T1:** {_f(target1)} ({((target1/px-1)*100):+.1f}%) · **T2:** {_f(target2)} ({((target2/px-1)*100):+.1f}%)")
    elif bear:
        stop = trr + width * 0.30
        target1 = lrr
        target2 = (rr.get("trend", {}).get("lrr", 0) or lrr)
        direction = "SHORT" if market_key != "ihsg" else "AVOID/WAIT"
        if market_key == "ihsg":
            parts.append(f"🔴 **IHSG buy-only — HINDARI.** Bearish ({_f(px)}). Tunggu reclaim {_f(lrr)} ({((lrr/px-1)*100):+.1f}%) sebelum mikir akumulasi.")
        else:
            if pos > 0.75:
                parts.append(f"🔴 **SHORT ZONE SEKARANG** — harga {_f(px)} di upper band ({pos:.0%}). Short di sini (Keith 'sell rip').")
            elif pos > 0.45:
                parts.append(f"🟠 **Mid-high ({pos:.0%})** — bisa short scale-in, atau tunggu rip ke {_f(trr)} ({((trr/px-1)*100):+.1f}%) buat entry lebih bagus.")
            else:
                parts.append(f"🟡 **Mid-low ({pos:.0%})** — udah turun jauh. Jangan short di bawah; tunggu bounce ke {_f(trr)} ({((trr/px-1)*100):+.1f}%).")
            parts.append(f"**Stop:** > {_f(stop)} · **T1:** {_f(target1)} ({((target1/px-1)*100):+.1f}%) · **T2:** {_f(target2)} ({((target2/px-1)*100):+.1f}%)")
    else:
        direction = "WAIT"
        parts.append(f"⚪ **Range-bound** ({_f(px)}, pos {pos:.0%}) — beli dekat {_f(lrr)}, jual dekat {_f(trr)}. No trend edge, fade extremes.")

    # ── Market-specific refinement (ONLY appropriate data) ───────────────
    if market_key in ("us_equity", "crypto"):
        opts = (snap.get("options_data", {}) or {}).get(ticker, {})
        if opts and opts.get("call_wall"):
            cw, pw, mp = opts.get("call_wall"), opts.get("put_wall"), opts.get("max_pain")
            gex = opts.get("net_gex")
            if bull and pw:
                parts.append(f"📊 **Options confirm:** Put Wall {_f(pw)} = dealer support (entry floor). "
                             f"Call Wall {_f(cw)} = upside magnet/T-zone. Max Pain {_f(mp)}.")
            elif bear and cw:
                parts.append(f"📊 **Options confirm:** Call Wall {_f(cw)} = dealer resistance (short ceiling). "
                             f"Put Wall {_f(pw)} = downside target.")
            if gex is not None:
                try:
                    g = float(gex)
                    parts.append(f"γ regime: {'LONG gamma (mean-revert, fade extremes)' if g > 0 else 'SHORT gamma (momentum, breakouts run)'}.")
                except (TypeError, ValueError):
                    pass
            # Vanna/charm timing
            try:
                from engines.options_greeks_engine import get_opex_calendar
                cal = get_opex_calendar()
                vcw = cal.get("vanna_charm_window", {}) if cal else {}
                status = vcw.get("status", "")
                if status in ("WINDOW_ACTIVE_BUILDING", "CHARM_MAX", "OPEX_DAY"):
                    parts.append(f"🗓️ **Timing terbaik:** vanna/charm window AKTIF ({status}) → {vcw.get('note', 'pin risk into OPEX')}. Charm-max ~{vcw.get('peak', '')}.")
                elif vcw.get("start"):
                    parts.append(f"🗓️ **Timing:** vanna/charm window buka {vcw.get('start')} → peak {vcw.get('peak')} (charm-max window = best entry buat pin move).")
            except Exception:
                pass
        else:
            parts.append("📊 Options belum ter-fetch — entry pakai TRR/LRR dulu. (Rebuild buat GEX/walls + vanna/charm timing.)")

    elif market_key == "forex":
        cot_map = (snap.get("cot_oi", {}) or {}).get("cot", {}) or snap.get("cot_data", {}) or {}
        cot = cot_map.get(ticker, {})
        if cot and cot.get("noncomm_net") is not None:
            net = cot.get("noncomm_net")
            chg = cot.get("noncomm_change_wow")
            parts.append(f"📋 **COT confirm:** non-comm net {net:+,.0f}"
                         + (f" (Δ {chg:+,.0f} WoW)" if chg is not None else "")
                         + f". {'Selaras sama long bias' if (bull and (net or 0) > 0) else 'Selaras sama short bias' if (bear and (net or 0) < 0) else 'Hati-hati: COT divergence dari TRR/LRR'}.")
        else:
            parts.append("📋 COT belum ter-fetch — entry pakai TRR/LRR. (COT confirm positioning saat live.)")

    elif market_key == "commodity":
        cot_map = (snap.get("cot_oi", {}) or {}).get("cot", {}) or snap.get("cot_data", {}) or {}
        cot = cot_map.get(ticker, {})
        if cot and cot.get("noncomm_net") is not None:
            net = cot.get("noncomm_net")
            parts.append(f"📋 **COT:** non-comm net {net:+,.0f} — {'managed money long' if (net or 0) > 0 else 'managed money short'}.")
        # OI walls via ETF proxy
        FUT_PROXY = {"CL=F": "USO", "GC=F": "GLD", "SI=F": "SLV", "NG=F": "UNG", "HG=F": "CPER", "RB=F": "UGA"}
        proxy = FUT_PROXY.get(ticker)
        opts = (snap.get("options_data", {}) or {}).get(proxy or ticker, {})
        if opts and opts.get("call_wall"):
            parts.append(f"📊 **OI walls (via {proxy or ticker}):** resistance {_f(opts.get('call_wall'))}, "
                         f"support {_f(opts.get('put_wall'))}, max-pain {_f(opts.get('max_pain'))}.")
        elif not cot:
            parts.append("📋 COT + OI belum ter-fetch — entry pakai TRR/LRR. (Saat live: COT + OI walls confirm.)")

    elif market_key == "ihsg":
        bandar_map = snap.get("ihsg_broker_proxy", {}) or snap.get("ihsg_broker_data", {}) or {}
        b = bandar_map.get(ticker, {})
        if b and b.get("phase"):
            parts.append(f"🏦 **Bandar:** {b.get('phase')} — {b.get('note', '')}")
        else:
            # Auto-compute bandar proxy from price/volume action (no manual!)
            bp = _auto_bandar_proxy(rr, snap, ticker)
            if bp:
                parts.append(f"🏦 **Bandar (auto-proxy):** {bp}")

    return {"direction": direction, "lines": parts}


def _auto_bandar_proxy(rr: dict, snap: dict, ticker: str) -> str:
    """Auto-derive bandar accumulation/distribution signal from price action + range position.
    Replaces 'manual check' — uses what we have (TRR/LRR position, phase, Hurst, BSI proxy)."""
    if not rr:
        return ""
    phase = rr.get("phase", "NEUTRAL")
    trade = rr.get("trade", {})
    px = rr.get("px", 0) or 0
    lrr = trade.get("lrr", 0) or 0
    trr = trade.get("trr", 0) or 0
    width = trr - lrr if (trr and lrr) else 0
    pos = (px - lrr) / width if width > 0 else 0.5
    hurst = rr.get("hurst", {}).get("value", 0.5) if isinstance(rr.get("hurst"), dict) else 0.5
    bsi = rr.get("bsi", {}) if isinstance(rr.get("bsi"), dict) else {}

    # Heuristic bandar phase from structure
    if phase == "BULL" and pos < 0.35:
        return ("ACCUMULATION (proxy) — harga di lower TRADE range + uptrend, "
                "pola bandar nyerap di bawah. Watch volume naik tanpa harga turun = akumulasi asli.")
    elif phase == "BULL" and pos > 0.75:
        return ("MARKUP/DISTRIBUSI awal (proxy) — harga di upper range + uptrend. "
                "Kalau volume spike tapi harga stuck = mulai distribusi.")
    elif phase == "BEAR" and pos > 0.65:
        return ("DISTRIBUTION (proxy) — harga di upper range + downtrend, bandar buang barang ke retail. "
                "Hindari FOMO di rip.")
    elif phase == "BEAR" and pos < 0.30:
        return ("MARKDOWN/FORCED SELL (proxy) — harga di lower range + downtrend. "
                "Tunggu basing sebelum akumulasi.")
    else:
        return (f"NETRAL (proxy) — range-bound, pos {pos:.0%}. "
                "Bandar belum nunjukin niat jelas. Pantau broker summary + bid-offer untuk konfirmasi.")


def _render_targets(rr: dict, px: float, market_key: str):
    """Render explicit nearest/mid/farthest target prices from TRR/LRR.

    Edward's request: di US stocks tab + front-run, kasih target terdekat + terjauh.
    Computed from TRR/LRR (TRADE/TREND/TAIL) — these ARE the system targets.
    """
    import streamlit as st
    if not rr: return
    trade = rr.get("trade", {})
    trend = rr.get("trend", {})
    tail = rr.get("tail", {})
    phase = rr.get("phase", "NEUTRAL")

    # For BULL/sideways: targets are upper TRR. For BEAR: targets are lower LRR.
    if phase == "BEAR":
        nearest = trade.get("lrr") or 0
        mid = trend.get("lrr") or 0
        farthest = tail.get("lrr") or 0
        label_n, label_m, label_f = "Target Terdekat (TRADE LRR)", "Target Mid (TREND LRR)", "Target Terjauh (TAIL LRR)"
        direction = "↓"
    else:
        nearest = trade.get("trr") or 0
        mid = trend.get("trr") or 0
        farthest = tail.get("trr") or 0
        label_n, label_m, label_f = "Target Terdekat (TRADE TRR)", "Target Mid (TREND TRR)", "Target Terjauh (TAIL TRR)"
        direction = "↑"

    is_fx = market_key == "forex"
    fmt = ".4f" if is_fx else ",.2f"
    cur_sym = "" if is_fx else "$"

    if nearest and px:
        d_near = (nearest/px - 1) * 100
        d_mid = (mid/px - 1) * 100 if mid else 0
        d_far = (farthest/px - 1) * 100 if farthest else 0
        st.markdown(
            f"**🎯 Target Prices** ({direction}): "
            f"Near **{cur_sym}{format(nearest, fmt)}** ({d_near:+.1f}%) · "
            f"Mid **{cur_sym}{format(mid, fmt)}** ({d_mid:+.1f}%) · "
            f"Far **{cur_sym}{format(farthest, fmt)}** ({d_far:+.1f}%)"
        )


def _broker_codes_explained(brokers: list, side="buy") -> str:
    # Common IHSG broker codes — classify foreign vs domestic + behavior
    FOREIGN_BROKERS = {"CS", "KZ", "MS", "AK", "BK", "DB", "GS", "ML", "DX", "RG", "UU"}  # CIMB Securities, Kim Eng (Maybank), Macquarie, etc.
    LOCAL_BANDAR_BROKERS = {"BR", "BNI", "DR", "FZ", "LG", "MQ", "MU", "NI", "RX", "PD", "PG", "YP", "YU", "YJ", "ZP", "BK"}  # local market makers
    RETAIL_BROKERS = {"AT", "AZ", "MG", "OD", "PC", "BQ", "EP", "II"}  # primarily retail flow

    results = []
    for code in brokers:
        c = str(code).upper().strip()
        if c in FOREIGN_BROKERS:
            results.append(f"`{c}` (foreign)")
        elif c in LOCAL_BANDAR_BROKERS:
            results.append(f"`{c}` (local bandar)")
        elif c in RETAIL_BROKERS:
            results.append(f"`{c}` (retail flow)")
        else:
            results.append(f"`{c}`")
    return " · ".join(results)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════

ACTION_COLORS = {
    "BUY_DIP": "#3FB950", "ADD": "#3FB950", "HOLD": "#D29922",
    "TRIM": "#D29922", "TRIM_RIP": "#FF8C00",
    "SHORT_RIP": "#F85149", "COVER": "#A371F7",
    "WATCH": "#8B949E", "NO_DATA": "#484F58",
}


def render_rich_ticker(
    ticker: str, rr: dict, snap: dict, market_key: str = "us_equity",
    show_options: bool = False, show_cot: bool = False,
    show_onchain: bool = False, show_bandar: bool = False,
    is_frontrun: bool = False, frontrun_info: dict = None,
    show_oi: bool = False,
):
    """Render comprehensive ticker card with all narratives.

    Args:
        ticker: symbol
        rr: TRR/LRR dict from risk_range engine
        snap: full snapshot for data lookup
        market_key: us_equity/forex/commodity/crypto/ihsg
        show_*: which overlays to enable
        is_frontrun: True for front-run tab tickers
        frontrun_info: optional chain reaction context for front-run
    """
    if not rr or not isinstance(rr, dict):
        with st.container(border=True):
            st.markdown(f"### {ticker}  &nbsp; <span style='color:#8B949E;font-size:0.7rem;'>NO DATA</span>",
                       unsafe_allow_html=True)
            st.caption("Price/RR data unavailable for this ticker.")
        return

    px = rr.get("px") or 0
    phase = rr.get("phase", "NEUTRAL")
    sig = rr.get("signals", {})
    action = sig.get("action", "HOLD")
    quality = sig.get("quality", "C")

    # IHSG no-short rule
    if market_key == "ihsg" and action in ("SHORT_RIP", "COVER"):
        action = "WATCH"

    color = ACTION_COLORS.get(action, "#8B949E")

    with st.container(border=True):
        # ── HEADER: ticker, price, action ────────────────────────────────
        hc1, hc2, hc3 = st.columns([2.2, 1.2, 1.5])
        with hc1:
            head = f"### {ticker}"
            if is_frontrun:
                head += "  🔮"
            st.markdown(head)
            st.caption(f"**Quality {quality}** · Phase **{phase}** · Formation {sig.get('formation','NEUTRAL')}")
        with hc2:
            st.metric("Price", f"\\${px:,.2f}" if market_key != "forex" else f"{px:.4f}")
        with hc3:
            st.markdown(
                f"<div style='background:{color};color:#0D1117;padding:8px 12px;"
                f"border-radius:6px;text-align:center;font-weight:800;font-size:0.85rem;'>"
                f"{action}</div>",
                unsafe_allow_html=True,
            )

        # ── FRONT-RUN context (kalau di front-run tab) ────────────────────
        if is_frontrun and frontrun_info:
            driver = frontrun_info.get("driver", "?")
            shock = frontrun_info.get("shock_pct", 0)
            expected = frontrun_info.get("expected_pct", 0)
            lag = frontrun_info.get("lag_days", 0)
            thesis = frontrun_info.get("thesis", "")
            chain = frontrun_info.get("chain", "")
            readiness = frontrun_info.get("readiness", "")
            readiness_line = f"\n\n**Status: {readiness}**" if readiness else ""
            st.info(
                f"🔮 **Front-Run Setup:** Driver **{driver}** moved **{shock:+.2f}%** → "
                f"expected impact pada {ticker}: **{expected:+.2f}% within {lag} days**. "
                f"Chain: {chain}. {thesis}{readiness_line}"
            )

        # ── TIER1ALPHA-STYLE SIGNAL BOXES (color-coded quality/phase/gamma) ──
        _render_signal_boxes(rr, snap, market_key, show_options, ticker)

        # ── POSITION REPORT — the main actionable view (header+entry+target+stop+
        #    dealer+vanna+expected move+breakout+dark pool+COT). Always visible. ──
        try:
            render_options_recommendation(rr, snap, ticker, market_key)
        except Exception:
            pass

        # ── ACCUMULATION READINESS — quiet-accumulation signal (always visible) ──
        try:
            _ar = compute_accumulation_readiness(rr, snap, ticker)
            if _ar:
                st.caption(f"{_ar['emoji']} **Readiness — {_ar['label']}** ({_ar['score']:+d}) · " + " · ".join(_ar["signals"][:3]))
        except Exception:
            pass

        # ── UNIMPORTANT DETAIL — collapsed toggle (raw greeks chain, OI heatmap,
        #    COT detail, bandar). Report above already has the actionable summary. ──
        with st.expander("🔍 Detail tambahan (raw greeks · OI heatmap · COT · bandar)", expanded=False):

            # TRR/LRR bands + phase (moved here from main view — report has the essentials)
            trade = rr.get("trade", {}); trend = rr.get("trend", {}); tail = rr.get("tail", {})
            st.markdown("**📊 TRR/LRR v20.3b (Hedgeye-style)**")
            rrc1, rrc2, rrc3 = st.columns(3)
            with rrc1:
                st.caption("**TRADE (15d)**")
                st.caption(f"LRR: \\${(trade.get('lrr') or 0):.2f}")
                st.caption(f"TRR: \\${(trade.get('trr') or 0):.2f}")
            with rrc2:
                st.caption("**TREND (63d)**")
                st.caption(f"LRR: \\${(trend.get('lrr') or 0):.2f}")
                st.caption(f"TRR: \\${(trend.get('trr') or 0):.2f}")
            with rrc3:
                st.caption("**TAIL (3yr)**")
                st.caption(f"LRR: \\${(tail.get('lrr') or 0):.2f}")
                st.caption(f"TRR: \\${(tail.get('trr') or 0):.2f}")
            st.caption(f"🧭 {_phase_narrative(rr)}")
            st.markdown("---")

            if show_options:
                opts_map = snap.get("yfinance_options", {}) or snap.get("options_data", {}) or {}
                opts = opts_map.get(ticker, {}) if isinstance(opts_map, dict) else {}
                fund_map = snap.get("fundamentals", {}) or {}
                fund = fund_map.get(ticker, {}) if isinstance(fund_map, dict) else {}

                st.markdown("**📈 Options + Greeks + Vanna/Charm — detail**")

                # Vanna/Charm calendar — ALWAYS available (calendar-based)
                try:
                    from engines.options_greeks_engine import build_options_intelligence
                    intel = build_options_intelligence(ticker, opts, px, fund)
                    vc = intel["opex_calendar"]["vanna_charm_window"]
                    cal = intel["opex_calendar"]

                    # Vanna/Charm window status
                    st.markdown(f"**🗓️ Vanna/Charm Window** (OPEX {cal['current_opex']}, {cal['days_to_opex']}d away)")
                    st.caption(f"{vc['note']}")
                    st.caption(f"Window: {vc['start']} (open) → {vc['peak']} (peak) → {vc['end']} (charm max)")

                    # Gamma positioning
                    g = intel["gamma"]
                    if g.get("available") and g.get("regime"):
                        st.markdown(f"**🎯 Gamma Regime:** {g.get('regime_note', '')}")
                        wall_parts = []
                        if g.get("call_wall"):
                            wall_parts.append(f"Call Wall \\${g['call_wall']:.2f} ({g.get('call_wall_dist_pct', 0):+.1f}%)")
                        if g.get("put_wall"):
                            wall_parts.append(f"Put Wall \\${g['put_wall']:.2f} ({g.get('put_wall_dist_pct', 0):+.1f}%)")
                        if g.get("gamma_flip"):
                            flip_state = "ABOVE (positive gamma)" if g.get("above_flip") else "BELOW (negative gamma)"
                            wall_parts.append(f"Gamma Flip \\${g['gamma_flip']:.2f} — price {flip_state}")
                        if g.get("max_pain"):
                            wall_parts.append(f"Max Pain \\${g['max_pain']:.2f}")
                        if wall_parts:
                            for wp in wall_parts:
                                st.caption(f"• {wp}")

                    # Short squeeze
                    sq = intel["squeeze"]
                    if sq.get("available"):
                        st.markdown(f"**🩳 Short Squeeze:** {sq.get('note', '')}")
                        if sq.get("days_to_cover"):
                            st.caption(f"Days to cover: {sq['days_to_cover']}")

                    # Expected move
                    if intel.get("expected_move_pct"):
                        st.caption(f"📏 Expected move (1wk): ±{intel['expected_move_pct']:.2f}%")
                except Exception as e:
                    st.caption(f"Vanna/charm calendar: {e}")

                # Raw options narrative (walls/IV/PC)
                opt_text = _options_narrative(opts, px, ticker)
                if opt_text:
                    st.markdown("**Detail:**")
                    st.markdown(opt_text)
                elif not opts:
                    st.caption("⚠️ Live options chain belum ke-fetch. Vanna/charm calendar di atas tetap valid (date-based). "
                              "Gamma walls + squeeze butuh options data dari yfinance/Deribit.")
                mm_text = _mm_positioning(opts, px)
                if mm_text:
                    st.markdown("**🏪 MM Positioning + Volatility Outlook**")
                    st.markdown(mm_text)

            if show_cot:
                cot_map = (snap.get("cot_oi", {}) or {}).get("cot", {}) or snap.get("cot_data", {}) or {}
                cot = cot_map.get(ticker, {}) if isinstance(cot_map, dict) else {}
                st.markdown("**📋 COT (Commitments of Traders)**")
                cot_text = _cot_narrative(cot, ticker)
                if cot_text:
                    st.markdown(cot_text)
                else:
                    from engines.live_data_engine import COT_TICKER_MAP
                    if ticker in COT_TICKER_MAP or ticker.upper() in COT_TICKER_MAP:
                        st.caption(f"COT untuk {ticker} ({COT_TICKER_MAP.get(ticker, COT_TICKER_MAP.get(ticker.upper()))}) belum ter-fetch — CFTC publish mingguan (Jumat). Coba Rebuild after Fri 3:30pm ET.")
                    else:
                        st.caption(f"{ticker} bukan produk CFTC reportable — no COT data (cuma futures utama: EUR/GBP/JPY/GOLD/CRUDE/dst).")

            if show_oi:
                _render_oi_heatmap(snap, ticker, market_key)

            if show_onchain:
                oc_map = snap.get("crypto_tokens", {}) or snap.get("onchain_data", {}) or {}
                oc = oc_map.get(ticker, {}) if isinstance(oc_map, dict) else {}
                st.markdown("**⛓️ On-Chain Activity (Accumulation/Distribution)**")
                oc_text = _onchain_narrative(oc, ticker)
                if oc_text:
                    st.markdown(oc_text)
                else:
                    _CHAIN_OK = {"BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "MATIC-USD", "ARB-USD", "OP-USD", "BNB-USD"}
                    if ticker in _CHAIN_OK:
                        st.caption(f"On-chain {ticker} belum ter-fetch dari DeFiLlama — coba Rebuild (butuh internet di server).")
                    else:
                        st.caption(f"{ticker} ga punya chain TVL di DeFiLlama — on-chain cuma buat L1/L2 utama (BTC/ETH/SOL/AVAX/dst).")

            if show_bandar:
                bandar_map = snap.get("ihsg_broker_proxy", {}) or snap.get("ihsg_broker_data", {}) or {}
                b = bandar_map.get(ticker, {}) if isinstance(bandar_map, dict) else {}
                st.markdown("**🏦 IHSG Bandar Analysis (Cornering / Accumulation / Distribution)**")
                b_text = _bandar_narrative(b, ticker)
                if b_text:
                    st.markdown(b_text)
                else:
                    # AUTO-COMPUTE bandar phase from price action (no manual!)
                    bp = _auto_bandar_proxy(rr, snap, ticker)
                    st.markdown(f"**Auto-proxy:** {bp}")
                    st.caption(
                        "ℹ️ Proxy dihitung dari TRR/LRR position + phase + Hurst. "
                        "Untuk data bandar real (broker summary, foreign flow, cross-trade), "
                        "butuh API berbayar (Invezgo/GOAPI) — bisa di-wire kalau lu kasih API key."
                    )

            # Correlation drivers (universal)
            try:
                from engines.chain_reaction_v2 import get_chain_engine
                cre = get_chain_engine()
                parents = cre.find_parents_of(ticker)
                if parents:
                    st.markdown("**🔗 Correlation Drivers (chain reaction)**")
                    for p in parents[:5]:
                        beta = p.get("beta", 0)
                        direction = "↗" if p.get("direction") == "SAME" else "↙"
                        st.caption(f"• **{p['parent']}** {direction} β={beta:.2f}, lag {p.get('lag_days', 0)}d — {p.get('thesis', '')}")
            except Exception:
                pass


def compute_accumulation_readiness(rr: dict, snap: dict, ticker: str) -> dict:
    """Detect if a name is being ACCUMULATED / setting up to rise, using options
    flow + greeks + dark pool. ONLY returns a signal if real data exists (else None).

    Methodology (from deep research):
      • Dark pool (Unusual Whales/scraped): prints BELOW spot + repeated + volume
        spike = institutions building BEFORE the public move ('front-run the rally').
      • Options flow: daily Vol >> OI = NEW positions; call-heavy + low PCR = bullish.
      • Gamma (GEX): price ABOVE gamma_flip = dealers long gamma (support); a large
        positive call_wall above = magnet/target; negative net GEX = explosive fuel.
      • DEX rising = dealers getting longer delta (bullish hedging flow).
    """
    od = (snap.get("options_data", {}) or {}).get(ticker, {})
    oc_check = (snap.get("onchain_data", {}) or {}).get(ticker, {})
    px_check = (snap.get("prices", {}) or {}).get(ticker)
    if not od and not oc_check and px_check is None:
        return None  # nothing to compute from

    px = rr.get("px", 0) or od.get("spot", 0) or 0
    score = 0
    signals = []
    has_any = False

    # ── GREEKS: gamma positioning (REAL options only — proxy GEX is unreliable) ──
    _real_opts = bool(od) and od.get("source") != "proxy"
    gex = od.get("net_gex") if _real_opts else None
    gflip = od.get("gamma_flip") if _real_opts else None
    cwall = od.get("call_wall") if _real_opts else None
    pwall = od.get("put_wall") if _real_opts else None
    if gflip and px:
        has_any = True
        if px > gflip:
            score += 1; signals.append(f"px>{gflip:,.0f} γ-flip → dealers long gamma (support)")
        else:
            signals.append(f"px<{gflip:,.0f} γ-flip → below flip (volatile/needs reclaim)")
    if gex is not None:
        has_any = True
        if gex < 0:
            score += 1; signals.append("net GEX negative → explosive-move fuel (squeeze risk up)")
        else:
            signals.append("net GEX positive → moves dampened/pinned")
    if cwall and px and cwall > px:
        signals.append(f"call wall {cwall:,.0f} = upside magnet/target ({(cwall/px-1)*100:+.0f}%)")

    # ── OPTIONS FLOW: PCR + new positioning ──
    pcr = od.get("put_call_ratio")
    if pcr is not None:
        has_any = True
        if pcr < 0.7:
            score += 1; signals.append(f"PCR {pcr:.2f} low → call-heavy (bullish flow)")
        elif pcr > 1.3:
            score -= 1; signals.append(f"PCR {pcr:.2f} high → put-heavy (hedging/bearish)")
    vol_oi = od.get("volume_oi_ratio")
    if vol_oi and vol_oi > 1.0:
        score += 1; signals.append(f"Vol/OI {vol_oi:.1f}× → NEW positions opening (fresh interest)")

    # ── DARK POOL (if present from scraped/UW) ──
    dp = od.get("dark_pool", {}) or {}
    dp_net = dp.get("net_sentiment") or od.get("dark_pool_sentiment")
    dp_below = dp.get("prints_below_pct") or od.get("dp_below_pct")
    if dp_net is not None or dp_below is not None:
        has_any = True
        if (dp_net and str(dp_net).lower() in ("bullish", "accumulation")) or (dp_below and dp_below > 60):
            score += 2; signals.append("🌑 Dark pool: net buying BELOW spot → institutions accumulating")
        elif (dp_net and str(dp_net).lower() in ("bearish", "distribution")) or (dp_below and dp_below < 40):
            score -= 2; signals.append("🌑 Dark pool: selling above spot → distribution")

    # ── FINRA off-exchange short volume — REAL free dark-pool signal (all US tickers) ──
    finra = (snap.get("finra_short", {}) or {}).get(ticker.upper(), {})
    if finra.get("signal"):
        has_any = True
        if finra["signal"] == "accumulation":
            score += 2; signals.append(f"🌑🟢 FINRA dark pool: {finra.get('note','')}")
        elif finra["signal"] == "distribution":
            score -= 2; signals.append(f"🌑🔴 FINRA dark pool: {finra.get('note','')}")
    dex = od.get("dex") or od.get("net_dex")
    if dex is not None:
        has_any = True
        if dex > 0:
            score += 1; signals.append("DEX positive → dealers long delta (supportive)")

    # ── ON-CHAIN (crypto): unusual TVL/volume/flow = quiet accumulation ──
    oc = (snap.get("onchain_data", {}) or {}).get(ticker, {})
    if oc:
        has_any = True
        tvl_chg = oc.get("tvl_change_7d") or oc.get("tvl_change_pct")
        vol_tvl = oc.get("volume_tvl_ratio")
        net_flow = oc.get("net_flow") or oc.get("netflow")
        if tvl_chg is not None:
            if tvl_chg > 10:
                score += 2; signals.append(f"⛓️ TVL +{tvl_chg:.0f}% → capital flowing IN (accumulation)")
            elif tvl_chg < -10:
                score -= 2; signals.append(f"⛓️ TVL {tvl_chg:.0f}% → capital leaving")
        if vol_tvl is not None and vol_tvl > 0.5:
            score += 1; signals.append(f"⛓️ Vol/TVL {vol_tvl:.2f} → unusual on-chain activity spike")
        if net_flow is not None:
            if net_flow > 0:
                score += 1; signals.append("⛓️ Net inflow positive → on-chain accumulation")
            else:
                score -= 1; signals.append("⛓️ Net outflow → on-chain distribution")

    # ── INSTITUTIONAL FLOW PROXY (price/vol-derived, works for ALL tickers) ──
    prices = snap.get("prices", {}) or {}
    if prices.get(ticker) is not None:
        try:
            from engines.institutional_proxy import analyze_institutional
            inst = analyze_institutional(ticker, prices, vix=snap.get("vix", 20.0) or 20.0)
            if inst.get("ok"):
                has_any = True
                fs = inst.get("flow_score", 0)
                bias = inst.get("bias", "NEUTRAL")
                if bias == "BULLISH" or fs > 0:
                    score += 1; signals.append(f"🏦 Institutional flow {bias} (score {fs}) — CTA/collar supportive")
                elif bias == "BEARISH" or fs < 0:
                    score -= 1; signals.append(f"🏦 Institutional flow {bias} (score {fs})")
        except Exception:
            pass

    # ── 13F SMART MONEY (which famous funds hold + recent action = quiet accumulation) ──
    try:
        from engines.smart_money_tracker import get_ticker_smart_money
        sm = get_ticker_smart_money(ticker)
        if sm.get("smart_money_held") and sm.get("n_holders", 0) > 0:
            has_any = True
            act = sm.get("recent_action", "")
            top = sm.get("top_holder", "")
            n = sm.get("n_holders", 0)
            if "adding" in act.lower() or "🟢" in act:
                score += 2; signals.append(f"💎 {n} smart-money funds hold (top: {top}) — net ADDING (quiet accumulation)")
            elif "trim" in act.lower() or "🔴" in act:
                score -= 1; signals.append(f"💎 {n} smart-money funds hold but net trimming")
            else:
                score += 1; signals.append(f"💎 {n} smart-money funds hold (top: {top}) — {act}")
    except Exception:
        pass

    if not has_any:
        return None

    if score >= 4:
        label, emoji = "SIAP NAIK (strong accumulation)", "🟢🟢"
    elif score >= 2:
        label, emoji = "Ancang-ancang (building)", "🟢"
    elif score >= 0:
        label, emoji = "Netral / wait", "⚪"
    elif score >= -2:
        label, emoji = "Hati-hati (soft)", "🟡"
    else:
        label, emoji = "Distribution (avoid)", "🔴"

    # Flag data provenance so modeled proxy isn't mistaken for real dealer flow/dark pool
    src = od.get("source", "")
    if src == "proxy":
        signals.insert(0, "📐 PROXY (price-derived estimate — bukan real flow/dark pool)")
    elif od.get("dark_pool") or od.get("dark_pool_sentiment"):
        signals.insert(0, "🌑 REAL dark pool + options flow")

    return {"score": score, "label": label, "emoji": emoji, "signals": signals[:7], "source": src or "yfinance"}


def build_options_recommendation(rr: dict, snap: dict, ticker: str, market_key: str = "us_equity") -> dict:
    """Position report. TWO modes:
      • REAL options (yfinance live) → full dealer/walls/vanna/charm/dark-pool + TRR/LRR confluence
      • No real options (proxy/futures/ihsg) → TRR/LRR-based ONLY (entry=LRR, target=TRR,
        stop below LRR) + COT (futures) / institutional (stocks). NO fake gamma shown.
    Proxy GEX is SMA-derived & unreliable, so it is NEVER displayed as dealer positioning."""
    od = (snap.get("options_data", {}) or {}).get(ticker, {})
    px = rr.get("px", 0) or od.get("spot", 0) or 0
    if not px:
        return None
    has_real_opts = bool(od) and od.get("source") != "proxy"

    # TRR/LRR bands (always)
    trade = rr.get("trade", {}) or {}; trend = rr.get("trend", {}) or {}; tail = rr.get("tail", {}) or {}
    t_lrr, t_trr = trade.get("lrr", 0) or 0, trade.get("trr", 0) or 0
    tr_lrr, tr_trr = trend.get("lrr", 0) or 0, trend.get("trr", 0) or 0
    tl_lrr = tail.get("lrr", 0) or 0
    width = t_trr - t_lrr if (t_trr and t_lrr) else px * 0.04
    pos = (px - t_lrr) / width if width > 0 else 0.5

    # Greeks ONLY if real options
    gflip = od.get("gamma_flip") if has_real_opts else None
    gex = od.get("net_gex") if has_real_opts else None
    cwall = od.get("call_wall") if has_real_opts else None
    pwall = od.get("put_wall") if has_real_opts else None
    maxpain = od.get("max_pain") if has_real_opts else None
    pcr = od.get("put_call_ratio") if has_real_opts else None
    em = (od.get("expected_move_pct") or od.get("expected_move")) if has_real_opts else None
    above_flip = bool(gflip and px > gflip)
    short_gamma = has_real_opts and ((gex is not None and gex < 0) or (gflip and px < gflip))

    # sanity: walls must be on the right side (put<px<call); ignore if inverted (bad data)
    if pwall and pwall > px: pwall = None
    if cwall and cwall < px: cwall = None

    # Direction
    phase = rr.get("phase", "NEUTRAL"); pc = rr.get("phase_code", 0)
    bull = phase == "BULL" or pc == 1; bear = phase == "BEAR" or pc == -1
    keith_note = None; keith_flip = False
    try:
        from engines.keith_signal_sync import resolve_direction
        kd = resolve_direction(ticker, "LONG" if bull else "SHORT" if bear else "NEUTRAL")
        kt = kd.get("keith_trade", "NEUTRAL")
        if kt and kt != "NEUTRAL":
            keith_note = f"Keith TRADE {kt} / TREND {kd.get('keith_trend','NEUTRAL')}"
        if kt == "BEARISH" and bull:
            bull = False; keith_flip = True
    except Exception:
        pass

    # Dark pool (real only)
    dp = od.get("dark_pool", {}) or {} if has_real_opts else {}
    dp_acc = has_real_opts and ((str(dp.get("net_sentiment") or od.get("dark_pool_sentiment") or "").lower() in ("bullish","accumulation")) or ((dp.get("prints_below_pct") or od.get("dp_below_pct") or 0) > 60))
    dp_dist = has_real_opts and ((str(dp.get("net_sentiment") or od.get("dark_pool_sentiment") or "").lower() in ("bearish","distribution")) or (0 < (dp.get("prints_below_pct") or od.get("dp_below_pct") or 100) < 40))

    def f(v): return f"${v:,.2f}"   # plain $ — rendered inside HTML div (no LaTeX)
    def pct(v): return f"{(v/px-1)*100:+.1f}%"

    # ── INSTRUMENT + DIRECTION ──
    instrument = None; direction = None; conviction = "medium"
    if market_key == "ihsg":
        instrument, direction = ("AKUMULASI (beli spot bertahap)", "long") if bull else ("WAIT / hindari (buy-only)", "flat")
    elif market_key in ("commodity", "forex"):
        instrument, direction = ("LONG FUTURES", "long") if bull else ("SHORT FUTURES", "short") if bear else ("WAIT (range)", "flat")
    else:  # us_equity / crypto
        if bull:
            if has_real_opts and (short_gamma or dp_acc):
                instrument, direction, conviction = "BUY CALL (leverage squeeze)", "long", "high"
            else:
                instrument, direction = "LONG SPOT/SHARES", "long"
        elif bear:
            if has_real_opts and (short_gamma or dp_dist):
                instrument, direction, conviction = "BUY PUT (leverage downside)", "short", "high"
            else:
                instrument, direction = "SHORT / SELL", "short"
        else:
            instrument, direction = ("WAIT — Keith bearish near-term (jangan chase)", "flat") if keith_flip else ("WAIT (range — fade extremes)", "flat")

    # ── ENTRY / TARGET / STOP (TRR/LRR base; walls refine if real) ──
    entry_zone = None; confluence = []; target = None; stop = None
    if direction == "long":
        # Buy the dip toward TRADE LRR (Keith). If price already below LRR, buy now.
        e_lo, e_hi = t_lrr, (t_lrr + width * 0.30)
        entry_zone = f"{f(e_lo)}–{f(e_hi)}" + (" (beli sekarang, udah di support)" if px <= e_hi else " (tunggu pullback ke sini)")
        if has_real_opts and pwall:
            confluence.append(f"Put wall {f(pwall)} = support dealer ({pct(pwall)})")
            if abs(pwall - t_lrr) / px < 0.04:
                confluence[-1] = f"🎯 Put wall {f(pwall)} ≈ TRADE LRR {f(t_lrr)} → support confluence kuat"
        # Target: TREND TRR (or call wall if real & nearer/aligned)
        tgt = tr_trr or px * 1.08
        if has_real_opts and cwall:
            if abs(cwall - tr_trr) / px < 0.05:
                confluence.append(f"🎯 Call wall {f(cwall)} ≈ TREND TRR {f(tr_trr)} → target confluence")
                tgt = min(cwall, tr_trr)
            else:
                confluence.append(f"Call wall {f(cwall)} = resistance dealer ({pct(cwall)})")
                tgt = cwall
        target = f"{f(tgt)} ({pct(tgt)})"
        # Stop: below TREND LRR (medium-term support), fallback TRADE LRR - buffer
        stop_lvl = tr_lrr if (tr_lrr and tr_lrr < px) else t_lrr * 0.97
        stop = f"< {f(stop_lvl)} ({pct(stop_lvl)})"
    elif direction == "short":
        e_lo, e_hi = (t_trr - width * 0.30), t_trr
        entry_zone = f"{f(e_lo)}–{f(e_hi)}" + (" (short sekarang, udah di resistance)" if px >= e_lo else " (tunggu rip ke sini)")
        if has_real_opts and cwall:
            confluence.append(f"Call wall {f(cwall)} = resistance dealer ({pct(cwall)})")
            if abs(cwall - t_trr) / px < 0.04:
                confluence[-1] = f"🎯 Call wall {f(cwall)} ≈ TRADE TRR {f(t_trr)} → resistance confluence"
        tgt = tr_lrr or px * 0.92
        if has_real_opts and pwall:
            confluence.append(f"Put wall {f(pwall)} = target support ({pct(pwall)})")
            tgt = pwall
        target = f"{f(tgt)} ({pct(tgt)})"
        stop_lvl = tr_trr if (tr_trr and tr_trr > px) else t_trr * 1.03
        stop = f"> {f(stop_lvl)} ({pct(stop_lvl)})"
    else:
        entry_zone = f"{f(t_lrr)} (beli) / {f(t_trr)} (jual) — range, fade extremes"

    # ── Dealer + vanna/charm (REAL options only) ──
    dealer = None; vc = None
    if has_real_opts and (gflip or gex is not None):
        if above_flip:
            dealer = f"Long gamma (di atas γ-flip {f(gflip)}) → harga pinned/stabil, dealer jual rip beli dip"
        elif gflip:
            dealer = f"Short gamma (di bawah γ-flip {f(gflip)}) → gerakan diperbesar; reclaim {f(gflip)} = flip bullish"
        else:
            dealer = "Short gamma → explosive" if (gex or 0) < 0 else "Long gamma → teredam"
        try:
            from engines.options_greeks_engine import build_options_intelligence
            intel = build_options_intelligence(ticker, od, px, {})
            vcw = intel.get("opex_calendar", {}).get("vanna_charm_window", {})
            dto = intel.get("opex_calendar", {}).get("days_to_opex")
            stt = vcw.get("status", "")
            if stt == "WINDOW_ACTIVE_BUILDING": vc = f"Vanna tailwind aktif ({dto}d ke OPEX) → kalau vol turun dealer beli → drift bullish, pin ke call wall/max pain"
            elif stt == "CHARM_MAX": vc = f"Charm max ({dto}d ke OPEX) → pinning ke max pain {f(maxpain) if maxpain else ''}; gerakan terbatas s/d expiry"
            elif stt == "POST_OPEX": vc = "Post-OPEX → gamma reset, posisi unwinding → window gerakan baru (vol naik)"
            elif stt == "PRE_WINDOW": vc = f"Pre-vanna window ({dto}d ke OPEX) — efek vanna/charm belum dominan"
            if intel.get("expected_move_pct"): em = intel["expected_move_pct"]
        except Exception:
            pass

    # COT (futures)
    cot_note = None
    if market_key in ("commodity", "forex"):
        cot = (snap.get("cot_data", {}) or {}).get(ticker, {})
        nc = cot.get("noncommercial_net") or cot.get("net_position")
        if nc is not None:
            aligned = (nc > 0 and direction == "long") or (nc < 0 and direction == "short")
            cot_note = f"COT non-comm net {nc:+,.0f} — {'selaras' if aligned else 'divergence (hati-hati)'}"

    dp_line = "🌑 Dark pool: akumulasi (institusi beli diam-diam)" if dp_acc else \
              "🌑 Dark pool: distribusi (institusi jual)" if dp_dist else None

    # FINRA off-exchange short volume — REAL free dark-pool signal (all US tickers,
    # independent of options). Overrides the (rarer) options dark_pool when present.
    finra = (snap.get("finra_short", {}) or {}).get(ticker.upper(), {})
    if finra.get("note"):
        sig = finra.get("signal")
        emoji = "🌑🟢" if sig == "accumulation" else "🌑🔴" if sig == "distribution" else "🌑"
        dp_line = f"{emoji} Dark pool (FINRA): {finra['note']}"
        if sig == "accumulation" and direction == "long":
            confluence.append(f"🌑 FINRA off-exch short {finra.get('short_pct',0):.0f}% → MM hedging dark-pool buys")

    # Expected move / breakout (REAL options only — needs real walls/IV)
    by_expiry = None; breakout_up = None; breakout_down = None
    if has_real_opts and em:
        lo = px * (1 - em/100); hi = px * (1 + em/100)
        by_expiry = f"{f(lo)} — {f(hi)} (±{em:.1f}%) s/d expiry"
    if has_real_opts and cwall:
        nxt = tr_trr if (tr_trr and tr_trr > cwall) else None
        breakout_up = f"break call wall {f(cwall)} → squeeze ke {f(nxt)} ({pct(nxt)})" if nxt else f"break call wall {f(cwall)} → gamma squeeze (dealer kejar)"
    if has_real_opts and pwall:
        nxt = tr_lrr if (tr_lrr and tr_lrr < pwall) else None
        breakout_down = f"break put wall {f(pwall)} → drop ke {f(nxt)} ({pct(nxt)})" if nxt else f"break put wall {f(pwall)} → support hilang, downside cepat"

    sig_label = "🟢 Bull" if bull else "🔴 Bear" if bear else "⚪ Netral"

    # ── MULTI-POSITIONING: how to express this trade via SPOT vs LEVERAGE ──
    # Only for markets with real long/short. IHSG = buy-only (spot only, no leverage section).
    positions = []
    if direction in ("long", "short"):
        is_long = direction == "long"
        e_txt = entry_zone or "—"
        # 1) SPOT / CASH (no leverage)
        if market_key == "ihsg":
            positions.append({"type": "💵 Spot (cash)", "detail":
                f"Akumulasi bertahap · entry {e_txt} · target {target or '—'} · stop {stop or '—'} · size penuh, hold sampai fase berubah"})
        elif market_key in ("us_equity", "crypto"):
            lbl = "Long shares/spot" if is_long else "Short shares (borrow)"
            positions.append({"type": "💵 Spot (cash, no leverage)", "detail":
                f"{lbl} · entry {e_txt} · target {target or '—'} · stop {stop or '—'} · size penuh, stop lebih longgar, hold lebih lama"})
        # 2) LEVERAGE via OPTIONS (real options + equity/crypto only)
        if has_real_opts and market_key in ("us_equity", "crypto"):
            if is_long:
                strike = gflip if (gflip and gflip <= px) else round(px, 2)
                fuel = "short-gamma = dealer kejar (gamma fuel) ✓" if short_gamma else "long-gamma = theta drag, pilih expiry ≥45d"
                positions.append({"type": "⚡ Leverage — BUY CALL", "detail":
                    f"Strike ~{f(strike)} (ATM/slightly-ITM), expiry ≥30-45d · risiko = premium (defined, ga kena likuidasi) · target call wall {f(cwall) if cwall else (target or '—')} · {fuel}"})
            else:
                strike = gflip if (gflip and gflip >= px) else round(px, 2)
                positions.append({"type": "⚡ Leverage — BUY PUT", "detail":
                    f"Strike ~{f(strike)} (ATM/slightly-ITM), expiry ≥30-45d · risiko = premium (defined) · target put wall {f(pwall) if pwall else (target or '—')}"})
        elif market_key in ("us_equity", "crypto"):
            # No real options → margin leverage is still available for the spot-vs-leverage choice
            positions.append({"type": "⚡ Leverage — Margin", "detail":
                f"{'Long' if is_long else 'Short'} margin 1.5-2x · entry {e_txt} · stop {stop or '—'} (lebih ketat dari spot) · size lebih kecil, awas margin call (options N/A buat ticker ini)"})
        # 3) LEVERAGE via FUTURES / PERP
        if market_key in ("commodity", "forex"):
            positions.append({"type": "⚡ Leverage — Futures", "detail":
                f"{'Long' if is_long else 'Short'} futures · entry {e_txt} · stop {stop or '—'} (di balik LRR/TRR) · size kecil (margin), stop ketat krn likuidasi"})
        elif market_key == "crypto":
            positions.append({"type": "⚡ Leverage — Perp/Futures", "detail":
                f"{'Long' if is_long else 'Short'} perp 2-5x · entry {e_txt} · stop {stop or '—'} · awas funding rate + likuidasi, size kecil"})

    return {
        "ticker": ticker, "market": market_key, "px": px, "has_real_opts": has_real_opts,
        "instrument": instrument, "direction": direction, "conviction": conviction, "pos": pos,
        "entry_zone": entry_zone, "confluence": confluence, "target": target, "stop": stop,
        "dealer": dealer, "vanna_charm": vc, "dark_pool": dp_line, "cot": cot_note, "keith": keith_note,
        "pcr": pcr, "expected_move": em, "by_expiry": by_expiry,
        "breakout_up": breakout_up, "breakout_down": breakout_down,
        "call_wall": cwall, "put_wall": pwall, "sig_label": sig_label, "positions": positions,
        "trade_lrr": t_lrr, "trade_trr": t_trr, "trend_lrr": tr_lrr, "trend_trr": tr_trr, "fmt": f,
    }


def render_options_recommendation(rr: dict, snap: dict, ticker: str, market_key: str = "us_equity"):
    """Clean scannable report. Plain $ inside HTML div (no LaTeX). TRR/LRR always shown.
    Options/greeks/dark-pool/vanna-charm ONLY when real options exist."""
    rec = build_options_recommendation(rr, snap, ticker, market_key)
    if not rec:
        return False
    f = rec["fmt"]
    bar = "#3FB950" if rec["direction"] == "long" else "#F85149" if rec["direction"] == "short" else "#8B949E"
    dir_emoji = {"long": "🟢", "short": "🔴", "flat": "⚪"}.get(rec["direction"], "⚪")
    conv = " · ⚡ high-conviction" if rec["conviction"] == "high" else ""
    if rec["has_real_opts"]:
        src = "🟢 live options + greeks"
    elif market_key in ("commodity", "forex"):
        src = "TRR/LRR + COT"
    elif market_key == "ihsg":
        src = "TRR/LRR + bandar"
    else:
        src = "TRR/LRR (options N/A)"

    # Header: TICKER · price · signal · TRR/LRR · walls(if real)
    bits = [f"📋 <b>{rec['ticker']}</b>", f"{f(rec['px'])}", rec["sig_label"],
            f"TRADE {f(rec['trade_lrr'])}–{f(rec['trade_trr'])}"]
    if rec["has_real_opts"] and (rec["call_wall"] or rec["put_wall"]):
        w = []
        if rec["call_wall"]: w.append(f"CW {f(rec['call_wall'])}")
        if rec["put_wall"]: w.append(f"PW {f(rec['put_wall'])}")
        bits.append(" ".join(w))
    header = " · ".join(bits) + f" <span style='opacity:0.55;font-size:0.82em'>({src})</span>"

    rows = [header, f"{dir_emoji} <b>Posisi:</b> {rec['instrument']}{conv}"]
    if rec["entry_zone"]: rows.append(f"<b>Entry:</b> {rec['entry_zone']}")
    for c in rec["confluence"][:2]:
        rows.append(f"<span style='opacity:0.85'>&nbsp;&nbsp;↳ {c}</span>")
    if rec["target"]: rows.append(f"<b>Target:</b> {rec['target']}  ·  <b>Stop:</b> {rec['stop']}")
    if rec["by_expiry"]: rows.append(f"<b>Expected move:</b> {rec['by_expiry']}")
    if rec["breakout_up"]: rows.append(f"<span style='opacity:0.85'>📈 {rec['breakout_up']}</span>")
    if rec["breakout_down"]: rows.append(f"<span style='opacity:0.85'>📉 {rec['breakout_down']}</span>")
    # Multi-positioning: spot vs leverage (only when ≥2 ways exist)
    if rec.get("positions") and len(rec["positions"]) >= 2:
        rows.append("<b>🎚️ Cara masuk (pilih sesuai gaya):</b>")
        for p in rec["positions"]:
            rows.append(f"<span style='opacity:0.9'>&nbsp;&nbsp;{p['type']}: {p['detail']}</span>")
    if rec["dealer"]: rows.append(f"<span style='opacity:0.8'><b>Dealer:</b> {rec['dealer']}</span>")
    if rec["vanna_charm"]: rows.append(f"<span style='opacity:0.8'><b>Vanna/charm:</b> {rec['vanna_charm']}</span>")
    if rec["dark_pool"]: rows.append(f"<span style='opacity:0.8'>{rec['dark_pool']}</span>")
    if rec["cot"]: rows.append(f"<span style='opacity:0.8'><b>COT:</b> {rec['cot']}</span>")
    if rec["keith"]: rows.append(f"<span style='opacity:0.65'>📌 {rec['keith']}</span>")
    extras = []
    if rec.get("pcr") is not None: extras.append(f"PCR {rec['pcr']:.2f}")
    if extras: rows.append(f"<span style='opacity:0.6;font-size:0.85em'>{' · '.join(extras)}</span>")

    st.markdown(
        f"<div style='background:#0d1117;border:1px solid #30363d;border-left:3px solid {bar};"
        f"border-radius:7px;padding:11px 14px;margin:7px 0;font-size:0.86rem;line-height:1.7;'>"
        + "<br>".join(rows) + "</div>",
        unsafe_allow_html=True,
    )
    return True
