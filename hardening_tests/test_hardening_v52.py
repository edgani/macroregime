"""Adversarial tests for the v5.2 real-source hardening gates."""
from __future__ import annotations

import ast
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from direction_authorization import authorize_direction, lineage_digest
from market_capabilities import derive_market_capabilities
from live_market_intelligence import summarize_option_chain
from proof_receipts import SCHEMA, TRUST_SCHEMA, REVOCATION_SCHEMA, ARTIFACT_HASH_ROLES, receipt_payload, verify_receipt
from proof_registry import component_status
from safe_snapshot import canonical_json, read_safe_snapshot, sha256_file, write_safe_snapshot
from scenario_valuation import equity_scenarios
from runtime_store import content_hash as runtime_content_hash, snapshot_integrity_valid

RESULTS: list[dict] = []
TEST_NOW = datetime(2026, 7, 24, 7, 0, 0, tzinfo=timezone.utc)
FIXED_PRIVATE_BYTES = bytes(range(1, 33))


def check(name: str, condition: bool, detail="") -> None:
    RESULTS.append({"name": name, "passed": bool(condition), "detail": str(detail)[:4000]})
    print(("PASS" if condition else "FAIL"), name, str(detail)[:300])


def now_iso(offset_seconds: float = 0) -> str:
    return (TEST_NOW + timedelta(seconds=offset_seconds)).isoformat().replace("+00:00", "Z")


def fixed_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(FIXED_PRIVATE_BYTES)


def sign_receipt(private: Ed25519PrivateKey, *, component: str, scope: str, claim_type: str,
                 receipt_id: str = "test-receipt", key_id: str = "test-key", artifact_rel: str,
                 issued_offset: float = -60, expiry_offset: float = 3600, overrides: dict | None = None) -> dict:
    artifact_path = ROOT / artifact_rel
    artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    receipt = {
        "schema": SCHEMA,
        "receipt_id": receipt_id,
        "key_id": key_id,
        "component": component,
        "scope": scope,
        "claim_type": claim_type,
        "issued_at": now_iso(issued_offset),
        "expires_at": now_iso(expiry_offset),
        "proof": {
            "wfa_pass": True,
            "lockbox_pass": True,
            "prospective_pass": True,
            "cost_model_pass": True,
            "multiple_testing_pass": True,
            "calibration_pass": True,
            "false_alarm_pass": True,
            "lead_time_pass": True,
            "remaining_return_lower_bound_positive": True,
            "expected_shortfall_pass": True,
            "capacity_pass": True,
            "market_specific_large_move_discovery_pass": True,
            "narrative_incremental_timing_pass": True,
            "market_specific_projection_pass": True,
            "bottleneck_value_bridge_pass": True,
            "projection_calibration_pass": True,
            "formula_sha256": artifact_hash,
            "code_manifest_sha256": artifact_hash,
            "dataset_manifest_sha256": artifact_hash,
            "frozen_spec_sha256": artifact_hash,
            "trial_ledger_sha256": artifact_hash,
            "prospective_evidence_sha256": artifact_hash,
            "large_move_benchmark_sha256": artifact_hash,
            "narrative_timing_benchmark_sha256": artifact_hash,
            "projection_spec_sha256": artifact_hash,
            "projection_benchmark_sha256": artifact_hash,
            "prospective_start": "2026-01-01T00:00:00Z",
            "prospective_end": "2026-07-01T00:00:00Z",
            "prospective_observations": 250,
            "prospective_regime_count": 5,
            "oos_max_drawdown": 0.10,
            "stress_max_drawdown": 0.15,
            "large_move_metrics": {"recall_at_20": 0.30, "precision_at_20": 0.15},
            "narrative_timing_metrics": {
                "timing_ready_50pct_hit_rate_12m": 0.40,
                "incremental_hit_rate_vs_dormant": 0.20,
                "incremental_bootstrap_lower": 0.05,
                "median_days_to_50pct": 120,
                "median_mae": 0.10,
            },
            "realized_performance_metrics": {
                "closed_trades": 250, "months": 30, "regimes": 5,
                "real_net_profit_factor": 1.8,
                "profit_factor_bootstrap_95pct_lower": 1.3,
            },
            "projection_metrics": {
                "count": 250, "months": 30, "regimes": 5,
                "median_abs_log_error": 0.10,
                "error_improvement_vs_no_change": 0.15,
                "interval_coverage": 0.80,
                "scenario_brier": 0.15,
                "direction_accuracy": 0.60,
                "projected_realized_rank_correlation": 0.20,
                "severe_loss_rate": 0.10,
            },
        },
        "human_approval": {"approved": True, "approver_id": "test-owner"},
        "artifacts": [
            {"role": role, "path": artifact_rel, "sha256": artifact_hash}
            for role in ARTIFACT_HASH_ROLES.values()
        ],
    }
    if overrides:
        for key, value in overrides.items():
            if key == "proof":
                receipt["proof"].update(value)
            else:
                receipt[key] = value
    raw = json.dumps(receipt_payload(receipt), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    receipt["signature"] = base64.b64encode(private.sign(raw)).decode()
    return receipt


@contextmanager
def temporary_default_trust(private: Ed25519PrivateKey, *, allowed_components=("*",), allowed_scopes=("*",)):
    trust_path = ROOT / "proof" / "trusted_public_keys.json"
    revoke_path = ROOT / "proof" / "revoked_receipts.json"
    old_trust = trust_path.read_bytes() if trust_path.exists() else None
    old_revoke = revoke_path.read_bytes() if revoke_path.exists() else None
    pub = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    trust = {"schema": TRUST_SCHEMA, "keys": {"test-key": {
        "public_key_base64": base64.b64encode(pub).decode(),
        "allowed_components": list(allowed_components),
        "allowed_scopes": list(allowed_scopes),
    }}}
    trust_path.parent.mkdir(parents=True, exist_ok=True)
    trust_path.write_text(json.dumps(trust), encoding="utf-8")
    revoke_path.write_text(json.dumps({"schema": REVOCATION_SCHEMA, "revoked_receipt_ids": []}), encoding="utf-8")
    old_pin = os.environ.get("WARROOM_TRUST_ROOT_SHA256")
    os.environ["WARROOM_TRUST_ROOT_SHA256"] = hashlib.sha256(trust_path.read_bytes()).hexdigest()
    try:
        yield trust_path, revoke_path
    finally:
        if old_pin is None:
            os.environ.pop("WARROOM_TRUST_ROOT_SHA256", None)
        else:
            os.environ["WARROOM_TRUST_ROOT_SHA256"] = old_pin
        if old_trust is None:
            trust_path.unlink(missing_ok=True)
        else:
            trust_path.write_bytes(old_trust)
        if old_revoke is None:
            revoke_path.unlink(missing_ok=True)
        else:
            revoke_path.write_bytes(old_revoke)


def proof_tests() -> None:
    artifact_rel = "hardening_tests/_proof_artifact.bin"
    artifact = ROOT / artifact_rel
    artifact.write_bytes(b"frozen proof artifact")
    private = fixed_private_key()
    scope = "FX_PAIR_SPECIFIC|fx|EURUSD=X|DAILY|LONG"
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            pub = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            trust = td / "trust.json"; revoke = td / "revoke.json"
            trust.write_text(json.dumps({"schema": TRUST_SCHEMA, "keys": {"test-key": {
                "public_key_base64": base64.b64encode(pub).decode(),
                "allowed_components": ["fx_pair_selector"], "allowed_scopes": [scope],
            }}}), encoding="utf-8")
            revoke.write_text(json.dumps({"schema": REVOCATION_SCHEMA, "revoked_receipt_ids": []}), encoding="utf-8")
            trust_pin = hashlib.sha256(trust.read_bytes()).hexdigest()
            receipt = sign_receipt(private, component="fx_pair_selector", scope=scope,
                                   claim_type="CAPITAL_PERMISSION", artifact_rel=artifact_rel)
            good = verify_receipt(receipt, component="fx_pair_selector", scope=scope,
                                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW)
            check("signed_receipt_valid", good.get("valid"), good)

            tampered = json.loads(json.dumps(receipt)); tampered["scope"] = scope + "-X"
            bad = verify_receipt(tampered, component="fx_pair_selector", scope=tampered["scope"],
                                 claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW)
            check("signature_tampering_blocked", not bad.get("valid") and "signature invalid" in bad.get("reasons", []), bad)
            wrong_component = verify_receipt(receipt, component="us_directional_selector", scope=scope,
                                             claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW)
            check("component_mismatch_blocked", not wrong_component.get("valid"), wrong_component)
            wrong_scope = verify_receipt(receipt, component="fx_pair_selector", scope=scope + "|OTHER",
                                         claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW)
            check("scope_mismatch_blocked", not wrong_scope.get("valid"), wrong_scope)
            expired = sign_receipt(private, component="fx_pair_selector", scope=scope, claim_type="CAPITAL_PERMISSION",
                                   artifact_rel=artifact_rel, issued_offset=-7200, expiry_offset=-3600, receipt_id="expired")
            check("expired_receipt_blocked", not verify_receipt(expired, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
            future = sign_receipt(private, component="fx_pair_selector", scope=scope, claim_type="CAPITAL_PERMISSION",
                                  artifact_rel=artifact_rel, issued_offset=3600, expiry_offset=7200, receipt_id="future")
            check("future_receipt_blocked", not verify_receipt(future, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
            revoke.write_text(json.dumps({"schema": REVOCATION_SCHEMA, "revoked_receipt_ids": ["test-receipt"]}), encoding="utf-8")
            check("revoked_receipt_blocked", not verify_receipt(receipt, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
            revoke.write_text(json.dumps({"schema": REVOCATION_SCHEMA, "revoked_receipt_ids": []}), encoding="utf-8")
            trust_pin = hashlib.sha256(trust.read_bytes()).hexdigest()
            untrusted = td / "empty.json"; untrusted.write_text(json.dumps({"schema": TRUST_SCHEMA, "keys": {}}), encoding="utf-8")
            untrusted_pin = hashlib.sha256(untrusted.read_bytes()).hexdigest()
            check("untrusted_key_blocked", not verify_receipt(receipt, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=untrusted, revocations_path=revoke,
                  trust_store_sha256=untrusted_pin, now=TEST_NOW).get("valid"))
            missing_artifact = json.loads(json.dumps(receipt)); missing_artifact["artifacts"][0]["path"] = "missing.bin"
            raw = json.dumps(receipt_payload(missing_artifact), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            missing_artifact["signature"] = base64.b64encode(private.sign(raw)).decode()
            check("missing_artifact_blocked", not verify_receipt(missing_artifact, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
            mismatch = json.loads(json.dumps(receipt)); mismatch["artifacts"][0]["sha256"] = "0" * 64
            raw = json.dumps(receipt_payload(mismatch), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            mismatch["signature"] = base64.b64encode(private.sign(raw)).decode()
            check("artifact_hash_mismatch_blocked", not verify_receipt(mismatch, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
            gate = sign_receipt(private, component="fx_pair_selector", scope=scope, claim_type="CAPITAL_PERMISSION",
                                artifact_rel=artifact_rel, receipt_id="gate", overrides={"proof": {"prospective_pass": False}})
            check("missing_proof_gate_blocked", not verify_receipt(gate, component="fx_pair_selector", scope=scope,
                  claim_type="CAPITAL_PERMISSION", trust_store_path=trust, revocations_path=revoke, trust_store_sha256=trust_pin, now=TEST_NOW).get("valid"))
    finally:
        artifact.unlink(missing_ok=True)


def registry_and_valuation_tests() -> None:
    registry = ROOT / "component_registry_v42.json"
    old = registry.read_bytes() if registry.exists() else None
    malicious = {"components": {"wasserstein_hmm": {
        "state": "HUMAN_APPROVED_LIMITED_PRODUCTION", "predictive_promoted": True,
        "wfa_pass": True, "lockbox_pass": True, "prospective_pass": True,
        "capital_permission": "HUMAN_APPROVED_LIMITED_PRODUCTION",
    }}}
    try:
        registry.write_text(json.dumps(malicious), encoding="utf-8")
        forged_row = json.loads(registry.read_text(encoding="utf-8"))["components"]["wasserstein_hmm"]
        status, run = component_status("wasserstein_hmm", forged_row)
        check("registry_boolean_forgery_blocked",
              status.get("capital_permission") == "BLOCKED"
              and status.get("decision_active") is False
              and status.get("live_weight") == 0.0
              and status.get("proof_run_valid") is False
              and run is None,
              status)
    finally:
        if old is None: registry.unlink(missing_ok=True)
        else: registry.write_bytes(old)

    scenarios = {k: {
        "demand": 100, "share": .1, "margin": .2, "multiple": 10, "net_debt": 0,
        "future_diluted_shares": 10, "probability": p, "probability_calibrated": True,
    } for k, p in (("bear", .2), ("base", .5), ("bull", .3))}
    out = equity_scenarios(10, scenarios, calibration_scope="FAKE", calibration_receipt=None)
    check("boolean_probability_calibration_blocked", out.get("expected_return_pct") is None and out.get("probability_status") == "UNCALIBRATED", out)


def snapshot_tests() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "snapshot.json"
        payload = {"a": [1, 2, 3], "nested": {"ok": True}}
        write_safe_snapshot(path, payload, schema="test.v1")
        check("safe_snapshot_roundtrip", read_safe_snapshot(path, expected_schema="test.v1") == payload)
        original = path.read_bytes(); path.write_bytes(original + b" ")
        try: read_safe_snapshot(path, expected_schema="test.v1"); blocked = False
        except ValueError: blocked = True
        check("snapshot_file_tampering_blocked", blocked)

        write_safe_snapshot(path, payload, schema="test.v1")
        envelope = json.loads(path.read_text(encoding="utf-8")); envelope["payload"]["a"][0] = 999
        path.write_text(canonical_json(envelope), encoding="utf-8")
        side = path.with_name(path.name + ".sha256.json")
        meta = json.loads(side.read_text(encoding="utf-8")); meta["file_sha256"] = sha256_file(path)
        side.write_text(canonical_json(meta), encoding="utf-8")
        try: read_safe_snapshot(path, expected_schema="test.v1"); blocked = False
        except ValueError as exc: blocked = "content hash" in str(exc)
        check("snapshot_content_tampering_blocked", blocked)

        write_safe_snapshot(path, payload, schema="test.v1")
        old_time = time.time() - 1000; os.utime(path, (old_time, old_time))
        try: read_safe_snapshot(path, expected_schema="test.v1", max_age_seconds=10); blocked = False
        except ValueError as exc: blocked = "stale" in str(exc)
        check("stale_snapshot_blocked", blocked)


def capability_tests() -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    base = {"live_intelligence": {}, "full_live_data": {}}
    loose = {"live_intelligence": {"us_options": [{"ticker": "SPY", "state": "LIVE", "observed_at": now}]}}
    check("summary_live_flag_cannot_enable_options", not derive_market_capabilities(loose)["us"]["options_enabled"])
    valid_us = {"live_intelligence": {"us_options": [{
        "ticker": "SPY", "state": "LIVE", "observed_at": now,
        "capability_evidence": {"row_level_validated": True, "exact_contracts": 10, "quote_rows": 10, "providers": ["X"], "observed_at": now},
    }]}}
    check("us_exact_contract_capability", derive_market_capabilities(valid_us)["us"]["options_enabled"])
    stale = json.loads(json.dumps(valid_us)); stale_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    stale["live_intelligence"]["us_options"][0]["observed_at"] = stale_time
    stale["live_intelligence"]["us_options"][0]["capability_evidence"]["observed_at"] = stale_time
    check("stale_option_capability_blocked", not derive_market_capabilities(stale)["us"]["options_enabled"])
    crossed_summary = summarize_option_chain(
        "SPY", [{
            "provider": "fixture", "underlying": "SPY", "contract": "SPY260821C00600000",
            "option_type": "call", "strike": 600, "expiration": "2026-08-21",
            "bid": 12.0, "ask": 11.0, "open_interest": 100, "volume": 5, "underlying_price": 590,
        }], observed_at=now, feed_state="LIVE",
    )
    crossed = {"live_intelligence": {"us_options": [crossed_summary]}}
    check("crossed_quote_capability_blocked", crossed_summary["capability_evidence"]["quote_rows"] == 0 and not derive_market_capabilities(crossed)["us"]["options_enabled"])
    crypto = {"live_intelligence": {"crypto_options": [{
        "underlying": "BTC", "state": "LIVE", "observed_at": now,
        "capability_evidence": {"row_level_validated": True, "exact_contracts": 5, "quote_rows": 5, "providers": ["X"], "observed_at": now},
    }]}}
    check("crypto_missing_venue_blocked", not derive_market_capabilities(crypto)["crypto"]["options_enabled"])
    commodity = {"live_intelligence": {"commodity_options": [{
        "state": "LIVE", "underlying_contract": "CL", "venue": "CME", "expiration": "2026-09-20",
        "strike": 80, "option_type": "call", "observed_at": now,
    }]}}
    check("commodity_generic_root_blocked", not derive_market_capabilities(commodity)["commodity"]["options_enabled"])
    fx_spot = {"live_intelligence": {"fx_options": [{
        "state": "LIVE", "pair": "EURUSD", "product_type": "SPOT", "provider": "X", "tenor": "1M", "observed_at": now,
    }]}}
    check("fx_spot_cannot_enable_options", not derive_market_capabilities(fx_spot)["fx"]["options_enabled"])
    fx_surface = {"live_intelligence": {"fx_vol_surfaces": [{
        "state": "LIVE", "pair": "EURUSD", "product_type": "VOL_SURFACE", "provider": "X", "tenor": "1M",
        "implied_volatility": .08, "delta": "25D", "observed_at": now,
    }]}}
    check("fx_vol_surface_capability", derive_market_capabilities(fx_surface)["fx"]["options_enabled"])
    check("ihsg_options_always_disabled", not derive_market_capabilities(base)["idx"]["options_enabled"])


def direction_tests() -> None:
    dc = {"source": "fixture", "dataset": "fx:EURUSD", "as_of": now_iso(), "max_age_seconds": 3600}
    dc["lineage_hash"] = lineage_digest(dc)
    no_receipt = authorize_direction(component="fx_pair_selector", scope="FX_PAIR_SPECIFIC", market="fx",
        instrument="EURUSD=X", horizon="DAILY", orientation="LONG", data_contract=dc,
        execution_geometry={"entry": 1.10, "stop": 1.09, "target": 1.12}, receipt=None, now=TEST_NOW)
    check("unsigned_direction_blocked", not no_receipt["authorized"], no_receipt)
    stale = dict(dc); stale["as_of"] = now_iso(-7200); stale["lineage_hash"] = lineage_digest(stale)
    out = authorize_direction(component="fx_pair_selector", scope="FX_PAIR_SPECIFIC", market="fx",
        instrument="EURUSD=X", horizon="DAILY", orientation="LONG", data_contract=stale,
        execution_geometry={"entry": 1.10, "stop": 1.09, "target": 1.12}, receipt=None, now=TEST_NOW)
    check("stale_direction_data_blocked", "data contract stale" in out["reasons"], out)
    bad_geometry = authorize_direction(component="fx_pair_selector", scope="FX_PAIR_SPECIFIC", market="fx",
        instrument="EURUSD=X", horizon="DAILY", orientation="LONG", data_contract=dc,
        execution_geometry={"entry": 1.10, "stop": 1.11, "target": 1.12}, receipt=None, now=TEST_NOW)
    check("invalid_execution_geometry_blocked", "invalid long execution geometry" in bad_geometry["reasons"], bad_geometry)
    ihsg = authorize_direction(component="ihsg_long_selector", scope="IHSG_LONG_ONLY_DAILY", market="idx",
        instrument="BBCA.JK", horizon="DAILY", orientation="SHORT", data_contract=dc,
        execution_geometry={"entry": 100, "stop": 105, "target": 90}, receipt=None, now=TEST_NOW)
    check("ihsg_short_blocked", "IHSG is long-only" in ihsg["reasons"], ihsg)

    private = fixed_private_key(); artifact_rel = "hardening_tests/_direction_artifact.bin"
    artifact = ROOT / artifact_rel; artifact.write_bytes(b"direction frozen artifacts")
    scope = "FX_PAIR_SPECIFIC|fx|EURUSD=X|DAILY|LONG"
    try:
        receipt = sign_receipt(private, component="fx_pair_selector", scope=scope,
                               claim_type="CAPITAL_PERMISSION", artifact_rel=artifact_rel)
        with temporary_default_trust(private, allowed_components=("fx_pair_selector",), allowed_scopes=(scope,)):
            out = authorize_direction(component="fx_pair_selector", scope="FX_PAIR_SPECIFIC", market="fx",
                instrument="EURUSD=X", horizon="DAILY", orientation="LONG", data_contract=dc,
                execution_geometry={"entry": 1.10, "stop": 1.09, "target": 1.12}, receipt=receipt, now=TEST_NOW)
            check("valid_exact_scope_direction_authorized", out["authorized"] and out["capital_permission"] == "HUMAN_APPROVED_LIMITED_PRODUCTION", out)
    finally:
        artifact.unlink(missing_ok=True)


def runtime_snapshot_tests() -> None:
    desk = {"meta": {"source": "fixture"}, "markets": {"us": {"bias": "NEUTRAL"}}}
    desk["runtime"] = {"content_hash": runtime_content_hash(desk)}
    check("runtime_snapshot_integrity_valid", snapshot_integrity_valid(desk))
    tampered = json.loads(json.dumps(desk)); tampered["markets"]["us"]["bias"] = "FORGED_LONG"
    check("runtime_snapshot_tampering_blocked", not snapshot_integrity_valid(tampered))


def static_tests() -> None:
    forbidden_imports = {"pickle", "joblib", "dill"}
    violations = []
    pkl_refs = []
    warning_suppression = []
    hardcoded_permissions = []
    # Scan scope: first-party production surface. Excluded: VCS, caches, the test
    # suite itself, virtualenvs, and research/archive (quarantined legacy/research
    # code that is not part of the production runtime per docs/audit/cleanup_plan.json).
    # data/resilient_market_data.py is a kept non-production legacy cache helper
    # (0 references in docs/audit/production_reachable.json); its local .pkl cache
    # strings are recorded as a finding in docs/audit/TEST_RESULTS.md instead of
    # being silently rewritten.
    legacy_nonproduction_allowlist = {"data/resilient_market_data.py"}
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", "__pycache__", "hardening_tests", ".venv", "venv", "node_modules", "archive"} for part in path.parts):
            continue
        if str(path.relative_to(ROOT)).replace("\\", "/") in legacy_nonproduction_allowlist:
            continue
        try: tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            violations.append(f"parse:{path.relative_to(ROOT)}:{exc}"); continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_imports:
                        violations.append(f"import:{path.relative_to(ROOT)}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in forbidden_imports:
                violations.append(f"from:{path.relative_to(ROOT)}:{node.module}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and ".pkl" in node.value.lower():
                pkl_refs.append(f"{path.relative_to(ROOT)}:{node.value}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"filterwarnings", "simplefilter"}:
                if node.args and isinstance(node.args[0], ast.Constant) and str(node.args[0].value).lower() == "ignore":
                    warning_suppression.append(str(path.relative_to(ROOT)))
            elif isinstance(node, ast.Dict):
                safe_zero_or_blocked = {
                    "BLOCKED", "DIRECTIONAL_CAPITAL_BLOCKED", "SHADOW_ONLY_ZERO_CAPITAL",
                    "N/A_NON_PREDICTIVE", "BLOCKED_PENDING_EXACT_INSTRUMENT_REPLICATION",
                    "BLOCKED_PENDING_EXACT_EXECUTABLE_REPLICATION", "BLOCKED_PENDING_EXACT_EXECUTION",
                    "PROOF_GATED",
                }
                scoped_risk_values = {
                    "CONDITIONAL_RISK_CAP_ONLY",
                    "CONDITIONAL_RISK_CAP_ONLY_FOR_US_BROAD_EQUITY_REDUCTION",
                }
                scoped_risk_files = {
                    "validate_v66_scoped_usable.py", "build_release_v66.py", "research_evidence_v66.py",
                    "release_contract_v76.py", "research_evidence_v76.py", "validate_v76_final.py",
                    "build_release_v76.py",
                    "research/archive/validate_v66_scoped_usable.py", "research/archive/build_release_v66.py",
                    "research/archive/research_evidence_v66.py", "research/archive/release_contract_v76.py",
                    "research/archive/research_evidence_v76.py", "research/archive/validate_v76_final.py",
                    "research/archive/build_release_v76.py",
                }
                rel = str(path.relative_to(ROOT)).replace("\\", "/")
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "directional_permission" and isinstance(value, ast.Constant) and value.value is True:
                        hardcoded_permissions.append(f"{rel}:directional_permission=True")
                    if isinstance(key, ast.Constant) and key.value == "capital_permission" and isinstance(value, ast.Constant):
                        cap = str(value.value).upper()
                        safe = cap in safe_zero_or_blocked or cap.startswith("BLOCKED_")
                        scoped = cap in scoped_risk_values and rel in scoped_risk_files
                        if not (safe or scoped):
                            hardcoded_permissions.append(f"{rel}:capital_permission={cap}")
    check("no_unsafe_deserialization_imports", not violations, violations)
    check("no_persistent_pkl_paths", not pkl_refs, pkl_refs[:50])
    check("no_warning_suppression", not warning_suppression, warning_suppression)
    check("no_hardcoded_direction_or_capital_permission", not hardcoded_permissions, hardcoded_permissions)
    wrapper = (ROOT / "validate_all.py").read_text(encoding="utf-8")
    check("validation_wrapper_checks_returncodes", "proc.returncode" in wrapper and "TimeoutExpired" in wrapper and "BLOCKED_BY_ENVIRONMENT" in wrapper)
    capabilities = (ROOT / "market_capabilities.py").read_text(encoding="utf-8")
    check("static_capabilities_defined", "STATIC_CAPABILITIES" in capabilities and "ROW_LEVEL_INSTRUMENT_SPECIFIC" in capabilities)


def main() -> int:
    proof_tests(); registry_and_valuation_tests(); snapshot_tests(); capability_tests(); direction_tests(); runtime_snapshot_tests(); static_tests()
    report = {
        "schema": "warroom.hardening_adversarial.v52",
        "status": "PASS" if all(x["passed"] for x in RESULTS) else "FAIL",
        "passed": sum(x["passed"] for x in RESULTS),
        "total": len(RESULTS),
        "checks": RESULTS,
    }
    (ROOT / "V52_HARDENING_ADVERSARIAL_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "passed", "total")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
