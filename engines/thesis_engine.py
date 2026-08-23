
from __future__ import annotations
import pandas as pd,numpy as np
from .scenario_engine import live_evidence

def lifecycle(state):
    d=live_evidence(state).copy();d['initial_prior']='DATA_GATED';d['catalyst_window']=['1-4Q','1-4Q','Days-4Q','Indeterminate'];d['thesis_decay']='DATA_GATED: requires dated catalyst likelihood model';d['invalidation']=['Growth weakens with credit/funding stress OR inflation reaccelerates materially','Inflation expectations/real yields fall while growth remains resilient','Credit/funding normalize despite weaker growth','Discriminating evidence separates scenarios'];return d

def coherent_probability_check(df):
    p=pd.to_numeric(df.get('probability'),errors='coerce').dropna()
    if len(p)!=len(df):return False,'Probabilities intentionally unavailable; no normalization performed.'
    return abs(p.sum()-1)<1e-6,f'Sum={p.sum():.6f}'
