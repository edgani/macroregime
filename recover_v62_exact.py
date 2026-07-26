"""Recover the exact V62 frozen protocol and data contract from the original v5.1 package.

This tool does not reconstruct or rerun V62 from a summary. It verifies the exact package and
artifact hashes, extracts safely, inventories required sources, and fails closed while anything is
missing. Outcome analysis remains prohibited until acquisition is complete.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, tempfile, zipfile
from pathlib import Path

EXPECTED_PACKAGE_SHA256 = "4f97add774a50690baf88e642e807be68eac3399b66628a2be2d61d9b116df99"
EXPECTED_PROTOCOL_SHA256 = "34d6925eb5dec62cfa84fd9ea40a8bd9b7910904900fde368621bde3356174a3"
EXPECTED_ABORT_SHA256 = "78c1d9e2c64f9cfa372900ee4b49927c2efd4ed5b5c07bac8bc8851c58db0bbf"
PROTOCOL_REL = Path("studies/V62_ETF_VOL_CROSSMARKET/config/V62_FROZEN_PROTOCOL.json")
ABORT_REL = Path("studies/V62_ETF_VOL_CROSSMARKET/results/V62_ACQUISITION_ABORT.json")


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def safe_name(name: str) -> bool:
    p=Path(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and not name.startswith(('/', '\\\\'))

def find_one(root: Path, suffix: Path) -> Path | None:
    hits=[p for p in root.rglob(suffix.name) if p.as_posix().endswith(suffix.as_posix())]
    return hits[0] if len(hits)==1 else None

def required_sources(protocol: object) -> list[dict]:
    rows=[]
    def walk(x, path=''):
        if isinstance(x,dict):
            lower={str(k).lower():v for k,v in x.items()}
            if any(k in lower for k in ('source_url','source_file','dataset_id','series_id','ticker')):
                rows.append({'path':path or '$','contract':x})
            for k,v in x.items(): walk(v,f'{path}.{k}' if path else str(k))
        elif isinstance(x,list):
            for i,v in enumerate(x): walk(v,f'{path}[{i}]')
    walk(protocol)
    return rows

def recover(package: Path, out: Path) -> dict:
    report={'schema':'warroom.v62_recovery.v53','status':'FAIL','outcome_analysis_permitted':False,'errors':[]}
    if not package.is_file():
        report['errors'].append('exact v5.1 global package is missing'); return report
    got=sha256(package); report['package_sha256']=got
    if got!=EXPECTED_PACKAGE_SHA256:
        report['errors'].append('global package SHA-256 mismatch'); return report
    with tempfile.TemporaryDirectory(prefix='v62_recover_') as td:
        root=Path(td)
        with zipfile.ZipFile(package) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or any(not safe_name(n) for n in names):
                report['errors'].append('unsafe or duplicate ZIP member'); return report
            z.extractall(root)
        protocol=find_one(root,PROTOCOL_REL); abort=find_one(root,ABORT_REL)
        if protocol is None or abort is None:
            report['errors'].append('exact V62 protocol or acquisition-abort artifact not found'); return report
        if sha256(protocol)!=EXPECTED_PROTOCOL_SHA256:
            report['errors'].append('V62 protocol hash mismatch')
        if sha256(abort)!=EXPECTED_ABORT_SHA256:
            report['errors'].append('V62 acquisition-abort hash mismatch')
        if report['errors']: return report
        payload=json.loads(protocol.read_text(encoding='utf-8'))
        out.mkdir(parents=True,exist_ok=True)
        shutil.copy2(protocol,out/protocol.name); shutil.copy2(abort,out/abort.name)
        report.update({'status':'PROTOCOL_RECOVERED_ACQUISITION_STILL_REQUIRED','protocol_sha256':EXPECTED_PROTOCOL_SHA256,
                       'abort_sha256':EXPECTED_ABORT_SHA256,'required_source_contracts':required_sources(payload),
                       'next_action':'Archive every exact source named by the recovered protocol, record hashes and availability timestamps, then use only the original frozen runner.',
                       'outcome_analysis_permitted':False})
    return report

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--package',type=Path,required=True); ap.add_argument('--out',type=Path,default=Path('research_v53/v62_recovered'))
    a=ap.parse_args(); r=recover(a.package,a.out); print(json.dumps(r,indent=2,sort_keys=True)); return 0 if r['status'].startswith('PROTOCOL_RECOVERED') else 2
if __name__=='__main__': raise SystemExit(main())
