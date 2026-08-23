
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parents[1]
def _r(fn):
    p=HERE/'research'/fn;return pd.read_csv(p) if p.exists() else pd.DataFrame()
def load_experiments():return _r('experiment_registry.csv')
def load_failures():return _r('failure_library.csv')
def load_search_ledger():return _r('search_ledger.csv')
def load_governance_overrides():return _r('governance_overrides.csv')
def proof_summary():
    e=load_experiments();return e.groupby('status').size().rename('count').reset_index().sort_values('count',ascending=False) if len(e) else pd.DataFrame()
