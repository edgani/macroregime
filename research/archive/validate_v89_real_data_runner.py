from __future__ import annotations
from pathlib import Path
import hashlib
import json
import tempfile

import pandas as pd

from market_data_admission import admit_manifest
from proof_readiness_audit import audit
from promotion_gate_v89 import evaluate as promote
from normalize_external_table import normalize

HERE = Path(__file__).resolve().parent
results = []

def check(name, condition, detail=""):
    results.append({"name": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")

current = audit(HERE / "runtime" / "market_evidence")
check("shipped package has zero admitted markets", current["admitted_count"] == 0, str(current["markets_admitted"]))
check("shipped package capital blocked", current["capital_permission"] == "BLOCKED")
check("all-market admission false", current["all_markets_admitted"] is False)

US_ROLES = [
    "security_master", "corporate_actions", "filing_fundamentals", "expectations",
    "bottleneck_transmission", "positioning_amplification", "valuation_snapshot",
    "execution_costs_capacity", "outcome_prices",
]

def make_manifest(root: Path, *, test_fixture=False, synthetic=False, future=False, technical=False, bad_hash=False):
    row = {
        "record_id": "r1", "instrument_id": "PERM1", "observation_at": "2020-01-01T00:00:00Z",
        "available_at": "2025-01-02T00:00:00Z" if future else "2020-01-02T00:00:00Z",
        "source_id": "OFFICIAL_OR_LICENSED", "source_record_id": "s1", "field_id": "revenue",
        "value": 1.0, "unit": "USD", "revision_id": "v1",
        "feature_domain": "price_momentum" if technical else "fundamentals",
        "synthetic": synthetic, "test_fixture": test_fixture,
    }
    table = root / "role.csv"; pd.DataFrame([row]).to_csv(table, index=False)
    digest = hashlib.sha256(table.read_bytes()).hexdigest()
    if bad_hash: digest = "0"*64
    roles = {role: {"path": "role.csv", "sha256": digest, "minimum_rows": 1} for role in US_ROLES}
    return {
        "market": "us", "evidence_mode": "REAL_POINT_IN_TIME_BLIND", "synthetic_data": False,
        "test_fixture": False, "decision_time": "2024-01-01T00:00:00Z", "history_start": "2010-01-01T00:00:00Z",
        "history_end": "2023-12-31T00:00:00Z", "universe_snapshot_hash": "a"*64,
        "security_master_hash": "b"*64, "global_trial_ledger_hash": "c"*64, "data_dictionary_hash": "d"*64,
        "data_custodian_receipt_hash": "e"*64, "source_license_receipt_hash": "f"*64, "roles": roles,
    }

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    manifest = make_manifest(root)
    mpath = root / "dataset_manifest.json"; mpath.write_text(json.dumps(manifest), encoding="utf-8")
    admitted = admit_manifest(mpath)
    check("structurally real PIT evidence can pass admission", admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root = Path(td); manifest = make_manifest(root, test_fixture=True)
    mpath=root/'dataset_manifest.json'; mpath.write_text(json.dumps(manifest),encoding='utf-8')
    admitted=admit_manifest(mpath)
    check("test fixture evidence rejected", not admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root = Path(td); manifest = make_manifest(root, synthetic=True)
    mpath=root/'dataset_manifest.json'; mpath.write_text(json.dumps(manifest),encoding='utf-8')
    admitted=admit_manifest(mpath)
    check("synthetic row rejected", not admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root = Path(td); manifest = make_manifest(root, future=True)
    mpath=root/'dataset_manifest.json'; mpath.write_text(json.dumps(manifest),encoding='utf-8')
    admitted=admit_manifest(mpath)
    check("future information rejected", not admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root = Path(td); manifest = make_manifest(root, technical=True)
    mpath=root/'dataset_manifest.json'; mpath.write_text(json.dumps(manifest),encoding='utf-8')
    admitted=admit_manifest(mpath)
    check("technical feature domain rejected", not admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root = Path(td); manifest = make_manifest(root, bad_hash=True)
    mpath=root/'dataset_manifest.json'; mpath.write_text(json.dumps(manifest),encoding='utf-8')
    admitted=admit_manifest(mpath)
    check("file hash mismatch rejected", not admitted["valid"], str(admitted["errors"]))

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    raw=root/'vendor.csv'
    pd.DataFrame([{"perm":"P1","obs":"2020-01-01T00:00:00Z","avail":"2020-01-02T00:00:00Z","rid":"R1","field":"backlog","val":5.0}]).to_csv(raw,index=False)
    mapping=root/'mapping.json'
    mapping.write_text(json.dumps({"columns":{"instrument_id":"perm","observation_at":"obs","available_at":"avail","source_record_id":"rid","field_id":"field","value":"val"},"constants":{"source_id":"LICENSED","unit":"USD","revision_id":"v1","feature_domain":"orders_backlog"}}),encoding='utf-8')
    output=root/'normalized.csv'; receipt=root/'receipt.json'
    result=normalize(raw,mapping,output)
    check("licensed export normalizer creates PIT table", output.exists() and result["rows"]==1)
    normalized=pd.read_csv(output)
    check("normalizer never marks synthetic or fixture", not normalized.synthetic.astype(bool).any() and not normalized.test_fixture.astype(bool).any())

rejected = promote({})
check("empty promotion receipt rejected", not rejected["eligible"])
check("permission remains blocked", rejected["permission"] == "BLOCKED")
forged = promote({"evidence_mode":"REAL_POINT_IN_TIME_BLIND","synthetic_data":False,"test_fixture":True,"holdout_visible_to_model":False,"data_admission_pass":True,"data_admission_hash":"a"*64,"dataset_manifest_hash":"b"*64,"blind_custodian_receipt_hash":"c"*64})
check("promotion rejects test fixture flag", not forged["eligible"] and any("test_fixture" in x for x in forged["reasons"]))

payload = {
    "schema": "warroom.v89.validation.v1",
    "passed": sum(x["pass"] for x in results),
    "total": len(results),
    "all_pass": all(x["pass"] for x in results),
    "checks": results,
}
(HERE / "V89_FINAL_VALIDATION.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))
