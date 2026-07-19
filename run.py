"""run.py — War Room OS end-to-end runner (gcfis orchestrator = brain, one pipeline).

Drop this + data_layer.py + dashboard.html into your warroom_pro_full root (next to gcfis/),
then:

    pip install -r requirements.txt          # yfinance, statsmodels, hmmlearn, etc.
    python run.py                            # live data on your machine → desk_data.json + dashboard.html
    python run.py --synthetic                # offline: proves the pipeline runs (no fabricated edge)
    python run.py --markets us,crypto        # subset

Output:
    desk_data.json   — structured desk (systemic macro + per-market setups + evidence lineage)
    dashboard_live.html — Capital Intelligence Map populated with the run

HONEST: setups only appear where the conviction gate is met. On synthetic/noise data that is
often zero rows — that is correct behavior (the gate refuses to fabricate). Edge is only real
where run_validation.py --cache clears perm_p<0.05 AND DSR>=0.95 on YOUR data.
"""
from __future__ import annotations
import os, sys, json, argparse, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)          # data_layer.py + gcfis/ live here
import data_layer as DL

from gcfis.orchestrator import run_gcfis
from gcfis.markets import market_of, is_long_only, MARKETS
from gcfis.engines.entry import run_entry
from gcfis.engines.asymmetric_discovery import run_discovery
from gcfis.market_drivers import read_all as market_bias


def _num(x, d=None):
    try:
        f = float(x)
        return round(f, 3)
    except Exception:
        return d


def _setup_from_ranking(entry, price, direction):
    """Enrich a ranking row (ticker/action/conviction/reason) with entry/stop/target via entry.py."""
    tk = entry.get("ticker")
    lo = is_long_only(tk)
    e = run_entry(price, direction, long_only=lo) if price is not None and len(price) > 60 else {}
    return {
        "tk": tk, "act": entry.get("action", ""), "dir": direction,
        "conv": _num(entry.get("conviction"), 0),
        "e": _num(e.get("entry_px"), None), "s": _num(e.get("stop"), None),
        "t": _num(e.get("target"), None), "rr": _num(e.get("rr"), None),
        "ty": e.get("entry_type", ""), "gm": e.get("gamma_regime", ""),
        "valid": bool(e.get("valid", False)), "warn": e.get("warning", ""),
        "why": entry.get("reason", ""),
    }



def _load_grades():
    """The walk-forward grade card (metric_grades.json). The UI emits a metric as a number only
    when its grade is VALIDATED; PARTIAL emits banded; REJECTED/FEED_GATED emit '—'. Regenerate
    with: python walkforward_validate.py"""
    import os, json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metric_grades.json")
    try:
        with open(p) as f: return json.load(f)
    except Exception:
        return {}



def _load_reference_data():
    """Curated structural maps. They are never presented as live flow observations."""
    out = {}
    for key, rel in (("chain_reactions", "data/chain_reactions.json"),
                     ("bottlenecks", "data/bottleneck_reference.json"),
                     ("ihsg_conglomerates", "data/ihsg_conglomerates.json")):
        path = os.path.join(HERE, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                out[key] = json.load(fh)
        except Exception as exc:
            out[key] = {"_error": f"{type(exc).__name__}: {exc}"}
    return out


def _data_health(data):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = []
    price_markets = data.get("prices") or {}
    for name, raw in (data.get("sources") or {}).items():
        text = str(raw)
        low = text.lower()
        records = len((price_markets.get(name) or {})) if isinstance(price_markets, dict) else 0
        if (("synthetic" in low and "disabled" not in low) or "test-only" in low):
            state = "SYNTHETIC_TEST"
        elif records > 0:
            state = "LIVE"
        elif "offline" in low or ("disabled" in low and "synthetic disabled" not in low):
            state = "OFFLINE"
        else:
            state = "NO_DATA"
        rows.append({
            "provider": name,
            "dataset": "market_data",
            "state": state,
            "observed": state == "LIVE",
            "records": records,
            "fetched_at": now,
            "stale_after_seconds": 90,
            "note": text,
            "data_semantics": "OBSERVED_PRICE_OR_VOLUME" if state == "LIVE" else ("TEST_ONLY" if state == "SYNTHETIC_TEST" else "MISSING"),
        })
    fred = str(data.get("fred_source") or "unavailable")
    fred_live = bool(data.get("fred"))
    rows.append({
        "provider": "FRED",
        "dataset": "macro",
        "state": "LIVE" if fred_live else "NO_DATA",
        "observed": fred_live,
        "fetched_at": now,
        "stale_after_seconds": 3600,
        "note": fred,
        "data_semantics": "OFFICIAL_MACRO_SERIES" if fred_live else "MISSING",
    })
    feed_status = (data.get("feeds") or {}).get("_status") or {}
    for name, raw in feed_status.items():
        text = str(raw)
        low = text.lower()
        if any(x in low for x in ("offline", "disabled")):
            state = "OFFLINE"
        elif any(x in low for x in ("failed", "absent", "unavailable", "no_data")):
            state = "NO_DATA"
        elif "live" in low or "snapshot" in low:
            state = "LIVE"
        else:
            state = "NO_DATA"
        rows.append({
            "provider": name,
            "dataset": "specialized",
            "state": state,
            "observed": state == "LIVE",
            "fetched_at": now,
            "stale_after_seconds": 3600 if "snapshot" in low else 180,
            "note": text,
            "data_semantics": "SEE_FEED_METADATA",
        })
    live = sum(1 for r in rows if r["state"] == "LIVE")
    synthetic = sum(1 for r in rows if r["state"] == "SYNTHETIC_TEST")
    overall = "LIVE" if live >= 2 else ("PARTIAL" if live else ("SYNTHETIC_TEST" if synthetic else "NO_DATA"))
    return {"overall": overall, "live_count": live, "total_count": len(rows), "sources": rows, "checked_at": now}


def _empty_desk(data, reason="No live price universe or benchmark was available."):
    markets = {}
    for m in data.get("markets") or []:
        cfg = MARKETS.get(m, {"label": m, "long_only": False, "drivers": []})
        markets[m] = {"label": cfg.get("label", m), "long_only": cfg.get("long_only", False),
                      "drivers": cfg.get("drivers", []), "bias": "NO_DATA",
                      "funnel": {"universe": 0, "eliminated": 0, "setups": 0}, "setups": []}
    return {
        "meta": {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                 "source": data.get("overall_source", "NO_DATA"), "sources": data.get("sources", {}),
                 "fred_source": data.get("fred_source", "NO_DATA"), "universe_n": 0,
                 "note": reason, "feeds_status": (data.get("feeds") or {}).get("_status", {})},
        "systemic": {"quad": None, "quad_name": "NO_DATA", "growth_roc": None, "infl_roc": None,
                     "liquidity": "NO_DATA", "fragility": "NO_DATA", "shock_prob": "NO_DATA",
                     "cross_asset": "NO_DATA", "defer_longs": None, "rotation_in": [], "rotation_out": []},
        "regime_tf": {"state": "NO_DATA"}, "regional": {}, "grades": _load_grades(),
        "markets": markets, "alpha": [], "desk_picks": {}, "feeds": {},
        "macro_observations": _macro_observations(data), "market_breadth": _market_breadth(data),
        "rotation_snapshot": _rotation_snapshot(data),
        "data_health": _data_health(data), "reference": _load_reference_data(),
        "institutional": {"overall_state": "NOT_LOADED", "statuses": [], "events": [],
                          "options_flow": [], "dark_pool": [], "sec_filings": [], "smart_money": [], "arkham_transfers": []},
    }


def _series_summary(series):
    """Compact latest observation summary for JSON/UI; never forward-fills missing values."""
    try:
        import pandas as pd
        x = pd.to_numeric(pd.Series(series), errors="coerce").dropna().sort_index()
        if x.empty:
            return None
        latest = float(x.iloc[-1]); previous = float(x.iloc[-2]) if len(x) > 1 else None
        def chg(n):
            if len(x) <= n or float(x.iloc[-n-1]) == 0: return None
            return (latest / float(x.iloc[-n-1]) - 1.0) * 100.0
        idx = x.index[-1]
        return {
            "timestamp": str(idx), "value": latest, "previous": previous,
            "change_abs": latest - previous if previous is not None else None,
            "change_1_period_pct": chg(1), "change_4_period_pct": chg(4),
            "observations": int(len(x)), "observed": True,
        }
    except Exception:
        return None


def _macro_observations(data):
    out = {}
    for sid, series in (data.get("fred") or {}).items():
        summary = _series_summary(series)
        if summary is not None:
            summary.update({"series_id": sid, "provider": "FRED", "state": "LIVE"})
            out[sid] = summary
    return out


def _market_breadth(data):
    """Breadth from the actually loaded universe; coverage is always disclosed."""
    import pandas as pd
    output = {}
    for market, rows in (data.get("prices") or {}).items():
        if market.startswith("_") or not isinstance(rows, dict):
            continue
        stats = []
        for ticker, raw in rows.items():
            try:
                if isinstance(raw, pd.DataFrame):
                    series = raw["Close"] if "Close" in raw.columns else raw.iloc[:, -1]
                else:
                    series = raw
                x = pd.to_numeric(pd.Series(series), errors="coerce").dropna().sort_index()
                if len(x) < 22:
                    continue
                last = float(x.iloc[-1]); prev = float(x.iloc[-2])
                row = {
                    "ticker": ticker, "ret_1d": (last / prev - 1) * 100 if prev else None,
                    "ret_5d": (last / float(x.iloc[-6]) - 1) * 100 if len(x) >= 6 and x.iloc[-6] else None,
                    "ret_20d": (last / float(x.iloc[-21]) - 1) * 100 if len(x) >= 21 and x.iloc[-21] else None,
                    "above_20d": last > float(x.tail(20).mean()),
                    "above_50d": last > float(x.tail(50).mean()) if len(x) >= 50 else None,
                    "above_200d": last > float(x.tail(200).mean()) if len(x) >= 200 else None,
                    "new_20d_high": last >= float(x.tail(20).max()),
                    "new_20d_low": last <= float(x.tail(20).min()),
                }
                stats.append(row)
            except Exception:
                continue
        n = len(stats)
        def ratio(key):
            vals = [r[key] for r in stats if r.get(key) is not None]
            return round(100 * sum(bool(v) for v in vals) / len(vals), 2) if vals else None
        def med(key):
            vals = [float(r[key]) for r in stats if r.get(key) is not None]
            return round(float(pd.Series(vals).median()), 4) if vals else None
        adv = sum(1 for r in stats if (r.get("ret_1d") or 0) > 0)
        dec = sum(1 for r in stats if (r.get("ret_1d") or 0) < 0)
        output[market] = {
            "provider": "derived_from_loaded_prices", "state": "LIVE" if n else "NO_DATA",
            "coverage": n, "advance": adv, "decline": dec, "unchanged": max(0, n-adv-dec),
            "advance_pct": round(100*adv/n,2) if n else None,
            "above_20d_pct": ratio("above_20d"), "above_50d_pct": ratio("above_50d"),
            "above_200d_pct": ratio("above_200d"), "new_20d_high_pct": ratio("new_20d_high"),
            "new_20d_low_pct": ratio("new_20d_low"), "median_ret_1d_pct": med("ret_1d"),
            "median_ret_5d_pct": med("ret_5d"), "median_ret_20d_pct": med("ret_20d"),
            "constituents": stats,
            "semantics": "Breadth is only over the loaded War Room universe, not the full exchange unless that universe is complete.",
        }
    return output


def _rotation_snapshot(data):
    """Cross-asset relative return snapshot from live loaded proxy prices."""
    import pandas as pd
    rows = []
    pools = {}
    pools.update((data.get("prices") or {}).get("_proxy") or {})
    pools.update(data.get("proxies") or {})
    for ticker, raw in pools.items():
        try:
            x = pd.to_numeric(pd.Series(raw), errors="coerce").dropna().sort_index()
            if len(x) < 21: continue
            last=float(x.iloc[-1])
            def ret(n): return (last/float(x.iloc[-n-1])-1)*100 if len(x)>n and x.iloc[-n-1] else None
            rows.append({"ticker":ticker,"ret_1d_pct":ret(1),"ret_5d_pct":ret(5),"ret_20d_pct":ret(20),"ret_60d_pct":ret(60),"timestamp":str(x.index[-1]),"observed":True})
        except Exception:
            continue
    ranked = sorted(rows, key=lambda r: (r.get("ret_20d_pct") is not None, r.get("ret_20d_pct") or -1e9), reverse=True)
    for i,row in enumerate(ranked,1): row["rank_20d"] = i
    return {"state":"LIVE" if ranked else "NO_DATA","provider":"derived_from_loaded_prices","rows":ranked,
            "semantics":"Relative price rotation is confirmation, not a dollar-flow ledger."}


def _driver_series(data):
    """Map already-loaded feeds → the driver matrix's SEMANTIC ids. Only the ones we can verify get
    wired; everything else stays absent → NO_DATA (honest). FRED + prices are already fetched — the
    matrix was simply never handed them (it ran on None). This is that missing wire, nothing fabricated."""
    import pandas as pd
    fred = data.get("fred") or {}
    px = {}
    for m in ("_proxy", "fx", "commodity", "us"):
        px.update((data.get("prices", {}) or {}).get(m, {}) or {})
    out = {}
    if fred.get("DFII10") is not None: out["TIPS10Y"] = fred["DFII10"]              # real 10Y (TIPS)
    if fred.get("BAMLH0A0HYM2") is not None: out["HY_OAS"] = fred["BAMLH0A0HYM2"]   # HY credit spread
    try:  # Fed net liquidity = balance sheet − TGA − RRP
        w, t, r = fred.get("WALCL"), fred.get("WTREGEN"), fred.get("RRPONTSYD")
        if w is not None and t is not None and r is not None:
            df = pd.concat([pd.Series(w), pd.Series(t), pd.Series(r)], axis=1).ffill().dropna()
            if len(df) > 40: out["FEDLIQ"] = df.iloc[:, 0] - df.iloc[:, 1] - df.iloc[:, 2]
    except Exception:
        pass
    for k in ("DX-Y.NYB", "UUP"):                                                   # dollar index (real price)
        if px.get(k) is not None: out["DXY"] = px[k]; break
    return out


def _quick_pct_change(series, periods):
    try:
        import pandas as pd
        x = pd.to_numeric(pd.Series(series), errors="coerce").dropna().sort_index()
        if len(x) <= periods or float(x.iloc[-periods-1]) == 0:
            return None
        return (float(x.iloc[-1]) / float(x.iloc[-periods-1]) - 1.0) * 100.0
    except Exception:
        return None


def build_fast_desk(data, top_per_market=12):
    """Latency-bounded first paint built from observed prices/macro only.

    The full GCFIS research pipeline runs later in the expanded worker plane. This function avoids
    blocking the initial dashboard on heavy model fitting while preserving honest NO_DATA/NO_SIGNAL
    semantics and the same JSON contract consumed by the UI.
    """
    prices = data.get("prices") or {}
    union = {t: v for m in (data.get("markets") or []) for t, v in (prices.get(m) or {}).items()}
    if not union:
        return _empty_desk(data)

    breadth = _market_breadth(data)
    rotation = _rotation_snapshot(data)
    macro = _macro_observations(data)
    fred = data.get("fred") or {}

    # Direction is rate-of-change context, not a calibrated forecast.
    growth_parts = [x for x in (_quick_pct_change(fred.get("INDPRO"), 12),
                                _quick_pct_change(fred.get("RSAFS"), 12),
                                _quick_pct_change(fred.get("PAYEMS"), 12)) if x is not None]
    growth_level = sum(growth_parts) / len(growth_parts) if growth_parts else None
    cpi_source = fred.get("CPI") if fred.get("CPI") is not None else fred.get("CPIAUCSL")
    cpi_yoy = _quick_pct_change(cpi_source, 12)
    cpi_prev = None
    try:
        import pandas as pd
        cpi = pd.to_numeric(pd.Series(cpi_source), errors="coerce").dropna().sort_index()
        if len(cpi) > 15 and float(cpi.iloc[-16]) != 0:
            cpi_prev = (float(cpi.iloc[-4]) / float(cpi.iloc[-16]) - 1.0) * 100.0
    except Exception:
        pass
    inflation_roc = cpi_yoy - cpi_prev if cpi_yoy is not None and cpi_prev is not None else None
    growth_roc = growth_level
    if growth_roc is None or inflation_roc is None:
        quad, quad_name = None, "PARTIAL_MACRO"
    elif growth_roc >= 0 and inflation_roc < 0:
        quad, quad_name = 1, "Goldilocks"
    elif growth_roc >= 0 and inflation_roc >= 0:
        quad, quad_name = 2, "Reflation"
    elif growth_roc < 0 and inflation_roc >= 0:
        quad, quad_name = 3, "Stagflation"
    else:
        quad, quad_name = 4, "Deflation"

    liq = data.get("treasury_liquidity") or {}
    liq_value = liq.get("bias") if liq.get("ok") else liq.get("state") or "NO_DATA"
    markets = {}
    all_setups = []
    for market in data.get("markets") or []:
        cfg = MARKETS.get(market, {"label": market, "long_only": False, "drivers": []})
        frames = (data.get("ohlcv") or {}).get(market) or {}
        setups = []
        if frames:
            try:
                from price_setups import price_signal_setups
                setups = price_signal_setups(frames, top=top_per_market) or []
            except Exception:
                setups = []
        b = breadth.get(market) or {}
        adv, above = b.get("advance_pct"), b.get("above_50d_pct")
        if adv is None and above is None:
            bias = "NO_DATA"
        elif (adv or 0) >= 55 and (above is None or above >= 50):
            bias = "LEAN_LONG"
        elif (adv or 100) <= 45 and (above is None or above < 50):
            bias = "WAIT" if cfg.get("long_only") else "LEAN_SHORT"
        else:
            bias = "NEUTRAL"
        markets[market] = {
            "label": cfg.get("label", market), "long_only": bool(cfg.get("long_only")),
            "drivers": cfg.get("drivers", []), "bias": bias,
            "data_state": b.get("state") or ("LIVE" if prices.get(market) else "NO_DATA"),
            "funnel": {"universe": len(prices.get(market) or {}), "eliminated": 0, "setups": len(setups)},
            "setups": setups,
        }
        all_setups.extend(({**row, "market": market} for row in setups))

    ranked_rotation = rotation.get("rows") or []
    systemic = {
        "quad": quad, "quad_name": quad_name, "growth_roc": _num(growth_roc),
        "infl_roc": _num(inflation_roc), "inflation_yoy": _num(cpi_yoy),
        "liquidity": liq_value, "liquidity_detail": liq,
        "fragility": "RESEARCH_PENDING", "shock_prob": "RESEARCH_PENDING",
        "cross_asset": rotation.get("state") or "NO_DATA", "defer_longs": None,
        "rotation_in": [r.get("ticker") for r in ranked_rotation[:3] if r.get("ticker")],
        "rotation_out": [r.get("ticker") for r in ranked_rotation[-3:] if r.get("ticker")],
        "semantics": "FAST_CONTEXT_ONLY; expanded research plane replaces this when available.",
    }
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "meta": {"generated": now, "source": data.get("overall_source", "NO_DATA"),
                 "sources": data.get("sources", {}), "fred_source": data.get("fred_source", "NO_DATA"),
                 "universe_n": len(union), "note": "Latency-bounded observed-data first paint.",
                 "feeds_status": (data.get("feeds") or {}).get("_status", {})},
        "systemic": systemic, "regime_tf": {"state": "FAST_CONTEXT", "quad": quad},
        "regional": {}, "grades": _load_grades(), "markets": markets, "alpha": [],
        "desk_picks": {"fast_context": sorted(all_setups, key=lambda r: float(r.get("conv") or 0), reverse=True)[:20]},
        "feeds": {}, "macro_observations": macro, "market_breadth": breadth,
        "rotation_snapshot": rotation, "data_health": _data_health(data),
        "reference": _load_reference_data(),
        "institutional": {"overall_state": "NOT_LOADED", "statuses": [], "events": [],
                          "options_flow": [], "dark_pool": [], "sec_filings": [], "smart_money": [], "arkham_transfers": []},
    }

def build_desk(data, top_per_market=12):
    import pandas as _pd
    def _c1d(x):
        if isinstance(x, _pd.DataFrame):
            for c in ("Close", "close", "Adj Close"):
                if c in x.columns: return x[c]
            return x.iloc[:, 3] if x.shape[1] > 3 else x.iloc[:, 0]
        return x
    prices, bench = data["prices"], _c1d(data["bench"])
    union = {}
    for m in data["markets"]:
        for _t, _v in (prices.get(m, {}) or {}).items():
            union[_t] = _c1d(_v)
    if bench is None or not union:
        return _empty_desk(data)

    from macro_inputs import assemble
    macro_in = assemble(data.get("fred"), union, bench, data.get("vix"))
    _ohlcv = {}                                   # flatten per-market OHLCV → entry engine's real risk range
    for _m, _d in (data.get("ohlcv") or {}).items():
        _ohlcv.update(_d or {})
    out = run_gcfis(union, bench, regime_posterior={"chop": 1.0}, ohlcv=_ohlcv, **macro_in)
    # multi-timeframe regime (structural/monthly/weekly/daily + posture)
    try:
        from regime_multitf import multi_timeframe_regime
        _allpx = {}
        import pandas as _pd
        def _close(x):
            if isinstance(x, _pd.DataFrame):
                for c in ("Close","close"):
                    if c in x.columns: return x[c]
                return x.iloc[:, 3] if x.shape[1] > 3 else x.iloc[:, 0]
            return x
        for _mk in data.get("prices", {}).values():
            if isinstance(_mk, dict):
                for _t, _v in _mk.items(): _allpx[_t] = _close(_v)
        if data.get("bench") is not None and "SPY" not in _allpx:
            _allpx["SPY"] = _close(data["bench"])
        _regime_tf = multi_timeframe_regime(data.get("fred"), _allpx)
    except Exception as _e:
        _regime_tf = {"error": str(_e)}
    # per-region regime from REAL price action (replaces hardcoded "IHSG Bull" mock row)
    try:
        from regional_regime import regional_regime
        _regional = regional_regime({**_allpx, **(data.get("proxies") or {})})
    except Exception as _e:
        _regional = {}
    rk = out.get("ranking", {})
    sysm = out.get("systemic", {})

    # ── systemic macro (Mission Control + Macro tab) ──
    fm = sysm.get("forward_macro", {}) or {}
    liq = sysm.get("liquidity", {}) or {}
    fr = sysm.get("fragility", {}) or {}
    sh = sysm.get("shock", {}) or {}
    xa = sysm.get("cross_asset", {}) or {}
    fl = sysm.get("flow", {}) or {}
    systemic = {
        "quad": fm.get("forward_quad"), "quad_name": fm.get("quad_name"),
        "growth_roc": _num(fm.get("GROC")), "infl_roc": _num(fm.get("IROC")),
        "liquidity": (data.get("treasury_liquidity", {}).get("bias")
                      if data.get("treasury_liquidity", {}).get("ok")
                      else ("expanding" if liq.get("expanding") else
                            (liq.get("reason") if liq.get("reason") and "no " not in str(liq.get("reason")).lower() else "NO_DATA"))),
        "liquidity_detail": data.get("treasury_liquidity", {}),
        "fragility": _num(fr.get("fragility")) if fr.get("ok") else fr.get("reason"),
        "shock_prob": _num(sh.get("shock_prob")) if sh.get("ok") else sh.get("reason"),
        "cross_asset": xa.get("regime"), "defer_longs": xa.get("defer_longs"),
        "rotation_in": fl.get("rotating_in", []), "rotation_out": fl.get("rotating_out", []),
    }

    # ── per-market setups (group ranking by market) ──
    long_rows = rk.get("master_long", [])
    short_rows = rk.get("master_short", [])
    spot_rows = rk.get("master_spot", [])
    eliminated = {e.get("ticker"): e.get("reason", "eliminated") for e in rk.get("eliminated", []) if isinstance(e, dict)}
    bias = market_bias(_driver_series(data))  # driver matrix now fed real FRED+price series (unmapped drivers → NO_DATA, honest)

    markets = {}
    _MKDEF = {"label": None, "long_only": False, "drivers": []}
    for m in data["markets"]:
        mk_cfg = MARKETS.get(m, {**_MKDEF, "label": m})
        pm = prices.get(m) or {}            # ← safe: a failed-fetch market (e.g. idx down) no longer KeyErrors
        univ = list(pm.keys())
        setups = []
        for row in long_rows:
            if market_of(row.get("ticker")) == m:
                setups.append(_setup_from_ranking(row, pm.get(row["ticker"]), "long"))
        for row in short_rows:
            if market_of(row.get("ticker")) == m and not mk_cfg["long_only"]:
                setups.append(_setup_from_ranking(row, pm.get(row["ticker"]), "short"))
        for row in spot_rows:
            if market_of(row.get("ticker")) == m:
                s = _setup_from_ranking(row, pm.get(row["ticker"]), "long")
                s["ty"] = s["ty"] or "SPOT"
                setups.append(s)
        setups = setups[:top_per_market]
        # if the full conviction pipeline surfaced nothing but we have OHLCV, fall back to the
        # VALIDATED price-signal path (bandarmetrics markup-readiness + RS + entry) so real data
        # shows real tickers. Labeled PRICE-SIGNAL (short-horizon), not the full conviction gate.
        if not setups and data.get("ohlcv", {}).get(m):
            try:
                from price_setups import price_signal_setups
                setups = price_signal_setups(data["ohlcv"][m], top=top_per_market)
            except Exception:
                pass
        drv = bias.get("gold" if m == "commodity" else m, {})
        markets[m] = {
            "label": mk_cfg["label"], "long_only": mk_cfg["long_only"],
            "drivers": mk_cfg["drivers"],
            "bias": drv.get("bias", "NO_DATA"),
            "funnel": {"universe": len(univ),
                       "eliminated": sum(1 for t in univ if t in eliminated),
                       "setups": len(setups)},
            "setups": setups,
        }

    # ── asymmetric alpha (Alpha tab) — structural, over the moonshot universe ──
    disc = run_discovery(top=20)
    alpha = [{
        "tk": c["ticker"], "market": c["domain"], "asymmetry": c["asymmetry"],
        "tier": c["tier"], "upside": c["upside_bucket"], "base_rate": c["base_rate"],
        "stage": c["stage"], "node": c["node"], "scarcity": c["scarcity"],
        "gated": c.get("feed_gated_neutral", []),
    } for c in disc["candidates"][:12]]

    return {
        "meta": {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "source": data["overall_source"],
            "sources": data["sources"], "fred_source": data["fred_source"],
            "universe_n": len(union),
            "note": disc["summary"].get("note", ""),
            "feeds_status": (data.get("feeds") or {}).get("_status", {}),   # per-feed: snapshot / live / absent
        },
        "systemic": systemic,
        "regime_tf": _regime_tf,
        "regional": _regional,
        "grades": _load_grades(),
        "markets": markets,
        "alpha": alpha,
        "desk_picks": out.get("final_desk", {}),
        "feeds": {k: v for k, v in (data.get("feeds") or {}).items() if k != "_status"},
        "macro_observations": _macro_observations(data),
        "market_breadth": _market_breadth(data),
        "rotation_snapshot": _rotation_snapshot(data),
        "data_health": _data_health(data),
        "reference": _load_reference_data(),
        "institutional": {"overall_state": "NOT_LOADED", "statuses": [], "events": [],
                          "options_flow": [], "dark_pool": [], "sec_filings": [], "smart_money": [], "arkham_transfers": []},
    }


def render_dashboard(desk, template_path, out_path):
    """Inject desk JSON into the approved dashboard template (self-contained HTML)."""
    if not os.path.exists(template_path):
        sys.stderr.write(f"[run] template {template_path} not found — skipping HTML render\n")
        return False
    html = open(template_path, encoding="utf-8").read()
    payload = "window.DASHBOARD_DATA = " + json.dumps(desk) + ";"
    if "/*__INJECT_DATA__*/" in html:
        html = html.replace("/*__INJECT_DATA__*/", payload)
    else:  # inject right after <body>
        html = html.replace("<body>", "<body>\n<script>" + payload + "</script>", 1)
    open(out_path, "w", encoding="utf-8").write(html)
    return True


def print_summary(desk):
    m = desk["meta"]; s = desk["systemic"]
    print(f"\n{'='*66}\nWAR ROOM OS — run @ {m['generated']}  [{m['source']}]  universe={m['universe_n']}")
    print(f"{'='*66}")
    print(f"MACRO: quad={s['quad']} ({s['quad_name']}) | liquidity={s['liquidity']} | "
          f"fragility={s['fragility']} | shock={s['shock_prob']} | x-asset={s['cross_asset']}")
    total = sum(len(mk["setups"]) for mk in desk["markets"].values())
    print(f"\nPER-MARKET SETUPS (convicted only — empty = gate not met, not a bug):")
    for mid, mk in desk["markets"].items():
        f = mk["funnel"]
        print(f"  {mk['label']:12} universe {f['universe']:>2} → eliminated {f['eliminated']:>2} → "
              f"setups {f['setups']:>2}   bias={mk['bias']}")
        for x in mk["setups"][:6]:
            rr = f"R/R {x['rr']}" if x["rr"] else "—"
            flag = "" if x["valid"] else " [INVALID: " + (x["warn"] or "gate") + "]"
            print(f"      {x['tk']:10} {x['act']:13} conv={x['conv']:<5} {x['ty']:12} {rr}{flag}")
    print(f"\n  TOTAL convicted setups: {total}")
    print(f"\nASYMMETRIC ALPHA (structural, top {len(desk['alpha'])}):")
    for a in desk["alpha"][:8]:
        g = " (feed-gated: " + ",".join(a["gated"]) + ")" if a["gated"] else ""
        print(f"  {a['tk']:8} asym={a['asymmetry']:<5} tier{a['tier']} {a['upside']:<8} "
              f"[{a['base_rate']}] {a['node'][:40]}{g}")
    print(f"\nRULE: act only where run_validation.py --cache clears perm_p<0.05 AND DSR>=0.95 on YOUR data.\n")


def main():
    ap = argparse.ArgumentParser(description="War Room OS runner")
    ap.add_argument("--synthetic", action="store_true", help="force offline synthetic (no live fetch)")
    ap.add_argument("--markets", default=None, help="comma list, e.g. us,crypto,fx")
    ap.add_argument("--start", default="2022-01-01")
    ap.add_argument("--out", default=os.path.join(HERE, "desk_data.json"))
    ap.add_argument("--template", default=os.path.join(HERE, "dashboard.html"))
    ap.add_argument("--html", default=os.path.join(HERE, "dashboard_live.html"))
    ap.add_argument("--institutional", action="store_true", help="fetch configured institutional feeds")
    args = ap.parse_args()

    markets = args.markets.split(",") if args.markets else None
    data = DL.load_all(markets=markets, start=args.start, allow_live=not args.synthetic,
                       fetch_live_feeds=not args.synthetic, allow_synthetic=args.synthetic)
    desk = build_desk(data)
    if args.institutional and not args.synthetic:
        from institutional_data import collect_institutional_data
        desk["institutional"] = collect_institutional_data(desk)

    json.dump(desk, open(args.out, "w"), indent=2, default=str)
    rendered = render_dashboard(desk, args.template, args.html)
    print_summary(desk)
    print(f"→ desk_data.json written: {args.out}")
    if rendered:
        print(f"→ dashboard written:      {args.html}  (open in a browser)")


if __name__ == "__main__":
    main()
