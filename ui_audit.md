# TAB AUDIT — Overlap & Consolidation Plan

## Current 8 tabs:
1. ⚡ Command Center
2. 🧭 Radar  
3. 📡 Health
4. 🎯 Playbook
5. 🌐 Markets
6. 📖 Narrative Lab
7. ⚠️ Risk
8. 🔬 Diagnostics

## DUPLICATES / OVERLAPS found:

### Command Center vs Radar:
- CC: regime probs, growth/inflation arrows
- Radar: SAME regime probs, SAME growth/inflation, SAME yield curve, SAME analog
- Radar: "Trade terbaik sekarang" = same as CC ticker board
→ MERGE: Radar becomes detailed deep-dive. CC stays as cockpit. Remove duplicate sections from Radar.

### Radar vs Playbook:
- Radar: has analog, next macro events, KEY indicators table
- Playbook: has same asset translation, same US spillover chain, same EM rotation
- Radar: "Trade terbaik sekarang" is basically mini-Playbook
→ MERGE: Keep Playbook as the strategy detail. Radar keeps the regime "WHY" view.

### Health vs Risk:
- Health: breadth, credit, VIX, yield curve, sector leadership, checklists
- Risk: SAME credit, SAME VIX, SAME yield curve, position sizing
→ MERGE into single "Health + Risk" tab. Remove duplicate VIX/credit sections.

### Markets (IHSG tab) vs Radar:
- Markets IHSG: has spillover chain, macro impact board, signal lifecycle
- Radar: has same spillover chain (US), same signal flow
→ Keep separate but remove duplicates.

### Playbook vs Narrative Lab:
- Playbook: has scenarios, policy playbooks
- Narrative Lab: has narrative scenarios, Claude analysis
- These are COMPLEMENTARY, not duplicate
→ MERGE into single "Strategy" tab with sub-tabs

### Markets lacks NOW vs FRONT-RUN ticker split:
- Currently shows sector performance and stock rankings (backward-looking)
- Should show: NOW plays (current regime) vs FRONT-RUN plays (transition)
- Must add regime_tickers integration to each market sub-tab

## NEW ARCHITECTURE (5 tabs, not 8):

1. ⚡ Command Center  — cockpit, all action in one screen
2. 📊 Regime Intel   — WHY: macro internals, analog, indicators, health (merged Radar+Health)  
3. 🎯 Strategy       — WHAT: playbook + scenarios + narrative (merged Playbook+NarrativeLab)
4. 🌐 Markets        — WHERE: each market with NOW + FRONT-RUN plays (upgraded Markets)
5. ⚠️ Risk & Diag    — SAFETY: crash, sizing, data quality (merged Risk+Diag)
