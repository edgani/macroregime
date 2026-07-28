"""V10.1 persistent current-context, decision and shadow worker."""
from __future__ import annotations
import argparse, os, signal, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
try:
 from dotenv import load_dotenv
 load_dotenv(HERE/'.env',override=False)
except Exception: pass
from runtime_store import claim_worker_instance,consume_force_refresh,force_refresh_requested,now_iso,release_worker_instance,write_snapshot,write_status
STOP=False
REFRESH=max(300,int(os.getenv('WARROOM_CORE_REFRESH_SECONDS','900')))
FULL_REFRESH=max(3600,int(os.getenv('WARROOM_FULL_REFRESH_SECONDS','21600')))

def _stop(*_):
 global STOP;STOP=True

def _build(fast:bool)->dict:
 import current_context_v101 as CC
 from run import build_desk
 import data_layer_v101 as DL
 CC.collect_all(fast=fast)
 desk=build_desk(DL.load_all(allow_live=False,allow_synthetic=False))
 desk.setdefault('runtime',{}).update({'core_collected_at':now_iso(),'core_profile':'V101_OPERATIONAL_CURRENT_ACTION','refresh_type':'FAST' if fast else 'FULL'})
 return desk

def run_once(*,fast:bool=True)->dict:
 write_status(state='COLLECTING_CURRENT_CONTEXT',last_attempt_at=now_iso(),error=None)
 try:
  desk=_build(fast);result=write_snapshot(desk,force=True)
  mc=desk.get('mission_control') or {}
  write_status(state='READY_OPERATIONAL_RESEARCH',last_success=now_iso(),revision=result.get('revision'),content_hash=result.get('content_hash'),research_permission=mc.get('research_permission'),shadow_permission=mc.get('shadow_permission'),systematic_live_permission=mc.get('systematic_live_permission'),shadow_candidates=mc.get('shadow_candidates'),error=None)
  if os.getenv('WARROOM_AUTO_SHADOW','0').lower() in {'1','true','yes'}:
   try:
    from shadow_runner_v101 import record
    shadow=record(desk);write_status(shadow_created=shadow.get('created'),shadow_error=None)
   except Exception as exc:write_status(shadow_error=f'{type(exc).__name__}: {exc}')
  return desk
 except Exception as exc:
  write_status(state='CURRENT_CONTEXT_ERROR',error=f'{type(exc).__name__}: {exc}');raise

def loop()->None:
 global STOP
 try:signal.signal(signal.SIGINT,_stop);signal.signal(signal.SIGTERM,_stop)
 except Exception:pass
 if not claim_worker_instance():write_status(state='ALREADY_RUNNING');return
 try:
  last_full=0.0;run_once(fast=False);last_full=time.monotonic();next_run=time.monotonic()+REFRESH
  while not STOP:
   if force_refresh_requested():consume_force_refresh();next_run=0
   if time.monotonic()>=next_run:
    full=time.monotonic()-last_full>=FULL_REFRESH;run_once(fast=not full)
    if full:last_full=time.monotonic()
    next_run=time.monotonic()+REFRESH
   write_status(state='READY_OPERATIONAL_RESEARCH',heartbeat_at=now_iso());time.sleep(2)
 finally:release_worker_instance();write_status(state='STOPPED')

def main():
 p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');p.add_argument('--full',action='store_true');a=p.parse_args();run_once(fast=not a.full) if a.once else loop()
if __name__=='__main__':main()
