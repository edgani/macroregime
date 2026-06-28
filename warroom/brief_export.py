"""warroom/brief_export.py — export the day's brief into the interactive deck (briefing.html).

Builds a compact JSON from compute's output `d` and injects it into briefing_template.html so the
deck renders with live data, fully self-contained (no server / no CDN — opens offline). app.py calls
export(d) each run; the deck always carries the latest snapshot.
"""
import os, json

_DIR = os.path.dirname(os.path.dirname(__file__))
_TEMPLATE = os.path.join(_DIR, "briefing_template.html")


def _safe(x):
    if isinstance(x, dict):
        return x.get("text") or x.get("summary") or x.get("label") or x.get("name") or str(x)
    return str(x)


def brief_dict(d):
    reg = d.get("regime") or {}
    rt = reg.get("regime_transition") if isinstance(reg.get("regime_transition"), dict) else {}
    crash = d.get("crash") or {}
    cr = d.get("cycle_rotation") or {}
    axes = [{"name": a.get("name"), "vote": a.get("vote", 0), "verdict": a.get("verdict", ""),
             "down": a.get("down_curve", ""), "up": a.get("up_curve", "")} for a in cr.get("axes", [])]
    # conviction with risk range + entry quality
    conv = []
    try:
        from warroom import optimal_entry as OE
    except Exception:
        OE = None
    for r in (d.get("conviction") or [])[:4]:
        q, why = (None, "")
        if OE is not None:
            try:
                q, why = OE.quality(r.get("_dir"), r.get("lrr"), r.get("trr"), r.get("close") or r.get("px"), r.get("timing"))
            except Exception:
                pass
        lrr, trr = r.get("lrr"), r.get("trr")
        conv.append({"ticker": r.get("ticker"), "dir": r.get("_dir"), "px": r.get("px"),
                     "entry": r.get("entry"), "stop": r.get("stop"), "target": r.get("target"),
                     "rr": (f"{lrr:.2f}–{trr:.2f}" if (lrr and trr) else ""),
                     "quality": q, "why": (why or (r.get("form") or "")).strip()})
    return {
        "date": str(d.get("data_asof") or d.get("data_asof") or ""),
        "regime": {"structural": reg.get("structural", "—"), "monthly": reg.get("monthly", "—"),
                   "operating": reg.get("operating", ""), "why": rt.get("summary", "") or reg.get("operating", ""),
                   "posture": reg.get("posture", "—")},
        "crash": {"type": crash.get("type", "—"), "pressure": crash.get("pressure"), "basis": crash.get("basis", "")},
        "compass": {"state": cr.get("compass", "—"), "color": cr.get("color", "amb"), "score": cr.get("score", 0),
                    "down": cr.get("down_axes", 0), "up": cr.get("up_axes", 0), "meaning": cr.get("meaning", ""), "axes": axes},
        "changed": [_safe(x) for x in (d.get("whatchanged") or [])][:7],
        "conviction": conv,
    }


def export(d, out_path=None):
    out_path = out_path or os.path.join(_DIR, "briefing.html")
    data = brief_dict(d)
    html = open(_TEMPLATE, encoding="utf-8").read()
    inject = "<script>window.BRIEF=" + json.dumps(data) + ";</script>\n</head>"
    html = html.replace("</head>", inject, 1)
    open(out_path, "w", encoding="utf-8").write(html)
    return out_path
