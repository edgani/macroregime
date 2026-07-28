from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/War_Room_OS_v66_Scoped_Usable_Risk_Control.zip')
SHA_OUT=Path('/mnt/data/War_Room_OS_v66_Scoped_Usable_Risk_Control.sha256.txt')
EXCLUDE={'PACKAGE_MANIFEST_V66.json'}
PARENT_SHA='7327a908a3fdad7a421e8d985ffc7693ec08039b7ed1a4650566c0563015ea0b'

def included_files(root=ROOT):
    rows=[]
    for p in root.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix()
        if rel in EXCLUDE or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc') or rel.startswith('.cache/'):
            continue
        rows.append((rel,p))
    return sorted(rows)

def write_manifest():
    files=[{'path':r,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for r,p in included_files()]
    manifest={
      'schema':'warroom.package_manifest.v66','release':'War_Room_OS_v66_Scoped_Usable_Risk_Control','parent_v65_sha256':PARENT_SHA,
      'files_digest_sha256':hashlib.sha256(json.dumps(files,separators=(',',':'),sort_keys=True).encode()).hexdigest(),'files':files,
      'active_operational_components':6,'evidence_active_research_components':3,'decision_active_scoped_risk_controls':1,
      'decision_active_ticker_or_directional_components':0,'point_in_time_ticker_selectors_proven':0,
      'capital_permission':'CONDITIONAL_RISK_CAP_ONLY_FOR_US_BROAD_EQUITY_REDUCTION',
      'current_scoped_control_state':'BASELINE_CAP_ALLOWED_AS_OF_2026_06_COMPLETED_MONTH',
      'policy':'The confirmed SMA10 component can only cap broad US equity exposure at completed monthly rebalances. It cannot create exposure or authorize a ticker, direction, target, short, leverage, crash forecast, or cross-market action.'
    }
    (ROOT/'PACKAGE_MANIFEST_V66.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def build(out=OUT):
    write_manifest(); files=included_files()+[('PACKAGE_MANIFEST_V66.json',ROOT/'PACKAGE_MANIFEST_V66.json')]
    epoch=(2026,7,26,0,0,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p in sorted(files):
            info=zipfile.ZipInfo(rel,date_time=epoch);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(out.read_bytes()).hexdigest();SHA_OUT.write_text(f'{h}  {out.name}\n')
    return {'sha256':h,'files':len(files),'out':str(out)}
if __name__=='__main__':print(json.dumps(build(),indent=2))
