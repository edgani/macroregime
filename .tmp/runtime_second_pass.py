from streamlit.testing.v1 import AppTest


def report(name, app):
    print(name, "exceptions=", len(app.exception), "buttons=", [b.label for b in app.button], "selectboxes=", [s.label for s in app.selectbox])
    assert not app.exception, [str(x.value) for x in app.exception]


app = AppTest.from_file("../app.py", default_timeout=180).run()
report("CONTROL ROOM", app)

for route in ["OPPORTUNITIES", "VERTICALS", "MACRO & EVENTS", "LEARNING / REPLAY"]:
    next(b for b in app.button if b.label == route).click()
    app.run(timeout=180)
    report(route, app)

for label in ["TRUE WALK-FORWARD", "BASELINES", "RUNNER RECALL", "FAILURES", "MISSED WINNERS", "PATTERN EXPECTANCY"]:
    next(b for b in app.button if b.label == label).click()
    app.run(timeout=180)
    report("LEARNING:" + label, app)

app.text_input[0].set_value("ZZZ_NOT_FOUND")
app.run(timeout=180)
report("SEARCH:NO_MATCH", app)
app.text_input[0].set_value("")
app.multiselect[0].set_value(["US"])
app.run(timeout=180)
report("MARKET:US", app)
next(b for b in app.button if b.label == "REFRESH").click()
app.run(timeout=180)
report("REFRESH", app)

next(b for b in app.button if b.label == "VERTICALS").click()
app.run(timeout=180)
if app.selectbox:
    options = list(app.selectbox[0].options)
    if len(options) > 1:
        app.selectbox[0].select(options[-1])
        app.run(timeout=180)
report("VERTICAL:SELECT", app)

next(b for b in app.button if b.label == "OPPORTUNITIES").click()
app.run(timeout=180)
if app.selectbox:
    options = list(app.selectbox[0].options)
    if len(options) > 1:
        app.selectbox[0].select(options[-1])
        app.run(timeout=180)
report("OPPORTUNITY:SELECT", app)
