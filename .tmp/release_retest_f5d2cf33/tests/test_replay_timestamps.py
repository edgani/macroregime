from pathlib import Path
import pandas as pd
root=Path(__file__).resolve().parents[1]
df=pd.read_csv(root/'data/replay_phases.csv')
# known corrected dates
assert ((df['case']=='SNDK') & (df['date'].astype(str)=='2025-08-14')).any()
assert not ((df['case']=='SNDK') & (df['date'].astype(str)=='2025-08-07')).any()
# after-close release must not use same-day regular-session fill
for case,date,nextdate in [('SNDK','2025-05-07','2025-05-08'),('SNDK','2025-08-14','2025-08-15'),('PLTR','2024-05-06','2024-05-07')]:
    r=df[(df['case']==case)&(df['date'].astype(str)==date)].iloc[0]
    assert str(r['earliest_regular_session'])==nextdate,(case,date,r['earliest_regular_session'])
print('TEST_REPLAY_TIMESTAMPS_PASS')
