from eros import pipeline
pipeline.fetch_all=lambda force=False:{'macro':{'as_of':'x','series':{}},'treasury':{'status':'NO_DATA'},'markets':{'status':'NO_DATA','markets':{}},'world':{},'news_leads':{'status':'NO_DATA','leads':[]}}
r=pipeline.run(False)
assert r['global_posture']=='BENIGN / SELECTIVE' or r['global_posture']
assert not r['qualified_opportunities']
assert 'WAIT' in r['current_action']
assert not r['ticker_candidates']
print('FAIL_CLOSED_NO_DATA_PASS')
