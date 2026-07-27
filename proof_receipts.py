"""Cryptographically verified proof receipts.

Editable registry booleans are never evidence.  Promotion requires an Ed25519 signature from a
locally trusted key, exact component/scope binding, artifact hashes, expiry/revocation checks, and
all frozen proof gates.  The shipped trust store is empty, therefore every predictive component is
blocked until the owner explicitly installs a trusted public key and signed receipt.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

HERE = Path(__file__).resolve().parent
TRUST_STORE = HERE / "proof" / "trusted_public_keys.json"
REVOCATIONS = HERE / "proof" / "revoked_receipts.json"
RECEIPTS_DIR = HERE / "proof" / "receipts"
SCHEMA = "warroom.proof_receipt.v3"
TRUST_SCHEMA = "warroom.trusted_keys.v1"
REVOCATION_SCHEMA = "warroom.revocations.v1"
REQUIRED_GATES = (
    "wfa_pass", "lockbox_pass", "prospective_pass", "cost_model_pass",
    "multiple_testing_pass", "calibration_pass", "false_alarm_pass",
    "lead_time_pass", "remaining_return_lower_bound_positive",
    "expected_shortfall_pass", "capacity_pass", "market_specific_large_move_discovery_pass",
    "narrative_incremental_timing_pass", "market_specific_projection_pass",
    "bottleneck_value_bridge_pass", "projection_calibration_pass",
)
ARTIFACT_HASH_ROLES = {
    "formula_sha256": "formula",
    "code_manifest_sha256": "code_manifest",
    "dataset_manifest_sha256": "dataset_manifest",
    "frozen_spec_sha256": "frozen_spec",
    "trial_ledger_sha256": "trial_ledger",
    "prospective_evidence_sha256": "prospective_evidence",
    "large_move_benchmark_sha256": "large_move_benchmark",
    "narrative_timing_benchmark_sha256": "narrative_timing_benchmark",
    "projection_spec_sha256": "projection_spec",
    "projection_benchmark_sha256": "projection_benchmark",
}



def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _json_file(path: Path) -> dict | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def load_trust_store(path: Path = TRUST_STORE) -> dict[str, dict]:
    raw = _json_file(path) or {}
    keys = raw.get("keys") if raw.get("schema") == TRUST_SCHEMA else None
    return {str(k): dict(v) for k, v in (keys or {}).items() if isinstance(v, dict)}


def load_revocations(path: Path = REVOCATIONS) -> set[str]:
    raw = _json_file(path) or {}
    if raw.get("schema") != REVOCATION_SCHEMA:
        return set()
    return {str(x) for x in (raw.get("revoked_receipt_ids") or [])}


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None

def receipt_payload(receipt: dict) -> dict:
    return {k: v for k, v in receipt.items() if k != "signature"}


def receipt_digest(receipt: dict) -> str:
    return hashlib.sha256(_canonical(receipt_payload(receipt))).hexdigest()


def _safe_artifact_path(rel: str) -> Path | None:
    try:
        p = (HERE / rel).resolve()
        p.relative_to(HERE.resolve())
        return p
    except Exception:
        return None


def _verify_artifacts(receipt: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    artifacts = receipt.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        return False, ["artifact bindings missing"]
    by_role: dict[str, dict] = {}
    for row in artifacts:
        if not isinstance(row, dict):
            reasons.append("invalid artifact binding")
            continue
        role = str(row.get("role") or "")
        if not role or role in by_role:
            reasons.append(f"artifact role missing or duplicate: {role or 'NONE'}")
            continue
        by_role[role] = row
        path = _safe_artifact_path(str(row.get("path") or ""))
        expected = str(row.get("sha256") or "").lower()
        if path is None or not path.is_file() or len(expected) != 64:
            reasons.append(f"artifact unavailable: {row.get('path')}")
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        if h != expected:
            reasons.append(f"artifact hash mismatch: {row.get('path')}")
    proof = receipt.get("proof") or {}
    for proof_key, role in ARTIFACT_HASH_ROLES.items():
        row = by_role.get(role)
        if not row:
            reasons.append(f"required artifact role missing: {role}")
            continue
        if str(row.get("sha256") or "").lower() != str(proof.get(proof_key) or "").lower():
            reasons.append(f"proof hash not bound to artifact role: {role}")
    return not reasons, reasons

def verify_receipt(receipt: dict | str | Path | None, *, component: str | None = None, scope: str | None = None,
                   claim_type: str | None = None, now: datetime | None = None,
                   trust_store_path: Path = TRUST_STORE, revocations_path: Path = REVOCATIONS,
                   trust_store_sha256: str | None = None, verify_artifacts: bool = True) -> dict:
    result = {"valid": False, "reasons": [], "receipt_id": None, "key_id": None, "digest": None}
    if receipt is None:
        result["reasons"].append("signed receipt missing")
        return result
    try:
        if isinstance(receipt, (str, Path)):
            p = Path(receipt)
            if not p.is_absolute():
                p = (HERE / p).resolve()
                p.relative_to(HERE.resolve())
            receipt = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise TypeError("receipt must be an object")
    except Exception as exc:
        result["reasons"].append(f"receipt unreadable: {type(exc).__name__}")
        return result

    result.update({"receipt_id": receipt.get("receipt_id"), "key_id": receipt.get("key_id"), "digest": receipt_digest(receipt)})
    if receipt.get("schema") != SCHEMA:
        result["reasons"].append("receipt schema mismatch")
    if not receipt.get("receipt_id"):
        result["reasons"].append("receipt id missing")
    revocation_raw = _json_file(revocations_path)
    if not revocation_raw or revocation_raw.get("schema") != REVOCATION_SCHEMA:
        result["reasons"].append("revocation registry missing or invalid")
        revoked_ids: set[str] = set()
    else:
        revoked_ids = {str(x) for x in (revocation_raw.get("revoked_receipt_ids") or [])}
    if str(receipt.get("receipt_id")) in revoked_ids:
        result["reasons"].append("receipt revoked")
    if bool(receipt.get("revoked")):
        result["reasons"].append("receipt self-revoked")
    if component and receipt.get("component") != component:
        result["reasons"].append("component mismatch")
    if scope and receipt.get("scope") != scope:
        result["reasons"].append("scope mismatch")
    if claim_type and str(receipt.get("claim_type") or "").upper() != claim_type.upper():
        result["reasons"].append("claim type mismatch")

    now = now or datetime.now(timezone.utc)
    issued = _parse_time(receipt.get("issued_at")); expires = _parse_time(receipt.get("expires_at"))
    if issued is None or expires is None:
        result["reasons"].append("issued/expiry time missing or invalid")
    else:
        if issued > now:
            result["reasons"].append("receipt not yet valid")
        if expires <= now:
            result["reasons"].append("receipt expired")

    proof = receipt.get("proof") or {}
    for gate in REQUIRED_GATES:
        if proof.get(gate) is not True:
            result["reasons"].append(f"proof gate missing: {gate}")
    frozen = tuple(ARTIFACT_HASH_ROLES)
    for key in frozen:
        val = str(proof.get(key) or "")
        if len(val) != 64 or any(c not in "0123456789abcdefABCDEF" for c in val):
            result["reasons"].append(f"invalid proof hash: {key}")
    prospective_start = _parse_time(proof.get("prospective_start"))
    prospective_end = _parse_time(proof.get("prospective_end"))
    try:
        prospective_observations = int(proof.get("prospective_observations") or 0)
    except (TypeError, ValueError):
        prospective_observations = 0
    if prospective_start is None or prospective_end is None or prospective_start >= prospective_end:
        result["reasons"].append("prospective evidence window missing or invalid")
    elif prospective_end > now:
        result["reasons"].append("prospective evidence has not matured")
    if prospective_observations < 200:
        result["reasons"].append("insufficient prospective observations; minimum is 200")
    try:
        prospective_regime_count = int(proof.get("prospective_regime_count") or 0)
    except (TypeError, ValueError):
        prospective_regime_count = 0
    if prospective_regime_count < 4:
        result["reasons"].append("insufficient prospective regime coverage; minimum is four")
    try:
        oos_max_drawdown = float(proof.get("oos_max_drawdown"))
        stress_max_drawdown = float(proof.get("stress_max_drawdown"))
    except (TypeError, ValueError):
        oos_max_drawdown = stress_max_drawdown = float("inf")
    if oos_max_drawdown > 0.15:
        result["reasons"].append("primary OOS maximum drawdown exceeds 15%")
    if stress_max_drawdown > 0.20:
        result["reasons"].append("stress maximum drawdown exceeds 20%")

    component_name = str(receipt.get("component") or component or "").lower()
    stock_like_scope = component_name.startswith(("us_", "idx_", "crypto_"))
    if stock_like_scope:
        # Extreme-winner discovery is mandatory for stock/token Alpha Center scopes.
        ew = proof.get("extreme_winner_metrics") or {}
        try:
            ew_recall20 = float(ew.get("recall_at_20_5x_36m"))
            ew_recall50 = float(ew.get("recall_at_50_5x_36m"))
            ew_precision20 = float(ew.get("precision_at_20_5x_36m"))
            ew_remaining = float(ew.get("median_remaining_return"))
            ew_known = bool(ew.get("mandatory_known_cases_captured"))
        except (TypeError, ValueError):
            ew_recall20 = ew_recall50 = ew_precision20 = ew_remaining = float("-inf")
            ew_known = False
        if ew_recall20 < 0.25:
            result["reasons"].append("extreme-winner Recall@20 below 25%")
        if ew_recall50 < 0.45:
            result["reasons"].append("extreme-winner Recall@50 below 45%")
        if ew_precision20 < 0.08:
            result["reasons"].append("extreme-winner Precision@20 below 8%")
        if ew_remaining < 3.0:
            result["reasons"].append("extreme-winner median remaining return below 300%")
        if not ew_known:
            result["reasons"].append("mandatory post-freeze known-case diagnostics not captured early")
    else:
        large_move = proof.get("large_move_metrics") or {}
        try:
            lm_recall = float(large_move.get("recall_at_20"))
            lm_precision = float(large_move.get("precision_at_20"))
        except (TypeError, ValueError):
            lm_recall = lm_precision = float("-inf")
        if lm_recall < 0.25:
            result["reasons"].append("large-move Recall@20 below 25%")
        if lm_precision < 0.10:
            result["reasons"].append("large-move Precision@20 below 10%")

    # A structural bottleneck is not sufficient. The signed proof must show that the
    # non-price activation state adds incremental timing value versus matched dormant
    # bottleneck controls.
    nt = proof.get("narrative_timing_metrics") or {}
    try:
        nt_hit = float(nt.get("timing_ready_50pct_hit_rate_12m"))
        nt_delta = float(nt.get("incremental_hit_rate_vs_dormant"))
        nt_lower = float(nt.get("incremental_bootstrap_lower"))
        nt_days = float(nt.get("median_days_to_50pct"))
        nt_mae = float(nt.get("median_mae"))
    except (TypeError, ValueError):
        nt_hit = nt_delta = nt_lower = float("-inf")
        nt_days = nt_mae = float("inf")
    if nt_hit < 0.35:
        result["reasons"].append("narrative timing-ready 12m +50% hit rate below 35%")
    if nt_delta < 0.15:
        result["reasons"].append("narrative timing uplift versus dormant bottlenecks below 15%")
    if nt_lower <= 0:
        result["reasons"].append("narrative timing bootstrap incremental lower bound is not positive")
    if nt_days > 180:
        result["reasons"].append("narrative median time to +50% exceeds 180 days")
    if nt_mae > 0.25:
        result["reasons"].append("narrative median MAE exceeds 25%")

    realized = proof.get("realized_performance_metrics") or {}
    try:
        closed_trades = int(realized.get("closed_trades"))
        realized_months = int(realized.get("months"))
        realized_regimes = int(realized.get("regimes"))
        real_pf = float(realized.get("real_net_profit_factor"))
        pf_lower = float(realized.get("profit_factor_bootstrap_95pct_lower"))
    except (TypeError, ValueError):
        closed_trades = realized_months = realized_regimes = 0
        real_pf = pf_lower = float("-inf")
    if closed_trades < 200:
        result["reasons"].append("fewer than 200 actual closed trades")
    if realized_months < 24:
        result["reasons"].append("realized trade history shorter than 24 months")
    if realized_regimes < 4:
        result["reasons"].append("realized trade history covers fewer than four regimes")
    if real_pf < 1.50:
        result["reasons"].append("real net profit factor below 1.50")
    if pf_lower < 1.20:
        result["reasons"].append("profit-factor bootstrap 95% lower bound below 1.20")

    projection = proof.get("projection_metrics") or {}
    market_name = component_name.split("_", 1)[0] if component_name else ""
    error_limits = {"us": 0.35, "idx": 0.40, "commodity": 0.22, "fx": 0.12, "crypto": 0.45}
    try:
        projection_count = int(projection.get("count"))
        projection_months = int(projection.get("months"))
        projection_regimes = int(projection.get("regimes"))
        projection_error = float(projection.get("median_abs_log_error"))
        projection_improvement = float(projection.get("error_improvement_vs_no_change"))
        projection_coverage = float(projection.get("interval_coverage"))
        projection_brier = float(projection.get("scenario_brier"))
        projection_direction = float(projection.get("direction_accuracy"))
        projection_rank = float(projection.get("projected_realized_rank_correlation"))
        projection_severe = float(projection.get("severe_loss_rate"))
    except (TypeError, ValueError):
        projection_count = projection_months = projection_regimes = 0
        projection_error = projection_brier = projection_severe = float("inf")
        projection_improvement = projection_direction = projection_rank = float("-inf")
        projection_coverage = float("-inf")
    if projection_count < 200:
        result["reasons"].append("fewer than 200 matured price projections")
    if projection_months < 24:
        result["reasons"].append("projection benchmark shorter than 24 months")
    if projection_regimes < 4:
        result["reasons"].append("projection benchmark covers fewer than four regimes")
    if market_name in error_limits and projection_error > error_limits[market_name]:
        result["reasons"].append("projection median target error above market-specific ceiling")
    if projection_improvement < 0.10:
        result["reasons"].append("projection does not beat no-change baseline error by 10%")
    if not 0.70 <= projection_coverage <= 0.90:
        result["reasons"].append("projection interval coverage outside 70%-90% calibration band")
    if projection_brier > 0.20:
        result["reasons"].append("projection scenario Brier score above 0.20")
    if projection_direction < 0.55:
        result["reasons"].append("projection direction accuracy below 55%")
    if projection_rank <= 0:
        result["reasons"].append("projected-versus-realized return rank correlation is not positive")
    if projection_severe > 0.15:
        result["reasons"].append("projection severe-loss rate above 15%")

    if claim_type and claim_type.upper() == "CAPITAL_PERMISSION":
        approval = receipt.get("human_approval") or {}
        if approval.get("approved") is not True or not approval.get("approver_id"):
            result["reasons"].append("human approval missing")

    if verify_artifacts:
        ok, reasons = _verify_artifacts(receipt)
        if not ok:
            result["reasons"].extend(reasons)

    expected_trust_hash = str(trust_store_sha256 or os.getenv("WARROOM_TRUST_ROOT_SHA256", "")).lower()
    actual_trust_hash = file_sha256(trust_store_path)
    trust_raw = _json_file(trust_store_path)
    if not expected_trust_hash or len(expected_trust_hash) != 64:
        result["reasons"].append("out-of-band trust-root hash not configured")
    elif actual_trust_hash != expected_trust_hash:
        result["reasons"].append("trust-root hash mismatch")
    if not trust_raw or trust_raw.get("schema") != TRUST_SCHEMA:
        result["reasons"].append("trust store schema invalid")
        keys = {}
    else:
        keys = {str(k): dict(v) for k, v in (trust_raw.get("keys") or {}).items() if isinstance(v, dict)}
    key_id = str(receipt.get("key_id") or "")
    key_row = keys.get(key_id)
    if not key_row:
        result["reasons"].append("signing key is not trusted")
    else:
        if key_row.get("disabled") is True:
            result["reasons"].append("signing key disabled")
        key_expiry = _parse_time(key_row.get("expires_at")) if key_row.get("expires_at") else None
        if key_expiry is not None and key_expiry <= now:
            result["reasons"].append("signing key expired")
        allowed_components = key_row.get("allowed_components") or ["*"]
        allowed_scopes = key_row.get("allowed_scopes") or ["*"]
        if component and "*" not in allowed_components and component not in allowed_components:
            result["reasons"].append("key not authorized for component")
        if scope and "*" not in allowed_scopes and scope not in allowed_scopes:
            result["reasons"].append("key not authorized for scope")
        try:
            public_raw = base64.b64decode(str(key_row.get("public_key_base64") or ""), validate=True)
            sig = base64.b64decode(str(receipt.get("signature") or ""), validate=True)
            Ed25519PublicKey.from_public_bytes(public_raw).verify(sig, _canonical(receipt_payload(receipt)))
        except (ValueError, InvalidSignature, TypeError):
            result["reasons"].append("signature invalid")

    result["valid"] = not result["reasons"]
    return result


def find_receipt(receipt_id: str | None) -> Path | None:
    if not receipt_id:
        return None
    candidate = RECEIPTS_DIR / f"{receipt_id}.json"
    return candidate if candidate.is_file() else None
