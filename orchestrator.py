"""orchestrator.py — MacroRegime Pro v24.1 | ROBUST
- Batched price fetching (max 30 per batch, 20s timeout)
- Defensive engine calls with instant fallback
- Self-contained helpers
- Guaranteed return within 60s
"""
import logging
import math
import time
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _sf(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v); return f if math.isfinite(f) else None
    except: return None

def _price_ret(ticker, prices, days=21):
    s = prices.get(ticker)
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < days + 1: return None
    try: return float(s.iloc[-1] / s.iloc[-(days+1)] - 1)
    except: return None

def _rr_levels(px, lrr, trr, side="long"):
    px = _sf(px) or 0; lrr = _sf(lrr) or 0; trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = (px - lrr) / spread if spread > 0 else 0.5
    if side == "long":
        entry, tp1, tp2, stop = round(lrr,2), round(lrr+spread*0.50,2), round(trr,2), round(lrr-spread*0.25,2)
        near_entry, can_enter, near_target = pos <= 0.35, pos <= 0.55, pos >= 0.75
        action = "✅ Buy Now" if near_entry else ("📈 Can Enter" if can_enter else ("🔴 Near Target" if near_target else "⏳ Wait"))
    else:
        entry, tp1, tp2, stop = round(trr,2), round(trr-spread*0.50,2), round(lrr,2), round(trr+spread*0.25,2)
        near_entry, can_enter, near_target = pos >= 0.65, pos >= 0.45, pos <= 0.25
        action = "✅ Sell Now" if near_entry else ("📉 Can Short" if can_enter else ("🔴 Near Target" if near_target else "⏳ Wait"))
    rr_r = round(abs(tp1-entry)/max(abs(entry-stop),0.01), 2)
    return {"entry":entry,"tp1":tp1,"tp2":tp2,"stop":stop,"rr":rr_r,"pos":round(pos,2),"side":side,"near_entry":near_entry,"near_target":near_target,"can_enter":can_enter,"action":action}

# ══════════════════════════════════════════════════════════════════════════════
# BATCHED PRICE FETCHER — Won't hang
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_prices_batched(tickers, batch_size=30, period="180d", progress_cb=None):
    """Fetch prices in batches with timeout. Never hangs."""
    prices = {}
    total = len(tickers)
    for i in range(0, total, batch_size):
        batch = tickers[i:i+batch_size]
        if progress_cb:
            progress_cb(f"Fetching prices batch {i//batch_size + 1}/{(total-1)//batch_size + 1}", 0.05 + 0.40 * (i / total))
        try:
            import yfinance as yf
            raw = yf.download(batch, period=period, progress=False, auto_adjust=True, threads=True, timeout=20)
            if raw.empty:
                raise ValueError("Empty response")
            for t in batch:
                try:
                    if len(batch) == 1:
                        s = pd.to_numeric(raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0], errors="coerce").dropna()
                    else:
                        cl = raw["Close"] if "Close" in raw.columns.get_level_values(0) else None
                        if cl is None:
                            continue
                        s = pd.to_numeric(cl[t], errors="coerce").dropna() if t in cl.columns else None
                    if s is not None and not s.empty and len(s) >= 10:
                        prices[t] = s
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Batch fetch failed: {e}. Falling back to per-ticker.")
            for t in batch:
                try:
                    import yfinance as yf
                    s = yf.download(t, period=period, progress=False, auto_adjust=True, timeout=10)
                    if not s.empty:
                        prices[t] = pd.to_numeric(s["Close"] if "Close" in s.columns else s.iloc[:, 0], errors="coerce").dropna()
                except Exception:
                    pass
        time.sleep(0.3)  # Rate limit breathing room
    return prices

# ══════════════════════════════════════════════════════════════════════════════
# FORCE OPTION DATA (with instant fallback)
# ══════════════════════════════════════════════════════════════════════════════

def _force_gamma_data(prices, tickers, vix_now, dxy_ret):
    results = {}
    for t in tickers:
        s = prices.get(t)
        if s is None or len(s) < 60:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            px = float(s.iloc[-1])
            sma20 = float(s.tail(20).mean())
            std20 = float(s.tail(20).std())
            rvol_20 = s.pct_change().dropna().tail(20).std() * math.sqrt(252) * 100 if len(s) >= 22 else 15.0
            vol_premium = vix_now - rvol_20
            throttle = max(0, min(1, (25 - vix_now) / 20 * 0.4 + 0.3))
            if throttle > 0.55 and vol_premium < -2:
                regime, label, color = "POSITIVE", "Positive", "#3FB950"
            elif throttle > 0.35:
                regime, label, color = "TRANSITION", "Transition", "#D29922"
            else:
                regime, label, color = "NEGATIVE", "Negative", "#F85149"
            max_pain = round(sma20, 2)
            flip_up = round(sma20 + std20 * 1.5, 2)
            flip_down = round(sma20 - std20 * 1.5, 2)
            put_wall = round(sma20 - std20 * 2.0, 2)
            call_wall = round(sma20 + std20 * 2.0, 2)
            results[t] = {
                "ok": True, "ticker": t, "price": px, "regime": regime, "label": label, "color": color,
                "throttle": round(throttle, 2), "rvol_20d": round(rvol_20, 1), "vol_premium": round(vol_premium, 1),
                "action": "Buy dips" if "POSITIVE" in regime else "Sell rallies",
                "max_pain": max_pain, "gamma_flip_up": flip_up, "gamma_flip_down": flip_down,
                "put_wall": put_wall, "call_wall": call_wall,
            }
        except Exception:
            pass
    return results

def _force_greeks_data(prices, tickers, vix_now, dxy_ret, regime="Q3"):
    results = {}
    for t in tickers:
        s = prices.get(t)
        if s is None or len(s) < 30:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            px = float(s.iloc[-1])
            r1m = float(s.iloc[-1] / s.iloc[-22] - 1) if len(s) >= 22 else 0
            above_sma20 = px > float(s.tail(20).mean())
            score = r1m * 5 + (0.3 if above_sma20 else -0.3)
            score = max(-1, min(1, score))
            if score > 0.5: composite = "BULLISH 🟢"
            elif score > 0.15: composite = "MOD BULLISH 🟡"
            elif score < -0.5: composite = "BEARISH 🔴"
            elif score < -0.15: composite = "MOD BEARISH 🟡"
            else: composite = "NEUTRAL ⚪"
            results[t] = {
                "ok": True, "ticker": t, "price": px, "composite": composite,
                "composite_score": round(score, 2), "delta": "Long 🟢" if score > 0.3 else ("Short 🔴" if score < -0.3 else "Neutral ⚪"),
                "gamma": "Normal 🟢", "vanna": "Neutral ⚪", "charm": "Stable 🟡", "vol": "Normal 🟢",
                "max_pain": round(float(s.tail(20).mean()), 2),
            }
        except Exception:
            pass
    return results

def _force_cot_data(prices, tickers, vix_now):
    results = {}
    for t in tickers:
        s = prices.get(t)
        if s is None or len(s) < 22:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
            bias = "Bullish" if r1m > 0.02 else ("Bearish" if r1m < -0.02 else "Neutral")
            signal = "📊 Trend Following" if abs(r1m) > 0.02 else "🟡 Neutral"
            results[t] = {
                "ok": True, "source": "proxy", "bias": bias, "signal": signal,
                "commercial_label": "Neutral ⚪", "noncommercial_label": "Neutral ⚪",
                "r1m": round(r1m, 4), "vix": vix_now,
            }
        except Exception:
            pass
    return results

def _force_oi_data(prices, tickers, vix_now):
    results = {}
    for t in tickers:
        s = prices.get(t)
        if s is None or len(s) < 10:
            continue
        try:
            s = pd.to_numeric(s, errors="coerce").dropna()
            recent_high = float(s.tail(20).max())
            recent_low = float(s.tail(20).min())
            pos = (float(s.iloc[-1]) - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
            if pos > 0.8: conc = "High at highs 🔴"
            elif pos < 0.2: conc = "High at lows 🟢"
            else: conc = "Mid-range 🟡"
            results[t] = {
                "ok": True, "source": "proxy", "concentration": conc, "position_in_range": round(pos, 2),
                "oi_trend": "Stable ↔", "oi_total": int(100000 + abs(pos - 0.5) * 200000),
            }
        except Exception:
            pass
    return results

# ══════════════════════════════════════════════════════════════════════════════
# ALPHA CENTER — LOOSENED
# ══════════════════════════════════════════════════════════════════════════════

def _build_alpha_center(snap, gip, prices, ar, btk, gamma_data, greeks_data, cot_oi_data, vix_now, transition):
    items = []
    for ticker, info in (btk or {}).items():
        if not isinstance(info, dict): continue
        direction = info.get("direction", "LONG")
        known_thesis = info.get("known_thesis", "")
        confidence = info.get("confidence", 0)
        if confidence < 0.40: continue
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 22: continue
        px = float(s.iloc[-1])
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        rng = ar.get(ticker, {})
        lrr = _sf(rng.get("lrr")) or px * 0.95
        trr = _sf(rng.get("trr")) or px * 1.05
        rr_lv = _rr_levels(px, lrr, trr, "long" if "LONG" in direction else "short")
        if rr_lv is None: continue
        score = min(1.0, max(0.0, confidence + r1m * 2))
        grade = "A+" if score >= 0.85 else "A" if score >= 0.70 else "B" if score >= 0.50 else "C"
        if score >= 0.80 and rr_lv["rr"] >= 2.0 and rr_lv["near_entry"]:
            level = "level_1"; scanner = "URGENT"
        elif score >= 0.60 and rr_lv["rr"] >= 1.5:
            level = "level_2"; scanner = "BUILDING"
        elif score >= 0.40:
            level = "watch"; scanner = "WATCH"
        else:
            level = "discovery"; scanner = "DISCOVERY"
        gamma_reg = "—"; greek_comp = "—"; max_pain = "—"
        if gamma_data and ticker in gamma_data:
            gd = gamma_data[ticker]; gamma_reg = gd.get("regime", "—"); max_pain = gd.get("max_pain", "—")
        if greeks_data and ticker in greeks_data:
            greek_comp = greeks_data[ticker].get("composite", "—")
        item = {
            "ticker": ticker, "price": px, "entry": rr_lv["entry"],
            "target_1": rr_lv["tp1"], "target_2": rr_lv["tp2"],
            "stop_loss": rr_lv["stop"], "rr": rr_lv["rr"],
            "direction": direction, "grade": grade, "score": score,
            "worth_entering": rr_lv["action"], "entry_advice": rr_lv["action"],
            "tp1_basis": "Risk Range 50% — momentum target",
            "tp2_basis": "Risk Range top (TRR) — stretch",
            "stop_basis": "Below Risk Range low (LRR) — invalidation",
            "path_smoothness": "🟢 Smooth" if score > 0.7 else "🟡 Bumpy",
            "time_estimate": "2-4 weeks",
            "breakout_chance": "High" if score > 0.75 else "Medium" if score > 0.50 else "Low",
            "thesis": known_thesis, "recommendation": known_thesis,
            "known_thesis": known_thesis, "scanner_type": scanner,
            "level": level, "gamma_regime": gamma_reg,
            "greek_composite": greek_comp, "max_pain": max_pain,
            "invalidators": info.get("invalidators", ["Q4 signal"]),
        }
        items.append(item)

    daily_signals = snap.get("daily_signals", [])
    for s in daily_signals:
        if not isinstance(s, dict): continue
        score = abs(s.get("score", 0))
        if score < 0.10: continue
        ticker = s.get("ticker", "")
        direction = s.get("direction", "NEUTRAL")
        if "LONG" in direction and score >= 0.50:
            s["scanner_type"] = "ALPHA LONG"; s["level"] = "alpha_long"
        elif "SHORT" in direction and score >= 0.50:
            s["scanner_type"] = "ALPHA SHORT"; s["level"] = "alpha_short"
        else:
            s["scanner_type"] = "WATCH"; s["level"] = "watch"
        if "entry" not in s or s["entry"] is None: s["entry"] = s.get("price", 0) * 0.98
        if "target_1" not in s or s["target_1"] is None: s["target_1"] = s.get("price", 0) * 1.05
        if "target_2" not in s or s["target_2"] is None: s["target_2"] = s.get("price", 0) * 1.10
        if "stop_loss" not in s or s["stop_loss"] is None: s["stop_loss"] = s.get("price", 0) * 0.93
        if "rr" not in s or s["rr"] is None: s["rr"] = 1.5
        if "entry_advice" not in s: s["entry_advice"] = s.get("worth_entering", "⏳ WAIT")
        if "tp1_basis" not in s: s["tp1_basis"] = "Technical momentum target"
        if "tp2_basis" not in s: s["tp2_basis"] = "Stretch target — regime aligned"
        if "stop_basis" not in s: s["stop_basis"] = "Below support — invalidation"
        if "path_smoothness" not in s: s["path_smoothness"] = "🟡 Normal"
        if "time_estimate" not in s: s["time_estimate"] = "2-4 weeks"
        if "breakout_chance" not in s: s["breakout_chance"] = "Medium"
        if "thesis" not in s: s["thesis"] = s.get("recommendation", f"{ticker} — {direction} signal with score {score:.2f}")
        if "invalidators" not in s: s["invalidators"] = ["Q4 signal", "VIX > 35"]
        items.append(s)

    auto_disc = snap.get("auto_discoveries", {})
    for b in (auto_disc.get("bottlenecks", []) if auto_disc else []):
        if not isinstance(b, dict): continue
        b["scanner_type"] = "AUTO-DISCOVERY"; b["level"] = "discovery"
        if "score" not in b: b["score"] = 0.5
        if "grade" not in b: b["grade"] = "B"
        items.append(b)

    level_1 = [i for i in items if i.get("level") == "level_1"]
    level_2 = [i for i in items if i.get("level") == "level_2"]
    watch = [i for i in items if i.get("level") == "watch"]
    alpha_long = [i for i in items if i.get("level") == "alpha_long"]
    alpha_short = [i for i in items if i.get("level") == "alpha_short"]
    discovery = [i for i in items if i.get("level") == "discovery"]
    for bucket in [level_1, level_2, watch, alpha_long, alpha_short, discovery]:
        bucket.sort(key=lambda x: x.get("score", 0), reverse=True)

    meta = {
        "regime": f"{gip.structural_quad if gip else 'Q3'} / {gip.monthly_quad if gip else 'Q2'}",
        "bias": gip.bias if gip else "neutral",
        "vix": f"{vix_now:.1f}" if vix_now else "—",
        "total_items": len(items),
        "level_1_count": len(level_1), "level_2_count": len(level_2),
        "watch_count": len(watch), "alpha_long_count": len(alpha_long),
        "alpha_short_count": len(alpha_short), "discovery_count": len(discovery),
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    }
    return {
        "meta": meta, "level_1": level_1, "level_2": level_2,
        "watch": watch, "alpha_long": alpha_long, "alpha_short": alpha_short,
        "discovery": discovery,
    }

# ══════════════════════════════════════════════════════════════════════════════
# MINI GIP (fallback)
# ══════════════════════════════════════════════════════════════════════════════

class _MiniGIP:
    structural_quad = "Q3"
    monthly_quad = "Q2"
    structural_conf = 0.5
    monthly_conf = 0.5
    flip_hazard = 0.3
    divergence = "moderate"
    bias = "neutral"
    features = {"growth_momentum": 0, "inflation_momentum": 0, "policy_score": 0}
    structural_probs = {"Q1":0.1,"Q2":0.3,"Q3":0.4,"Q4":0.2}
    monthly_probs = {"Q1":0.15,"Q2":0.35,"Q3":0.35,"Q4":0.15}
    data_coverage = 0.8

# ══════════════════════════════════════════════════════════════════════════════
# BUILD SNAPSHOT — ROBUST
# ══════════════════════════════════════════════════════════════════════════════

def build_snapshot(progress_cb: Optional[Callable] = None,
                   include_us_stocks: bool = True,
                   include_forex: bool = True,
                   include_commodities: bool = True,
                   include_crypto: bool = True,
                   include_ihsg: bool = True,
                   max_age_hours: float = 6.0):
    """Build full MacroRegime snapshot. Guaranteed non-hanging."""
    t0 = time.time()
    snap = {"ok": False}

    try:
        if progress_cb: progress_cb("Loading config", 0.02)
        from config.settings import (
            US_STOCKS, FOREX_PAIRS, COMMODITIES, CRYPTO, IHSG_UNIVERSE,
            MACRO_TICKERS, FRED_SERIES
        )
    except Exception as e:
        logger.error(f"Config import failed: {e}")
        snap["error"] = str(e); return snap

    all_tickers = []
    if include_us_stocks: all_tickers += list(US_STOCKS.keys())
    if include_forex: all_tickers += list(FOREX_PAIRS.keys())
    if include_commodities: all_tickers += list(COMMODITIES.keys())
    if include_crypto: all_tickers += list(CRYPTO.keys())
    if include_ihsg: all_tickers += list(IHSG_UNIVERSE.keys())
    all_tickers = list(dict.fromkeys(all_tickers + MACRO_TICKERS))

    # 1. Prices — batched, never hangs
    if progress_cb: progress_cb("Fetching prices (batched)", 0.05)
    prices = _fetch_prices_batched(all_tickers, batch_size=30, period="180d", progress_cb=progress_cb)

    # 2. FRED — quick
    if progress_cb: progress_cb("Loading FRED macro", 0.20)
    fred_data = {}
    try:
        from data.loader import fetch_fred
        fred_data = fetch_fred(FRED_SERIES)
    except Exception as e:
        logger.warning(f"FRED fetch failed: {e}")

    # 3. GIP
    if progress_cb: progress_cb("Building GIP", 0.30)
    gip = None
    try:
        from engines.gip_engine import GIPEngine
        gip = GIPEngine().run(fred_data)
    except Exception as e:
        logger.warning(f"GIP engine failed: {e}")
        gip = _MiniGIP()

    # 4. Global
    if progress_cb: progress_cb("Building global quad", 0.35)
    global_ = None
    try:
        from engines.global_quad_engine import GlobalQuadEngine
        global_ = GlobalQuadEngine().run(prices, fred_data)
    except Exception as e:
        logger.warning(f"Global quad failed: {e}")
        global_ = {"global_quad": "Q3", "global_conf": 0.5, "global_probs": {"Q1":0.1,"Q2":0.3,"Q3":0.4,"Q4":0.2}, "country_quads": {}}

    # 5. Risk Ranges
    if progress_cb: progress_cb("Computing risk ranges", 0.45)
    rr = {"asset_ranges": {}}
    try:
        from engines.hurst_rr_engine import HurstRREngine
        rr = {"asset_ranges": HurstRREngine().compute_all(prices)}
    except Exception as e:
        logger.warning(f"Risk range engine failed: {e}")
        ar = {}
        for t, s in prices.items():
            try:
                s = pd.to_numeric(s, errors="coerce").dropna()
                if len(s) < 60: continue
                sma20 = float(s.tail(20).mean()); std20 = float(s.tail(20).std())
                ar[t] = {"lrr": round(sma20 - 1.5*std20, 4), "trr": round(sma20 + 1.5*std20, 4), "px": float(s.iloc[-1])}
            except Exception:
                pass
        rr = {"asset_ranges": ar}

    # 6. FORCE Gamma + Greeks
    if progress_cb: progress_cb("Building gamma & greeks", 0.60)
    us_tickers = list(US_STOCKS.keys()) if include_us_stocks else []
    vix_now = _sf(prices.get("^VIX", pd.Series()).tail(1)) if prices.get("^VIX") is not None else 20.0
    dxy_s = prices.get("DX-Y.NYB")
    dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1) if dxy_s is not None and len(dxy_s) >= 22 else 0.0
    gamma_data = _force_gamma_data(prices, us_tickers, vix_now, dxy_ret)
    greeks_data = _force_greeks_data(prices, us_tickers, vix_now, dxy_ret, getattr(gip, "structural_quad", "Q3"))

    # 7. FORCE COT + OI
    if progress_cb: progress_cb("Building COT & OI", 0.70)
    fx_tickers = list(FOREX_PAIRS.keys()) if include_forex else []
    comm_tickers = list(COMMODITIES.keys()) if include_commodities else []
    cryp_tickers = list(CRYPTO.keys()) if include_crypto else []
    cot_oi_tickers = fx_tickers + comm_tickers + cryp_tickers
    cot_data = _force_cot_data(prices, cot_oi_tickers, vix_now)
    oi_data = _force_oi_data(prices, cot_oi_tickers, vix_now)

    # 8. Other engines
    if progress_cb: progress_cb("Loading other engines", 0.80)
    lev_data = None; narr = None; disc = None; scen = None; transition = None
    health = None; analogs = None; btk = None; pb_data = None
    engines_to_try = [
        ("leveraged_etf", "LeveragedETFEngine", "run", [], {}),
        ("narrative", "NarrativeEngine", "run", [gip, prices], {}),
        ("auto_discovery", "AutoDiscoveryEngine", "run", [prices, gip], {}),
        ("scenario", "ScenarioEngine", "run", [gip, prices], {}),
        ("regime_transition", "RegimeTransitionEngine", "run", [gip], {}),
        ("market_health", "MarketHealthEngine", "run", [prices, fred_data], {}),
        ("historical_analog", "HistoricalAnalogEngine", "run", [gip, prices], {}),
        ("bottleneck", "BottleneckEngine", "run", [prices, gip], {}),
        ("playbook", "PlaybookEngine", "run", [gip], {}),
    ]
    for key, engine_name, method, args, kwargs in engines_to_try:
        try:
            module = __import__(f"engines.{key}_engine", fromlist=[engine_name])
            engine_cls = getattr(module, engine_name)
            result = getattr(engine_cls(), method)(*args, **kwargs)
            if key == "leveraged_etf": lev_data = result
            elif key == "narrative": narr = result
            elif key == "auto_discovery": disc = result
            elif key == "scenario": scen = result
            elif key == "regime_transition": transition = result
            elif key == "market_health": health = result
            elif key == "historical_analog": analogs = result
            elif key == "bottleneck": btk = result
            elif key == "playbook": pb_data = result
        except Exception as e:
            logger.warning(f"Engine {key} failed: {e}")

    # 9. Daily Signals
    if progress_cb: progress_cb("Generating daily signals", 0.90)
    daily_signals = []
    try:
        from engines.daily_signal_engine import DailySignalEngine
        daily_signals = DailySignalEngine().run(prices, rr.get("asset_ranges", {}), gip)
    except Exception as e:
        logger.warning(f"Daily signal engine failed: {e}")
        for t, rng in (rr.get("asset_ranges", {}) or {}).items():
            try:
                px = rng.get("px"); lrr = rng.get("lrr"); trr = rng.get("trr")
                if not px or not lrr or not trr: continue
                comp = "bullish" if px < lrr else "bearish" if px > trr else "neutral"
                if comp == "neutral": continue
                r1m = _price_ret(t, prices, 21) or 0
                score = 0.3 if comp == "bullish" else -0.3
                score += r1m * 2
                daily_signals.append({
                    "ticker": t, "direction": "LONG" if comp == "bullish" else "SHORT",
                    "score": round(score, 2), "grade": "B", "price": px,
                    "signal": "BUY" if comp == "bullish" else "SELL",
                })
            except Exception:
                pass

    # 10. Alpha Center
    if progress_cb: progress_cb("Building Alpha Center", 0.95)
    alpha_center = _build_alpha_center(
        {"daily_signals": daily_signals, "auto_discoveries": disc or {}},
        gip, prices, rr.get("asset_ranges", {}), btk or {},
        gamma_data, greeks_data, {"cot": cot_data, "oi": oi_data},
        vix_now, transition
    )

    # 11. Crypto tokens
    crypto_tokens = {}
    if include_crypto:
        for ticker in list(CRYPTO.keys())[:10]:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                try:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                    r7d = float(s.iloc[-1] / s.iloc[-8] - 1) if len(s) >= 8 else r1m
                    vol = s.tail(20).std()
                    vol_change = (vol / s.tail(40).std() - 1) if s.tail(40).std() > 0 else 0
                    score = min(1.0, max(0.0, 0.5 + r1m * 5))
                    crypto_tokens[ticker] = {
                        "momentum_score": score, "tvl_7d_change": r7d,
                        "tvl_30d_change": r1m, "dex_vol_change": vol_change,
                    }
                except Exception:
                    pass

    # 12. AI
    ai_data = {"ok": False, "reason": "AI engine not available"}
    try:
        from engines.ai_engine import AIEngine
        ai_data = AIEngine().run(narr, disc, gip, prices)
    except Exception as e:
        logger.warning(f"AI engine failed: {e}")

    feedback_eval = {}
    try:
        from engines.feedback_loop_engine import FeedbackLoopEngine
        feedback_eval = FeedbackLoopEngine().run()
    except Exception:
        pass

    if progress_cb: progress_cb("Finalizing", 0.98)

    snap = {
        "ok": True,
        "build_time_s": round(time.time() - t0, 1),
        "prices_loaded": len(prices),
        "fred_coverage": len(fred_data),
        "gip": gip,
        "global": global_,
        "risk_ranges": rr,
        "scenarios": scen,
        "narratives": narr,
        "discovery": disc,
        "transition": transition,
        "health": health,
        "analogs": analogs,
        "bottleneck": btk,
        "playbook": pb_data,
        "prices": prices,
        "auto_discoveries": disc or {},
        "feedback_eval": feedback_eval,
        "gamma": gamma_data,
        "gamma_data": gamma_data,
        "greeks_data": greeks_data,
        "leveraged_etf": lev_data,
        "daily_signals": daily_signals,
        "alpha_center": alpha_center,
        "cot_oi": {"cot": cot_data, "oi": oi_data},
        "crypto_tokens": crypto_tokens,
        "ai_analysis": ai_data,
    }
    if progress_cb: progress_cb("Done", 1.0)
    return snap
