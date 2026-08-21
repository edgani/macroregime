# Legacy Quarantine Scan

The bundled legacy Warroom repository is retained only as historical/reference code. It is NOT imported by final_core/production_entry.py.

## Potential technical/synthetic production paths detected in legacy code
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:7:  TREND    : breadth (% di atas MA50/MA200) + momentum (median RS63) + market structure (trend quality).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:13:  WEALTH   : momentum tema sekuler (AI=SMH, Power=proxy, Nuclear=NLR/URA, India=INDA, Robotics=BOTZ,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:16:             pakai synthetic + flag. Ini SATU-SATUNYA yang genuinely butuh FRED buat akurat.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:45:# ─────────────────────────────── TREND (breadth + momentum + structure) ───────────────────────────────
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:132:# ─────────────────────────────── WEALTH (secular theme momentum) ───────────────────────────────
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:156:            "basis": " · ".join(f"{k} {v*100:+.0f}%" for k, v in sorted(scores.items(), key=lambda x: -x[1])[:4]) + " (theme ETF momentum)",
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:170:        synthetic = a.get("synthetic", False) or a.get("basis") == "synthetic"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:172:        if synthetic:
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:173:            status += " (synthetic — wire FRED_API_KEY)"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/meters.py:175:        return {"name": "Liquidity", "value": val, "status": status, "color": col, "real": not synthetic,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/causal_chain.py:7:     is currently CONFIRMING or NOT from live price momentum. A chain with most links confirming = thesis
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/causal_chain.py:13:HONEST: the chains are a CURATED library (priors), and 'confirming/flip' come from simple price momentum,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/causal_chain.py:27:     "flips": [{"label": "DXY peaks — momentum rolls over", "a": "DX-Y.NYB", "sig": "roll_down"},
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/causal_chain.py:28:               {"label": "XAU prints a bottom — gold momentum turns up", "a": "GLD", "sig": "turn_up"}]},
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/causal_chain.py:35:               {"label": "Gold momentum rolls over", "a": "GLD", "sig": "roll_down"}]},
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/synthesis.py:8:    ACT · ACT-SMALL · WAIT · AVOID · EXIT-WATCH
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/synthesis.py:148:        call = "ACT-SMALL"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/synthesis.py:160:    if call in ("ACT", "ACT-SMALL"):
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/internals.py:45:    # concentration: top-5 momentum share (are gains narrow or broad?)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/internals.py:60:            "top5_momentum_share": round(top5_share, 0) if top5_share else None,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/internals.py:77:    narrow = (b.get("top5_momentum_share") or 0) > 60
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/internals.py:81:        mode, style, col = "EXPANSION", "momentum — continuation valid, add on acceptance", "grn"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/internals.py:83:        mode, style, col = "PINNING", "range — fade extremes, don't chase breakouts", "gry"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crowd.py:5:above its 50DMA + average RSI + average extension. Extreme heat = euphoria (fade / reversal risk);
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/macro_regime.py:10:  • RISK-ON/OFF regime (trend + dollar-falling + momentum) memprediksi drawdown: corr +0.28 (p<0.0001).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/macro_regime.py:68:            "components": {"trend_above_10ma": bool(trend), "momentum_positive": bool(mom), "dollar_falling": bool(dxy_dn)},
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/market_cap_target.py:17:  • Convexity: upside/downside, EV (probability-weighted), max permanent loss, tail ratio
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/market_cap_target.py:22:HONEST: multiples & probabilitas = prior. Validasi lewat outcome (tracker) + backtest. Ga ada DCF penuh;
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/market_cap_target.py:30:# p_* = probabilitas skenario (jumlah = 1). dilution = haircut buat share issuance/unlock.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/market_cap_target.py:168:    """Convexity dari scenario tree: upside/downside %, EV (probability-weighted), max permanent loss,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/early_warning.py:8:  ⚠️ EUPHORIA = TOP: LEMAH di sample ini (p=0.34) — bias bull-market 2013-18. Butuh data 2008/2020/2022
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/early_warning.py:12:  fg = 40%·(1−VIX_pct) + 30%·(1−breadth_below_50ma) + 30%·momentum_z
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/brief_export.py:118:    # 3 Liquidity — from funding_stress (FRED); price-proxy synthetic flag if no key
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/brief_export.py:126:    # 5 Wealth — secular theme momentum (price)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/brief_export.py:135:    # 8 Trend — breadth + momentum + structure (price)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/rotation.py:5:it out/under-performing) and RS momentum (is that improving or fading), then place it in a rotation
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/rotation.py:35:    mom = float(rs.iloc[-1] / rs.iloc[-mom_lb - 1] - 1)        # RS momentum
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/rotation.py:84:    # fast movers (high |momentum| = fast rotation, don't get left behind)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/thesis_playbook.py:6:  • THESIS CARD (#1 audit doc-6): hypothesis, evidence, mechanism, beneficiaries, probability, horizon,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/thesis_playbook.py:25:        "probability": 0.78, "horizon": "2026-2028",
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/thesis_playbook.py:34:        "probability": 0.74, "horizon": "2025-2030",
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/thesis_playbook.py:43:        "probability": 0.68, "horizon": "2026-2027",
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/thesis_playbook.py:87:    return [{"name": k, "status": v["status"], "probability": v["probability"], "horizon": v["horizon"]}
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/cycle_rotation.py:187:            {"pair": "MTUM/SPY (momentum)", **(momo or {})}]
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/themes.py:6:momentum of its names), and traces from the hot nodes along the edges to the ADJACENT themes that
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/signal_edge.py:7:  • Sinyal absolut (breakout, volume-spike, base-breakout) → lift 0.56-1.01x = TIDAK ada edge.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/data.py:3:then live yfinance, then deterministic synthetic so the app ALWAYS renders.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/data.py:58:def _synth(t, n=420):
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/data.py:105:                cached.setdefault(t, _synth(t, days))
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/data.py:110:        cached.setdefault(t, _synth(t, days))
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/data.py:111:    return cached, ("synthetic · demo (no live feed)" if not _from_cache(tickers) else "cache + synthetic")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/attention.py:8:Tiap item: judul, status, arah (naik/turun/breakout/confirm), dan skor urgency 0-100. Semua diturunkan
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/lpm.py:35:    """mode='cumulative' -> cumsum; mode='windowed' -> rolling(window).sum. Then EMA(span)."""
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/timing.py:8:  • Exit anticipation — when to scale out BEFORE the herd (TREND ceiling, RSI stretch, distribution).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/timing.py:11:Uses price structure (extension vs 50DMA, RSI, 60d range position, 20d momentum, ATR) + the Hedgeye
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/timing.py:67:        phase, fomo, entry_t = "Distribution / stalling", "LATE — crowd already in", "prepare exit; momentum fading at the highs"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/timing.py:93:        ex.append(f"RSI {rsi:.0f} stretched — trail / take partials")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:98:    changed = ("momentum accelerating" if ac > 0 else "momentum decelerating") + f" ({ac:+.0f}% 21d vs 63d)"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:99:    trapped = ("late momentum longs" if dr == "Short" else "underweight allocators" if dr == "Long" else "both sides undecided")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:486:    ck = {"ACT": "grn", "ACT-SMALL": "grn", "WAIT": "amb", "AVOID": "red", "EXIT-WATCH": "amb"}.get(call, "gry")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:532:        return "<span class='wr-note'>quad probabilities need FRED (live on your machine).</span>"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:640:            "EV = probability-weighted. Alpha dipisah: TACTICAL &lt;20% · STRATEGIC 20-80% · GENERATIONAL 10x+. "
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:641:            "Multiples & probabilitas = PRIOR yang bisa lu kalibrasi di market_cap_target.py — bukan presisi karangan.</div>")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:677:    quad_html = (f"<div class='wr-lbl'>Quad path — next-quad probability (Hedgeye GIP)</div>"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:735:                      f"<span class='wr-why'>heat {cm['heat']}/100 · {cm['pct_above50']}% above 50DMA · avg RSI {cm['avg_rsi']} — {cm['verdict']}</span></div>")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:849:             + _tile("DXY momentum", (f"{dm:+.1f}%" if dm is not None else "—"), "21d", "sub"))
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:851:    html = (f"<div class='wr-top'><b>FX</b><span>DXY · momentum · setups</span></div>"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:856:            f"<div class='wr-note'>Carry / rate-differential need FRED rates (engine: fx_carry) — absent, not faked. DXY trend/momentum + setups are price-derived.</div>")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:892:            f"<div class='wr-note' style='margin-top:8px;'>Rotation from 21d sector ETF momentum. Green = inflow leadership, red = outflow.</div>")
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:1207:    # 4. crash probability — extract type/pressure/basis
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:1362:    note = "<div class='wr-note'>Ant Markets discipline: hold a hypothesis, watch for disconfirming evidence, switch when it fires. Chains are curated priors; link/flip status is from 20-day price momentum — a reasoning checklist, not proven causality.</div>"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:1387:        ("Crash lead-time (24mo risk)", "PRODUCTION", "grn", "probabilistic, honestly bounded"),
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:1391:        ("Sector/asset rotation momentum", "RESEARCH", "amb", "descriptive; not proven predictive"),
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:2075:                        f"<div class='mcx-atttitle'>{t['name']} <span style='font-size:11px;color:#8b97a7;font-weight:400'>P={t['probability']:.0%} · {t['horizon']}</span></div>"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:2121:    if b and b.get("top5_momentum_share"):
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:2122:        narrow = (b["top5_momentum_share"] or 0) > 60
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/render.py:2123:        extra += (f"<div class='wr-note'><b>Concentration:</b> top-5 names carry {int(b['top5_momentum_share'])}% of the universe's gains — "
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/statelog.py:65:        ev.append((sev, f"Shock probability: {prev.get('shock')} → {curr.get('shock')}"))
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:1:"""warroom/crash_lead.py — EARLY WARNING SYSTEM: seberapa early bisa warn crash? (jujur, probabilistik).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:13:  • Lead terkuat: prior vol (persisten, semua horizon) + momentum melemah (~6-18mo lead).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:28:    """Composite early-warning score → probabilistic crash risk at 12/24/36mo. panel: DataFrame monthly
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:29:    with spx, cape, rate10, cpi_yoy. Returns probability + positioning (NOT a binary sell)."""
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:55:    # map score → crash probability multiplier (from tested table)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:59:    # momentum-based nearer-term flag (~6-18mo lead)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/crash_lead.py:75:            "momentum_warning": mom_warn, "action": action,
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/funding_stress.py:5:Live: pulls FRED (no key needed via fredgraph CSV). Sandbox/offline: synthetic fallback (flagged).
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/funding_stress.py:30:def _synth():
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/funding_stress.py:50:        data = _synth(); src = "synthetic · demo (set FRED access for live)"
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/country_regime.py:6:country's regime is derived from its US-listed equity ETF (growth proxy = 63d vs 126d momentum) and
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/country_regime.py:40:    """growth = 63d-126d momentum accel of the country ETF; inflation = shared commodity tilt.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/country_regime.py:96:            "note": ("price-proxy quads (retail-grade, coincident) — growth from country ETF momentum, "
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/investment_memo.py:7:  · Scenario probability · Catalyst timeline · Invalidation · Alternative · Beta play · Decision (best
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/fred.py:30:    # 1) robust loader from the repo: FRED API key -> fredgraph CSV -> DBnomics -> synthetic, parquet-cached
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/price_action.py:12:  low effort + big result     -> NO-SUPPLY / NO-DEMAND (thin, suspect, easy to reverse)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:18:Precise probabilities need Fed funds futures (CME) — this is the curve-implied first order.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:136:def fed_probabilities(cme_implied=None, rate=None):
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:137:    """Market-implied probability of the next Fed move.
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:141:    ...} and this returns it cleaned. Without it, there is NO clean probability — fall back to the
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:142:    curve-implied direction in rate_path() (a bias, not a probability). This function never fabricates
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/policy.py:150:                f"(~{rate.get('implied_25s','?')}\u00d725bps over ~1y). Plug CME FedWatch for true probabilities."}
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/compute.py:484:                # use live for the risk-regime trend/momentum; keep macro panel for quad/inflation
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/compute.py:490:    # Crash lead-time early warning (probabilistic, multi-horizon — how early can we warn)
/mnt/data/EROS_SELF_FINAL/EROS_AGENT_COMPLETE_BUNDLE_v2/warroom_os/warroom/compute.py:663:    return v if 5.0 <= v <= 60.0 else 20.0   # guard against synthetic/bogus VIX
