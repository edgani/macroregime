from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash,file_hash


def build():
    fixture=ROOT/'data/fixtures/aal_1d_engineering.csv'
    source_manifest=json.loads((ROOT/'legacy/source_manifest.json').read_text())
    quality=json.loads((ROOT/'artifacts/bundled_panel_invalid_ohlc_rows.json').read_text())
    rows=[
      {
        "dataset_id":"NEWZIP-AAL-1D-ENGINEERING-001","asset":"AAL","timeframe":"1d",
        "evidence_tier":"UNIT_FIXTURE","claim_ceiling":"ENGINEERING_ONLY",
        "point_in_time_complete":False,"revision_policy":"LATEST_ONLY","quality_status":"ACCEPTED_ENGINEERING_FIXTURE",
        "source_zip_sha256":source_manifest['source_zip_sha256'],
        "source_path":"warroom_os/research/sp500_panel.parquet",
        "normalized_path":"data/fixtures/aal_1d_engineering.csv","normalized_sha256":file_hash(fixture),
        "burned_windows":[["2013-02-08","2013-10-25"]],
        "allowed_uses":["contract_tests","causality_tests","pipeline_smoke_tests"],
        "forbidden_uses":["edge_claim","paper","live","hidden_oos"]
      },
      {
        "dataset_id":"NEWZIP-SP500-PANEL-LEGACY-001","asset":"SP500_FIXED_CONSTITUENTS","timeframe":"1d",
        "evidence_tier":"DEVELOPMENT","claim_ceiling":"DEVELOPMENT_ONLY",
        "point_in_time_complete":False,"revision_policy":"LATEST_ONLY","quality_status":"QUARANTINED",
        "source_zip_sha256":source_manifest['source_zip_sha256'],
        "source_path":"warroom_os/research/sp500_panel.parquet",
        "source_file_sha256":"db2a61d7f66d219354cfaad9dff01a5c9d5b01145ae11549cd11555588729420",
        "quality_artifact_path":"artifacts/bundled_panel_invalid_ohlc_rows.json",
        "quality_artifact_sha256":file_hash(ROOT/'artifacts/bundled_panel_invalid_ohlc_rows.json'),
        "invalid_ohlc_rows":quality['issue_count'],"affected_tickers":quality['tickers'],
        "burned_windows":[["2013-02-08","2018-02-07"]],
        "allowed_uses":["failure_analysis","development_diagnostics_after_explicit_quarantine"],
        "forbidden_uses":["silent_row_drop","hidden_oos","paper","live","production_calibration"]
      }
    ]
    return {"datasets":rows,"catalog_hash":canonical_hash(rows)}

if __name__=='__main__':
    out=ROOT/'validation/data_catalog.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+"\n"
    if '--check' in sys.argv:
        if not out.exists() or out.read_text()!=expected: raise SystemExit('data catalog stale')
        print('PASS: data catalog')
    else: out.write_text(expected); print(out)
