with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    tr_label = f"{structural_quad}→{q.get('next_quad', '?')}" if q.get('next_quad') else "No transition"
    narr = snap.get("narrative_discovery", {})
    btl = snap.get("bottleneck_discovery", {})

    def ret_n(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    def get_ret(s, n):
        r = ret_n(s, n)
        return f"{r:+.1%}" if r == r else "—"

    def ticker_card(tk, name, ret1m, ret3m, signal):
        color = "#3fb950" if signal == "long" else "#f85149" if signal == "short" else "#d29922"
        icon = "▲" if signal == "long" else "▼" if signal == "short" else "⚡"
        return f"""
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;min-width:140px;flex:1;">
          <div>
            <div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div>
            <div style="font-size:10px;color:#8b949e;">{name}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:{color};font-weight:700;">{icon} {ret1m}</div>
            <div style="font-size:9px;color:#8b949e;">3M: {ret3m}</div>
          </div>
        </div>
        """

    def render_ticker_cards(ticker_list, names_map, signal_type, per_row=2):
        if not ticker_list: return
        cards = []
        for t in ticker_list:
            s = prices.get(t)
            cards.append(ticker_card(t, names_map.get(t, t), get_ret(s, 21), get_ret(s, 63), signal_type))
        for i in range(0, len(cards), per_row):
            row = cards[i:i+per_row]
            _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    def render_heatmap(assets_list):
        if not prices: return
        heat_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for tk, name in assets_list:
            s = prices.get(tk)
            if s is not None:
                r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                c = "#1a4d2e" if r1 > 0.05 else "#2d5a3d" if r1 > 0 else "#5c1a1a" if r1 < -0.05 else "#3d1a1a" if r1 < 0 else "#2d3748"
                txt = "#4ade80" if r1 > 0 else "#f87171" if r1 < 0 else "#a0aec0"
                heat_html.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
        heat_html.append('</div>')
        _h("".join(heat_html))

    def render_sector_bars():
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

    def render_bottleneck(market_filter):
        if not btl: 
            st.caption("No bottleneck data")
            return
        if btl.get("summary"): st.caption(btl["summary"])
        basket = btl.get("front_run_basket", [])
        filtered = [item for item in basket if market_filter.lower() in item.get("market", "").lower() or market_filter.lower() in item.get("sector", "").lower()]
        if not filtered: filtered = basket[:6]
        if filtered:
            b_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for item in filtered[:8]:
                tk = item.get("ticker","—")
                sec = item.get("sector","—")[:10]
                score = item.get("bottleneck_score",0)
                stage = item.get("stage","—")
                stage_c = {"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stage, "#8b949e")
                b_html.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:9px;color:#8b949e;">{sec}</div><div style="font-size:10px;color:{stage_c};">{stage} · {score:.2f}</div></div>')
            b_html.append('</div>')
            _h("".join(b_html))

    def render_master_board(market_side):
        all_tickers = []
        side_map = {"us": [("Long","us_longs","#3fb950"),("Short","us_shorts","#f85149")],
                    "ihsg": [("Long","ihsg_buys","#fb923c")],
                    "fx": [("Long","fx_longs","#58a6ff"),("Short","fx_shorts","#f85149")],
                    "comm": [("Long","commodity_longs","#fb923c"),("Short","commodity_shorts","#f85149")],
                    "crypto": [("Long","crypto_longs","#a371f7"),("Short","crypto_shorts","#f85149")]}
        for side_name, key, color in side_map.get(market_side, []):
            for t in tickers.get(key, [])[:3]:
                all_tickers.append((t, side_name, color))
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:3]:
                all_tickers.append((item.get("ticker","—"), "Adap", "#58a6ff"))
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:2]:
                for b in n.get("primary_beneficiaries", [])[:2]:
                    all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))

    def render_market_section(title, long_list, short_list, fr_long, fr_short, names_map, heat_assets, market_key):
        st.markdown(f"**📍 NOW — LONG**")
        if long_list:
            render_ticker_cards(long_list, names_map, "long", 2)
        else: st.caption("No longs")
        
        if short_list:
            st.markdown("**📍 NOW — SHORT**")
            render_ticker_cards(short_list, names_map, "short", 2)
        
        if fr_long or fr_short:
            st.divider()
            c_fr_l, c_fr_s = st.columns(2)
            with c_fr_l:
                if fr_long:
                    st.markdown("**⚡ ACCUMULATE**")
                    render_ticker_cards(fr_long, names_map, "fr", 2)
            with c_fr_s:
                if fr_short:
                    st.markdown("**⚡ FADE**")
                    render_ticker_cards(fr_short, names_map, "short", 2)
        
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap(heat_assets)
        
        if market_key == "us":
            st.markdown("**📊 Sector Leadership (Top 5)**")
            render_sector_bars()
        
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck(market_key)
        
        st.markdown("**📋 Master Board**")
        render_master_board(market_key)

    if fw in ("now", "1-2 weeks", "1-2w", "1-2W"):
        _h(f"""
        <div style="background:#1a3a2a;border:1px solid #3fb950;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#3fb950;font-size:13px;font-weight:700;">⚡ FRONT-RUN WINDOW: {fw.upper()} · {tr_label}</div>
          <div style="color:#c9d1d9;font-size:12px;margin-top:4px;">{transition.get('front_run_rationale', '—')}</div>
        </div>
        """)

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        fr_us_long = us_longs[:3] if fw in ("now", "1-2 weeks") else []
        fr_us_short = us_shorts[:2] if fw in ("now", "1-2 weeks") else []
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis"}
        heat = [("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")]
        render_market_section("US", us_longs, us_shorts, fr_us_long, fr_us_short, names, heat, "us")

    # ══════ 🇮🇩 IHSG (Long Only) ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        fr_ihsg = ihsg_longs[:3] if fw in ("now", "1-2 weeks") else []
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
        heat_ihsg = [("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")]
        render_market_section("IHSG", ihsg_longs, [], fr_ihsg, [], names_ihsg, heat_ihsg, "ihsg")

    # ══════ 💱 FX (Long + Short) ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fx_shorts = tickers.get("fx_shorts", [])  # Add to regime_tickers if needed
        fr_fx_long = fx_longs[:2] if fw in ("now", "1-2 weeks") else []
        fr_fx_short = fx_shorts[:2] if fw in ("now", "1-2 weeks") else []
        names_fx = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY"}
        heat_fx = [("EURUSD=X","EUR/USD"),("USDJPY=X","USD/JPY"),("AUDUSD=X","AUD/USD"),("USDIDR=X","USD/IDR"),("UUP","DXY")]
        render_market_section("FX", fx_longs, fx_shorts, fr_fx_long, fr_fx_short, names_fx, heat_fx, "fx")

    # ══════ 🛢️ COMMODITIES (Long + Short) ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        comm_shorts = tickers.get("commodity_shorts", [])  # Add to regime_tickers if needed
        fr_comm_long = comm_longs[:3] if fw in ("now", "1-2 weeks") else []
        fr_comm_short = comm_shorts[:2] if fw in ("now", "1-2 weeks") else []
        names_comm = {"CL=F":"WTI Oil","GC=F":"Gold","HG=F":"Copper","SI=F":"Silver","NG=F":"Nat Gas","BZ=F":"Brent","URA":"Uranium"}
        heat_comm = [("CL=F","WTI Oil"),("GC=F","Gold"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas")]
        render_market_section("Commodities", comm_longs, comm_shorts, fr_comm_long, fr_comm_short, names_comm, heat_comm, "comm")

    # ══════ 🔐 CRYPTO (Long + Short) ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        cry_shorts = tickers.get("crypto_shorts", [])  # Add to regime_tickers if needed
        fr_cry_long = cry_longs[:2] if fw in ("now", "1-2 weeks") and vix < 22 else []
        fr_cry_short = cry_shorts[:2] if fw in ("now", "1-2 weeks") and vix < 22 else []
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
        heat_cry = [("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")]
        render_market_section("Crypto", cry_longs, cry_shorts, fr_cry_long, fr_cry_short, names_cry, heat_cry, "crypto")

with tabs[2]:
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw: st.markdown("**Regime State**"); st.json(q)
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {}); m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(k, 0.0); mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad; is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else: st.info("No probability data")
    st.divider(); st.markdown("**Raw Macro Indicators**")
    rows = []
    for lbl, key, note in [("INDPRO YoY","indpro_yoy","▲" if f.get("indpro_acc") else "▼"),("CPI YoY","cpi_yoy","▲" if f.get("cpi_acc") else "▼"),("Core PCE","corepce_yoy","▲" if f.get("corepce_acc") else "▼"),("VIX","vix_last",""),("HY OAS","hy_oas",f"Δ1M: {f.get('hy_oas_1m',0):+.0f}bps"),("Policy Score","policy_score","+ve=cutting")]:
        val = f.get(key)
        if val is not None:
            try:
                v = float(val) if not isinstance(val, bool) else float("nan")
                if v == v: rows.append({"Indicator": lbl, "Value": f"{v:+.2f}" if abs(v) < 100 else f"{v:.2f}", "Note": note})
            except: pass
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    
    fred_ok = st.session_state.get("_fred_api_ok", False)
    fred_err = st.session_state.get("_fred_api_err", "")
    
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0); missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else: st.error("FRED metadata unavailable")

    if not fred_ok:
        st.error(f"🚨 FRED API Direct Test FAILED: {fred_err}")
        st.info("Causes: (1) Key invalid/expired, (2) Streamlit Cloud blocks FRED, (3) Rate limited.")
    else:
        st.success("✅ FRED API Direct Test PASSED — but loader still 0. Check fred_loader.py cache logic.")

    if rally:
        st.divider(); st.markdown("**Most Hated Rally — Checklist**")
        st.caption(f"Stage: {rally.get('stage', '?')} | Action: {rally.get('action', '?')}")
        for item in rally.get("checklist", []):
            ok = item.get("value", False)
            icon = "✅" if ok else "⬜"
            color = "#3fb950" if ok else "#8b949e"
            raw = item.get("raw", 0)
            _h(f'<div style="color:{color};font-size:13px;margin:4px 0;">{icon} {item.get("item", "—")} <span style="color:#8b949e;">({raw:.3f})</span></div>')
        if rally_clear >= 4: st.success("All 4 cleared")
        else: st.info(f"{rally_clear}/4 cleared")

    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()