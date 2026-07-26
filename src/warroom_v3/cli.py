from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path

from .hashing import canonical_hash
from .runtime import bootstrap_binance_scope, collect_binance_scope, import_canonical_csv, build_asset_snapshot, system_status
from .storage import atomic_write
from .evaluation import build_evaluation_report

ASSETS=("BTCUSDT","ETHUSDT"); FRAMES=("15m","1h","4h","1d")

def root_path() -> Path:
    return Path(os.environ.get("WARROOM_ROOT") or Path.cwd()).resolve()

def emit(value): print(json.dumps(value,indent=2,sort_keys=True,default=str))

def incident(root: Path,command: str,scope: str | None,exc: Exception) -> dict:
    payload={"recorded_at":datetime.now(timezone.utc).isoformat(),"command":command,"scope":scope,
             "error_type":type(exc).__name__,"message":str(exc),"claim_ceiling":"OPERATIONS_INCIDENT_ONLY"}
    payload["incident_hash"]=canonical_hash(payload)
    atomic_write(root/f"runtime/incidents/{payload['incident_hash']}.json",json.dumps(payload,indent=2,sort_keys=True).encode())
    return payload

def run_all(root: Path,fn,command: str) -> int:
    rows=[]; failures=0
    for asset in ASSETS:
        for tf in FRAMES:
            try: rows.append(fn(root,asset=asset,timeframe=tf))
            except Exception as exc:
                failures+=1; rows.append({"status":"ERROR","asset":asset,"timeframe":tf,"incident":incident(root,command,f"{asset}:{tf}",exc)})
    emit({"command":command,"results":rows,"failures":failures})
    return 1 if failures else 0

def main(argv: list[str] | None=None) -> int:
    root=root_path()
    p=argparse.ArgumentParser(description="War Room OS v3 operations CLI")
    sub=p.add_subparsers(dest="cmd",required=True)
    for name in ("bootstrap","collect"):
        q=sub.add_parser(name); q.add_argument("asset",choices=ASSETS); q.add_argument("timeframe",choices=FRAMES)
    sub.add_parser("bootstrap-all"); sub.add_parser("collect-all"); sub.add_parser("status"); sub.add_parser("evaluate")
    q=sub.add_parser("snapshot"); q.add_argument("asset",choices=ASSETS)
    q=sub.add_parser("import-csv"); q.add_argument("path"); q.add_argument("--tier",choices=("bootstrap","prospective"),default="bootstrap")
    q=sub.add_parser("serve"); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=8080)
    q=sub.add_parser("streamlit"); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=8501)
    args=p.parse_args(argv)
    try:
        if args.cmd=="bootstrap": emit(bootstrap_binance_scope(root,asset=args.asset,timeframe=args.timeframe)); return 0
        if args.cmd=="collect": emit(collect_binance_scope(root,asset=args.asset,timeframe=args.timeframe)); return 0
        if args.cmd=="bootstrap-all": return run_all(root,bootstrap_binance_scope,"bootstrap-all")
        if args.cmd=="collect-all": return run_all(root,collect_binance_scope,"collect-all")
        if args.cmd=="status": emit(system_status(root)); return 0
        if args.cmd=="evaluate": emit(build_evaluation_report(root)); return 0
        if args.cmd=="snapshot": emit(build_asset_snapshot(root,asset=args.asset)); return 0
        if args.cmd=="import-csv": emit(import_canonical_csv(root,csv_path=args.path,tier=args.tier)); return 0
        if args.cmd=="serve":
            import uvicorn
            os.environ["WARROOM_ROOT"]=str(root)
            uvicorn.run("warroom_v3.api:app",host=args.host,port=args.port,reload=False,app_dir=str(root/"src")); return 0
        if args.cmd=="streamlit":
            import subprocess, sys
            env=os.environ.copy(); env["WARROOM_ROOT"]=str(root); env["PYTHONPATH"]=str(root/"src")
            app=root/"streamlit_app.py"
            return subprocess.call([sys.executable,"-m","streamlit","run",str(app),f"--server.address={args.host}",f"--server.port={args.port}","--server.headless=true","--server.fileWatcherType=none"],env=env)
    except Exception as exc:
        emit({"status":"ERROR","incident":incident(root,args.cmd,getattr(args,"asset",None),exc)})
        return 1
    return 1
