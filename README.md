# MacroRegime Autonomy Stack v10 — LIGHTWEIGHT

## Problem Solved
Streamlit Cloud free tier stuck installing PyTorch (2GB+). This version removes ALL heavy ML dependencies.

## What's Different
- NO `torch`
- NO `transformers`
- NO 500MB model downloads
- NLP is 100% regex/knowledge-based (still powerful for financial headlines)
- Build time: <2 minutes on Streamlit Cloud

## Install
1. Replace `requirements.txt` with the lightweight version
2. Copy ALL `engines/*.py` and `config/autonomy_settings.py` to your repo
3. Replace `orchestrator.py` with the lightweight version
4. Push → redeploy

## Files
- `requirements.txt` — lightweight deps
- `engines/news_nlp_engine_v3.py` — regex NLP (no FinBERT)
- `engines/price_cluster_engine_v3.py` — graph clustering
- `engines/edgar_scraper_engine.py` — SEC 10-K parser
- `engines/supply_chain_graph_engine.py` — NetworkX centrality
- `engines/leading_indicator_engine.py` — GBM regression
- `engines/regime_predictor_engine.py` — ensemble predictor
- `engines/auto_discovery_engine_v3.py` — integration brain
- `engines/feedback_loop_engine_v3.py` — learning loop
- `config/autonomy_settings.py` — tunable params
- `orchestrator.py` — full orchestrator with autonomy step 15
