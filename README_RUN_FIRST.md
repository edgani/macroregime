# README_RUN_FIRST

This build keeps the current repo engines and snapshot pipeline, but replaces the broken bridge UI with a simpler visible refactor UI.

What changed:
- new app entry in `app.py`
- backup of old app in `app_legacy_singlefile.py`
- new render/runtime modules:
  - `ui/final_runtime.py`
  - `ui/final_pages.py`

Run:
    pip install -r requirements.txt
    streamlit run app.py