from __future__ import annotations

def validate_desk(desk: dict) -> dict:
    errors=[]; warnings=[]
    meta=desk.get("meta") or {}
    if str(meta.get("source", "")).upper().startswith("SYNTHETIC"):
        errors.append("synthetic source may not enter the user-facing dashboard")
    markets=desk.get("markets") or {}
    if "idx" in markets or "commodity" in markets:
        errors.append("non-canonical UI market key present")
    surfaced=set()
    for mk, market in markets.items():
        for row in market.get("setups") or []:
            tk=str(row.get("tk") or "").upper()
            if not tk or tk=="—": continue
            surfaced.add(tk)
            e,s,t=row.get("e"),row.get("s"),row.get("t")
            if row.get("valid"):
                try:
                    if row.get("dir")=="long" and not(float(s)<float(e)<float(t)):
                        errors.append(f"{tk}: long level invariant failed")
                    if row.get("dir")=="short" and not(float(t)<float(e)<float(s)):
                        errors.append(f"{tk}: short level invariant failed")
                except Exception:
                    errors.append(f"{tk}: valid setup missing numeric levels")
    state=desk.get("alpha_foundry") or {}
    for row in state.get("shortlist") or []:
        tk=str(row.get("ticker") or "").upper()
        if tk: surfaced.add(tk)
    for row in desk.get("alpha") or []:
        tk=str(row.get("tk") or "").upper()
        if tk: surfaced.add(tk)
    sys=desk.get("systemic") or {}
    bad=[x for x in sys.get("rotation_in") or [] if str(x).upper() not in surfaced]
    if bad: errors.append("Mission rotation names not surfaced elsewhere: "+", ".join(bad))
    raw=set(str(x).upper() for x in sys.get("rotation_in_raw") or [])
    confirmed=set(str(x).upper() for x in sys.get("rotation_in") or [])
    if not confirmed.issubset(raw): errors.append("confirmed rotation is not a subset of raw rotation")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "surfaced_tickers": sorted(surfaced)}

def enforce_desk(desk: dict) -> dict:
    audit=validate_desk(desk); desk["consistency_audit"]=audit
    if not audit["ok"]:
        # Fail closed: remove decision-bearing outputs, retain diagnostics.
        for market in (desk.get("markets") or {}).values(): market["setups"]=[]; market.setdefault("funnel", {})["setups"]=0
        desk["alpha"]=[]
        desk.setdefault("systemic", {})["rotation_in"]=[]
        desk.setdefault("systemic", {})["rotation_out"]=[]
        desk.setdefault("meta", {})["source"]="CONSISTENCY_BLOCKED"
    return desk
