from __future__ import annotations
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
os.environ['WARROOM_ROOT']=str(ROOT)
app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
if app.exception:
    raise SystemExit('streamlit app exceptions: '+','.join(str(e.value) for e in app.exception))
if not any(title.value=='War Room OS v3' for title in app.title):
    raise SystemExit('streamlit title missing')
print('PASS: streamlit app smoke test')
