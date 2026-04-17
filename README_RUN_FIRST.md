# README_RUN_FIRST

This zip is a full mirror of the uploaded current repo, rebuilt as a fresh archive so you can delete the old folder and extract from scratch.

What is included:
- all source files from the uploaded repo
- hidden config files like `.gitattributes`, `.gitignore`, `.streamlit/*`
- `.cache/*`
- `config/`, `data/`, `domain/`, `engines/`, `features/`, `orchestration/`, `scripts/`, `ui/`, `utils/`
- docs and reports already present in the uploaded repo

What was NOT removed:
- no source/module folders were removed
- no scenarios / what-if / engine folders were removed
- no cache or pycache folders were removed

Recommended run:
1. create a fresh folder
2. extract this zip there
3. install deps:
   pip install -r requirements.txt
4. run:
   streamlit run app.py

If you want a slimmer production-clean zip later, that would be a separate artifact.
This one is the safest 'nothing missing' full rebuild.