"""Bounded V9.9 collector: quotes first, unified packet second, official context in the slow lane."""
from __future__ import annotations
import argparse, os, signal, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE/'.env',override=False)
except Exception:pass
from runtime_sanitizer import sanitize_runtime_payload
from runtime_store import claim_worker_instance,consume_force_refresh,force_refresh_requested,now_iso,release_worker_instance,write_snapshot,write_status
STOP=False
MARKETS=['us','idx','crypto','commodity','fx']
REFRESH_SECONDS=max(300,int(os.getenv('WARROOM_CORE_REFRESH_SECONDS','900')))
PUBLIC_REFRESH_SECONDS=max(3600,int(os.getenv('WARROOM_PUBLIC_REFRESH_SECONDS','21600')))

def _stop(*_args):
    global STOP; STOP=True

def _install_signals():
    try:signal.signal(signal.SIGTERM,_stop);signal.signal(signal.SIGINT,_stop)
    except (ValueError,OSError):pass

def _refresh_quotes()->None:
    try:
        from execution_quote_collector_v99 import collect
        result=collect(); write_status(quote_count=result.get('quote_count',0),quote_markets=result.get('markets_with_quote',0),quote_refresh_error=None)
    except Exception as exc:
        write_status(quote_refresh_error=f'{type(exc).__name__}: {exc}')

def build_core(*,allow_live:bool=True)->dict:
    import data_layer as DL
    from run import build_fast_desk
    if allow_live:_refresh_quotes()
    data=DL.load_all(markets=MARKETS,allow_live=allow_live,allow_synthetic=False)
    desk=build_fast_desk(data)
    desk.setdefault('runtime',{}).update({'core_collected_at':now_iso(),'core_profile':'UNIFIED_DECISION_PACKET_CURRENT_CONTEXT'})
    return sanitize_runtime_payload(desk)

def _public_due()->bool:
    manifests=sorted((HERE/'runtime'/'v99_public_acquisition').glob('*/v99_public_acquisition_manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    return not manifests or time.time()-manifests[0].stat().st_mtime>=PUBLIC_REFRESH_SECONDS

def refresh_public_context()->dict|None:
    if os.getenv('WARROOM_DISABLE_PUBLIC_REFRESH','0').lower() in {'1','true','yes'} or not _public_due():return None
    try:
        from public_context_collector_v99 import collect
        result=collect(); write_status(public_source_markets=result.get('markets_with_at_least_one_real_snapshot',0),public_refresh_error=None); return result
    except Exception as exc:
        write_status(public_refresh_error=f'{type(exc).__name__}: {exc}'); return None

def run_once(*,allow_live:bool=True)->dict:
    write_status(state='COLLECTING',last_attempt_at=now_iso(),error=None)
    desk=build_core(allow_live=allow_live); result=write_snapshot(desk,force=True)
    write_status(state='READY_UNIFIED_CONTEXT',last_success=now_iso(),revision=result.get('revision'),content_hash=result.get('content_hash'),capital_permission='BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL',error=None)
    return desk

def loop()->None:
    _install_signals()
    if not claim_worker_instance():
        write_status(state='ALREADY_RUNNING',capital_permission='BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL');return
    try:
        run_once(allow_live=True)
        if refresh_public_context() is not None:run_once(allow_live=False)
        next_run=time.monotonic()+REFRESH_SECONDS
        while not STOP:
            if force_refresh_requested():consume_force_refresh();next_run=0.0
            if time.monotonic()>=next_run:
                run_once(allow_live=True)
                if refresh_public_context() is not None:run_once(allow_live=False)
                next_run=time.monotonic()+REFRESH_SECONDS
            write_status(state='READY_UNIFIED_CONTEXT',heartbeat_at=now_iso(),capital_permission='BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL');time.sleep(2.0)
    finally:
        release_worker_instance();write_status(state='STOPPED',capital_permission='BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    if args.once:run_once(allow_live=not args.offline)
    else:loop()
if __name__=='__main__':main()
