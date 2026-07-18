from pathlib import Path
import re, json, sys
root=Path(__file__).resolve().parent
html=(root/'dashboard.html').read_text(encoding='utf-8')
checks={
 'alpha_array_empty': 'const ALPHA=[];' in html,
 'no_hardcoded_setup_objects': not bool(re.search(r"\{tk:['\"](?:NVDA|MU|GEV|BBCA|BREN|BTC|SOL|CL=F|USD/JPY)", html)),
 'no_mock_regional_values': 'Late Expansion' not in html,
 'mission_cross_confirmed_label': 'Cross-confirmed RS improving' in html,
 'generic_tabs_registry_driven': 'Registered Components & Current Proof State' in html,
 'ccxi_not_auto_universe': 'WARROOM_INCLUDE_CURATED_DISCOVERY' in (root/'warroom/data.py').read_text(),
 'consistency_guard_present': (root/'consistency_guard.py').exists(),
 'canonical_market_keys': '"idx" in markets or "commodity" in markets' in (root/'consistency_guard.py').read_text(),
}
report={'pass':all(checks.values()),'checks':checks}
(root/'HARD_CODE_AND_CROSS_TAB_AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2)); sys.exit(0 if report['pass'] else 1)
