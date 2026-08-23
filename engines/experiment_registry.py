
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parents[1]
def load_experiments(): return pd.read_csv(HERE/'research'/'experiment_registry.csv')
def load_failures(): return pd.read_csv(HERE/'research'/'failure_library.csv')
def load_search_ledger(): return pd.read_csv(HERE/'research'/'search_ledger.csv')
def proof_summary():
    e=load_experiments(); return e.groupby('status').size().rename('count').reset_index().sort_values('count',ascending=False)
