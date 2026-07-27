from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

import pandas as pd

import fill_normalizer_v93
import provider_gap_solver_v93

ROOT = Path(__file__).resolve().parent
checks = []

def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(condition), "detail": detail})

# Syntax and source-domain controls.
for filename in ["public_data_bootstrap_v93.py", "fill_normalizer_v93.py", "provider_gap_solver_v93.py"]:
    ast.parse((ROOT / filename).read_text(encoding="utf-8"))
check("v93_python_parse", True)
text = (ROOT / "public_data_bootstrap_v93.py").read_text(encoding="utf-8")
for domain in ["sec.gov", "cftc.gov", "binance.vision", "deribit.com"]:
    check(f"official_domain_{domain}", domain in text)
for forbidden in ["SMA", "RSI", "MACD", "breakout", "candlestick"]:
    check(f"no_technical_{forbidden}", forbidden.lower() not in text.lower())

# Fill normalizer rejects paper fills and accepts mapped live fills.
with tempfile.TemporaryDirectory() as temp_dir:
    temp = Path(temp_dir)
    frame = pd.DataFrame([{
        "Account": "A1", "Symbol": "TEST", "Side": "BUY", "Quantity": 1, "Price": 10,
        "DateTime": "2026-01-01T00:00:00Z", "Commission": 0.1, "ExchangeFee": 0.01,
        "Tax": 0, "Financing": 0, "BorrowFee": 0, "OrderID": "O1", "FillID": "F1", "Currency": "USD"
    }])
    input_path = temp / "fills.csv"; frame.to_csv(input_path, index=False)
    mapping = json.loads((ROOT / "V93_FILL_MAPPING_TEMPLATE.json").read_text(encoding="utf-8"))
    mapping["constants"]["venue"] = "TEST_VENUE"; mapping["constants"]["market"] = "US"; mapping["constants"]["is_live_fill"] = False
    mapping_path = temp / "mapping.json"; mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    rejected = False
    try:
        fill_normalizer_v93.normalize(input_path, mapping_path, temp / "out.csv")
    except ValueError:
        rejected = True
    check("paper_fill_rejected", rejected)
    mapping["constants"]["is_live_fill"] = True
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    result = fill_normalizer_v93.normalize(input_path, mapping_path, temp / "out.csv")
    check("live_fill_normalized", result["rows"] == 1 and result["capital_permission"] == "BLOCKED_PENDING_PROOF")

# Gap solver remains fail-closed.
gap = provider_gap_solver_v93.solve(ROOT / "V92_CURRENT_5_OF_5_AUDIT.json")
check("gap_solver_five_markets", len(gap["markets"]) == 5)
check("gap_solver_blocks_capital", gap["capital_permission"] == "BLOCKED" and gap["fully_proven"] == 0)
check("every_market_requires_user_fills", all(row["user_account_export"] for row in gap["markets"]))

report = {"schema": "warroom.v93.validation.v1", "checks": checks, "passed": sum(x["passed"] for x in checks), "total": len(checks)}
report["all_passed"] = report["passed"] == report["total"]
(ROOT / "V93_FINAL_VALIDATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["all_passed"] else 1)
