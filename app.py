with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    btl = snap.get("bottleneck_discovery", {})
    narr = snap.get("narrative_discovery", {})

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
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;">
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

    def render_cards(ticker_list, names_map, signal_type, per_row=2):
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

    # ═══════════════════════════════════════════════════════════════════════
    # BOTTLENECK FILTER — Explicit per market, ga nyampur
    # ═══════════════════════════════════════════════════════════════════════
    def is_us_ticker(tk):
        return not any(x in tk for x in [".JK", "=X", "-USD", "=F", "URA"]) and tk not in ["^JKSE"]

    def is_ihsg_ticker(tk):
        return ".JK" in tk or tk == "^JKSE"

    def is_fx_ticker(tk):
        return "=X" in tk

    def is_comm_ticker(tk):
        return "=F" in tk or tk == "URA"

    def is_crypto_ticker(tk):
        return "-USD" in tk

    def render_bottleneck_filtered(filter_fn, market_name):
        if not btl:
            st.caption("No bottleneck data")
            return
        if btl.get("summary"): st.caption(btl["summary"])
        basket = btl.get("front_run_basket", [])
        # Filter by ticker pattern
        filtered = [item for item in basket if filter_fn(item.get("ticker", ""))]
        if not filtered:
            st.caption(f"No {market_name} bottleneck detected")
            return
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

    # ═══════════════════════════════════════════════════════════════════════
    # MASTER BOARD FILTER — Cuma ticker dari market itu
    # ═══════════════════════════════════════════════════════════════════════
    def render_master_filtered(long_key, short_key, color_long, color_short, filter_fn, market_name):
        all_tickers = []
        # Regime tickers for this market only
        for t in tickers.get(long_key, [])[:4]:
            all_tickers.append((t, "Long", color_long))
        if short_key:
            for t in tickers.get(short_key, [])[:4]:
                all_tickers.append((t, "Short", color_short))
        # Bottleneck filtered
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:6]:
                tk = item.get("ticker","—")
                if filter_fn(tk) and tk not in [x[0] for x in all_tickers]:
                    all_tickers.append((tk, "Adap", "#58a6ff"))
        # Narrative filtered
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:3]:
                for b in n.get("primary_beneficiaries", [])[:3]:
                    if filter_fn(b) and b not in [x[0] for x in all_tickers]:
                        all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))
        else:
            st.caption(f"No {market_name} tickers")

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(us_longs, names, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(us_shorts, names, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")])
        st.markdown("**📊 Sector Leadership (Top 5)**")
        render_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_us_ticker, "US")
        st.markdown("**📋 Master Board**")
        render_master_filtered("us_longs", "us_shorts", "#3fb950", "#f85149", is_us_ticker, "US")

    # ══════ 🇮🇩 IHSG (Long Only) ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
        st.markdown("**📍 NOW — LONG**")
        render_cards(ihsg_longs, names_ihsg, "long", 3)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_ihsg_ticker, "IHSG")
        st.markdown("**📋 Master Board**")
        render_master_filtered("ihsg_buys", None, "#fb923c", "#f85149", is_ihsg_ticker, "IHSG")

    # ══════ 💱 FX (Long + Short) ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fx_shorts = tickers.get("fx_shorts", [])
        names_fx = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(fx_longs, names_fx, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(fx_shorts, names_fx, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("EURUSD=X","EUR/USD"),("USDJPY=X","USD/JPY"),("AUDUSD=X","AUD/USD"),("USDIDR=X","USD/IDR"),("UUP","DXY")])
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_fx_ticker, "FX")
        st.markdown("**📋 Master Board**")
        render_master_filtered("fx_longs", "fx_shorts", "#58a6ff", "#f85149", is_fx_ticker, "FX")

    # ══════ 🛢️ COMMODITIES (Long + Short) ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        comm_shorts = tickers.get("commodity_shorts", [])
        names_comm = {"CL=F":"WTI Oil","GC=F":"Gold","HG=F":"Copper","SI=F":"Silver","NG=F":"Nat Gas","BZ=F":"Brent","URA":"Uranium"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(comm_longs, names_comm, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(comm_shorts, names_comm, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("CL=F","WTI Oil"),("GC=F","Gold"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas")])
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_comm_ticker, "Commodities")
        st.markdown("**📋 Master Board**")
        render_master_filtered("commodity_longs", "commodity_shorts", "#fb923c", "#f85149", is_comm_ticker, "Commodities")

    # ══════ 🔐 CRYPTO (Long + Short) ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        cry_shorts = tickers.get("crypto_shorts", [])
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(cry_longs, names_cry, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(cry_shorts, names_cry, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_crypto_ticker, "Crypto")
        st.markdown("**📋 Master Board**")
        render_master_filtered("crypto_longs", "crypto_shorts", "#a371f7", "#f85149", is_crypto_ticker, "Crypto")

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

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
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
    
    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()