from __future__ import annotations
import csv,json,hashlib
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RV=ROOT/'research_v58'
univ=json.loads((RV/'V58_RESEARCH_UNIVERSE.json').read_text())
readiness=json.loads((RV/'V58_DATA_READINESS_MATRIX.json').read_text())
rmap={r['candidate_id']:r for r in readiness['rows']}
rows=[]
for c in univ['candidates']:
    r=rmap[c['candidate_id']]
    if r['data_readiness']=='AGGREGATE_RETURN_SERIES_TESTED':
        continue
    req=r.get('data_required') or []
    # Accessibility tier is about source logistics, not expected alpha quality.
    txt=' '.join(map(str,req)).lower()
    if c.get('source_signal_class') in {'PLACEBO','DROP'}:
        tier='A_OFFICIAL_SIGNAL_FILES_OR_WRDS'
        next_action='Acquire official PlacebosIndiv/drop signal files or reconstruct exact official code inputs; build portfolios with the frozen OpenAP portfolio engine.'
    elif any(x in txt for x in ['ibes','compustat','crsp','option','borrow','dealer','tbt','broker','13f','order book','depth']):
        tier='C_LICENSED_OR_SPECIALIZED'
        next_action='Acquire point-in-time licensed/specialized data, freeze source hashes and availability lags, then run canonical replication before variants.'
    elif any(x in txt for x in ['fred','public','price','returns','futures','macro','on-chain','network','inventory','curve']):
        tier='B_PUBLIC_OR_MIXED'
        next_action='Archive exact public/mixed source series, verify revisions and timestamps, then freeze canonical replication and negative controls.'
    else:
        tier='D_SOURCE_MAPPING_REQUIRED'
        next_action='Complete exact source and lineage mapping before formula or backtest.'
    rows.append({
      'candidate_id':c['candidate_id'],'name':c['name'],'family':c['family'],'source_class':c['source_class'],
      'source_signal_class':c.get('source_signal_class',''),'primary_role':c['primary_role'],
      'market_scope':'|'.join(c.get('market_scope') or []),'data_readiness':r['data_readiness'],
      'accessibility_tier':tier,'data_required':'|'.join(map(str,req)),'next_valid_action':next_action,
      'live_decision_weight':0.0,'capital_permission':'BLOCKED'
    })
rows.sort(key=lambda x:(x['accessibility_tier'],x['family'],x['name']))
out={
 'schema':'warroom.all_untested_acquisition_queue.v60','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'candidate_count':len(rows),'accessibility_tier_counts':dict(Counter(x['accessibility_tier'] for x in rows)),
 'family_counts':dict(Counter(x['family'] for x in rows)),
 'scope_boundary':'Queue contains every currently mapped candidate not directly tested with its own return/outcome data. Tier ranks data logistics only, not expected edge quality.',
 'rows':rows,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
(RV/'V60_ALL_UNTESTED_ACQUISITION_QUEUE.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
with (RV/'V60_ALL_UNTESTED_ACQUISITION_QUEUE.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'count':len(rows),'tiers':out['accessibility_tier_counts'],'families':out['family_counts']},indent=2))
