"""run.py — War Room OS end-to-end runner (gcfis orchestrator = brain, one pipeline).

Drop this + data_layer.py + dashboard.html into your warroom_pro_full root (next to gcfis/),
then:

    pip install -r requirements.txt          # yfinance, statsmodels, hmmlearn, etc.
    python run.py                            # live data on your machine → desk_data.json + dashboard.html
    python run.py --synthetic                # offline: proves the pipeline runs (no fabricated edge)
    python run.py --markets us,crypto        # subset

Output:
    desk_data.json   — structured desk (systemic macro + per-market setups + asymmetric alpha)
    dashboard.html   — the approved v0.3 UI, POPULATED with the run (open in a browser)

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




_NON_STOCK_US = {
    "SPY","IWM","XLI","XLY","XHB","USO","GLD","UUP","TLT","IEF","DBC","HYG","XLK","XLE","XLF","XLV","XLP","XLU","XLB","XLRE","XLC","IWD","IWF","MTUM",
    "SMH","SOXX","ARKK","COPX","GDX","GDXJ","SIL","XOP","OIH","AMLP","EEM","EWZ","INDA","FXI","EWY","EWT","EWW","EFA",
    "EZU","EWU","EWJ","EIDO","EWA","EWC","EWG","EWL","EZA","LQD","JNK","AGG","BIL","TIP","EMB","SHY","BOTZ","NLR","ITA","KWEB","IGV","^VIX"
}

def _surfaceable_ticker(market, ticker):
    t = str(ticker or "").upper()
    if market == "us":
        return bool(t) and t not in _NON_STOCK_US and not t.startswith("^") and "=" not in t and not t.endswith("-USD")
    if market == "idx":
        return t.endswith(".JK") and not t.startswith("^")
    if market == "crypto":
        return t.endswith("-USD")
    return bool(t)

def _history_eligible_count(ohlcv_map):
    count = 0
    for frame in (ohlcv_map or {}).values():
        try:
            df = __import__("pandas").DataFrame(frame)
            cols = {str(c).lower() for c in df.columns}
            if len(df.dropna()) >= 200 and {"open","high","low","close"}.issubset(cols):
                count += 1
        except Exception:
            pass
    return count

def _driver_bundle(driver_models, market, tickers):
    if market != "commodity":
        model = driver_models.get(market, {})
        rows = []
        for row in model.get("drivers", []):
            if row.get("reading_z") is None:
                continue
            rows.append({k: row.get(k) for k in ("factor","series","horizon","strength","reading_z","signed_contribution_z","effect")})
        return model.get("bias", "NO_DATA"), rows, model.get("fed", 0), model.get("total", 0), market.upper()
    types = []
    upper = {str(t).upper() for t in tickers}
    if upper & {"CL=F","BZ=F","USO"}: types.append("oil")
    if upper & {"GC=F","SI=F","GLD","SLV"}: types.append("gold")
    rows, biases, fed, total = [], [], 0, 0
    for subtype in types:
        model = driver_models.get(subtype, {})
        fed += int(model.get("fed", 0)); total += int(model.get("total", 0))
        if model.get("bias") not in (None,"NO_DATA"): biases.append(model.get("bias"))
        for row in model.get("drivers", []):
            if row.get("reading_z") is None: continue
            copy = {k: row.get(k) for k in ("factor","series","horizon","strength","reading_z","signed_contribution_z","effect")}
            copy["factor"] = subtype.upper()+" · "+str(copy.get("factor"))
            rows.append(copy)
    bias = biases[0] if len(set(biases)) == 1 else ("MIXED" if biases else "NO_DATA")
    label = "/".join(x.upper() for x in types) if types else "NO_SUPPORTED_COMMODITY_MODEL"
    return bias, rows, fed, total, label

def _num(x, d=None):
    try:
        f = float(x)
        return round(f, 3)
    except Exception:
        return d


def _setup_from_ranking(entry, price, direction, ohlcv=None):
    """Convert an orchestrator row into one UI setup without recomputing valid levels.

    The orchestrator already ran the entry engine with true OHLCV and risk range. Reusing those
    values avoids the old bug where run.py silently replaced them with a close-only ATR fallback.
    """
    tk = entry.get("ticker")
    lo = is_long_only(tk)
    existing = {
        "entry_px": entry.get("entry_px"), "stop": entry.get("stop"),
        "target": entry.get("target"), "rr": entry.get("rr"),
        "entry_type": entry.get("entry_type"), "gamma_regime": entry.get("gamma_regime"),
        "valid": entry.get("entry_valid"),
    }
    has_existing = all(existing.get(k) not in (None, 0, 0.0, "") for k in ("entry_px", "stop", "target"))
    if has_existing:
        e = existing
        level_source = ((entry.get("execution") or {}).get("level_source")
                        or "ORCHESTRATOR_RISK_RANGE")
        warning = ((entry.get("execution") or {}).get("warning") or "")
    else:
        e = run_entry(price, direction, long_only=lo, ohlcv=ohlcv, ticker=tk) if price is not None and len(price) > 60 else {}
        level_source = e.get("rr_source", "UNAVAILABLE")
        warning = e.get("warning", "")
    entry_px, stop, target = e.get("entry_px"), e.get("stop"), e.get("target")
    direction_ok = True
    try:
        if direction == "long": direction_ok = float(stop) < float(entry_px) < float(target)
        elif direction == "short": direction_ok = float(target) < float(entry_px) < float(stop)
    except Exception:
        direction_ok = False
    valid = bool(e.get("valid", False)) and direction_ok
    if not direction_ok:
        warning = (warning + "; " if warning else "") + "directional level invariant failed"
    safe_level_source = "MQA_RISK_RANGE_PROXY" if "hedgeye" in str(level_source).lower() else level_source
    try:
        as_of = str(__import__("pandas").Timestamp(__import__("pandas").DataFrame(ohlcv).index[-1]).date()) if ohlcv is not None else None
    except Exception:
        as_of = None
    return {
        "tk": tk, "act": entry.get("action", ""), "dir": direction,
        "conv": _num(entry.get("conviction"), 0), "score_label": "CONVICTION_SCORE",
        "e": _num(entry_px, None), "s": _num(stop, None),
        "t": _num(target, None), "rr": _num(e.get("rr"), None),
        "ty": e.get("entry_type", ""), "gm": e.get("gamma_regime", ""),
        "valid": valid, "warn": warning, "why": entry.get("reason", ""),
        "level_source": safe_level_source,
        "stop_basis": "RISK_RANGE_INVALIDATION" if "risk_range" in str(level_source).lower() else "VOLATILITY_FALLBACK",
        "target_basis": "TACTICAL_RESPONSE_ZONE" if "risk_range" in str(level_source).lower() else "VOLATILITY_FALLBACK",
        "structural_target": (entry.get("opportunity") or {}).get("base"),
        "invalidation": entry.get("invalidation") or {},
        "data_quality": "DAILY_OHLC_SNAPSHOT" if ohlcv is not None else "CLOSE_ONLY",
        "evidence_family": "MULTI_FACTOR_ORCHESTRATOR",
        "as_of": as_of,
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
        raise SystemExit("no price data (need bench + universe). On your machine: pip install yfinance.")

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
        "liquidity": (lambda _r, _t: ("expanding" if liq.get("expanding")
                      else (_r if _r and "no " not in _r.lower() else (_t or "—"))))(
                      liq.get("reason"),
                      data.get("treasury_liquidity", {}).get("bias") if data.get("treasury_liquidity", {}).get("ok") else None),
        "fragility": _num(fr.get("fragility")) if fr.get("ok") else fr.get("reason"),
        "fragility_label": fr.get("label"), "fragility_components": fr.get("components", {}),
        "shock_score": _num(sh.get("shock_prob")) if sh.get("ok") else sh.get("reason"),
        "shock_prob": _num(sh.get("shock_prob")) if sh.get("ok") else sh.get("reason"),
        "shock_label": sh.get("alert"), "shock_components": sh.get("components", {}),
        "cross_asset": xa.get("regime"), "defer_longs": xa.get("defer_longs"),
        "rotation_in_raw": fl.get("rotating_in", []), "rotation_out_raw": fl.get("rotating_out", []),
        "rotation_scores": fl.get("rotation_score", {}),
        "rotation_method": "RELATIVE_STRENGTH_PROXY_NOT_CAPITAL_FLOW",
        "rotation_in": [], "rotation_out": [],
    }

    # ── per-market setups (group ranking by market) ──
    long_rows = rk.get("master_long", [])
    short_rows = rk.get("master_short", [])
    spot_rows = rk.get("master_spot", [])
    eliminated = {e.get("ticker"): e.get("reason", "eliminated") for e in rk.get("eliminated", []) if isinstance(e, dict)}
    driver_models = market_bias(_driver_series(data))  # current change-z readings; missing series remain NO_DATA

    markets = {}
    _MKDEF = {"label": None, "long_only": False, "drivers": []}
    for m in data["markets"]:
        mk_cfg = MARKETS.get(m, {**_MKDEF, "label": m})
        pm = prices.get(m) or {}
        ohlcv_m = (data.get("ohlcv", {}).get(m, {}) or {})
        univ = [t for t in pm.keys() if _surfaceable_ticker(m, t)]
        evaluated = []
        for row in long_rows:
            if market_of(row.get("ticker")) == m and _surfaceable_ticker(m, row.get("ticker")):
                evaluated.append(_setup_from_ranking(row, pm.get(row["ticker"]), "long", ohlcv_m.get(row["ticker"])))
        for row in short_rows:
            if market_of(row.get("ticker")) == m and not mk_cfg["long_only"] and _surfaceable_ticker(m, row.get("ticker")):
                evaluated.append(_setup_from_ranking(row, pm.get(row["ticker"]), "short", ohlcv_m.get(row["ticker"])))
        for row in spot_rows:
            if market_of(row.get("ticker")) == m and _surfaceable_ticker(m, row.get("ticker")):
                setup = _setup_from_ranking(row, pm.get(row["ticker"]), "long", ohlcv_m.get(row["ticker"]))
                setup["ty"] = setup["ty"] or "SPOT"
                evaluated.append(setup)
        # Price-only fallback is a separate research path. It cannot be called the full
        # conviction selector and invalid rows do not count as entry-valid.
        if not any(row.get("valid") for row in evaluated) and ohlcv_m:
            try:
                from price_setups import price_signal_setups
                evaluated = price_signal_setups(ohlcv_m, top=max(top_per_market * 3, top_per_market))
            except Exception:
                evaluated = []
        valid_rows = [row for row in evaluated if row.get("valid") and _surfaceable_ticker(m, row.get("tk"))]
        failed_rows = [row for row in evaluated if not row.get("valid")]
        bias_value, driver_rows, driver_fed, driver_total, driver_scope = _driver_bundle(driver_models, m, [row.get("tk") for row in valid_rows] or univ)
        driver_confidence = "NONE" if driver_fed == 0 else ("LOW" if driver_fed < 2 else "PARTIAL")
        for row in valid_rows:
            direction = str(row.get("dir") or "").lower()
            contra = ((direction == "long" and bias_value in {"SHORT", "LEAN_SHORT"}) or
                      (direction == "short" and bias_value in {"LONG", "LEAN_LONG"}))
            aligned = ((direction == "long" and bias_value in {"LONG", "LEAN_LONG"}) or
                       (direction == "short" and bias_value in {"SHORT", "LEAN_SHORT"}))
            row["macro_alignment"] = "COUNTER_REGIME" if contra else ("ALIGNED" if aligned else "NEUTRAL_OR_NO_DATA")
            row["driver_confidence"] = driver_confidence
            # Price/RS-only rows are watch setups, not recommendations. A low-coverage macro
            # headwind is disclosed, not used as a hidden hard block.
            if row.get("evidence_family") == "PRICE_RS":
                row["act"] = "WATCH_LONG" if direction == "long" else "WATCH_SHORT"
            elif contra:
                row["act"] = "WATCH_COUNTER_REGIME"
        setups = valid_rows[:top_per_market]
        ui_key = {"idx": "ihsg", "commodity": "commod"}.get(m, m)
        source_info = dict((data.get("market_meta") or {}).get(m) or {})
        markets[ui_key] = {
            "source_market": m, "label": mk_cfg["label"], "long_only": mk_cfg["long_only"],
            "drivers": mk_cfg["drivers"], "driver_scope": driver_scope,
            "driver_readings": driver_rows, "driver_coverage": {"fed": driver_fed, "total": driver_total},
            "bias": bias_value, "source_info": source_info,
            "funnel": {"loaded": len(pm), "surfaceable": len(univ),
                       "history_eligible": _history_eligible_count({t: ohlcv_m[t] for t in univ if t in ohlcv_m}),
                       "signal_valid": len(valid_rows), "displayed": len(setups),
                       "failed": len(failed_rows), "non_surfaceable": len(pm) - len(univ)},
            "setups": setups,
        }

    # Current Alpha output is intentionally empty here. The previous path used a curated
    # moonshot universe with neutral feed defaults, which is research prior—not a live selector.
    # Alpha cards now come only from the frozen Alpha Foundry shortlist or validated final desk.
    disc = {"summary": {"note": "Curated structural priors are excluded from live Alpha output."}}
    alpha = []


    return {
        "meta": {
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "source": data["overall_source"],
            "sources": data["sources"], "fred_source": data["fred_source"],
            "universe_n": len(union),
            "note": disc["summary"].get("note", ""),
            "universe_source": "CONFIGURED_LIVE_SCAN_UNIVERSE",
            "universe_claim_ceiling": "NOT_FULL_MARKET_SELECTOR",
            "feeds_status": (data.get("feeds") or {}).get("_status", {}),
            "market_meta": data.get("market_meta", {}),
            "data_claim": "LATEST_AVAILABLE_DAILY_SNAPSHOT_NOT_STREAMING",
            "trading_permission": "RESEARCH_ONLY_PAPER_AND_LIVE_BLOCKED",
        },
        "systemic": systemic,
        "regime_tf": _regime_tf,
        "regional": _regional,
        "grades": _load_grades(),
        "markets": markets,
        "alpha": alpha,
        "desk_picks": out.get("final_desk", {}),
        "feeds": {k: v for k, v in (data.get("feeds") or {}).items() if k != "_status"},  # onchain/cot/gex/finra when present
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
    args = ap.parse_args()

    markets = args.markets.split(",") if args.markets else None
    data = DL.load_all(markets=markets, start=args.start, allow_live=not args.synthetic)
    desk = build_desk(data)

    json.dump(desk, open(args.out, "w"), indent=2, default=str)
    rendered = render_dashboard(desk, args.template, args.html)
    print_summary(desk)
    print(f"→ desk_data.json written: {args.out}")
    if rendered:
        print(f"→ dashboard written:      {args.html}  (open in a browser)")


if __name__ == "__main__":
    main()
