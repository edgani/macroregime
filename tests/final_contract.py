from pathlib import Path
import ast
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ui=(ROOT/'opportunity_ui.py').read_text(encoding='utf-8')
macro=(ROOT/'macro_embedded.py').read_text(encoding='utf-8')
ast.parse(app); ast.parse(ui); ast.parse(macro)

u=pd.read_csv(ROOT/'data/universe.csv')
assert set(['US','IHSG','FX','Commodity','Crypto']).issubset(set(u.market)), set(u.market)
assert not u.symbol.duplicated().any(), u[u.symbol.duplicated(keep=False)][['market','symbol']].to_dict('records')
assert 'JPY=X' not in set(u.symbol), 'redundant FX placeholder must be removed'
assert 'defillama_slug' in u.columns
assert {'VVV-USD','HYPE-USD','AAVE-USD','UNI-USD','SKY-USD'}.issubset(set(u.symbol))

for fn in ['fetch_deribit_option_snapshot','fetch_option_snapshot','_expression_tables','_expression_readiness','_render_control_room','_render_verticals','_render_macro_visual_room']:
    assert f'def {fn}(' in app, fn
for fn in ['render_opportunity_tracker','render_learning_lab','render_dense_table','dense_table_html','install_memequant_style']:
    assert f'def {fn}(' in ui, fn
for fn in ['compute_macro_gate_snapshot','render_macro_control_room']:
    assert f'def {fn}(' in macro, fn

# Macro module may expose a compatibility entrypoint, but it must never inject its retired visual system.
assert '<style>' not in macro
assert 'st.dataframe' not in macro and 'st.tabs(' not in macro and 'st.expander' not in macro
renderer=macro.split('def render_macro_control_room():',1)[1]
assert 'return compute_macro_gate_snapshot' in renderer

# Expression/data contracts are preserved behind the unified surface.
assert 'US","ACTIVE WHEN EARNED' in app
assert 'BTC / ETH","VISIBLE · DERIBIT' in app
assert 'FX","VISIBLE' in app
assert 'Commodity","VISIBLE' in app
assert 'IHSG","NOT ALLOWED"' in app
assert 'NAV_ITEMS=["CONTROL ROOM","OPPORTUNITIES","VERTICALS","MACRO & EVENTS","LEARNING / REPLAY"]' in app
assert 'st.sidebar' not in app

# One product design system only.
visible=app+ui
for legacy in ['DECISION DESK','Legacy research / validation','st.tabs(','st.dataframe','st.metric','st.expander','st.sidebar']:
    assert legacy not in visible, legacy
assert 'mq-table-wrap' in ui and 'mq-pagehead' in ui and 'mq-grid' in ui

# Valuation must fail closed when same-sector peer evidence is weak; no whole-market fallback or seed percentile action.
assert 'GATED · insufficient same-sector peers' in app
assert 'same-sector forward P/E' in app
action_block=app.split('def action_from_relative_rank',1)[1].split('def deep_crypto_metrics',1)[0]
assert 'gap_rank' not in action_block
rank_block=app.split('def rank_opportunities',1)[1].split('def infer_specific_root',1)[0]
assert 'gap_rank' not in rank_block

for banned in ['talib.RSI','ta.rsi','MACD(','stoch(','bollinger','moving_average_signal']:
    assert banned.lower() not in app.lower(), banned

src=pd.read_csv(ROOT/'data/source_registry.csv')
assert 'status' in src.columns
assert (src.status.astype(str).str.contains('REQUIRED').any())
assert (src.source.astype(str).str.contains('Deribit').any())
print({'FINAL_CONTRACT_PASS':True,'universe':len(u),'markets':sorted(u.market.unique().tolist()),'sources':len(src)})
