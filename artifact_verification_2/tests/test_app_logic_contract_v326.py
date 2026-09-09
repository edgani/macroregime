from __future__ import annotations
import ast, math
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'app.py').read_text(encoding='utf-8')
tree=ast.parse(source)

def load_fn(name,ns):
    node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    mod=ast.Module(body=[node],type_ignores=[]); ast.fix_missing_locations(mod)
    exec(compile(mod,str(ROOT/'app.py'),'exec'),ns)
    return ns[name]

def sf(x):
    try:
        v=float(x); return v if np.isfinite(v) else np.nan
    except Exception:return np.nan

def clamp(x,lo,hi):
    return max(lo,min(hi,x)) if np.isfinite(x) else np.nan

scenario=load_fn('scenario_growth_bands',{'pd':pd,'np':np,'Tuple':tuple,'safe_float':sf,'clamp':clamp})
a=scenario(pd.Series({'revenue_growth_yoy':.2}))
assert all(math.isnan(float(x)) for x in a),a
b=scenario(pd.Series({'revenue_growth_yoy':.2,'eps_growth_yoy':.2}))
assert all(abs(float(x)-.2)<1e-12 for x in b),b

# Cross-sectional stock fundamentals are one correlated family, not four votes.
def percentile_rank(s,value):
    x=pd.to_numeric(s,errors='coerce').dropna()
    if x.empty or not np.isfinite(sf(value)): return np.nan
    less=(x<value).sum(); equal=(x==value).sum(); return float((less+0.5*equal)/len(x))

def tx_delta(row): return (0,0,'transaction gated')
add=load_fn('add_cross_sectional_evidence',{'pd':pd,'np':np,'safe_float':sf,'percentile_rank':percentile_rank,'transaction_evidence_delta':tx_delta})
df=pd.DataFrame([
 {'market':'US','symbol':'A','sector':'S','revenue_growth_yoy':.5,'eps_growth_yoy':.6,'gross_margin_change':.08,'fcf_growth_yoy':.7,'net_margin':.3,'data_quality':'HIGH'},
 {'market':'US','symbol':'B','sector':'S','revenue_growth_yoy':.1,'eps_growth_yoy':.1,'gross_margin_change':.01,'fcf_growth_yoy':.1,'net_margin':.1,'data_quality':'HIGH'},
 {'market':'US','symbol':'C','sector':'S','revenue_growth_yoy':.08,'eps_growth_yoy':.05,'gross_margin_change':.005,'fcf_growth_yoy':.04,'net_margin':.08,'data_quality':'HIGH'},
 {'market':'US','symbol':'D','sector':'S','revenue_growth_yoy':.02,'eps_growth_yoy':.01,'gross_margin_change':0,'fcf_growth_yoy':.01,'net_margin':.05,'data_quality':'HIGH'},
 {'market':'US','symbol':'E','sector':'S','revenue_growth_yoy':-.1,'eps_growth_yoy':-.1,'gross_margin_change':-.02,'fcf_growth_yoy':-.1,'net_margin':.02,'data_quality':'HIGH'},
])
out=add(df)
r=out[out.symbol=='A'].iloc[0]
assert int(r['fundamental_confirmation_count'])>=2,r
assert int(r['evidence_families'])==1,r

print('TEST_APP_LOGIC_CONTRACT_V326_PASS')
