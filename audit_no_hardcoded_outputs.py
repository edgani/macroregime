from pathlib import Path
import json, re, sys

root = Path(__file__).resolve().parent
html = (root / 'dashboard.html').read_text(encoding='utf-8')
run = (root / 'run.py').read_text(encoding='utf-8')
app = (root / 'app.py').read_text(encoding='utf-8')
runtime = (root / 'desk_runtime.py').read_text(encoding='utf-8')
checks = {
    '14_tabs_preserved': len(re.findall(r'<div class="tab(?: on| core)?" data-v=', html)) == 14,
    'no_static_alpha_array': 'const ALPHA' not in html,
    'no_static_tab_payload': 'const TABS' not in html,
    'no_static_market_payload': 'const MARKET=' not in html,
    'no_legacy_current_tickers': not bool(re.search(r'\b(?:NVDA|MU|GEV|BBCA|BREN|CCXI)\b', html)),
    'no_legacy_current_values': all(term not in html for term in ('Q3 · Growth↓ Inflation↑', 'Crash 24mo', 'US Equity</span><span class="v">35%')),
    'alpha_is_runtime_watch': 'Current Cross-Market Tactical Discovery Watch' in html and '_build_alpha_watch' in run,
    'foundry_is_separate': 'Frozen US Alpha Foundry' in html,
    'mission_is_rich_dynamic': all(term in html for term in ('Data Feed Health & Freshness','Multi-Timeframe Regime','Cross-Market Opportunity Monitor','Early-Warning Snapshot','Alpha Proof Factory')),
    'all_major_tabs_have_runtime_panels': all(term in html for term in ('Growth / Inflation Nowcast','Current Early-Warning State','Causal Chain Reference Library','Current US Company Watch','Current Surfaced Nodes','Runtime Integrity & Research Ledger')),
    'no_curated_discovery_in_run': 'run_discovery' not in run,
    'desk_schema_guard': 'V7_NONBLOCKING_REFRESH_2026_07_18' in runtime and 'desk_schema_version' in run,
    'research_permission_header': 'RESEARCH ONLY · PAPER/LIVE BLOCKED' in html,
    'risk_range_deoverclaimed': 'MQA_RISK_RANGE_PROXY' in run,
    'no_mock_current_fallback': all(term not in html for term in ('const mock=', 'Late Expansion', 'Recovery 31%', 'MOCK v0.2', 'v0.3 · MOCK')),
    'initial_header_is_research_only': 'v0.7 · LOADING' in html and 'RESEARCH ONLY · PAPER/LIVE BLOCKED' in html,
}
report = {'pass': all(checks.values()), 'checks': checks}
(root / 'HARD_CODE_AND_CROSS_TAB_AUDIT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
sys.exit(0 if report['pass'] else 1)
