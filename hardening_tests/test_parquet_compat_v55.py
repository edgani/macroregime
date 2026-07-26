from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from parquet_compat import read_parquet_compat
from research_v55.flat_parquet_snappy import read_flat_parquet, snappy_decompress

OUT = ROOT / "V55_PARQUET_COMPAT_VALIDATION.json"
CHECKS = []


def check(name: str, condition: bool, **detail) -> None:
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL", **detail})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_digest(frame: pd.DataFrame) -> str:
    values = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    return hashlib.sha256(values).hexdigest()


def reject(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:
        check(name, True, rejected_with=type(exc).__name__, detail=str(exc)[:160])
    else:
        check(name, False, detail="input was accepted")


def main() -> int:
    check("snappy_literal", snappy_decompress(b"\x05\x10hello") == b"hello")
    check("snappy_copy", snappy_decompress(b"\x09\x08abc\x16\x03\x00") == b"abcabcabc")
    reject("snappy_invalid_offset", lambda: snappy_decompress(b"\x04\x0e\x01\x00"))

    expected = {
        "bt_nobootstrap.parquet": ((483, 7), None, ["ticker", "n", "n_closed", "hit", "exp_pct", "pf", "maxdd"]),
        "factor_ic.parquet": ((5, 8), None, ["mean_IC", "IC_std", "IC_IR", "t_stat", "p_value", "pct_positive", "n_periods", "PASS"]),
        "macro_attribution.parquet": ((1820, 16), "Date", None),
        "macro_panel.parquet": ((1713, 8), "Date", ["spx", "cape", "cpi_yoy", "rate10", "gold", "oil", "gas", "dxy"]),
        "sp500_panel.parquet": ((607342, 7), None, ["date", "open", "high", "low", "close", "volume", "Name"]),
        "validated_tickers.parquet": ((45, 8), None, ["ticker", "n_closed", "hit", "exp_pct", "pf", "boot_p", "wf_consistency", "PASS"]),
    }
    before = {name: digest(ROOT / "research" / name) for name in expected}
    frames = {}
    for name, (shape, index_name, columns) in expected.items():
        path = ROOT / "research" / name
        first = read_parquet_compat(path)
        second = read_parquet_compat(path)
        frames[name] = first
        check(f"{name}:shape", first.shape == shape, actual=list(first.shape))
        check(f"{name}:index", first.index.name == index_name, actual=first.index.name)
        if columns is not None:
            check(f"{name}:columns", list(first.columns) == columns, actual=list(first.columns))
        check(f"{name}:deterministic", frame_digest(first) == frame_digest(second), digest=frame_digest(first))

    panel = frames["sp500_panel.parquet"]
    check("sp500_anchor", str(panel.iloc[0]["date"].date()) == "2013-02-08" and panel.iloc[0]["Name"] == "AAL" and abs(float(panel.iloc[0]["close"]) - 14.75) < 1e-12)
    macro = frames["macro_panel.parquet"]
    check("macro_anchor", str(macro.index[0].date()) == "1881-01-01" and abs(float(macro.iloc[0]["spx"]) - 6.19) < 1e-12)
    factor = frames["factor_ic.parquet"]
    check("factor_index_restored", "mom_126" in factor.index and bool(factor.loc["mom_126", "PASS"]) is False)
    projection = read_flat_parquet(ROOT / "research" / "sp500_panel.parquet", columns=["date", "close", "Name"])
    check("projection_semantics", projection.equals(panel[["date", "close", "Name"]]))
    reject("unknown_column", lambda: read_flat_parquet(ROOT / "research" / "sp500_panel.parquet", columns=["NO_SUCH_COLUMN"]))
    reject("duplicate_projection", lambda: read_flat_parquet(ROOT / "research" / "sp500_panel.parquet", columns=["close", "close"]))

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bad = td / "bad.parquet"
        bad.write_bytes(b"NOTPARQUET")
        reject("bad_magic", lambda: read_flat_parquet(bad))
        truncated = td / "truncated.parquet"
        source = (ROOT / "research" / "macro_panel.parquet").read_bytes()
        truncated.write_bytes(source[:-19])
        reject("truncated_file", lambda: read_flat_parquet(truncated))

    after = {name: digest(ROOT / "research" / name) for name in expected}
    check("source_immutability", before == after, mutations=[name for name in before if before[name] != after[name]])
    known_hashes = {
        "macro_panel.parquet": "3ee5d345976759c93e2f37ad77b7e110a891a05e5d36817204fa239768d5d802",
        "macro_attribution.parquet": "257c98959bd4d3c5233e8e922236efd0765fa3a7cb737042d56025e2b5774d67",
        "sp500_panel.parquet": "db2a61d7f66d219354cfaad9dff01a5c9d5b01145ae11549cd11555588729420",
    }
    check("registered_source_hashes", all(after[name] == value for name, value in known_hashes.items()), actual={name: after[name] for name in known_hashes})

    passed = sum(row["status"] == "PASS" for row in CHECKS)
    report = {
        "schema": "warroom.validation.parquet_compat.v55",
        "status": "PASS" if passed == len(CHECKS) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(CHECKS),
        "source_mutations": 0 if before == after else 1,
        "scope": "Flat scalar Parquet; PLAIN/RLE_DICTIONARY; RLE definition levels; SNAPPY/UNCOMPRESSED. Unsupported features fail closed.",
        "checks": CHECKS,
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "checks_passed", "checks_total", "source_mutations"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
