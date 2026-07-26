from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'research_v58'; RES=R/'results'; LED=R/'ledgers'
NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def metric(c,split,cost='0.0'):
    x=c['splits'][split][cost]
    return {k:x.get(k) for k in ['n','start','end','mean_monthly','annualized_mean','annualized_sharpe','hac_t','hac_se','bonferroni_lower_bound','max_drawdown','positive_year_fraction','leave_one_year_out_min_mean']}

results=json.loads((RES/'V58_OPENAP_212_POSTSAMPLE_RESULTS.json').read_text())
ledger=json.loads((LED/'V58_GLOBAL_TRIAL_LEDGER.json').read_text())
sig=pd.read_csv(R/'data'/'SignalDoc.csv').set_index('Acronym')
selected=['AnnouncementReturn','AnalystRevision','DivYieldST']
source_contracts={
'AnnouncementReturn':{
 'primary_role':'event_information_diffusion',
 'exact_definition':'Sum of market-adjusted returns from trading day -1 through +2 around the quarterly earnings announcement date; original OpenAP definition uses IBES fpi=6 announcement dates.',
 'required_point_in_time_sources':['IBES historical announcement dates with publication timestamps','CRSP daily returns, delisting returns and shares/prices','contemporaneous market and risk-free return','point-in-time security identifier link table'],
 'execution_variants_frozen_for_discovery':['close(-2) to close(+2)','open(0) to close(+2)','post-announcement close(0) to close(+5)','long-only top quantile and long-short spread'],
 'critical_bias_tests':['announcement timestamp before/after close','earnings date revisions','delisting return inclusion','same-day multiple announcements','microcap exclusion and capacity','transaction cost and event turnover'],
 'prospective_path':'Create signed event predictions before each announcement using only information available at order time; no use of the realized announcement return as a selection input.',
},
'AnalystRevision':{
 'primary_role':'expectations_revision',
 'exact_definition':'For current-fiscal-year IBES estimates (fpi=1), keep the last observation each month and compute current mean estimate divided by prior-month mean estimate.',
 'required_point_in_time_sources':['IBES Detail or Summary history with estimate timestamps and broker identifiers','CRSP daily/monthly returns and delisting returns','point-in-time identifier links','actual earnings and guidance timestamps for contamination controls'],
 'execution_variants_frozen_for_discovery':['raw ratio','signed percentage revision','breadth of upward minus downward analysts','revision magnitude times analyst agreement','1m and 3m holding periods'],
 'critical_bias_tests':['stale-estimate removal','broker duplication','post-announcement contamination','split adjustments','coverage and microcap filters','turnover and crowding'],
 'prospective_path':'Persist every estimate snapshot and signed monthly rank before returns; compare incremental value over earnings momentum and price momentum.',
},
'DivYieldST':{
 'primary_role':'distribution_seasonality',
 'exact_definition':'Use qualifying CRSP cash distributions and prior payment timing to predict next-month dividend seasonality; discretize expected yield into the frozen bins from SignalDoc.',
 'required_point_in_time_sources':['CRSP distribution history including distcd and ex/pay dates','CRSP prices, returns and delisting returns','corporate-action adjustment history','point-in-time identifier links'],
 'execution_variants_frozen_for_discovery':['exact OpenAP bins','continuous expected yield','ex-dividend-month indicator','long-only versus long-short','exclude special distributions'],
 'critical_bias_tests':['ex-date versus declaration-date availability','special dividend contamination','tax/clientele seasonality','price drop around ex-date','turnover/capacity','subperiod stability after decimalization'],
 'prospective_path':'Freeze expected distribution calendar before month start and record signed cross-sectional ranks; no retroactive distribution edits.',
}}
claims_by={c['claim']['series']:c for c in results['claims']}
rows=[]
for name in selected:
    c=claims_by[name]; meta=sig.loc[name].to_dict(); led=next(x for x in ledger['rows'] if x['study']=='V58_OPENAP_212_POSTSAMPLE' and x['candidate']==name)
    rows.append({
      'study_id':'V59_'+name.upper(), 'candidate':name, 'display_name':meta['LongDescription'],
      'status':'MAPPING_COMPLETE_FRESH_POINT_IN_TIME_DATA_REQUIRED',
      'why_advanced':'Survived gross one-sided Bonferroni lower bounds in both validation and lockbox after accounting for all 795 v58 claims.',
      'why_not_proven':'No survivor remains after the coarse 25 bps/month global stress; maintained aggregate portfolios do not expose constituents, turnover, borrow, capacity or data-vintage errors.',
      'global_795_metrics':{
        'validation_lb_gross':led['global_validation_lb_gross'],'lockbox_lb_gross':led['global_lockbox_lb_gross'],
        'validation_lb_25bps':led['global_validation_lb_25bps'],'lockbox_lb_25bps':led['global_lockbox_lb_25bps']},
      'family_212_metrics':{'validation_gross':metric(c,'validation'),'lockbox_gross':metric(c,'lockbox')},
      'original_metadata':{k:meta.get(k) for k in ['Authors','Year','SampleStartYear','SampleEndYear','Cat.Data','Cat.Economic','Sign','Stock Weight','Portfolio Period','Detailed Definition','Notes']},
      **source_contracts[name],
      'promotion_gate':[
        'exact source lineage and stock-level reconstruction hash match','validation and untouched lockbox lower bounds positive after the full updated global trial budget',
        'positive after measured turnover, spread, market impact, borrow and delisting costs','incremental value over simple event/revision/dividend baselines',
        'stable across market-cap and liquidity buckets without microcap dependence','no single calendar year contributes over 30 percent of total improvement',
        'signed prospective observations mature with zero live weight until approval'],
      'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
queue={'schema':'warroom.survivor_replication_queue.v59','created_at_utc':NOW,'source_v58_ledger_sha256':sha(LED/'V58_GLOBAL_TRIAL_LEDGER.json'),
       'candidate_count':len(rows),'claims':rows,'queue_order':['AnnouncementReturn','AnalystRevision','DivYieldST'],
       'short_interest_note':'ShortInterest survived the 212-family gross gate but failed the conservative global 795-claim validation lower bound, so it remains a secondary challenger rather than an advanced survivor.',
       'ensemble_note':'Any ensemble of these candidates is post-selection and cannot be treated as proof until frozen and evaluated on genuinely new data.',
       'predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED'}
out=R/'V59_SURVIVOR_REPLICATION_QUEUE.json';out.write_text(json.dumps(queue,indent=2,sort_keys=True)+'\n')

md=['# V59 Fresh Point-in-Time Replication Queue','',f'Generated: {NOW}','',
'## Gate from V58','',
'- 868 mapped candidates.','- 795 registered empirical claims in the current data-ready batteries.','- Three candidates survive the conservative global 795-claim correction on gross maintained returns.','- Zero candidates survive the same global gate after a coarse 25 bps/month deduction.','- Therefore all three remain research candidates with zero live weight.','']
for i,r in enumerate(rows,1):
    md += [f"## {i}. {r['candidate']} — {r['display_name']}",'',f"**Role:** {r['primary_role']}",'',f"**Exact definition:** {r['exact_definition']}",'',
           '**Why advanced:** '+r['why_advanced'],'','**Why not proven:** '+r['why_not_proven'],'',
           '**Required sources:**',''] + [f'- {x}' for x in r['required_point_in_time_sources']] + ['', '**Critical bias tests:**',''] + [f'- {x}' for x in r['critical_bias_tests']] + ['', '**Promotion gate:**',''] + [f'- {x}' for x in r['promotion_gate']] + ['']
md += ['## Secondary challenger','','ShortInterest stays in the ledger but is not advanced: its global 795-claim validation lower bound is negative.','','## Capital boundary','','Live decision weight: `0.0`  ','Capital permission: `BLOCKED`','']
(R/'V59_SURVIVOR_REPLICATION_QUEUE.md').write_text('\n'.join(md))
print(out,sha(out))
