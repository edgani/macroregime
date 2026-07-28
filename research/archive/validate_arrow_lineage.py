from pathlib import Path
import re

html = Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
checks = {
    'no modulo candidate routing': 'j%l2.length' not in html and 'i%l2.length' not in html,
    'no generic cartesian graph calls outside curated supply chain': len(re.findall(r'connectAll\(', html)) <= 2,
    'mission candidate uses market parent': "l2.find(m=>m.market===c.market)" in html,
    'market/setup direction gate present': 'isSetupAligned' in html,
    'provider/ticker event lineage present': 'providerMatches' in html,
    'state-colored arrowheads present': 'arrow-constructive' in html and 'arrow-destructive' in html,
    'edge relation tooltip present': 'relation||e.evidence' in html,
    'NO_DATA edge blocking present': 'edgeAllowed' in html,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL'), name)
if failed:
    raise SystemExit('Arrow-lineage validation failed: ' + ', '.join(failed))
