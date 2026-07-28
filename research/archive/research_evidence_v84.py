"""V8.4 LLM-contamination and global-search integrity evidence."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = HERE / "research_v84/V84_ANTI_OVERFIT_AUDIT_RESULTS.json"
REVOCATION = HERE / "V84_PROOF_REVOCATION.json"


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def attach_research_evidence_v84(desk: dict) -> dict:
    out = deepcopy(desk) if isinstance(desk, dict) else {}
    result = _read(RESULT)
    revocation = _read(REVOCATION)
    out["v84_anti_overfit_evidence"] = {
        "version": "8.4",
        "state": result.get("confirmatory_proof_status", "NO_RESULT"),
        "capital_permission": "BLOCKED",
        "contamination_control_pass": bool(result.get("contamination_control_pass")),
        "local_pbo": result.get("local_pbo") or {},
        "local_deflated_sharpe": result.get("local_deflated_sharpe") or {},
        "causal_grouping_incrementality": result.get("causal_grouping_incrementality") or {},
        "revoked_components": revocation.get("revoked_components") or [],
        "claim": "Prior archive evidence is exploratory only. It cannot be used as proof because LLM-memory contamination, full trial accounting and unseen holdouts were not controlled.",
    }
    proof = out.setdefault("proof_status", {})
    proof.update({
        "final_trading_system": False,
        "capital_permission": "BLOCKED",
        "decision_active_predictive_components": 0,
        "archive_confirmatory_components": 0,
        "reason": "The prior archive claim was revoked under the V8.4 LLM-contamination firewall; independent post-cutoff/prospective proof is absent.",
    })
    return out
