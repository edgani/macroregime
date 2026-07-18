"""Deployment-side connection verifier for War Room OS.

No credentials are printed. Use --strict after configuring the desired providers.
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name('.env'), override=False)
except Exception:
    pass

from institutional_data import collect_institutional_data
from live_market_intelligence import collect_live_market_intelligence
from full_live_data_hub import collect_full_live_data


def minimal_desk():
    return {
        'meta': {'source':'connection_test','generated':None},
        'markets': {'us': {'setups': []}}, 'alpha': [],
        'macro_observations': {}, 'market_breadth': {}, 'rotation_snapshot': {},
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--strict',action='store_true',help='Fail if any configured/public provider is ERROR/OFFLINE.')
    ap.add_argument('--offline',action='store_true',help='Disable network and validate cache/fail-closed behavior.')
    ap.add_argument('--write-report',action='store_true')
    args=ap.parse_args()
    if args.offline: os.environ['WARROOM_NETWORK_MODE']='offline'
    desk=minimal_desk()
    institutional=collect_institutional_data(desk)
    derivatives=collect_live_market_intelligence(desk,institutional)
    full=collect_full_live_data(desk)
    statuses=[]
    for plane,obj in [('institutional',institutional),('derivatives',derivatives),('full_hub',full)]:
        for x in obj.get('statuses') or []:
            statuses.append({'plane':plane,**x})
    bad=[x for x in statuses if x.get('state') in {'ERROR','OFFLINE'}]
    configured_bad=[x for x in bad if x.get('state')!='NOT_CONFIGURED']
    report={
        'network_mode':os.getenv('WARROOM_NETWORK_MODE','live'),
        'planes':{
            'institutional':institutional.get('overall_state'),
            'derivatives':derivatives.get('overall_state'),
            'full_hub':full.get('overall_state'),
        },
        'status_counts':{state:sum(1 for x in statuses if x.get('state')==state) for state in sorted({str(x.get('state')) for x in statuses})},
        'statuses':statuses,
        'strict_pass':not configured_bad,
        'limitations':['Authentication, entitlements and current provider schemas can only be verified on this deployment machine.','A provider can become unavailable after this check.'],
    }
    text=json.dumps(report,indent=2,default=str)
    print(text)
    if args.write_report:
        Path(__file__).with_name('LIVE_CONNECTION_REPORT.json').write_text(text+'\n',encoding='utf-8')
    if args.strict and configured_bad:
        raise SystemExit(2)


if __name__=='__main__': main()
