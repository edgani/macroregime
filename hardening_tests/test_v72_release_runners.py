"""Adversarial tests for V72 licensed preflight and one-time lockbox runner."""
from __future__ import annotations
from pathlib import Path
import sys
import hashlib
import json
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import v72_release_runners as rr

PASS = 0
FAILURES: list[str] = []


def check(name: str, cond: bool) -> None:
    global PASS
    if cond:
        PASS += 1
    else:
        FAILURES.append(name)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p: Path, x) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_source(td: Path):
    dates = ["2019-10-07", "2025-06-30"]
    cal = td / "calendar.csv"
    cal.write_text("trading_dt\n" + "\n".join(dates) + "\n")
    proto = td / "protocol.json"
    dump(proto, {"data_integrity":{"frozen_expected_calendar":{"sha256":sha(cal)}}})
    files=[]
    root=td/"licensed";root.mkdir()
    for product,folder in (("TBT","tbt"),("QUOTES","quotes"),("UNDERLIER","underlier")):
        for d in dates:
            p=root/folder/f"{product}_{d}.csv";p.parent.mkdir(exist_ok=True)
            p.write_text(f"product,date\n{product},{d}\n")
            files.append({"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p),"product":product,"trading_dt":d,"license_classification":"PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION"})
    manifest=td/"source_manifest.json"
    dump(manifest,{"schema":rr.SOURCE_SCHEMA,"protocol_sha256":sha(proto),"license_classification":"PROPRIETARY_INTERNAL_USE_NO_RAW_REDISTRIBUTION","expected_trading_dates":dates,"files":files})
    return root,manifest,cal,proto


def make_derived(td: Path, source_receipt_path: Path, source_receipt: dict):
    root=td/"derived";root.mkdir()
    rows=[]
    for claim,key in rr.CLAIM_FILES.items():
        p=root/f"{key}.csv";p.write_text("trading_dt,x\n2022-07-01,1\n")
        rows.append({"claim_id":claim,"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p),"format":"CSV"})
    mp=td/"derived_manifest.json"
    dump(mp,{"schema":rr.DERIVED_SCHEMA,"source_receipt_sha256":sha(source_receipt_path),"source_manifest_sha256":source_receipt["source_manifest_sha256"],"protocol_sha256":sha(rr.PROTOCOL_PATH),"evaluator_spec_sha256":sha(rr.SPEC_PATH),"license_classification":"DERIVED_INTERNAL_RESEARCH_NO_RAW_REDISTRIBUTION","lockbox_state":"SEALED_UNOPENED","files":rows})
    return root,mp


with tempfile.TemporaryDirectory(prefix="v72_runner_test_") as tmp:
    td=Path(tmp)
    old_cal,old_proto=rr.FROZEN_CALENDAR_PATH,rr.PROTOCOL_PATH
    root,manifest,cal,proto=make_source(td)
    rr.FROZEN_CALENDAR_PATH=cal;rr.PROTOCOL_PATH=proto
    try:
        receipt=rr.validate_licensed_source_package(manifest,root)
        check("valid source passes",receipt["status"]=="PASS_READY_TO_DERIVE_FROZEN_TABLES")
        check("all source files checked",receipt["files_checked"]==6)
        check("calendar bound",receipt["frozen_calendar_sha256"]==sha(cal))
        check("capital blocked",receipt["capital_permission"]=="BLOCKED" and receipt["live_decision_weight"]==0.0)

        bad=json.loads(manifest.read_text());bad["expected_trading_dates"]=["2019-10-07"]
        bp=td/"bad_calendar.json";dump(bp,bad)
        try: rr.validate_licensed_source_package(bp,root); ok=False
        except rr.V72RunnerError: ok=True
        check("manifest cannot choose shorter calendar",ok)

        bad=json.loads(manifest.read_text());bad["files"][0]["sha256"]="0"*64
        bp=td/"bad_hash.json";dump(bp,bad)
        try: rr.validate_licensed_source_package(bp,root);ok=False
        except rr.V72RunnerError:ok=True
        check("raw tamper rejected",ok)

        bad=json.loads(manifest.read_text());bad["files"][0]["license_classification"]="PUBLIC"
        bp=td/"bad_license.json";dump(bp,bad)
        try: rr.validate_licensed_source_package(bp,root);ok=False
        except rr.V72RunnerError:ok=True
        check("raw license mismatch rejected",ok)

        bad=json.loads(manifest.read_text());bad["files"]=[x for x in bad["files"] if x["product"]!="QUOTES"]
        bp=td/"missing_quotes.json";dump(bp,bad)
        try: rr.validate_licensed_source_package(bp,root);ok=False
        except rr.V72RunnerError:ok=True
        check("missing complete quote surface rejected",ok)

        source_receipt_path=td/"source_receipt.json";dump(source_receipt_path,receipt)
        droot,dmanifest=make_derived(td,source_receipt_path,receipt)
        dreceipt,paths=rr.validate_derived_package(dmanifest,droot,source_receipt_path)
        check("valid derived package passes",dreceipt["status"]=="PASS_READY_FOR_ONE_TIME_FROZEN_EVALUATION")
        check("three exact claims bound",set(paths)=={"c1","c2","c3"})
        check("derived remains blocked",dreceipt["capital_permission"]=="BLOCKED")

        bad=json.loads(dmanifest.read_text());bad["source_receipt_sha256"]="f"*64
        bp=td/"bad_source_receipt.json";dump(bp,bad)
        try: rr.validate_derived_package(bp,droot,source_receipt_path);ok=False
        except rr.V72RunnerError:ok=True
        check("source receipt tamper rejected",ok)

        bad=json.loads(dmanifest.read_text());bad["files"][0]["path"]="../escape.csv"
        bp=td/"unsafe_derived.json";dump(bp,bad)
        try: rr.validate_derived_package(bp,droot,source_receipt_path);ok=False
        except rr.V72RunnerError:ok=True
        check("derived path traversal rejected",ok)

        bad=json.loads(dmanifest.read_text());bad["files"][1]["claim_id"]=bad["files"][0]["claim_id"]
        bp=td/"duplicate_claim.json";dump(bp,bad)
        try: rr.validate_derived_package(bp,droot,source_receipt_path);ok=False
        except rr.V72RunnerError:ok=True
        check("duplicate claim rejected",ok)

        bad=json.loads(dmanifest.read_text());bad["lockbox_state"]="OPENED"
        bp=td/"opened_manifest.json";dump(bp,bad)
        try: rr.validate_derived_package(bp,droot,source_receipt_path);ok=False
        except rr.V72RunnerError:ok=True
        check("already-open manifest rejected",ok)

        # The opening receipt must be durably written before outcome parsing/evaluation.
        old_eval=rr.evaluate_all
        def fail_eval(*_a,**_k): raise RuntimeError("planted evaluator interruption")
        rr.evaluate_all=fail_eval
        derived_receipt=td/"derived_receipt.json";open_receipt=td/"open_receipt.json";result=td/"result.json"
        try:
            rr.open_and_evaluate_lockbox(derived_manifest_path=dmanifest,derived_root=droot,source_receipt_path=source_receipt_path,derived_receipt_path=derived_receipt,open_receipt_path=open_receipt,result_path=result)
            interrupted=False
        except RuntimeError:
            interrupted=True
        check("planted evaluator interruption observed",interrupted)
        check("opening receipt precedes outcomes",open_receipt.is_file() and not result.exists())
        try:
            rr.open_and_evaluate_lockbox(derived_manifest_path=dmanifest,derived_root=droot,source_receipt_path=source_receipt_path,derived_receipt_path=derived_receipt,open_receipt_path=open_receipt,result_path=result)
            ok=False
        except rr.V72RunnerError:
            ok=True
        check("lockbox cannot be reopened after interruption",ok)
        rr.evaluate_all=old_eval

        duplicate=td/"dup.json";duplicate.write_text('{"a":1,"a":2}')
        try: rr.load_json(duplicate);ok=False
        except rr.V72RunnerError:ok=True
        check("duplicate JSON keys rejected",ok)
    finally:
        rr.FROZEN_CALENDAR_PATH=old_cal;rr.PROTOCOL_PATH=old_proto

report={"schema":"warroom.v72_release_runner_validation","status":"PASS" if not FAILURES else "FAIL","checks_passed":PASS,"checks_total":PASS+len(FAILURES),"failures":FAILURES,"licensed_history_in_release":False,"historical_outcomes_opened":False,"predictive_components_promoted":0,"live_decision_weight":0.0,"capital_permission":"BLOCKED"}
Path(__file__).resolve().parents[1].joinpath("V72_RELEASE_RUNNER_VALIDATION.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if not FAILURES else 1)
