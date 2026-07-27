"""Validate browser-exported IDX JSON without altering source records or timestamps."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('--output', default='runtime/v94_idx_browser_import'); a=p.parse_args()
    src=Path(a.input)
    raw=src.read_text(encoding='utf-8')
    data=json.loads(raw)
    if not isinstance(data,(dict,list)): raise SystemExit('IDX export must be JSON object or array')
    out=Path(a.output); out.mkdir(parents=True, exist_ok=True)
    dest=out/src.name; dest.write_text(raw, encoding='utf-8')
    receipt={
      'schema':'warroom.v94.idx_browser_import.v1',
      'source':'IDX_OFFICIAL_BROWSER_EXPORT',
      'imported_at':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
      'path':str(dest.resolve()), 'sha256':sha256_file(dest),
      'capital_permission':'BLOCKED',
      'claim_limit':'Current/public IDX export only; not survivor-free historical proof.'
    }
    (out/(src.stem+'_receipt.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
