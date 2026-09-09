from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ui = (ROOT / "opportunity_ui.py").read_text(encoding="utf-8")
app = (ROOT / "app.py").read_text(encoding="utf-8")

assert 'st.session_state.get("mq_global_search_v322","")' in ui
assert 'st.session_state.get("mq_market_scope_v322")' in ui
assert 'str.contains(query,regex=False,na=False)' in ui

for label in [
    "DETECTION PRICE", "CURRENT PRICE", "MOVE SINCE DETECTION",
    "DRIVER", "FIRST ORDER", "SECOND ORDER", "BOTTLENECK", "BENEFICIARY",
    "REVENUE LINK", "MARGIN LINK", "CATALYST", "INVALIDATION",
    "Component availability", "CAPTURE GATE",
]:
    assert label in ui, label

assert 'score_label=_num(score_value,0) if math.isfinite(score_value) else "GATED"' in ui

print("TEST_OPPORTUNITY_COCKPIT_CONTRACT_V33_PASS")
