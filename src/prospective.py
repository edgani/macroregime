from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from .common import OUTPUTS, ROOT, package_version_hash, sha256_file, utc_now, write_json

CURRENT_CSV = OUTPUTS / "current" / "US_TOP20_SHADOW_SHORTLIST.csv"
CURRENT_RECEIPT = OUTPUTS / "current" / "US_TOP20_SHADOW_RECEIPT.json"


def seal() -> Path:
    if not CURRENT_CSV.exists() or not CURRENT_RECEIPT.exists():
        raise FileNotFoundError("Run current selector first.")
    receipt = json.loads(CURRENT_RECEIPT.read_text(encoding="utf-8"))
    decision_date = receipt["decision_date"]
    directory = OUTPUTS / "prospective" / decision_date
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copy2(CURRENT_CSV, directory / CURRENT_CSV.name)
    shutil.copy2(CURRENT_RECEIPT, directory / CURRENT_RECEIPT.name)
    seal_receipt = {
        "sealed_at_utc": utc_now(),
        "decision_date": decision_date,
        "contract_sha256": package_version_hash(),
        "shortlist_sha256": sha256_file(directory / CURRENT_CSV.name),
        "source_receipt_sha256": sha256_file(directory / CURRENT_RECEIPT.name),
        "retrospective_edit_allowed": False,
        "status": "SEALED_PROSPECTIVE_SHADOW",
    }
    write_json(directory / "PROSPECTIVE_SEAL.json", seal_receipt)
    print(json.dumps(seal_receipt, indent=2))
    return directory


def score_outcome(decision_date: str, price_file: Path, horizon: int = 63) -> Path:
    directory = OUTPUTS / "prospective" / decision_date
    seal_path = directory / "PROSPECTIVE_SEAL.json"
    shortlist_path = directory / CURRENT_CSV.name
    if not seal_path.exists() or not shortlist_path.exists():
        raise FileNotFoundError(directory)
    if (directory / f"OUTCOME_T{horizon}.csv").exists():
        raise RuntimeError("Outcome already scored; immutable receipt refuses overwrite.")
    prices = pd.read_parquet(price_file)
    prices["date"] = pd.to_datetime(prices["date"])
    shortlist = pd.read_csv(shortlist_path)
    start = pd.Timestamp(decision_date)
    rows = []
    for ticker in shortlist["ticker"]:
        series = prices[(prices["ticker"] == ticker) & prices["date"].ge(start)].sort_values("date")
        if len(series) <= horizon:
            rows.append({"ticker": ticker, "status": "NOT_YET_UNLOCKED"})
            continue
        entry = series.iloc[0]
        exit_row = series.iloc[horizon]
        rows.append(
            {
                "ticker": ticker,
                "entry_date": entry["date"],
                "exit_date": exit_row["date"],
                "entry_adj_close": entry["adj_close"],
                "exit_adj_close": exit_row["adj_close"],
                "return": exit_row["adj_close"] / entry["adj_close"] - 1,
                "status": "UNLOCKED",
            }
        )
    result = pd.DataFrame(rows)
    target = directory / f"OUTCOME_T{horizon}.csv"
    result.to_csv(target, index=False)
    write_json(
        directory / f"OUTCOME_T{horizon}_RECEIPT.json",
        {
            "scored_at_utc": utc_now(),
            "horizon": horizon,
            "result_sha256": sha256_file(target),
            "unlocked": int(result["status"].eq("UNLOCKED").sum()),
            "not_yet_unlocked": int(result["status"].eq("NOT_YET_UNLOCKED").sum()),
        },
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seal")
    score = sub.add_parser("score")
    score.add_argument("--decision-date", required=True)
    score.add_argument("--price-file", type=Path, default=ROOT / "data/processed/prices_sp500_pit.parquet")
    score.add_argument("--horizon", type=int, default=63)
    args = parser.parse_args()
    if args.command == "seal":
        seal()
    else:
        score_outcome(args.decision_date, args.price_file, args.horizon)


if __name__ == "__main__":
    main()
