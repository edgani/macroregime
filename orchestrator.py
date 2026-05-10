"""
PATCH for orchestrator.py — Loosened Alpha Center + Daily Signals filters
Replace these functions in your existing orchestrator.py
"""

# ══════════════════════════════════════════════════════════════════════════════
# REPLACE: _build_alpha_center function
# ══════════════════════════════════════════════════════════════════════════════

def _build_alpha_center(snap, gip, prices, ar, btk, gamma_data, greeks_data, cot_oi_data, vix_now, transition):
    """Build Alpha Center with LOOSENED filters — include more tickers."""
    import pandas as pd
    import math

    items = []

    # 1. Bottleneck tickers (keep existing logic)
    for ticker, info in (btk or {}).items():
        if not isinstance(info, dict): continue
        direction = info.get("direction", "LONG")
        known_thesis = info.get("known_thesis", "")
        confidence = info.get("confidence", 0)

        # LOOSENED: include confidence >= 0.40 (was 0.50)
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

        # Determine level
        if score >= 0.80 and rr_lv["rr"] >= 2.0 and rr_lv["near_entry"]:
            level = "level_1"
            scanner = "URGENT"
        elif score >= 0.60 and rr_lv["rr"] >= 1.5:
            level = "level_2"
            scanner = "BUILDING"
        elif score >= 0.40:
            level = "watch"
            scanner = "WATCH"
        else:
            level = "discovery"
            scanner = "DISCOVERY"

        # Enrich with Greeks/Gamma if available
        gamma_reg = "—"; greek_comp = "—"; max_pain = "—"
        if gamma_data and ticker in gamma_data:
            gd = gamma_data[ticker]
            gamma_reg = gd.get("regime", "—")
            max_pain = gd.get("max_pain", "—")
        if greeks_data and ticker in greeks_data:
            greek_comp = greeks_data[ticker].get("composite", "—")

        item = {
            "ticker": ticker,
            "price": px,
            "entry": rr_lv["entry"],
            "target_1": rr_lv["tp1"],
            "target_2": rr_lv["tp2"],
            "stop_loss": rr_lv["stop"],
            "rr": rr_lv["rr"],
            "direction": direction,
            "grade": grade,
            "score": score,
            "worth_entering": rr_lv["action"],
            "entry_advice": rr_lv["action"],
            "tp1_basis": "Risk Range 50% — momentum target",
            "tp2_basis": "Risk Range top (TRR) — stretch",
            "stop_basis": "Below Risk Range low (LRR) — invalidation",
            "path_smoothness": "🟢 Smooth" if score > 0.7 else "🟡 Bumpy",
            "time_estimate": rr_lv["hold"],
            "breakout_chance": "High" if score > 0.75 else "Medium" if score > 0.50 else "Low",
            "hold": rr_lv["hold"],
            "thesis": known_thesis,
            "recommendation": known_thesis,
            "known_thesis": known_thesis,
            "scanner_type": scanner,
            "level": level,
            "gamma_regime": gamma_reg,
            "greek_composite": greek_comp,
            "max_pain": max_pain,
            "invalidators": info.get("invalidators", ["Q4 signal"]),
        }
        items.append(item)

    # 2. Daily Signals — LOOSENED: include |score| >= 0.10 (was 0.70 for STRONG)
    daily_signals = snap.get("daily_signals", [])
    for s in daily_signals:
        if not isinstance(s, dict): continue
        score = abs(s.get("score", 0))
        if score < 0.10: continue  # ← LOOSENED from 0.70

        ticker = s.get("ticker", "")
        direction = s.get("direction", "NEUTRAL")

        # Categorize into alpha_long / alpha_short / watch
        if "LONG" in direction and score >= 0.50:
            s["scanner_type"] = "ALPHA LONG"
            s["level"] = "alpha_long"
        elif "SHORT" in direction and score >= 0.50:
            s["scanner_type"] = "ALPHA SHORT"
            s["level"] = "alpha_short"
        else:
            s["scanner_type"] = "WATCH"
            s["level"] = "watch"

        # Enrich missing fields for narrative card
        if "entry" not in s or s["entry"] is None:
            s["entry"] = s.get("price", 0) * 0.98
        if "target_1" not in s or s["target_1"] is None:
            s["target_1"] = s.get("price", 0) * 1.05
        if "target_2" not in s or s["target_2"] is None:
            s["target_2"] = s.get("price", 0) * 1.10
        if "stop_loss" not in s or s["stop_loss"] is None:
            s["stop_loss"] = s.get("price", 0) * 0.93
        if "rr" not in s or s["rr"] is None:
            s["rr"] = 1.5
        if "entry_advice" not in s:
            s["entry_advice"] = s.get("worth_entering", "⏳ WAIT")
        if "tp1_basis" not in s:
            s["tp1_basis"] = "Technical momentum target"
        if "tp2_basis" not in s:
            s["tp2_basis"] = "Stretch target — regime aligned"
        if "stop_basis" not in s:
            s["stop_basis"] = "Below support — invalidation"
        if "path_smoothness" not in s:
            s["path_smoothness"] = "🟡 Normal"
        if "time_estimate" not in s:
            s["time_estimate"] = "2-4 weeks"
        if "breakout_chance" not in s:
            s["breakout_chance"] = "Medium"
        if "hold" not in s:
            s["hold"] = "2-4 weeks"
        if "thesis" not in s:
            s["thesis"] = s.get("recommendation", f"{ticker} — {direction} signal with score {score:.2f}")
        if "invalidators" not in s:
            s["invalidators"] = ["Q4 signal", "VIX > 35"]

        items.append(s)

    # 3. Discovery / Auto-discoveries
    auto_disc = snap.get("auto_discoveries", {})
    for b in (auto_disc.get("bottlenecks", []) if auto_disc else []):
        if not isinstance(b, dict): continue
        b["scanner_type"] = "AUTO-DISCOVERY"
        b["level"] = "discovery"
        if "score" not in b: b["score"] = 0.5
        if "grade" not in b: b["grade"] = "B"
        items.append(b)

    # Categorize
    level_1 = [i for i in items if i.get("level") == "level_1"]
    level_2 = [i for i in items if i.get("level") == "level_2"]
    watch = [i for i in items if i.get("level") == "watch"]
    alpha_long = [i for i in items if i.get("level") == "alpha_long"]
    alpha_short = [i for i in items if i.get("level") == "alpha_short"]
    discovery = [i for i in items if i.get("level") == "discovery"]

    # Sort by score
    level_1 = sorted(level_1, key=lambda x: x.get("score", 0), reverse=True)
    level_2 = sorted(level_2, key=lambda x: x.get("score", 0), reverse=True)
    watch = sorted(watch, key=lambda x: x.get("score", 0), reverse=True)
    alpha_long = sorted(alpha_long, key=lambda x: x.get("score", 0), reverse=True)
    alpha_short = sorted(alpha_short, key=lambda x: x.get("score", 0), reverse=True)
    discovery = sorted(discovery, key=lambda x: x.get("score", 0), reverse=True)

    meta = {
        "regime": f"{gip.structural_quad if gip else 'Q3'} / {gip.monthly_quad if gip else 'Q2'}",
        "bias": gip.bias if gip else "neutral",
        "vix": f"{vix_now:.1f}" if vix_now else "—",
        "total_items": len(items),
        "level_1_count": len(level_1),
        "level_2_count": len(level_2),
        "watch_count": len(watch),
        "alpha_long_count": len(alpha_long),
        "alpha_short_count": len(alpha_short),
        "discovery_count": len(discovery),
        "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    }

    return {
        "meta": meta,
        "level_1": level_1,
        "level_2": level_2,
        "watch": watch,
        "alpha_long": alpha_long,
        "alpha_short": alpha_short,
        "discovery": discovery,
    }


# ══════════════════════════════════════════════════════════════════════════════
# REPLACE: In build_snapshot(), add this line before returning:
# ══════════════════════════════════════════════════════════════════════════════
# snap["alpha_center"] = _build_alpha_center(snap, gip, prices, ar, btk, gamma_data, greeks_data, cot_oi_data, vix_now, transition)
