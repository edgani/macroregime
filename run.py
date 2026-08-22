from eros.pipeline import run
import json, argparse
p=argparse.ArgumentParser(); p.add_argument('--refresh',action='store_true'); a=p.parse_args()
r=run(force=a.refresh)
print(json.dumps({'status':r['system_status'],'global_posture':r['global_posture'],'current_action':r['current_action'],'states':len(r['states']),'verified_scenarios':len(r['scenarios']),'scenario_radar':len(r['scenario_radar']),'ticker_candidates':len(r['ticker_candidates']),'qualified_opportunities':len(r['qualified_opportunities']),'source_summary':r['source_summary']},indent=2))
