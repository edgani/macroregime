from pathlib import Path

app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

for slug in ["CONTROL_ROOM", "OPPORTUNITIES", "VERTICALS", "MACRO_EVENTS", "LEARNING_REPLAY"]:
    assert f'"{slug}"' in app

assert 'st.query_params.get("route")' in app
assert 'st.query_params["route"] = ROUTE_TO_QUERY[target]' in app
assert 'st.session_state["decision_nav_v322"]=linked' in app
print("deep-link routing contract: PASS")
