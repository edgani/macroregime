# 🚀 INSTALL — MacroRegime Pro v2 Full Bundle

## TL;DR
Extract this zip, push to your GitHub repo, Streamlit Cloud auto-redeploys.

## Step-by-Step

### Option A: Replace your existing repo (recommended)

```bash
# 1. From your local repo
cd /path/to/your/edgani/tes  # or wherever your Streamlit-connected repo is

# 2. Backup current state
git add . && git commit -m "Pre-v2 backup"

# 3. Replace everything with v2 bundle
rm -rf app.py orchestrator.py requirements.txt data/ engines/ config/
unzip ~/Downloads/macroregime_v2_FULL.zip
cp -r macroregime_FULL/* .
cp -r macroregime_FULL/.streamlit .streamlit  # optional

# 4. Commit and push
git add .
git commit -m "v2: cascade engine, yves v2, discovery brain, GIP v10"
git push

# 5. Streamlit Cloud auto-redeploys.
```

### Option B: Clone fresh repo

```bash
unzip ~/Downloads/macroregime_v2_FULL.zip
cd macroregime_FULL
git init
git remote add origin https://github.com/edgani/tes.git
git add .
git commit -m "Initial v2"
git push -u origin main --force
```

## ⚠️ Required Streamlit Secrets

Streamlit Cloud → your app → Settings → Secrets — paste:

```toml
FRED_API_KEY = "your_fred_key_here"
POLYGON_API_KEY = "your_polygon_key_here"   # optional, free tier OK
```

Get FRED key (free, instant): https://fredaccount.stlouisfed.org/apikeys
Get Polygon key (free 5 req/min): https://polygon.io/dashboard/signup

## ✅ What's New (vs current deployed)

| Component | Status |
|---|---|
| `app.py` (3,830 lines) | PATCHED — adds portfolio sizing sidebar + 8 v2 dashboard sections |
| `orchestrator.py` (2,354 lines) | PATCHED — 9 v2 engine imports + 8 v2 engine calls |
| `requirements.txt` | Added `zstandard>=0.21` |
| `data/fred_loader.py` | NEW v3 — FRED API key support + 30 series + multi-source fallback |
| `data/loader.py` | NEW v4 — Tiered universe + Polygon fallback + auto-blacklist |
| `engines/vanna_proxy_engine.py` | BUG FIX — defensive scoping |
| `engines/afternoon_signal.py` | BUG FIX — defensive scoping |
| `engines/cascade_engine.py` ★ | NEW — Universal second-order mapping (Oil→Tankers, etc.) |
| `engines/yves_engine.py` ★ | NEW — 6 specific actionable alert types |
| `engines/portfolio_sizing.py` ★ | NEW — % of portfolio sizing with Kelly + caps |
| `engines/discovery_brain.py` ★ | NEW — Adaptive + Reactive + Proactive triad |
| `engines/cem_karsan_universal.py` ★ | NEW — Multi-market options (Deribit + yfinance + proxy) |
| `engines/ticker_universe_expander.py` ★ | NEW — Auto-discover new tickers |
| `engines/edgar_scraper_real.py` | NEW — replaces 13-line stub |
| `engines/supply_chain_graph_real.py` | NEW — replaces 13-line stub (NetworkX) |
| `engines/gip_engine_v10.py` ★ | NEW — Bayesian + nowcasting (Edward's Q1 GIP→100%) |

Stub engines renamed to `.OLD_STUB` (preserved as backup):
- `engines/edgar_scraper_engine.py.OLD_STUB`
- `engines/supply_chain_graph_engine.py.OLD_STUB`
- `engines/risk_range_engine.py.OLD_STUB`

All your existing engines (49 total) are preserved — only new ones added on top.

## 📊 Expected First Run Log

```
INFO | data.fred_loader   | FRED v3 loaded 28/30 series via {'api': 28}
INFO | data.loader        | Tier 1 done: 48/50 core
INFO | orchestrator       | V2 engines loaded: cascade=True yves=True sizing=True
                            discovery=True cem=True expander=True edgar=True
                            supply=True gip10=True
INFO | orchestrator       | Cascade engine: 8 active shocks, 156 total impacts
INFO | orchestrator       | Yves v2: 3 alerts generated
INFO | orchestrator       | Discovery Brain: 24 candidates (A=2 R=10 P=12)
INFO | orchestrator       | Ticker expander auto-add: ['FRO','STNG','POET','VST',...]
INFO | orchestrator       | Portfolio sizing v2: 14 positions, 87% deployed
INFO | orchestrator       | Orchestrator complete in ~85s
```

## 🚨 Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'config'` | You extracted only partial files. Use this full bundle. |
| FRED returns 0 series | `FRED_API_KEY` not set in Streamlit secrets |
| `ModuleNotFoundError: networkx` | `pip install networkx>=3.0` (in requirements.txt already) |
| V2 sections not showing | Check orchestrator log for `V2 engines loaded:` line |
| Cascade returns 0 impacts | Active shocks need 5d return >5% on key tickers — try forcing a CL=F shock test |

## 📁 Bundle Contents

```
macroregime_FULL/
├── .devcontainer/         # Dev container config
├── .streamlit/             # Streamlit config + secrets example
├── config/                 # YOUR existing config (settings.py, narrative_universe.py)
├── data/
│   ├── fred_loader.py      # v3 NEW
│   └── loader.py           # v4 NEW
├── docs/
│   ├── README.md
│   └── INTEGRATION_PATCHES.md
├── engines/                # ALL existing engines + 9 new v2 engines
│   ├── (49 existing engines preserved)
│   ├── cascade_engine.py            # NEW ★
│   ├── cem_karsan_universal.py      # NEW ★
│   ├── discovery_brain.py            # NEW ★
│   ├── edgar_scraper_real.py         # NEW (replaces stub)
│   ├── gip_engine_v10.py             # NEW ★
│   ├── portfolio_sizing.py           # NEW ★
│   ├── supply_chain_graph_real.py    # NEW (replaces stub)
│   ├── ticker_universe_expander.py   # NEW ★
│   └── yves_engine.py                # NEW ★
├── scripts/
│   └── cleanup.sh
├── app.py                  # PATCHED (3,830 lines)
├── orchestrator.py         # PATCHED (2,354 lines)
├── requirements.txt        # UPDATED
├── bottleneck_reference.json
└── INSTALL.md              # this file
```

## #process — Process output, manage risk accordingly.
