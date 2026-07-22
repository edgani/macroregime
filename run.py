"""run.py — War Room OS v4.2 deep-reaudit runner.

The runner builds a fail-closed research terminal. Generic price context is descriptive only;
predictive promotion requires exact-scope walk-forward, lockbox and prospective evidence.

Drop this + data_layer.py + dashboard.html into your warroom_pro_full root (next to gcfis/),
then:

    pip install -r requirements.txt          # yfinance, statsmodels, hmmlearn, etc.
    python run.py                            # live data on your machine → desk_data.json + dashboard.html
    python run.py --synthetic                # offline: proves the pipeline runs (no fabricated edge)
    python run.py --markets us,crypto        # subset

Output:
    desk_data.json   — structured desk (systemic macro + per-market setups + evidence lineage)
    dashboard_live.html — Capital Intelligence Map populated with the run

HONEST: a software run proves only pipeline operation. It does not prove predictive edge.
Capital remains blocked until the proof registry records repeated PIT walk-forward, one-time
lockbox, realistic costs/capacity, prospective evidence and human signoff.
"""
from __future__ import annotations
import os, sys, json, argparse, datetime as dt

from research_kernel import attach_research_kernel

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


def _research_band(value, unavailable="UNAVAILABLE"):
    """Banded descriptive display for unpromoted composite diagnostics.

    Thresholds are fixed presentation bands, not calibrated event probabilities.
    """
    x = _num(value, None)
    if x is None:
        return unavailable
    if x < 33.333333:
        return "LOW_RESEARCH_BAND"
    if x < 66.666667:
        return "MODERATE_RESEARCH_BAND"
    return "HIGH_RESEARCH_BAND"


def _safe_research_reason(value):
    """Translate legacy price-pattern vocabulary into descriptive, non-intent semantics."""
    text = str(value or "")
    replacements = {
        "smart money": "unverified large-participant context",
        "stealth accumulation": "positive price/volume pressure proxy",
        "accumulation": "positive price/volume context",
        "distribution": "negative price/volume context",
        "markup-readiness": "positive price-pressure proxy",
        "markup": "positive price-pressure context",
        "markdown": "negative price-pressure context",
        "position building": "rising participation context",
        "liquidation": "falling participation context",
    }
    for old, new in replacements.items():
        text = text.replace(old, new).replace(old.title(), new).replace(old.upper(), new.upper())
    return text


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
        "why": _safe_research_reason(entry.get("reason", "")),
        "evidence_semantics": "RESEARCH_RANKING_CONTEXT; conviction is not probability; ownership and intent are unverified.",
    }



def _load_grades():
    """The walk-forward grade card (metric_grades.json). The UI emits a metric as a number only
    when its exact grade is PRODUCTION or LIMITED_PRODUCTION; all other grades remain research/monitoring context; REJECTED/FEED_GATED emit '—'. Regenerate
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
    desk = {
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
    return attach_research_kernel(desk)


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




def _alpha_signal_context(data, breadth, markets):
    """Build descriptive live context for the structural alpha universe.

    These are ranking inputs, not calibrated predictive factors.  Crowding and reflexivity are
    cross-sectional price-context percentiles over the actually loaded universe.  Missing
    fundamentals remain feed-gated inside the discovery engine.
    """
    import pandas as pd
    ticker_market = {}
    for market in data.get("markets") or []:
        for ticker in ((data.get("prices") or {}).get(market) or {}):
            ticker_market[str(ticker).upper()] = market

    raw = []
    for market, block in (breadth or {}).items():
        for row in (block or {}).get("constituents") or []:
            ticker = str(row.get("ticker") or "").upper()
            if not ticker:
                continue
            raw.append({
                "ticker": ticker,
                "market": market,
                "ret_5d": abs(float(row.get("ret_5d") or 0.0)),
                "ret_20d": abs(float(row.get("ret_20d") or 0.0)),
                "new_high": bool(row.get("new_20d_high")),
            })
    frame = pd.DataFrame(raw)
    signals = {}
    if not frame.empty:
        frame["crowding_pct"] = frame["ret_20d"].rank(pct=True, method="average") * 100.0
        frame["reflexivity"] = frame["ret_5d"].rank(pct=True, method="average") * 85.0 + frame["new_high"].astype(float) * 15.0
        for row in frame.to_dict("records"):
            signals[row["ticker"]] = {
                "crowding_pct": round(float(row["crowding_pct"]), 2),
                "reflexivity": round(min(100.0, float(row["reflexivity"])), 2),
            }

    setup_map = {}
    for market, block in (markets or {}).items():
        for setup in (block or {}).get("setups") or []:
            ticker = str(setup.get("tk") or "").upper()
            if ticker:
                setup_map[ticker] = {**setup, "market": market}
    return signals, ticker_market, setup_map


def _build_alpha_candidates(data, breadth, markets, top=160):
    """Build a structural research inventory without an unvalidated weighted alpha score.

    The ordering is an explicit research-queue prior only: loaded names first, then lifecycle
    stage, hidden-node flag and ticker.  No upside, probability, EV, fair value or capital
    direction is inferred from structural centrality or price momentum.
    """
    from gcfis.data.moonshot_universe import all_candidates
    from scenario_valuation import withheld

    ticker_market = {}
    for market in data.get("markets") or []:
        for ticker in ((data.get("prices") or {}).get(market) or {}):
            ticker_market[str(ticker).upper()] = market
    setup_map = {}
    for market, block in (markets or {}).items():
        for setup in (block or {}).get("setups") or []:
            ticker = str(setup.get("tk") or "").upper()
            if ticker:
                setup_map[ticker] = {**setup, "market": market}

    stage_order = {"emergence": 0, "acceleration": 1, "consensus": 2}
    mapped = []
    seen = set()
    for candidate in all_candidates(hidden_only=False):
        ticker = str(candidate.get("ticker") or "").upper()
        key = (ticker, str(candidate.get("node") or ""))
        if not ticker or key in seen:
            continue
        seen.add(key)
        market = ticker_market.get(ticker) or ("idx" if ticker.endswith(".JK") else ("crypto" if ticker.endswith("-USD") else "us"))
        setup = setup_map.get(ticker) or {}
        valuation_kind = "token" if market == "crypto" else "equity"
        mapped.append({
            "tk": ticker,
            "market": market,
            "domain": candidate.get("domain"),
            "framework": candidate.get("framework"),
            "source": candidate.get("source"),
            "stage": candidate.get("stage"),
            "lifecycle_stage": candidate.get("stage") or "unknown",
            "node": candidate.get("node"),
            "scarcity": candidate.get("scarcity"),
            "is_hidden": bool(candidate.get("is_hidden")),
            "is_crowded": bool(candidate.get("is_crowded")),
            "price_loaded": ticker in ticker_market,
            "timing": setup,
            "timing_action": setup.get("act") or "NO_PRICE_CONTEXT",
            "timing_valid": False,
            "research_priority_basis": "LOADED_STATUS_THEN_LIFECYCLE_STAGE_THEN_HIDDEN_FLAG; NOT EXPECTED RETURN",
            "proof_domains": [],
            "evidence_domains": [],
            "required_evidence_domains": 4,
            "next_missing_gate": "independent mechanism and direct value-capture evidence",
            "mapped": bool(candidate.get("node")),
            "queue_priority": None,
            "proof_state": "PROOF_MISSING",
            "value_capture_state": "UNASSESSED",
            "expectation_gap_state": "UNASSESSED",
            "remaining_return_state": "UNASSESSED",
            "scenario_valuation": withheld(valuation_kind),
            "asymmetry": None,
            "tier": None,
            "upside": None,
            "base_rate": None,
            "confidence": "UNCALIBRATED",
            "capital_permission": "BLOCKED",
        })

    mapped.sort(key=lambda row: (
        0 if row.get("price_loaded") else 1,
        stage_order.get(str(row.get("stage") or "").lower(), 9),
        0 if row.get("is_hidden") else 1,
        str(row.get("tk") or ""),
    ))
    rows = mapped[:top]
    return rows, {
        "universe": len(mapped),
        "mapped": len(mapped),
        "ranked_candidates": len(rows),
        "proof": 0,
        "live_timing": sum(1 for r in rows if r.get("price_loaded")),
        "note": "Structural research inventory only. Queue order is not alpha ranking.",
        "semantics": "No numeric alpha potential, probability, EV, fair value or sizing without point-in-time economic inputs and exact-scope proof.",
    }


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
                setups = price_signal_setups(frames, top=top_per_market, market_id=market) or []
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
            "bias_state": "FAST_PRICE_CONTEXT" if bias != "NO_DATA" else "PARTIAL",
            "driver_coverage": None, "driver_total": len(cfg.get("drivers", [])),
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
    alpha, alpha_meta = _build_alpha_candidates(data, breadth, markets, top=160)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    desk = {
        "meta": {"generated": now, "source": data.get("overall_source", "NO_DATA"),
                 "sources": data.get("sources", {}), "fred_source": data.get("fred_source", "NO_DATA"),
                 "universe_n": len(union), "note": "Latency-bounded observed-data first paint.",
                 "feeds_status": (data.get("feeds") or {}).get("_status", {})},
        "systemic": systemic, "regime_tf": {"state": "FAST_CONTEXT", "quad": quad},
        "regional": {}, "grades": _load_grades(), "markets": markets, "alpha": alpha,
        "alpha_meta": alpha_meta, "desk_picks": {"picks": [], "state": "CAPITAL_BLOCKED", "reason": "Fast context never produces capital picks."},
        "feeds": {}, "macro_observations": macro, "market_breadth": breadth,
        "rotation_snapshot": rotation, "data_health": _data_health(data),
        "reference": _load_reference_data(),
        "institutional": {"overall_state": "NOT_LOADED", "statuses": [], "events": [],
                          "options_flow": [], "dark_pool": [], "sec_filings": [], "smart_money": [], "arkham_transfers": []},
    }
    return attach_research_kernel(desk)

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
        "fragility_raw": _num(fr.get("fragility")) if fr.get("ok") else None,
        "fragility": _research_band(fr.get("fragility")) if fr.get("ok") else (fr.get("reason") or "UNAVAILABLE"),
        "shock_raw": _num(sh.get("shock_prob")) if sh.get("ok") else None,
        "shock_prob": _research_band(sh.get("shock_prob")) if sh.get("ok") else (sh.get("reason") or "UNAVAILABLE"),
        "systemic_semantics": "UNPROMOTED_COMPOSITES_ARE_BANDED_RESEARCH_WARNINGS_NOT_PROBABILITIES",
        "quad_state": "RESEARCH_PROXY",
        "quad_semantics": "Market/macro proxy context; not an objective economic state and not a trade signal.",
        "cross_asset": xa.get("regime"), "defer_longs": xa.get("defer_longs"),
        "rotation_in": [], "rotation_out": [],
        "rotation_semantics": "Use rotation_snapshot observed relative price leadership only; legacy inferred flow lists are withheld.",
    }

    # ── per-market descriptive context screens ──
    # No predictive selector in the current registry is promoted.  The full GCFIS ranking is kept
    # in research diagnostics but may not populate a directional market board.  Every market uses
    # its own downstream adapter after the descriptive OHLCV context screen.
    bias = market_bias(_driver_series(data))
    markets = {}
    _MKDEF = {"label": None, "long_only": False, "drivers": []}
    for m in data["markets"]:
        mk_cfg = MARKETS.get(m, {**_MKDEF, "label": m})
        pm = prices.get(m) or {}
        univ = list(pm.keys())
        setups = []
        frames = (data.get("ohlcv") or {}).get(m) or {}
        if frames:
            try:
                from price_setups import price_signal_setups
                setups = price_signal_setups(frames, top=top_per_market, market_id=m) or []
            except Exception:
                setups = []
        drv = bias.get("gold" if m == "commodity" else m, {})
        driver_bias = drv.get("bias", "NO_DATA")
        driver_fed = int(drv.get("fed") or 0)
        driver_total = len(drv.get("drivers") or [])
        markets[m] = {
            "label": mk_cfg["label"],
            "long_only": mk_cfg["long_only"],
            "drivers": mk_cfg["drivers"],
            "data_state": "LIVE" if len(univ) else "NO_DATA",
            "bias": driver_bias,
            "bias_state": ("LIVE" if driver_bias not in (None, "", "NO_DATA") else
                           ("PARTIAL" if driver_fed else "ACTION_REQUIRED")),
            "driver_coverage": driver_fed,
            "driver_total": driver_total,
            "selector_state": "DESCRIPTIVE_CONTEXT_ONLY",
            "directional_selector_permission": "BLOCKED",
            "funnel": {"universe": len(univ), "eliminated": 0, "setups": len(setups)},
            "setups": setups,
        }

    # ── asymmetric alpha (Alpha Center) — structural headroom + live timing context ──
    alpha, alpha_meta = _build_alpha_candidates(data, _market_breadth(data), markets, top=240)

    desk = {
        "meta": {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "source": data["overall_source"],
            "sources": data["sources"], "fred_source": data["fred_source"],
            "universe_n": len(union),
            "note": alpha_meta.get("note", ""),
            "feeds_status": (data.get("feeds") or {}).get("_status", {}),   # per-feed: snapshot / live / absent
        },
        "systemic": systemic,
        "regime_tf": _regime_tf,
        "regional": _regional,
        "grades": _load_grades(),
        "markets": markets,
        "alpha": alpha,
        "alpha_meta": alpha_meta,
        "desk_picks": {"picks": [], "state": "CAPITAL_BLOCKED", "reason": "No exact-scope selector is promoted in the proof registry."},
        "feeds": {k: v for k, v in (data.get("feeds") or {}).items() if k != "_status"},
        "macro_observations": _macro_observations(data),
        "market_breadth": _market_breadth(data),
        "rotation_snapshot": _rotation_snapshot(data),
        "data_health": _data_health(data),
        "reference": _load_reference_data(),
        "institutional": {"overall_state": "NOT_LOADED", "statuses": [], "events": [],
                          "options_flow": [], "dark_pool": [], "sec_filings": [], "smart_money": [], "arkham_transfers": []},
    }
    return attach_research_kernel(desk)


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
    print(f"\n{'='*72}\nWAR ROOM OS v4.2 — run @ {m['generated']}  [{m['source']}]  universe={m['universe_n']}")
    print(f"{'='*72}")
    print(f"MACRO CONTEXT: quad={s.get('quad')} ({s.get('quad_name')}) | liquidity={s.get('liquidity')} | "
          f"fragility={s.get('fragility')} | shock={s.get('shock_prob')} | x-asset={s.get('cross_asset')}")
    total = sum(len(mk.get("setups") or []) for mk in desk.get("markets", {}).values())
    print("\nPER-MARKET DESCRIPTIVE CONTEXT (not a directional selector):")
    for mid, mk in desk.get("markets", {}).items():
        f = mk.get("funnel") or {}
        print(f"  {mk.get('label', mid):12} universe {f.get('universe',0):>3} -> contexts {f.get('setups',0):>3} "
              f"selector={mk.get('directional_selector_permission','BLOCKED')} bias_context={mk.get('bias')}")
        for x in (mk.get("setups") or [])[:5]:
            print(f"      {x.get('tk','—'):12} {x.get('act','RESEARCH_CONTEXT'):34} "
                  f"setup_rank={x.get('setup_rank',x.get('conv'))} geometry={x.get('execution_state')}")
    print(f"  TOTAL descriptive context rows: {total}")
    print(f"\nALPHA RESEARCH INVENTORY ({len(desk.get('alpha') or [])} rows; not expected-return ranking):")
    for a in (desk.get("alpha") or [])[:8]:
        print(f"  {a.get('tk','—'):8} proof={a.get('proof_state')} stage={a.get('stage')} "
              f"value={a.get('value_capture_state')} scenario={obj_status(a.get('scenario_valuation'))}")
    pr = desk.get('proof_registry') or {}
    comps = pr.get('components') or {}
    promoted = [k for k,v in comps.items() if str(v.get('state','')).upper() in {'LIMITED_PRODUCTION_ELIGIBLE','HUMAN_APPROVED_LIMITED_PRODUCTION'}]
    print(f"\nPROOF REGISTRY: {len(promoted)} promoted components / {len(comps)} total")
    print("CAPITAL PERMISSION: BLOCKED unless exact-scope evidence artifacts independently clear every gate.\n")


def obj_status(value):
    return value.get('state') or value.get('status') or 'WITHHELD' if isinstance(value, dict) else 'WITHHELD'


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
