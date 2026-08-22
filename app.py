from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit('Streamlit not installed. Run EROS.bat or: python -m pip install -r requirements.txt') from exc

from eros.pipeline import run, load_or_run

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='EROS Warroom',page_icon='◈',layout='wide',initial_sidebar_state='collapsed')
st.markdown(r'''
<style>
:root{--bg:#070a0f;--panel:#0d131c;--panel2:#101824;--line:#202c3d;--mut:#8290a3;--tx:#e8eef7;--cyan:#52d6ce;--green:#46cf83;--amber:#e4b24f;--red:#ee6a62;--blue:#64a9ff}
.stApp{background:var(--bg);color:var(--tx)} header[data-testid="stHeader"]{background:transparent}.block-container{max-width:1750px;padding-top:.75rem;padding-bottom:2rem}
#MainMenu,footer{visibility:hidden}.eros-top{border:1px solid var(--line);background:linear-gradient(135deg,#0d141e,#0a0f16);padding:14px 16px;border-radius:7px;margin-bottom:10px}
.eros-title{font-family:ui-monospace,monospace;font-size:20px;font-weight:800;letter-spacing:.9px}.eros-sub{font-size:11px;color:var(--mut);margin-top:2px}.tag{font-family:ui-monospace,monospace;font-size:10px;border:1px solid var(--line);border-radius:3px;padding:3px 7px;margin-right:5px}.tag.live{color:var(--green)}.tag.wait{color:var(--amber)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 13px;margin:5px 0}.k{font-family:ui-monospace,monospace;color:var(--mut);font-size:9px;letter-spacing:.6px;text-transform:uppercase}.v{font-family:ui-monospace,monospace;font-size:17px;font-weight:700;margin-top:4px}.mut{color:var(--mut);font-size:11px}.good{color:var(--green)}.bad{color:var(--red)}.amb{color:var(--amber)}.cyan{color:var(--cyan)}
.scenario{background:var(--panel);border-left:3px solid var(--cyan);border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line);border-radius:5px;padding:12px 14px;margin:7px 0}.radar{border-left-color:var(--amber)}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);padding:10px;border-radius:6px}[data-testid="stMetricLabel"]{color:var(--mut)}
.stTabs [data-baseweb="tab-list"]{gap:5px;border-bottom:1px solid var(--line)}.stTabs [data-baseweb="tab"]{font-family:ui-monospace,monospace;background:#0b1119;border:1px solid var(--line);border-bottom:none;border-radius:5px 5px 0 0;padding:8px 14px}.stTabs [aria-selected="true"]{color:var(--cyan)!important;background:#101923!important}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:5px}.stButton>button{background:#101923;border:1px solid #2a3a50;color:var(--tx)}
</style>
''',unsafe_allow_html=True)

if 'state' not in st.session_state:
    with st.spinner('EROS is fetching factual data and building the current decision map…'):
        try: st.session_state.state=run(force=False)
        except Exception as e: st.session_state.state={'error':str(e),'states':[],'scenarios':[],'scenario_radar':[],'ticker_candidates':[],'markets':{},'world':{},'source_summary':{},'current_action':'NO_DATA','global_posture':'NO_DATA','risk_flags':[],'news_leads':[]}

r=st.session_state.state
st.markdown(f'''<div class="eros-top"><div class="eros-title">EROS / WARROOM</div><div class="eros-sub">Global economic state → reality → scenario → asset → company/ticker → priced-in → EV → action</div><div style="margin-top:8px"><span class="tag live">AUTO LIVE DATA</span><span class="tag wait">FAIL-CLOSED</span><span class="tag">NO CLASSIC TECHNICAL ALPHA</span></div></div>''',unsafe_allow_html=True)

b1,b2,b3,b4,b5,b6=st.columns([1.2,1.2,1,1,1,1])
with b1:
    st.metric('GLOBAL POSTURE',r.get('global_posture','UNKNOWN'))
with b2:
    st.metric('ACTION',r.get('current_action','UNKNOWN'))
with b3: st.metric('VERIFIED SCENARIOS',len(r.get('scenarios',[])))
with b4: st.metric('SCENARIO RADAR',len(r.get('scenario_radar',[])))
with b5: st.metric('TICKER CANDIDATES',len(r.get('ticker_candidates',[])))
with b6:
    if st.button('↻ REFRESH LIVE',use_container_width=True):
        with st.spinner('Refreshing official/public data, market context and scenario radar…'):
            st.session_state.state=run(force=True)
        st.rerun()

cmd,glob,opp,port,lab=st.tabs(['COMMAND CENTER','GLOBAL EXPLORER','OPPORTUNITY ENGINE','PORTFOLIO','RESEARCH LAB'])

with cmd:
    st.markdown('### NOW: WHAT THE WORLD IS TELLING US')
    states=r.get('states',[])
    cols=st.columns(4)
    for i,s in enumerate(states):
        tone='good' if s.get('direction')=='UP' else 'bad' if s.get('direction')=='DOWN' else 'amb'
        ev='<br>'.join(s.get('evidence',[])[:3]) or 'No current factual evidence.'
        with cols[i%4]:
            st.markdown(f'''<div class="card"><div class="k">{s.get('label')}</div><div class="v {tone}">{s.get('value')}</div><div class="mut">{ev}</div><div class="mut" style="margin-top:6px">as of {s.get('as_of') or '—'} · {s.get('confidence')}</div></div>''',unsafe_allow_html=True)
    st.markdown('### WHAT CAN HAPPEN NEXT · VERIFIED-EVIDENCE SCENARIOS')
    if not r.get('scenarios'):
        st.info('No verified scenario chain can be built from available factual evidence yet. EROS remains WAIT rather than inventing one.')
    for s in r.get('scenarios',[]):
        chain=' → '.join(s.get('causal_chain',[]))
        st.markdown(f'''<div class="scenario"><div class="k">{s.get('scenario_id')} · {s.get('status')}</div><div class="v cyan">{s.get('title')}</div><div class="mut" style="margin-top:7px">{chain}</div><div class="mut" style="margin-top:7px">Probability: <b>{'UNKNOWN' if s.get('probability') is None else s.get('probability')}</b> · Timing: <b>{s.get('timing')}</b> · Duration: <b>{s.get('duration')}</b></div></div>''',unsafe_allow_html=True)
        with st.expander('Evidence / invalidation / next discriminating data'):
            a,b,c=st.columns(3); a.write('**Confirming**'); a.write(s.get('confirming',[])); b.write('**Contradicting**'); b.write(s.get('contradicting',[])); c.write('**Next data**'); c.write(s.get('next_data',[]))
    st.markdown('### SCENARIO RADAR · THINGS EROS THINKS MAY MATTER BEFORE THEY ARE PROVEN')
    st.caption('Automatically discovered news leads are NOT treated as facts. This is where “2008 in the making”, mega-IPO/index reflexivity, China gold demand, etc. first appear and get a verification checklist.')
    if not r.get('scenario_radar'): st.info('No external scenario leads available from the current public-news feed.')
    for s in r.get('scenario_radar',[]):
        st.markdown(f'''<div class="scenario radar"><div class="k">{s.get('scenario_id')} · {s.get('status')}</div><div class="v amb">{s.get('title')}</div><div class="mut" style="margin-top:6px">{s.get('hypothesis')}</div><div class="mut" style="margin-top:6px">Needs proof: {', '.join(s.get('needs_verification',[]))}</div></div>''',unsafe_allow_html=True)

with glob:
    st.markdown('### GLOBAL EXPLORER')
    st.caption('Market prices are context/outcomes only—not directional technical alpha. Country macro uses official/public sources where available.')
    regions=['US','INDONESIA','CHINA','JAPAN','EUROZONE','CRYPTO','COMMODITIES','FX']
    regtabs=st.tabs(regions)
    markets=r.get('markets',{}).get('markets',{}) if isinstance(r.get('markets'),dict) else {}
    world=r.get('world',{})
    for tab,reg in zip(regtabs,regions):
        with tab:
            a,b=st.columns([1,2])
            with a:
                if reg in world:
                    st.markdown('#### Macro context')
                    w=world.get(reg,{})
                    if w.get('data'): st.dataframe(pd.DataFrame([{'metric':k,**v} for k,v in w['data'].items()]),hide_index=True,use_container_width=True)
                    else: st.info('No current country macro data returned.')
                else: st.markdown('#### Market / physical context')
            with b:
                st.markdown('#### Market context')
                rows=markets.get(reg,[])
                if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
                else: st.info('No market feed available for this region in the current run.')
            if reg=='US':
                st.markdown('#### US economic state')
                st.dataframe(pd.DataFrame([x for x in r.get('states',[]) if x.get('state_id') in ['GROWTH','LABOR','INFLATION','POLICY','RATES','CREDIT','LIQUIDITY','HOUSING','FISCAL']]),hide_index=True,use_container_width=True)
            if reg=='INDONESIA':
                st.warning('Indonesia production-grade BI/BPS/OJK/IDX/KSEI/BKPM ingestion remains a required expansion. EROS will not fake missing local macro/flow evidence.')

with opp:
    st.markdown('### OPPORTUNITY ENGINE')
    st.caption('Candidates are generated automatically from scenarios. A candidate is NOT a recommendation until company transmission, PIT validation, priced-in and EV gates pass.')
    assets=r.get('asset_candidates',[])
    st.markdown('#### Scenario → Asset expressions')
    if assets: st.dataframe(pd.DataFrame(assets),hide_index=True,use_container_width=True)
    else: st.info('No asset expression can be routed from current scenarios.')
    st.markdown('#### Asset → Company/Ticker candidates')
    rows=r.get('ticker_candidates',[])
    if rows:
        slim=[]
        for x in rows:
            slim.append({k:x.get(k) for k in ['ticker','market','scenario_id','theme','exposure_status','fundamentals_status','balance_sheet_status','valuation_status','priced_in_status','evidence_level','action']})
        st.dataframe(pd.DataFrame(slim),hide_index=True,use_container_width=True)
        st.markdown('#### Candidate deep dive')
        tickers=[x.get('ticker') for x in rows]
        sel=st.selectbox('Ticker',tickers)
        x=next(z for z in rows if z.get('ticker')==sel)
        st.markdown(f'''<div class="card"><div class="k">{x.get('market')} · {x.get('scenario_id')}</div><div class="v">{x.get('ticker')} · {x.get('action')}</div><div class="mut">{x.get('mechanism')}</div></div>''',unsafe_allow_html=True)
        d=x.get('details') or {}; c1,c2,c3,c4=st.columns(4)
        c1.metric('Revenue growth', '—' if d.get('revenueGrowth') is None else f"{d.get('revenueGrowth')*100:.1f}%")
        c2.metric('Operating margin', '—' if d.get('operatingMargins') is None else f"{d.get('operatingMargins')*100:.1f}%")
        c3.metric('Free cash flow', '—' if d.get('freeCashflow') is None else f"{d.get('freeCashflow')/1e9:.2f}B")
        c4.metric('Forward P/E','—' if d.get('forwardPE') is None else f"{d.get('forwardPE'):.1f}")
        st.write('**Exposure:**',x.get('exposure_status')); st.write('**Valuation / priced-in:**',x.get('valuation_status'),'/',x.get('priced_in_status')); st.write('**Catalyst gate:**',x.get('catalyst'))
        st.info('Four production probabilities + EV are intentionally absent until calibration/PIT ticker replay is available. This prevents a visually attractive candidate from becoming a fake BUY.')
    else:
        st.warning('NO CANDIDATE WITH CURRENT DATA. EROS stays WAIT.')

with port:
    st.markdown('### PORTFOLIO')
    st.caption('Paste positions to map scenario concentration. No sizing is invented without calibrated covariance/cost/capacity inputs.')
    raw=st.text_area('Positions (one per line: TICKER,WEIGHT)',placeholder='NVDA,0.15\nBBCA.JK,0.10\nGC=F,0.05')
    if raw.strip():
        pos=[]
        for line in raw.splitlines():
            try:t,w=[z.strip() for z in line.split(',',1)]; pos.append({'ticker':t,'weight':float(w)})
            except Exception:pass
        if pos:
            st.dataframe(pd.DataFrame(pos),hide_index=True,use_container_width=True)
            cand={x.get('ticker'):x for x in r.get('ticker_candidates',[])}
            mapped=[]
            for p in pos:
                x=cand.get(p['ticker']); mapped.append({**p,'scenario':x.get('scenario_id') if x else 'UNMAPPED','theme':x.get('theme') if x else 'UNMAPPED','evidence':x.get('evidence_level') if x else 'NO_CURRENT_SCENARIO_MAP'})
            st.dataframe(pd.DataFrame(mapped),hide_index=True,use_container_width=True)
            st.warning('Portfolio sizing/hedging remains decision-support only until full portfolio validation is completed.')

with lab:
    st.markdown('### RESEARCH LAB')
    st.caption('All scientific machinery lives here—not on the daily decision screen.')
    ss=r.get('source_summary',{}); st.json(ss)
    st.markdown('#### Evidence')
    st.dataframe(pd.DataFrame(r.get('evidence',[])),hide_index=True,use_container_width=True)
    st.markdown('#### News leads used only for scenario radar')
    st.dataframe(pd.DataFrame(r.get('news_leads',[])),hide_index=True,use_container_width=True)
    st.markdown('#### Existing audit handoff')
    hand=ROOT/'FINAL_HANDOFF'
    files=sorted(p.name for p in hand.glob('*') if p.is_file())
    st.write(files)
    st.download_button('Download current Warroom state JSON',json.dumps(r,indent=2,default=str),'EROS_warroom_state.json','application/json')
