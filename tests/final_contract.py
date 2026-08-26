from pathlib import Path
import ast
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
macro=(ROOT/'macro_embedded.py').read_text(encoding='utf-8')
ast.parse(app); ast.parse(macro)

u=pd.read_csv(ROOT/'data/universe.csv')
assert set(['US','IHSG','FX','Commodity','Crypto']).issubset(set(u.market)), set(u.market)
assert not u.symbol.duplicated().any(), u[u.symbol.duplicated(keep=False)][['market','symbol']].to_dict('records')
assert 'JPY=X' not in set(u.symbol), 'redundant FX placeholder must be removed'
assert 'defillama_slug' in u.columns
assert {'VVV-USD','HYPE-USD','AAVE-USD','UNI-USD','SKY-USD'}.issubset(set(u.symbol))

for fn in ['fetch_deribit_option_snapshot','fetch_option_snapshot','_expression_tables','_expression_readiness','_render_opportunity_detail']:
    assert f'def {fn}(' in app, fn
for fn in ['compute_macro_gate_snapshot','render_macro_control_room']:
    assert f'def {fn}(' in macro, fn

# Final macro renderer must be a single compact page, not another nested tab maze.
renderer=macro.split('def render_macro_control_room():',1)[1]
assert 'st.tabs(' not in renderer
assert 'Most supported paths' in renderer
assert 'Where the economy is going' in renderer
assert 'What would change the action?' in renderer

# Expression contract.
assert 'US","ACTIVE WHEN EARNED' in app
assert 'BTC / ETH","VISIBLE · DERIBIT' in app
assert 'FX","VISIBLE' in app
assert 'Commodity","VISIBLE' in app
assert 'IHSG","NOT ALLOWED"' in app
assert 'Expression coverage · nothing disappears when gated' in app
assert 'Opportunity map · evidence × unpriced asymmetry' in app


# Valuation must fail closed when same-sector peer evidence is weak; no whole-market fallback or seed percentile action.
assert 'GATED · insufficient same-sector peers' in app
assert 'same-sector forward P/E' in app
action_block=app.split('def action_from_relative_rank',1)[1].split('def deep_crypto_metrics',1)[0]
assert 'gap_rank' not in action_block
rank_block=app.split('def rank_opportunities',1)[1].split('def infer_specific_root',1)[0]
assert 'gap_rank' not in rank_block

# Classic technical indicators must never enter the calculation path.
for banned in ['talib.RSI','ta.rsi','MACD(','stoch(','bollinger','moving_average_signal']:
    assert banned.lower() not in app.lower(), banned

src=pd.read_csv(ROOT/'data/source_registry.csv')
assert 'status' in src.columns
assert (src.status.astype(str).str.contains('REQUIRED').any())
assert (src.source.astype(str).str.contains('Deribit').any())

print({'FINAL_CONTRACT_PASS':True,'universe':len(u),'markets':sorted(u.market.unique().tolist()),'sources':len(src)})
