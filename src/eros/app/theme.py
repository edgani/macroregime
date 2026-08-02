"""EROS visual system: restrained dark interface for decision support."""
# ruff: noqa: E501

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --panel-2: #111827;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #3fb950;
  --amber: #d29922;
  --red: #f85149;
  --blue: #58a6ff;
}
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: Inter, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
}
[data-testid="stHeader"] { background: rgba(13,17,23,.92); }
[data-testid="stMainBlockContainer"] { max-width: 1500px; padding-top: 1.5rem; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
.hero {
  border: 1px solid var(--border); border-radius: 14px; padding: 16px;
  background: linear-gradient(135deg, #161b22 0%, #0f1b2d 100%); margin-bottom: 8px;
}
.hero-kicker, .section-heading span { color: var(--blue); letter-spacing: .12em; font-size: 11px; font-weight: 700; text-transform: uppercase; }
.hero h1 { font-size: 26px; margin: 3px 0 4px; }
.hero p, .section-heading p, .status-card p { color: var(--muted); margin: 0; }
.mode-strip { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.mode-pill { border: 1px solid var(--border); border-radius: 999px; padding: 5px 10px; font-size: 11px; color: var(--muted); }
.section-heading { margin: 22px 0 12px; }
.section-heading h2 { margin: 4px 0; font-size: 20px; }
.status-card { min-height: 142px; border: 1px solid var(--border); background: var(--panel); border-radius: 10px; padding: 16px; }
.status-card strong { display: block; font-size: 22px; margin: 16px 0 8px; }
.card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 12px; }
.evidence-badge { display: inline-block; border: 1px solid var(--border); border-radius: 999px; padding: 3px 7px; font-size: 9px; font-weight: 700; letter-spacing: .04em; color: var(--muted); }
.live, .proven-scope-limited, .replicated-oos { border-color: #238636; color: var(--green); }
.partial, .prospective-pending, .historically-supported, .candidate { border-color: #9e6a03; color: var(--amber); }
.stale, .busted-as-tested { border-color: #da3633; color: var(--red); }
.decision-row { border-left: 2px solid var(--border); padding: 8px 12px; margin: 6px 0; background: rgba(22,27,34,.55); color: var(--text); }
.brief { border: 1px solid #1f6feb; background: rgba(31,111,235,.08); border-radius: 10px; padding: 14px; margin: 10px 0; }
.brief h3 { margin: 0 0 6px; font-size: 20px; }
.brief ul { margin: 4px 0 0; padding-left: 20px; }
.brief li { margin: 4px 0; color: #c9d1d9; }
[data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--border); }
button[data-baseweb="tab"] { background: var(--panel); border: 1px solid var(--border); border-radius: 8px 8px 0 0; padding: 10px 14px; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--text); border-bottom-color: var(--blue); }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
@media (max-width: 800px) {
  [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; }
  .hero h1 { font-size: 24px; }
  button[data-baseweb="tab"] { padding: 8px; font-size: 11px; }
}
</style>
"""
