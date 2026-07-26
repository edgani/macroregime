from __future__ import annotations
import hashlib, json, tempfile, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import v72_release_runners as rr

PASS=0
FAIL=[]
def check(name, cond):
    global PASS
    if cond:
        PASS+=1
    else:
        FAIL.append(name)

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p: Path, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n",encoding="utf-8")

with tempfile.TemporaryDirectory(prefix="v72_manifest_generators_") as tmp:
    td=Path(tmp)
    old_cal,old_proto=rr.FROZEN_CALENDAR_PATH,rr.PROTOCOL_PATH
    cal=td/"calendar.csv"; cal.write_text("trading_dt\n2019-10-07\n2019-10-08\n",encoding="utf-8")
    proto=td/"protocol.json"; dump(proto,{"data_integrity":{"frozen_expected_calendar":{"sha256":sha(cal)}}})
    rr.FROZEN_CALENDAR_PATH=cal; rr.PROTOCOL_PATH=proto
    try:
        root=td/"licensed"
        dates=["2019-10-07","2019-10-08"]
        for d in dates:
            paths=[
                root/"tbt"/f"C1_TBT_{d}.zip",
                root/"quotes"/f"OPTION_QUOTES_SPX_1MIN_{d}.zip",
                root/"underlier"/f"SPX_ES_1MIN_{d}.csv",
            ]
            for p in paths:
                p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(f"{p.name}\n".encode())
        a=rr.generate_source_manifest(root)
        b=rr.generate_source_manifest(root)
        check("source manifest deterministic", a==b)
        check("source exact row count", len(a["files"])==6)
        check("source frozen calendar exact", a["expected_trading_dates"]==dates)
        check("source remains blocked", a["capital_permission"]=="BLOCKED" and a["live_decision_weight"]==0.0)
        check("source digest stable", a["manifest_digest_sha256"]==b["manifest_digest_sha256"])

        missing=root/"quotes"/"OPTION_QUOTES_SPX_1MIN_2019-10-08.zip"
        missing.unlink()
        try: rr.generate_source_manifest(root); ok=False
        except rr.V72RunnerError: ok=True
        check("missing exact quote day rejected",ok)
        missing.write_bytes(b"restored")

        grk=(root/"grk"/"C1_GRK_2019-10-07.zip");grk.parent.mkdir();grk.write_bytes(b"one day")
        try: rr.generate_source_manifest(root);ok=False
        except rr.V72RunnerError:ok=True
        check("partial GRK rejected",ok)
        (root/"grk"/"C1_GRK_2019-10-08.zip").write_bytes(b"two day")
        with_grk=rr.generate_source_manifest(root)
        check("complete GRK included",len(with_grk["files"])==8)
        try: rr.generate_source_manifest(root,include_grk=False);ok=False
        except rr.V72RunnerError:ok=True
        check("present GRK cannot be silently excluded",ok)

        a_valid=rr.generate_source_manifest(root, include_grk=True)
        source_manifest=td/"source_manifest.json";dump(source_manifest,a_valid)
        # Generate a validation receipt using the same tiny fixture contract.
        receipt=rr.validate_licensed_source_package(source_manifest,root)
        source_receipt=td/"source_receipt.json";dump(source_receipt,receipt)
        derived=td/"derived";derived.mkdir()
        for name in ("c1.csv","c2.csv","c3.csv"):
            (derived/name).write_text("trading_dt,x\n2022-07-01,1\n",encoding="utf-8")
        dm1=rr.generate_derived_manifest(derived,source_receipt)
        dm2=rr.generate_derived_manifest(derived,source_receipt)
        check("derived manifest deterministic",dm1==dm2)
        check("derived exact claim set",{r["claim_id"] for r in dm1["files"]}==set(rr.CLAIM_FILES))
        check("derived sealed unopened",dm1["lockbox_state"]=="SEALED_UNOPENED" and dm1["historical_outcomes_opened"] is False)
        check("derived remains blocked",dm1["capital_permission"]=="BLOCKED")
        try:
            rr.generate_derived_manifest(derived,source_receipt,filenames={
                "V72_C1_VERIFIED_GAMMA_RESPONSE":"../c1.csv",
                "V72_C2_INCREMENTAL_PIN_BREAK":"c2.csv",
                "V72_C3_NET_GAMMA_SCALP":"c3.csv",
            });ok=False
        except rr.V72RunnerError:ok=True
        check("derived traversal rejected",ok)
    finally:
        rr.FROZEN_CALENDAR_PATH=old_cal;rr.PROTOCOL_PATH=old_proto

report={"schema":"warroom.v72_manifest_generator_validation","status":"PASS" if not FAIL else "FAIL","checks_passed":PASS,"checks_total":PASS+len(FAIL),"failures":FAIL,"historical_outcomes_opened":False,"predictive_components_promoted":0,"live_decision_weight":0.0,"capital_permission":"BLOCKED"}
out=Path(__file__).resolve().parents[1]/"V72_MANIFEST_GENERATOR_VALIDATION.json"
out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if not FAIL else 1)
