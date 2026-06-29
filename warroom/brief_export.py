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
    """Composite 0-100 meters — ONLY the ones with real data. Missing-feed meters are flagged, not faked."""
    crash = d.get("crash") or {}; cr = d.get("cycle_rotation") or {}; conv = d.get("conviction") or []
    out = []
    cp = crash.get("pressure")
    if isinstance(cp, (int, float)):
        out.append({"name": "Crash", "value": round(cp), "status": crash.get("type", "—"),
                    "color": "grn" if cp < 40 else "amb" if cp < 65 else "red",
                    "components": [k.replace("_", " ") for k in (crash.get("components") or {})][:6], "real": True})
    sc = cr.get("score"); n = cr.get("n_axes") or 7
    if isinstance(sc, (int, float)):
        out.append({"name": "Rotation", "value": round(abs(sc) / n * 100), "status": cr.get("compass", "—"),
                    "color": cr.get("color", "amb"), "components": [a.get("name") for a in cr.get("axes", [])][:6], "real": True})
    if conv:
        cv = round(max((r.get("score", 0) or 0) for r in conv))
        out.append({"name": "Conviction", "value": min(cv, 100), "status": "top setup", "color": "inf",
                    "components": ["regime", "rotation", "flow", "entry"], "real": True})
    try:
        from warroom import optimal_entry as OE
        qs = [OE.quality(r.get("_dir"), r.get("lrr"), r.get("trr"), r.get("close") or r.get("px"), r.get("timing"))[0]
              for r in conv[:5] if r.get("lrr") and r.get("trr")]
        qs = [q for q in qs if q is not None]
        if qs:
            ev = round(sum(qs) / len(qs))
            out.append({"name": "Entry", "value": ev, "status": "scale-in" if ev >= 60 else "wait" if ev < 45 else "selective",
                        "color": "grn" if ev >= 60 else "amb", "components": ["risk range", "timing", "location"], "real": True})
    except Exception:
        pass
    for nm, comp in [("Liquidity", ["Fed", "ECB", "BOJ", "RRP", "TGA", "M2"]), ("Credit", ["HY", "IG", "CDS", "bank funding"]),
                     ("Bubble", ["valuation", "leverage", "sentiment", "options"]), ("Trend", ["breadth", "momentum", "internals"])]:
        out.append({"name": nm, "value": None, "status": "needs data feed", "color": "gry", "components": comp, "real": False})
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
    }


def export(d, out_path=None):
    out_path = out_path or os.path.join(_DIR, "briefing.html")
    data = brief_dict(d)
    html = open(_TEMPLATE, encoding="utf-8").read()
    inject = "<script>window.BRIEF=" + json.dumps(data) + ";</script>\n</head>"
    html = html.replace("</head>", inject, 1)
    open(out_path, "w", encoding="utf-8").write(html)
    return out_path
