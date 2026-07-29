"""Prospective shadow-order recorder for eligible V10.1 packets."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from runtime_store import read_snapshot
from shadow_execution_ledger_v95 import append_forecast, append_order_intent, append_shadow_fill, verify
from warroom.research import trial_counter

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"
UTC = dt.timezone.utc
TRIAL_ID = "V101_FIXED_ACTION_POLICY"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _hash_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _existing_ids(path: Path) -> set[str]:
    if not path.exists(): return set()
    out=set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row=json.loads(line)
            if row.get("record_type")=="FORECAST": out.add(str(row.get("forecast_id")))
        except Exception: pass
    return out


def _git_commit() -> str:
    """Best-effort git HEAD binding for reproducibility; never fails the run."""
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, timeout=10)
        commit = out.stdout.strip()
        return commit if len(commit) == 40 else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def record(snapshot: Mapping[str, Any] | None = None, *, max_new: int = 12, simulate_fill: bool = True, trial_registries: tuple | None = None) -> dict[str, Any]:
    snapshot = dict(snapshot or read_snapshot() or {})
    if not snapshot:
        return {"state":"NO_SNAPSHOT","created":0,"verification":verify(LEDGER)}
    registries = trial_registries if trial_registries is not None else trial_counter.DEFAULT_REGISTRIES
    try:
        trial_counter.require_registered(TRIAL_ID, registries)
    except trial_counter.TrialNotRegistered as exc:
        return {"state":"TRIAL_NOT_REGISTERED","created":0,"error":str(exc),"verification":verify(LEDGER)}
    candidates=list(((snapshot.get("alpha_center") or {}).get("shadow_candidates") or []))
    now=dt.datetime.now(UTC); existing=_existing_ids(LEDGER); created=[]; skipped=[]
    data_hash=_hash_value({"current_context":snapshot.get("current_context"),"generated":snapshot.get("meta",{}).get("generated")})
    code_hash=_file_hash(HERE/"action_engine_v101.py")
    model_hash=_file_hash(HERE/"V101_ACTION_POLICY.json")
    trial_hash=trial_counter.content_hash(registries)
    for packet in candidates[:max_new]:
        action=packet.get("current_action") or {}; risk=action.get("risk_plan") or {}; projection=action.get("projection") or {}
        market=str(packet.get("market") or ""); ticker=str(packet.get("ticker") or "")
        day=now.strftime("%Y%m%d"); fid=(f"F95_V101_{market.upper()}_{ticker.upper().replace('=','_').replace('.','_')}_{day}")[:84]
        if fid in existing:
            skipped.append({"ticker":ticker,"reason":"ALREADY_RECORDED_TODAY"});continue
        direction="LONG" if action.get("direction")=="LONG_BIAS" else "SHORT" if action.get("direction")=="SHORT_BIAS" else "NO_TRADE"
        horizon_days=int(projection.get("horizon_days") or 90)
        generated=now; decision=now+dt.timedelta(seconds=1); outcome_start=decision; outcome_end=outcome_start+dt.timedelta(days=horizon_days)
        expected=float(projection.get("expected_return") or 0.0)
        low_return=float(projection.get("low_return") or 0.0); high_return=float(projection.get("high_return") or 0.0)
        shortfall=min(0.0,low_return if direction=="LONG" else -high_return)
        projection_hash=_hash_value(projection)
        entry_ref=float(risk.get("entry") or 0.0)
        target_price=round(entry_ref*(1.0+expected), 10) if entry_ref>0 else None
        forecast={
            "forecast_id":fid,"trial_id":TRIAL_ID,"market":market,"security_id":ticker,
            "generated_at":generated.isoformat().replace("+00:00","Z"),"decision_at":decision.isoformat().replace("+00:00","Z"),
            "outcome_start":outcome_start.isoformat().replace("+00:00","Z"),"outcome_end":outcome_end.isoformat().replace("+00:00","Z"),
            "horizon":f"{horizon_days}D","direction":direction,"probability":float(action.get("confidence") or 0.0),
            "expected_return":expected,"expected_shortfall":shortfall,"invalidation":str(risk.get("invalidation") or "Fundamental/physical thesis invalidated"),
            "target_price":target_price,"lower_confidence_bound_return":low_return,
            "opportunity_cost_estimate":projection.get("opportunity_cost"),
            "git_commit":_git_commit(),
            "regime":str(((snapshot.get("current_action_state") or {}).get("macro_state") or {}).get("state") or "UNKNOWN"),
            "model_hash":model_hash,"data_snapshot_hash":data_hash,"code_snapshot_hash":code_hash,"global_trial_ledger_hash":trial_hash,"projection_file_hash":projection_hash,
        }
        try:
            append_forecast(LEDGER,forecast,now=generated)
            order_id=("S100_"+fid[4:])[:90]
            order={"forecast_id":fid,"shadow_order_id":order_id,"created_at":decision.isoformat().replace("+00:00","Z"),"instrument_id":ticker,
                   "side":str(risk.get("side") or ("BUY" if direction=="LONG" else "SELL")),"quantity":float(risk.get("quantity") or 0.0),
                   "order_type":"REFERENCE_MARKET","reference_price":float(risk.get("entry") or 0.0),"max_slippage_bps":25.0}
            append_order_intent(LEDGER,order,now=decision)
            if simulate_fill:
                fill_time=decision+dt.timedelta(seconds=1)
                fill={"forecast_id":fid,"shadow_order_id":order_id,"filled_at":fill_time.isoformat().replace("+00:00","Z"),
                      "quantity":order["quantity"],"price":order["reference_price"],"commission":0.0,"fees":0.0,"spread_cost":0.0,"slippage_cost":0.0,
                      "source_snapshot_hash":data_hash}
                append_shadow_fill(LEDGER,fill,now=fill_time)
            created.append({"market":market,"ticker":ticker,"forecast_id":fid,"direction":direction})
            existing.add(fid)
        except Exception as exc:
            skipped.append({"ticker":ticker,"reason":f"{type(exc).__name__}: {exc}"})
    try: ledger_display=str(LEDGER.relative_to(HERE))
    except ValueError: ledger_display=str(LEDGER)
    result={"schema":"warroom.v101.shadow_run.v1","generated_at":now.isoformat().replace("+00:00","Z"),"created":len(created),"created_rows":created,"skipped":skipped,"verification":verify(LEDGER),"ledger":ledger_display,"claim_limit":"Prospective shadow simulation only; not live performance."}
    out=HERE/"runtime"/"v101_shadow"/"last_run.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    return result


def main()->None:
    parser=argparse.ArgumentParser();parser.add_argument("--max-new",type=int,default=12);parser.add_argument("--no-fill",action="store_true");args=parser.parse_args()
    print(json.dumps(record(max_new=args.max_new,simulate_fill=not args.no_fill),indent=2,ensure_ascii=False))

if __name__=="__main__":main()
