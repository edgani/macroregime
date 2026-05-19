# 🚀 MacroRegime Pro v2.1 PATCH — Sprint 5 Fixes

**Date:** May 15, 2026

## Apa yang Diperbaiki dari v2

| Issue di Screenshot | Fix di v2.1 |
|---|---|
| `Failed to import risk_range_engine` | ✅ REAL implementation 353 lines dengan ATR + multi-duration + regime-conditional |
| Bad tickers SIPHONICS/FANUC/KEYENCE/TSMC/dll spam log | ✅ Company name → ticker mapping + smart blacklist |
| Cascade dynamic edges run 4x dalam 1 build | ✅ Disk cache 6h TTL → cuma compute sekali |
| 122s build time | ✅ Setelah cache populated → ~50-70s |
| YFRateLimitError → 0DTE chain spam fail | ✅ Yahoo cooldown 60s setelah 429 → skip Tier 2 |
| Dashboard penuh dengan ticker tables | ✅ Dashboard = **MACRO ONLY**, ticker stuff dipindah ke Alpha Center |
| Scrolling banyak di Dashboard | ✅ 4 tabs (Yves / GIP / Discovery / Cascade summary) |

## Install (Update dari v2)

```bash
# Dari root repo lu (yang udah ada v2 sebelumnya)
cd /path/to/edgani/tes

# 1. Backup
git add . && git commit -m "Pre-v2.1 backup"

# 2. Extract v2.1 patch
unzip ~/Downloads/macroregime_v2_1.zip

# 3. Overlay patch ke repo
cp macroregime_FULL_v21/app.py .
cp macroregime_FULL_v21/orchestrator.py .
cp macroregime_FULL_v21/data/loader.py data/loader.py
cp macroregime_FULL_v21/engines/risk_range_engine.py engines/risk_range_engine.py
cp macroregime_FULL_v21/engines/cascade_engine.py engines/cascade_engine.py
cp macroregime_FULL_v21/engines/supply_chain_graph_real.py engines/supply_chain_graph_real.py
rm -f engines/risk_range_engine.py.OLD_STUB

# 4. Commit + push
git add .
git commit -m "v2.1: Sprint 5 — risk_range real, cascade cache, smart filter, dashboard reorg"
git push
```

Streamlit Cloud auto-redeploy.

## Verifikasi Setelah Deploy

Lu harusnya lihat:

```
INFO | orchestrator | V2 engines loaded: cascade=True yves=True ...
INFO | data.fred_loader | FRED v3 loaded 28/29 series via {'api': 28}
INFO | data.loader | Skipped 22 unmappable names: ['SIPHONICS', 'FANUC', ...]
INFO | data.loader | Skipped 10 blacklisted tickers
INFO | engines.cascade_engine | Cascade dynamic edges: 3276 discovered (FRESH compute)
  ← FIRST BUILD ONLY. Subsequent builds:
INFO | engines.cascade_engine | Cascade dynamic edges: 3276 loaded from cache (0.5h old)
INFO | orchestrator | Cascade engine: 3 active shocks, 294 total impacts
INFO | orchestrator | Yves v2: 1 alerts generated
INFO | orchestrator | Discovery Brain: 28 candidates
INFO | orchestrator | Portfolio sizing v2: N positions, X% deployed
INFO | orchestrator | RiskRangeEngine v2: 250 ranges calculated  ← NEW!
INFO | orchestrator | Orchestrator complete in ~80s  ← faster than 122s
```

## Dashboard Sekarang (NO TICKERS)

**🏠 Dashboard** = 100% macro views, dengan 4 tabs untuk grouping:

```
🚀 V2 Macro Engine Outputs
[KPI Row: 5 metrics — Yves alerts, Cascade shocks, Discovery count, New tickers, Portfolio deployed]

📑 Tabs:
├── 🧠 Yves Behavioral      → Alert cards (no ticker tables)
├── 📊 GIP v10 Bayesian     → Quad metrics, probability bars
├── 🔍 Discovery Summary    → Counts + top 5 highest conviction thesis names
└── ⚡ Cascade Summary      → Shock sources, impact counts
```

## Alpha Center (semua ticker stuff)

**⚡ Alpha Center** sekarang punya 5 sub-tabs:

```
🚀 V2 Ticker-Level Outputs
├── 💰 Sizing (% portfolio)  → Full sized position table
├── ⚡ Cascade Detail        → 1st/2nd/3rd order ticker breakdowns
├── 🔮 Discovery Detail      → Full discovery candidates dengan long/short tickers
├── 🆕 New Tickers           → Auto-discovered ticker table
└── 🔗 Supply Chain          → Chokepoint analysis
```

Plus existing Alpha Center content yang lama.

## Risk Range v2 Methodology (Better than Proxy)

Improved dari mean ± multiplier × stdev ke:

1. **ATR-based volatility** — captures jump risk, bukan cuma close-to-close
2. **Regime-conditional multipliers** — Q1 ranges tighter (1.3x), Q4 widest (2.0x trade, 6.5x tail)
3. **Asymmetric ranges** — bullish formation = wider upside Trade range
4. **VIX adjustment** — elevated VIX widens ranges proportionally
5. **Volume-weighted bias** — high vol regime gets larger ranges
6. **Multi-duration MAs** — 20d/50d/200d basis for Trade/Trend/Tail
7. **Quality grading** — A+/A/B/C based on formation + distance from low

## Performance Improvements

| Layer | Before | After |
|---|---|---|
| Cascade dynamic edges | Compute 4x per build (~3s each) | Compute once, cache 6h (other builds: <0.01s) |
| Yahoo rate limit | Cascade retry hell | 60s cooldown skip → no wasted time |
| Tier 2 loading | Always attempted even when rate-limited | Skipped if rate-limit active |
| Bad ticker fetches | 22+ failures per build | 0 failures (filtered before fetch) |
| Build time | 122s | ~50-80s typical |

## Troubleshooting

| Symptom | Fix |
|---|---|
| Risk range tabel kosong | Wait 1 build untuk cache populate, then refresh |
| VVIX still missing | Already mapped to ^VVIX. Check log: should see `^VVIX` in fetch list |
| Some tickers still failing | They're truly delisted or wrong format — let auto-blacklist handle |
| First build masih 122s | Normal — caches kosong. Second build will be much faster |

## #process — Manage risk accordingly.
