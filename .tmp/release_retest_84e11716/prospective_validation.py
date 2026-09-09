from __future__ import annotations

import json, math, sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from opportunity_outcomes import OUTCOME_HORIZONS, path_outcome

SCHEMA='''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS universe_observations(
 asof_date TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT,
 source TEXT NOT NULL, observed_at_utc TEXT NOT NULL, metadata_json TEXT NOT NULL,
 PRIMARY KEY(asof_date,market,symbol,source));
CREATE TABLE IF NOT EXISTS baseline_selections(
 id INTEGER PRIMARY KEY AUTOINCREMENT, asof_date TEXT NOT NULL, observed_at_utc TEXT NOT NULL,
 market TEXT NOT NULL, baseline TEXT NOT NULL, symbol TEXT NOT NULL, benchmark TEXT,
 anchor_price REAL, feature_value REAL, snapshot_json TEXT NOT NULL,
 UNIQUE(asof_date,market,baseline));
CREATE TABLE IF NOT EXISTS baseline_outcomes(
 id INTEGER PRIMARY KEY AUTOINCREMENT, selection_id INTEGER NOT NULL, horizon TEXT NOT NULL,
 horizon_end_utc TEXT, absolute_return REAL, benchmark_return REAL, alpha_vs_benchmark REAL,
 completed INTEGER NOT NULL DEFAULT 0, outcome_json TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
 UNIQUE(selection_id,horizon));
CREATE TABLE IF NOT EXISTS runner_anchor_snapshots(
 id INTEGER PRIMARY KEY AUTOINCREMENT, asof_date TEXT NOT NULL, observed_at_utc TEXT NOT NULL,
 market TEXT NOT NULL, symbol TEXT NOT NULL, benchmark TEXT, anchor_price REAL, snapshot_json TEXT NOT NULL,
 audited INTEGER NOT NULL DEFAULT 0, audited_at_utc TEXT,
 UNIQUE(asof_date,market,symbol));
CREATE INDEX IF NOT EXISTS idx_runner_due ON runner_anchor_snapshots(audited,observed_at_utc);
'''

def _utc(x:Any=None)->str:
    t=pd.Timestamp.utcnow() if x is None else pd.Timestamp(x)
    if t.tzinfo is None: t=t.tz_localize('UTC')
    else: t=t.tz_convert('UTC')
    return t.isoformat()

def _f(x):
    try:
        v=float(x); return v if math.isfinite(v) else None
    except Exception:return None

def _json(x):
    def clean(v):
        if isinstance(v,dict): return {str(k):clean(z) for k,z in v.items()}
        if isinstance(v,(list,tuple)): return [clean(z) for z in v]
        try:
            if pd.isna(v): return None
        except Exception: pass
        if isinstance(v,float) and not math.isfinite(v): return None
        return v
    return json.dumps(clean(x),sort_keys=True,default=str,allow_nan=False)

def _local_date(ts: Any, market: str)->str:
    t=pd.Timestamp(ts)
    if t.tzinfo is None:t=t.tz_localize('UTC')
    else:t=t.tz_convert('UTC')
    tz={"US":"America/New_York","IHSG":"Asia/Jakarta","HK":"Asia/Hong_Kong","Hong Kong":"Asia/Hong_Kong","China":"Asia/Shanghai","Taiwan":"Asia/Taipei","Europe":"Europe/Berlin","Crypto":"UTC"}.get(str(market),'UTC')
    return t.tz_convert(ZoneInfo(tz)).date().isoformat()

class ProspectiveValidationStore:
    def __init__(self,path:Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._cx() as cx: cx.executescript(SCHEMA)
    def _cx(self):
        cx=sqlite3.connect(str(self.path)); cx.row_factory=sqlite3.Row; return cx
    def snapshot_universe(self,catalog:pd.DataFrame,market:str,source:str,observed_at:Any=None)->int:
        if catalog is None or catalog.empty:return 0
        ts=_utc(observed_at); d=_local_date(ts,market); n=0
        with self._cx() as cx:
            for _,r in catalog.iterrows():
                sym=str(r.get('symbol') or r.get('ticker') or '').strip()
                if not sym:continue
                cur=cx.execute('INSERT OR IGNORE INTO universe_observations(asof_date,market,symbol,name,source,observed_at_utc,metadata_json) VALUES(?,?,?,?,?,?,?)',(d,str(market),sym,str(r.get('name') or sym),str(source),ts,_json(dict(r))))
                n+=max(0,cur.rowcount)
        return n
    def freeze_baselines(self,scan:pd.DataFrame,benchmarks:Mapping[str,str],observed_at:Any=None)->int:
        if scan is None or scan.empty:return 0
        ts=_utc(observed_at); total=0
        rules=[
            ('Strongest 6M performer','price_change_6m','max'),
            ('Highest earnings growth','eps_growth_yoy','max'),
            ('Cheapest valuation','forward_pe','min'),
            ('Highest analyst revisions','expectation_revision_score','max'),
        ]
        with self._cx() as cx:
            for market,g0 in scan.groupby('market'):
                if str(market) not in {'US','IHSG','HK','Hong Kong','China','Europe','Taiwan'}:continue
                d=_local_date(ts,str(market)); g=g0.copy()
                picks=[]
                for name,col,direction in rules:
                    vals=pd.to_numeric(g.get(col,pd.Series(index=g.index,dtype=float)),errors='coerce')
                    if name=='Cheapest valuation':
                        # A positive multiple is not automatically defensible.  The
                        # selector must be frozen only from rows whose PIT valuation
                        # evidence actually cleared the model's own data gate.
                        confidence=g.get('valuation_confidence',pd.Series(index=g.index,dtype=object)).astype(str).str.upper()
                        vals=vals.where((vals>0) & confidence.isin({'HIGH','MEDIUM'}))
                    if name=='Highest analyst revisions':
                        revision_state=g.get('expectation_revision_state',pd.Series(index=g.index,dtype=object)).astype(str).str.upper()
                        vals=vals.where(~revision_state.isin({'','N/A','NA','UNKNOWN','NONE','DATA GATED','GATED'}))
                    valid=vals.dropna()
                    if valid.empty:continue
                    idx=valid.idxmax() if direction=='max' else valid.idxmin(); picks.append((name,idx,float(vals.loc[idx])))
                if 'sector' in g and 'price_change_6m' in g:
                    tmp=g.assign(_m=pd.to_numeric(g['price_change_6m'],errors='coerce')).dropna(subset=['_m'])
                    tmp=tmp[tmp['sector'].astype(str).str.strip().ne('') & tmp['sector'].astype(str).str.upper().ne('UNKNOWN')]
                    if not tmp.empty:
                        sm=tmp.groupby('sector')['_m'].median(); top=sm.idxmax(); sg=tmp[tmp['sector']==top]
                        # representative expression: most liquid if available, else best 6M inside sector
                        liq=pd.to_numeric(sg.get('avg_value_20d',pd.Series(index=sg.index,dtype=float)),errors='coerce')
                        idx=liq.idxmax() if liq.notna().any() else sg['_m'].idxmax(); picks.append(('Sector momentum',idx,float(sm.loc[top])))
                # Freeze the existing engine itself as a transparent comparator.  This
                # is a ranking baseline, not a validated score or probability.
                if 'research_action' in g:
                    tiers={'BUILD CANDIDATE':5,'SELECTIVE ADD / WATCH':4,'HOLD / NEEDS BETTER PRICE':3,'WATCH / NO FORCED TRADE':2,'WATCH / VALUATION GATED':2,'WATCH / DATA GATED':1}
                    action=g['research_action'].astype(str).map(tiers).fillna(0.0)
                    evidence=pd.to_numeric(g.get('evidence_families',pd.Series(index=g.index,dtype=float)),errors='coerce').fillna(0.0)
                    readiness=g.get('vertical_status',pd.Series(index=g.index,dtype=object)).astype(str).str.upper().isin({'READY','PARTIAL'})
                    engine_value=(action*100.0+evidence).where(readiness)
                    valid_engine=engine_value.dropna()
                    if not valid_engine.empty:
                        idx=valid_engine.idxmax(); picks.append(('Existing engine',idx,float(engine_value.loc[idx])))
                for name,idx,val in picks:
                    r=g.loc[idx]; sym=str(r.get('symbol') or ''); px=_f(r.get('price'))
                    if not sym or px is None or px<=0:continue
                    cur=cx.execute('INSERT OR IGNORE INTO baseline_selections(asof_date,observed_at_utc,market,baseline,symbol,benchmark,anchor_price,feature_value,snapshot_json) VALUES(?,?,?,?,?,?,?,?,?)',(d,ts,str(market),name,sym,str(benchmarks.get(str(market),'')),px,val,_json(dict(r))))
                    total+=max(0,cur.rowcount)
        return total
    def selections_due(self,limit:int=6)->pd.DataFrame:
        q='''SELECT b.*,MAX(o.updated_at_utc) AS last_update FROM baseline_selections b LEFT JOIN baseline_outcomes o ON b.id=o.selection_id GROUP BY b.id ORDER BY (MAX(o.updated_at_utc) IS NOT NULL) ASC,MAX(o.updated_at_utc) ASC,b.observed_at_utc ASC LIMIT ?'''
        with self._cx() as cx: rows=cx.execute(q,(int(limit),)).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()
    def upsert_outcomes(self,selection:Mapping[str,Any],asset:pd.Series,benchmark:Optional[pd.Series]=None)->int:
        n=0
        for h,days in OUTCOME_HORIZONS.items():
            result=path_outcome(asset,selection['observed_at_utc'],anchor_price=selection.get('anchor_price'),benchmark=benchmark,horizon_days=days)
            if not result:continue
            with self._cx() as cx:
                cx.execute('''INSERT INTO baseline_outcomes(selection_id,horizon,horizon_end_utc,absolute_return,benchmark_return,alpha_vs_benchmark,completed,outcome_json,updated_at_utc) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(selection_id,horizon) DO UPDATE SET horizon_end_utc=excluded.horizon_end_utc,absolute_return=excluded.absolute_return,benchmark_return=excluded.benchmark_return,alpha_vs_benchmark=excluded.alpha_vs_benchmark,completed=excluded.completed,outcome_json=excluded.outcome_json,updated_at_utc=excluded.updated_at_utc''',(int(selection['id']),h,result.get('horizon_end_utc'),_f(result.get('absolute_return')),_f(result.get('benchmark_return')),_f(result.get('alpha_vs_benchmark')),1 if result.get('completed') else 0,_json(result),_utc()))
            n+=1
        return n
    def baseline_outcomes_frame(self)->pd.DataFrame:
        q='''SELECT o.*,b.baseline,b.market,b.symbol,b.asof_date,b.observed_at_utc FROM baseline_outcomes o JOIN baseline_selections b ON o.selection_id=b.id ORDER BY o.updated_at_utc DESC'''
        with self._cx() as cx: rows=cx.execute(q).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def freeze_runner_cohort(self,scan:pd.DataFrame,benchmarks:Mapping[str,str],observed_at:Any=None)->int:
        # Freeze one PIT runner-audit anchor per symbol/local-market day.
        if scan is None or scan.empty:return 0
        ts=_utc(observed_at); total=0
        with self._cx() as cx:
            for _,r in scan.iterrows():
                market=str(r.get('market') or ''); sym=str(r.get('symbol') or '').strip(); px=_f(r.get('price'))
                if not market or not sym or px is None or px<=0:continue
                d=_local_date(ts,market)
                cur=cx.execute('INSERT OR IGNORE INTO runner_anchor_snapshots(asof_date,observed_at_utc,market,symbol,benchmark,anchor_price,snapshot_json) VALUES(?,?,?,?,?,?,?)',(d,ts,market,sym,str(benchmarks.get(market,'')),px,_json(dict(r))))
                total+=max(0,cur.rowcount)
        return total

    def runner_anchors_due(self,min_age_days:int=91,limit:int=8,now:Any=None)->pd.DataFrame:
        cutoff=pd.Timestamp(_utc(now))-pd.Timedelta(days=int(min_age_days))
        with self._cx() as cx:
            rows=cx.execute("SELECT * FROM runner_anchor_snapshots WHERE audited=0 AND observed_at_utc<=? ORDER BY observed_at_utc ASC,id ASC LIMIT ?",(cutoff.isoformat(),int(limit))).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def mark_runner_audited(self,anchor_id:int,observed_at:Any=None)->None:
        with self._cx() as cx:
            cx.execute('UPDATE runner_anchor_snapshots SET audited=1,audited_at_utc=? WHERE id=?',(_utc(observed_at),int(anchor_id)))

    def runner_anchors_frame(self)->pd.DataFrame:
        with self._cx() as cx:
            rows=cx.execute('SELECT * FROM runner_anchor_snapshots ORDER BY observed_at_utc DESC').fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def universe_frame(self,market:Optional[str]=None)->pd.DataFrame:
        with self._cx() as cx:
            rows=cx.execute('SELECT * FROM universe_observations WHERE market=? ORDER BY observed_at_utc DESC' if market else 'SELECT * FROM universe_observations ORDER BY observed_at_utc DESC',(market,) if market else ()).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()
