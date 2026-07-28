from __future__ import annotations
from pathlib import Path
import hashlib
import json
import tempfile

import numpy as np
import pandas as pd

from build_dataset_manifest_v91 import build as build_predictor
from build_outcome_manifest_v91 import build as build_outcome
from market_data_admission_v91 import admit_manifest, _registry
from outcome_data_admission_v91 import admit as admit_outcome
from market_projection_benchmark_v91 import evaluate_exact_market
from asof_panel_builder_v90 import build as build_asof


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def evidence_frame(instrument: str = "TEST1") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "record_id": "R1", "instrument_id": instrument,
            "observation_at": "2010-01-01T00:00:00Z", "available_at": "2010-01-02T00:00:00Z",
            "source_id": "UNIT_SOURCE", "source_record_id": "SRC1", "field_id": "FUNDAMENTAL_FACT",
            "value": 1.0, "unit": "RATIO", "revision_id": "REV1", "feature_domain": "fundamental",
            "synthetic": False, "test_fixture": False,
        }
    ])


def decisions_frame(instrument: str = "TEST1") -> pd.DataFrame:
    dates = pd.date_range("2010-02-01", periods=240, freq="MS", tz="UTC")
    return pd.DataFrame({
        "forecast_id": [f"F{i:04d}" for i in range(len(dates))],
        "instrument_id": instrument,
        "decision_time": dates.astype(str),
        "model_hash": h("model"),
        "regime": [f"R{i % 4}" for i in range(len(dates))],
    })


def projection_frame(market: str = "us") -> pd.DataFrame:
    n = 240
    as_of = pd.date_range("2010-01-01", periods=n, freq="MS", tz="UTC")
    realized = 100 + np.linspace(5, 80, n)
    current = np.full(n, 100.0)
    # 75% interval hits, ordered scenarios; expected target tracks outcome closely.
    low = realized * 0.85
    base = realized.copy()
    high = realized * 1.15
    miss_idx = np.arange(n) % 4 == 0
    low[miss_idx] = realized[miss_idx] * 0.70
    base[miss_idx] = realized[miss_idx] * 0.80
    high[miss_idx] = realized[miss_idx] * 0.90
    return pd.DataFrame({
        "prediction_id": [f"P{i:04d}" for i in range(n)], "market": market,
        "instrument_id": [f"I{i:04d}" for i in range(n)], "as_of": as_of.astype(str),
        "horizon_end": (as_of + pd.offsets.MonthEnd(12)).astype(str), "regime": [f"R{i%4}" for i in range(n)],
        "current_price": current, "target_low": low, "target_base": base,
        "target_high": high, "expected_target_price": realized * (0.99 + (np.arange(n)%3)*0.005),
        "probability_low": 0.1, "probability_base": 0.8, "probability_high": 0.1,
        "realized_price": realized, "point_in_time_valid": True, "model_frozen_before_outcome": True,
        "projection_hash": h("projection"), "outcome_source_hash": h("outcome"),
    })


def main() -> dict:
    checks = []
    def check(name: str, condition: bool, detail=""):
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        market = "us"
        ev = evidence_frame(); ev_path = root / "evidence.csv"; ev.to_csv(ev_path, index=False)
        decisions = decisions_frame(); decisions_path = root / "decisions.csv"; decisions.to_csv(decisions_path, index=False)
        core, optional, outcomes = _registry(market)
        receipts = {key: h(key) for key in (
            "universe_snapshot_hash", "security_master_hash", "global_trial_ledger_hash",
            "data_dictionary_hash", "data_custodian_receipt_hash", "source_license_receipt_hash",
            "code_snapshot_hash", "model_hash",
        )}
        manifest_path = root / "predictor_manifest.json"
        manifest = build_predictor(
            manifest_path=manifest_path, market=market, model_id="US_TEST_CORE",
            decision_times_file=decisions_path, role_files={role: ev_path for role in core},
            history_start="2010-01-01", history_end="2030-01-01", receipts=receipts,
        )
        admission = admit_manifest(manifest_path)
        check("builder_output_passes_forecast_local_admission", admission.get("valid") is True, admission.get("errors"))
        check("historical_proof_ready_is_reachable", admission.get("historical_proof_ready") is True, admission)
        check("optional_addons_do_not_block_core", not (set(optional) & set(manifest["roles"])), optional)
        check("outcomes_absent_from_predictor_manifest", not (set(outcomes) & set(manifest["roles"])), manifest["roles"].keys())
        check("portable_relative_paths", all(not Path(spec["path"]).is_absolute() for spec in manifest["roles"].values()), manifest["roles"])

        # Core role removal must block.
        broken = json.loads(manifest_path.read_text())
        broken["roles"].pop(core[0])
        broken_path = root / "broken_manifest.json"; broken_path.write_text(json.dumps(broken))
        broken_result = admit_manifest(broken_path)
        check("missing_core_role_blocks", broken_result.get("valid") is False and core[0] in broken_result.get("missing_core_roles", []), broken_result)

        # Predictor builder must reject outcomes.
        outcome_rejected = False
        try:
            build_predictor(
                manifest_path=root / "bad.json", market=market, model_id="BAD", decision_times_file=decisions_path,
                role_files={"outcome_prices": ev_path}, history_start="2010-01-01", history_end="2030-01-01", receipts=receipts,
            )
        except ValueError:
            outcome_rejected = True
        check("predictor_builder_rejects_outcome_roles", outcome_rejected)

        # Forecast-local as-of join excludes future rows rather than rejecting the whole history.
        ev2 = pd.concat([ev, ev.assign(record_id="R2", source_record_id="SRC2", field_id="FUTURE_FACT", available_at="2040-01-01T00:00:00Z")], ignore_index=True)
        snapshots, asof_audit = build_asof(ev2.rename(columns={"instrument_id":"instrument_id"}), decisions[["forecast_id","instrument_id","decision_time","model_hash"]])
        check("future_rows_excluded_forecast_locally", asof_audit["future_rows"] == 0 and "FUTURE_FACT" not in set(snapshots.get("field_id", [])), asof_audit)

        # Separate outcome custody is reachable and bound to a seal.
        outcome_frame = pd.DataFrame({
            "forecast_id": decisions["forecast_id"], "horizon_end": decisions["decision_time"],
            "realized_return": 0.1, "max_adverse_excursion": -0.05, "max_favorable_excursion": 0.2,
        })
        outcome_path = root / "outcomes.csv"; outcome_frame.to_csv(outcome_path, index=False)
        seal_path = root / "seal.json"; seal_path.write_text(json.dumps({"predictor_manifest_hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}))
        seal_hash = hashlib.sha256(seal_path.read_bytes()).hexdigest()
        outcome_manifest_path = root / "outcome_manifest.json"
        build_outcome(manifest_path=outcome_manifest_path, market=market, outcome_files={role: outcome_path for role in outcomes}, forecast_seal_hash=seal_hash, custodian_hash=h("custodian"))
        outcome_admission = admit_outcome(outcome_manifest_path, predictor_manifest_hash=hashlib.sha256(manifest_path.read_bytes()).hexdigest(), forecast_seal_hash=seal_hash)
        check("separate_outcome_manifest_passes", outcome_admission.get("valid") is True, outcome_admission)
        bad_outcome = admit_outcome(outcome_manifest_path, predictor_manifest_hash=hashlib.sha256(manifest_path.read_bytes()).hexdigest(), forecast_seal_hash=h("wrong"))
        check("outcome_seal_mismatch_blocks", bad_outcome.get("valid") is False, bad_outcome)

        # Exact-market scoring no longer demands four absent markets.
        projection = evaluate_exact_market(projection_frame("us"), "us")
        check("exact_market_projection_scoring_reachable", projection.get("valid") is True and projection.get("market") == "us", projection)
        check("exact_market_file_rejects_cross_market_mix", evaluate_exact_market(pd.concat([projection_frame("us"), projection_frame("idx")], ignore_index=True), "us").get("valid") is False)

        # Current real bootstrap is explicitly nonhistorical.
        bootstrap_receipt = json.loads((Path(__file__).with_name("bootstrap_evidence") / "us" / "security_master_current_receipt.json").read_text())
        check("real_us_bootstrap_snapshot_present", bootstrap_receipt.get("instruments", 0) > 10000, bootstrap_receipt)
        check("bootstrap_not_mislabeled_historical_proof", bootstrap_receipt.get("proof_ceiling") == "CURRENT_SNAPSHOT_BOOTSTRAP_ONLY", bootstrap_receipt)

    payload = {
        "schema": "warroom.v91.proof_plane_validation.v1",
        "checks": checks,
        "passed": sum(row["status"] == "PASS" for row in checks),
        "failed": sum(row["status"] == "FAIL" for row in checks),
    }
    payload["all_pass"] = payload["failed"] == 0
    return payload


if __name__ == "__main__":
    result = main()
    Path(__file__).with_name("V91_FINAL_VALIDATION.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    raise SystemExit(0 if result["all_pass"] else 1)
