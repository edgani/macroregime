"""warroom/brief_export.py — export the day's brief into the interactive deck (briefing.html).

Builds a compact JSON from compute's `d` and injects it into briefing_template.html so the deck
renders the full 12-slide briefing with live data, self-contained (no server / CDN — opens offline).
Scenario tree + narrative lifecycle are DERIVED here from existing engine output (regime transition,
beta-play leader run) — no new engines. app.py calls export(d) each run.
"""
import os, json

_DIR = os.path.dirname(os.path.dirname(__file__))
_TEMPLATE = os.path.join(_DIR, "briefing_template.html")

QUAD_ASSETS = {
    "Quad 1": [["Tech / Nasdaq", "up"], ["Discretionary", "up"], ["Crypto", "up"], ["Small-caps", "up"]],
    "Quad 2": [["Energy", "up"], ["Materials / copper", "up"], ["EM equities", "up"], ["Gold", "up"]],
    "Quad 3": [["Gold", "up"], ["Energy", "up"], ["Staples", "up"], ["Long bonds", "down"]],
    "Quad 4": [["Utilities", "up"], ["Staples", "up"], ["USD", "up"], ["Equities", "down"]],
}


def _safe(x):
    if isinstance(x, dict):
        return x.get("text") or x.get("summary") or x.get("label") or x.get("name") or str(x)
    return str(x)


def _qassets(quad):
    if not quad:
        return []
    for k, v in QUAD_ASSETS.items():
        if k in str(quad):
            return v
    return []


def _scenarios(d):
    reg = d.get("regime") or {}
    rt = reg.get("regime_transition") if isinstance(reg.get("regime_transition"), dict) else {}
    out = []
    frm = rt.get("from_quad") or reg.get("structural")
    nxt = rt.get("implied_next") or reg.get("monthly")
    haz = rt.get("flip_hazard")
    if frm and nxt and str(frm) != str(nxt):
        p = int(round((haz if isinstance(haz, (int, float)) else 0.5) * 100))
        out.append({"trigger": f"{frm} → {nxt} turn confirms", "prob": p, "branch": _qassets(nxt)})
        out.append({"trigger": f"Turn fails — stays {frm}", "prob": 100 - p, "branch": _qassets(frm)})
    pol = d.get("policy") or {}
    if pol.get("bait") or pol.get("hike_75_priced"):
        out.append({"trigger": "Fed hike-shock (75bps bait plays out)", "prob": 25,
                    "branch": [["USD", "up"], ["Gold", "down"], ["Tech / Nasdaq", "down"], ["Crypto", "down"]]})
    return out


def _narrative(d):
    bp = d.get("beta_plays") or {}
    out = []
    for theme, info in bp.items():
        run = info.get("leader_run_pct")
        if run is None:
            continue
        if run < 10:
            stage, num = "Accumulation", 2
        elif run < 25:
            stage, num = "Early markup", 4
        elif run < 50:
            stage, num = "Markup", 6
        elif run < 80:
            stage, num = "Late markup", 8
        else:
            stage, num = "Distribution risk", 9
        out.append({"theme": theme.split("(")[0].strip(), "leader": info.get("leader"),
                    "run": round(run, 0), "stage": stage, "num": num})
    out.sort(key=lambda x: -x["num"])
    return out[:8]


def _bottleneck(d):
    bp = d.get("beta_plays") or {}
    tg = d.get("theme_graph") or {}
    themes = []
    for theme, info in bp.items():
        tiers = []
        for tname, rows in (info.get("tiers") or {}).items():
            for r in rows[:4]:
                tiers.append({"ticker": r.get("ticker"), "role": r.get("role", ""), "verdict": r.get("verdict", "")})
        themes.append({"name": theme.split("(")[0].strip(), "leader": info.get("leader"),
                       "run": round(info.get("leader_run_pct", 0), 0), "tiers": tiers[:8]})
    nd = [{"frm": x.get("from"), "to": x.get("to"), "rel": x.get("rel", "")} for x in tg.get("next_dots", [])[:5]]
    br = [{"ticker": x.get("ticker"), "themes": x.get("themes", [])} for x in tg.get("bridges", [])[:6]]
    return {"themes": themes, "next_dots": nd, "bridges": br}


def _why(d):
    drv = d.get("drivers") or {}
    tg = d.get("theme_graph") or {}
    pol = d.get("policy") or {}
    chains = [f"{x.get('from')} → {x.get('to')} ({x.get('rel', '')})" for x in tg.get("next_dots", [])[:5]]
    return {"summary": drv.get("summary", ""), "chains": chains,
            "bait": pol.get("bait", ""), "fed_lean": pol.get("fed_lean", "")}


def _meters(d):
    """10 composite meters matching the mockup. Real-data ones carry values; missing-feed ones are flagged, not faked."""
    crash = d.get("crash") or {}; cr = d.get("cycle_rotation") or {}; conv = d.get("conviction") or []
    reg = d.get("regime") or {}
    mc = d.get("meters_computed") or {}   # price-proxy meters (trend/credit/bubble/wealth/liquidity)
    out = []
    # 1 Macro — derived from regime quad confidence (real, from struct_probs)
    sp = reg.get("struct_probs") if isinstance(reg.get("struct_probs"), dict) else {}
    macro_v = round(max(sp.values()) * 100) if sp else None
    out.append({"name": "Macro", "value": macro_v, "status": f"{reg.get('structural', '—')}" + (f" / {reg.get('monthly')}" if reg.get('monthly') else ""),
                "color": "inf", "components": ["Growth", "PMI", "Employment", "Credit", "Yield", "Liquidity"], "real": macro_v is not None})
    # 2 Crash
    cp = crash.get("pressure")
    out.append({"name": "Crash", "value": round(cp) if isinstance(cp, (int, float)) else None,
                "status": crash.get("type", "—"), "color": "grn" if (cp or 0) < 40 else "amb" if (cp or 0) < 65 else "red",
                "components": [k.replace("_", " ") for k in (crash.get("components") or {})][:6], "real": isinstance(cp, (int, float))})
    # 3 Liquidity — from funding_stress (FRED); price-proxy synthetic flag if no key
    out.append(mc.get("liquidity") or {"name": "Liquidity", "value": None, "status": "needs data feed", "color": "gry",
                "components": ["Fed", "ECB", "BOJ", "RRP", "TGA", "M2"], "real": False})
    # 4 Rotation
    sc = cr.get("score"); n = cr.get("n_axes") or 7
    out.append({"name": "Rotation", "value": round(abs(sc) / n * 100) if isinstance(sc, (int, float)) else None,
                "status": cr.get("compass", "—"), "color": cr.get("color", "amb"),
                "components": ["ETF Flow", "Country Flow", "Sector Flow", "Cross Asset"], "real": isinstance(sc, (int, float))})
    # 5 Wealth — secular theme momentum (price)
    out.append(mc.get("wealth") or {"name": "Wealth", "value": None, "status": "needs data feed", "color": "gry",
                "components": ["AI", "Power Grid", "Nuclear", "India", "Robotics"], "real": False})
    # 6 Bubble — extension + vol + valuation (price)
    out.append(mc.get("bubble") or {"name": "Bubble", "value": None, "status": "needs data feed", "color": "gry",
                "components": ["Valuation", "Leverage", "Sentiment", "Options"], "real": False})
    # 7 Credit — ETF spread proxy (price)
    out.append(mc.get("credit") or {"name": "Credit", "value": None, "status": "needs data feed", "color": "gry",
                "components": ["HY", "IG", "CDS", "Bank Funding"], "real": False})
    # 8 Trend — breadth + momentum + structure (price)
    out.append(mc.get("trend") or {"name": "Trend", "value": None, "status": "needs data feed", "color": "gry",
                "components": ["Breadth", "Momentum", "Market Structure", "Internals"], "real": False})
    # 9 Entry
    try:
        from warroom import optimal_entry as OE
        qs = [OE.quality(r.get("_dir"), r.get("lrr"), r.get("trr"), r.get("close") or r.get("px"), r.get("timing"))[0]
              for r in conv[:5] if r.get("lrr") and r.get("trr")]
        qs = [q for q in qs if q is not None]
        ev = round(sum(qs) / len(qs)) if qs else None
    except Exception:
        ev = None
    out.append({"name": "Entry", "value": ev, "status": ("scale-in" if (ev or 0) >= 60 else "wait" if (ev or 0) < 45 else "selective") if ev is not None else "needs data",
                "color": "grn" if (ev or 0) >= 60 else "amb", "components": ["Trend", "Flow", "Valuation", "Positioning"], "real": ev is not None})
    # 10 Conviction
    cv = round(max((r.get("score", 0) or 0) for r in conv)) if conv else None
    out.append({"name": "Conviction", "value": min(cv, 100) if cv is not None else None, "status": "agreement across engines",
                "color": "inf", "components": ["all engines"], "real": cv is not None})
    return out


def _thesis_beta(d):
    tb = d.get("thesis_beta") or {}
    out = []
    for theme, info in list(tb.items())[:5]:
        out.append({"theme": theme, "leader": info.get("leader"),
                    "members": [{"ticker": m["ticker"], "beta": m["beta"], "conv": m["convexity"],
                                 "vol": m["ann_vol"], "asym": m["asym"]} for m in info.get("members", [])[:6]]})
    return out


def brief_dict(d):
    reg = d.get("regime") or {}
    rt = reg.get("regime_transition") if isinstance(reg.get("regime_transition"), dict) else {}
    crash = d.get("crash") or {}
    cr = d.get("cycle_rotation") or {}
    axes = [{"name": a.get("name"), "vote": a.get("vote", 0), "verdict": a.get("verdict", ""),
             "down": a.get("down_curve", ""), "up": a.get("up_curve", "")} for a in cr.get("axes", [])]
    try:
        from warroom import optimal_entry as OE
    except Exception:
        OE = None
    conv = []
    for r in (d.get("conviction") or [])[:4]:
        q, why = (None, "")
        if OE is not None:
            try:
                q, why = OE.quality(r.get("_dir"), r.get("lrr"), r.get("trr"), r.get("close") or r.get("px"), r.get("timing"))
            except Exception:
                pass
        lrr, trr = r.get("lrr"), r.get("trr")
        # asymmetry (Convexity/Asymmetric-Return spec): upside/downside/RR/EV/P/Kelly/tier
        asym = {}
        try:
            px = float(str(r.get("px")).replace(",", "")); stop = float(str(r.get("stop")).replace(",", "")); tgt = float(str(r.get("target")).replace(",", ""))
            dr = r.get("_dir")
            up = (tgt - px) / px * 100 if dr == "Long" else (px - tgt) / px * 100
            dn = (stop - px) / px * 100 if dr == "Long" else (px - stop) / px * 100
            if up > 0 and dn < 0:
                rr = up / abs(dn); prob = max(0.40, min(0.78, 0.40 + 0.35 * (max(r.get("score", 0) or 0, 0) / 100.0)))
                ev = prob * up + (1 - prob) * dn; kelly = max(0.0, min(0.25, (prob * rr - (1 - prob)) / rr))
                asym = {"up": round(up), "dn": round(dn), "rr": round(rr, 1), "ev": round(ev),
                        "prob": round(prob * 100), "kelly": round(kelly * 100),
                        "tier": "generational" if up >= 80 else "strategic" if up >= 20 else "tactical"}
        except Exception:
            pass
        conv.append({"ticker": r.get("ticker"), "dir": r.get("_dir"), "px": r.get("px"),
                     "entry": r.get("entry"), "stop": r.get("stop"), "target": r.get("target"),
                     "rr": (f"{lrr:.2f}–{trr:.2f}" if (lrr and trr) else ""),
                     "quality": q, "why": (why or (r.get("form") or "")).strip(), "asym": asym})
    return {
        "date": str(d.get("data_asof") or ""),
        "regime": {"structural": reg.get("structural", "—"), "monthly": reg.get("monthly", "—"),
                   "operating": reg.get("operating", ""), "why": rt.get("summary", "") or reg.get("operating", ""),
                   "posture": reg.get("posture", "—")},
        "crash": {"type": crash.get("type", "—"), "pressure": crash.get("pressure"), "basis": crash.get("basis", ""),
                  "components": crash.get("components", {}), "bottom": (crash.get("bottom") or {}).get("state", "")},
        "compass": {"state": cr.get("compass", "—"), "color": cr.get("color", "amb"), "score": cr.get("score", 0),
                    "down": cr.get("down_axes", 0), "up": cr.get("up_axes", 0), "meaning": cr.get("meaning", ""), "axes": axes},
        "changed": [_safe(x) for x in (d.get("whatchanged") or [])][:7],
        "conviction": conv,
        "why": _why(d),
        "bottleneck": _bottleneck(d),
        "scenarios": _scenarios(d),
        "narrative": _narrative(d),
        "meters": _meters(d),
        "thesis_beta": _thesis_beta(d),
        "causal": [{"name": c.get("name"), "verdict": c.get("verdict"), "color": c.get("color"),
                    "integrity": c.get("integrity"), "thesis": c.get("thesis"),
                    "links": [{"label": l["label"], "ok": l["ok"]} for l in c.get("links", [])],
                    "flips": [{"label": f["label"], "fired": f["fired"]} for f in c.get("flips", [])]}
                   for c in (d.get("causal_chains") or [])],
    }


def export(d, out_path=None):
    out_path = out_path or os.path.join(_DIR, "briefing.html")
    data = brief_dict(d)
    html = open(_TEMPLATE, encoding="utf-8").read()
    inject = "<script>window.BRIEF=" + json.dumps(data) + ";</script>\n</head>"
    html = html.replace("</head>", inject, 1)
    open(out_path, "w", encoding="utf-8").write(html)
    return out_path
