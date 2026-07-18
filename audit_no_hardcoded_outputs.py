from pathlib import Path
import re, json, sys
root=Path(__file__).resolve().parent
html=(root/'dashboard.html').read_text(encoding='utf-8')
checks={
 'alpha_array_empty': 'const ALPHA=[];' in html,
 'no_hardcoded_setup_objects': not bool(re.search(r"\{tk:['\"](?:NVDA|MU|GEV|BBCA|BREN|BTC|SOL|CL=F|USD/JPY)", html)),
 'no_mock_regional_values': 'Late Expansion' not in html,
 'mission_independent_confirmation_label': 'Independently confirmed RS improving' in html,
 'generic_tabs_registry_driven': 'Registered Components & Current Proof State' in html,
 'no_legacy_static_panels': 'Q3 · Growth↓ Inflation↑' not in html and 'panic-bottom PROD' not in html,
 'daily_snapshot_not_live_label': 'RESEARCH ONLY · PAPER/LIVE BLOCKED' in html,
 'early_warning_key_fixed': "ew:'EARLY WARNING'" in html,
 'ccxi_not_auto_universe': 'WARROOM_INCLUDE_CURATED_DISCOVERY' in (root/'warroom/data.py').read_text(),
 'consistency_guard_present': (root/'consistency_guard.py').exists(),
 'canonical_market_keys': 'CANONICAL_MARKETS' in (root/'consistency_guard.py').read_text() and '"idx": "ihsg"' in (root/'consistency_guard.py').read_text() and '"commodity": "commod"' in (root/'consistency_guard.py').read_text(),
}
report={'pass':all(checks.values()),'checks':checks}
(root/'HARD_CODE_AND_CROSS_TAB_AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2)); sys.exit(0 if report['pass'] else 1)
