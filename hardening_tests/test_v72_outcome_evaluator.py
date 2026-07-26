from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from v72_outcome_evaluator import V72EvaluationError, evaluate_all, evaluate_claim_1

REPORT = ROOT / "V72_OUTCOME_EVALUATOR_VALIDATION.json"


def dates_for_split(start: str, periods: int) -> pd.DatetimeIndex:
    return pd.bdate_range(start, periods=periods)


def build_fixture(*, planted: bool, seed: int = 72):
    rng = np.random.default_rng(seed)
    dates = list(dates_for_split("2021-01-04", 180))
    dates += list(dates_for_split("2022-07-01", 120))
    dates += list(dates_for_split("2023-07-03", 120))

    c1_rows = []
    c2_rows = []
    c3_rows = []
    for d in dates:
        for _ in range(4):
            lag = abs(rng.normal(0.0002, 0.00005))
            seasonal = abs(rng.normal(0.00018, 0.00004))
            shock = abs(rng.normal(0.001, 0.0004))
            unsigned = abs(rng.normal(1.0, 0.3))
            gross = abs(rng.normal(0.8, 0.2))
            signed = rng.normal(0.0, 1.0)
            interaction = signed * shock
            gdepth = signed / abs(rng.normal(20.0, 2.0))
            base = 0.4 * lag + 0.5 * seasonal + 0.05 * shock + rng.normal(0, 0.00001)
            effect = (-0.00004 * signed - 0.018 * interaction - 0.0002 * gdepth) if planted else 0.0
            c1_rows.append({
                "trading_dt": d, "lagged_rv": lag, "intraday_seasonal_rv": seasonal,
                "abs_spot_shock": shock, "unsigned_gamma_magnitude": unsigned,
                "gross_oi_topology": gross, "signed_omm_gamma": signed,
                "signed_omm_gamma_x_abs_spot_shock": interaction, "gamma_to_depth": gdepth,
                "future_rv_5m": base + effect + rng.normal(0, 0.000005),
                "future_rv_15m": 1.5 * base + 1.4 * effect + rng.normal(0, 0.000006),
                "future_rv_30m": 2.0 * base + 1.8 * effect + rng.normal(0, 0.000007),
            })

            dist = abs(rng.normal(0.5, 0.2))
            tte = rng.uniform(10, 360)
            exp_move = rng.uniform(0.003, 0.02)
            lagrv = abs(rng.normal(0.01, 0.003))
            ugc = abs(rng.normal(0.4, 0.15))
            sgc = rng.normal(0, 1)
            approach = rng.choice([-1.0, 1.0])
            sgx = sgc * approach
            gd = sgc / abs(rng.normal(15, 3))
            logit = 0.5 - 1.3 * dist - 0.001 * tte + 5 * exp_move + 0.2 * lagrv + 0.1 * ugc
            if planted:
                logit += 1.2 * sgc + 0.8 * sgx + 1.5 * gd
            p = 1 / (1 + np.exp(-logit))
            pin = float(rng.random() < p)
            c2_rows.append({
                "trading_dt": d, "distance_to_strike": dist,
                "time_to_expiry_minutes": tte, "expected_move_fraction": exp_move,
                "lagged_rv": lagrv, "unsigned_gamma_concentration": ugc,
                "signed_gamma_concentration": sgc,
                "signed_gamma_concentration_x_approach_direction": sgx,
                "gamma_to_depth": gd, "pin_event": pin,
            })

        gap = rng.normal(0.002, 0.006)
        selected_edge = 0.8 if (planted and gap > 0) else 0.0
        pnl = selected_edge + rng.normal(0.0, 0.15)
        double = (0.45 if planted and gap > 0 else 0.0) + rng.normal(0.0, 0.12)
        baseline = rng.normal(-0.05 if planted else 0.0, 0.08)
        c3_rows.append({
            "trading_dt": d, "ex_ante_variance_gap": gap,
            "net_pnl": pnl, "simple_baseline_pnl": baseline,
            "double_cost_net_pnl": double,
        })
    return pd.DataFrame(c1_rows), pd.DataFrame(c2_rows), pd.DataFrame(c3_rows)


def must_raise(fn, text: str) -> None:
    try:
        fn()
    except V72EvaluationError as exc:
        if text.lower() not in str(exc).lower():
            raise AssertionError(str(exc))
        return
    raise AssertionError("expected V72EvaluationError")


def main() -> int:
    checks = []

    def check(name, fn):
        try:
            fn(); checks.append({"name": name, "status": "PASS"})
        except Exception as exc:
            checks.append({"name": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

    planted = build_fixture(planted=True)
    result = evaluate_all(*planted, fixture_mode=True)
    check("planted_historical_gate_detected", lambda: None if result["historical_gate_pass"] else (_ for _ in ()).throw(AssertionError(result["gate_components"])))
    check("planted_validation_all_positive", lambda: None if all(v > 0 for v in result["simultaneous_inference"]["validation"]["observed"].values()) else (_ for _ in ()).throw(AssertionError()))
    check("planted_lockbox_lcb_all_positive", lambda: None if all(v > 0 for v in result["simultaneous_inference"]["lockbox"]["simultaneous_lower_bound"].values()) else (_ for _ in ()).throw(AssertionError(result["simultaneous_inference"]["lockbox"])))
    check("historical_pass_never_promotes_live", lambda: None if result["predictive_components_promoted"] == 0 and result["live_decision_weight"] == 0 and result["capital_permission"] == "BLOCKED" else (_ for _ in ()).throw(AssertionError()))
    check("prospective_gate_remains_unmatured", lambda: None if result["gate_components"]["prospective_gate"] == "NOT_MATURED" else (_ for _ in ()).throw(AssertionError()))
    check("placebo_gate_passes_planted_effect", lambda: None if result["gate_components"]["placebo_gate"]["status"] == "PASS" else (_ for _ in ()).throw(AssertionError(result["gate_components"]["placebo_gate"])))

    null = build_fixture(planted=False, seed=73)
    null_result = evaluate_all(*null, fixture_mode=True)
    check("null_fixture_not_promoted", lambda: None if not null_result["historical_gate_pass"] else (_ for _ in ()).throw(AssertionError(null_result["gate_components"])))
    check("deterministic_recompute", lambda: None if evaluate_all(*planted, fixture_mode=True)["simultaneous_inference"] == result["simultaneous_inference"] else (_ for _ in ()).throw(AssertionError()))

    bad = planted[0].drop(columns=["signed_omm_gamma"])
    check("missing_signed_gamma_rejected", lambda: must_raise(lambda: evaluate_claim_1(bad), "missing columns"))
    zero = planted[0].copy(); zero["gross_oi_topology"] = 1.0
    check("zero_variance_discovery_feature_rejected", lambda: must_raise(lambda: evaluate_claim_1(zero), "zero-variance"))
    malformed = planted[0].copy(); malformed.loc[0, "future_rv_5m"] = np.nan
    check("nonfinite_outcome_rejected", lambda: must_raise(lambda: evaluate_claim_1(malformed), "non-finite"))

    failures = [x for x in checks if x["status"] != "PASS"]
    report = {
        "schema": "warroom.v72_outcome_evaluator_validation",
        "status": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
        "planted_fixture_status": result["status"],
        "null_fixture_status": null_result["status"],
        "production_outcomes": "NOT_EVALUATED_LICENSED_DATA_REQUIRED",
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
