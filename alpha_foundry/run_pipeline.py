from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_module(module: str, *arguments: str) -> None:
    command = [sys.executable, "-m", module, *arguments]
    print("\n>>>", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room US Alpha Foundry runner")
    parser.add_argument("--mode", choices=["quick", "full", "build-only", "test"], default="quick")
    parser.add_argument("--sec-user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    args = parser.parse_args()

    if args.mode == "test":
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
        return

    if args.sec_user_agent:
        os.environ["SEC_USER_AGENT"] = args.sec_user_agent
    if not os.environ.get("SEC_USER_AGENT"):
        raise RuntimeError("SEC_USER_AGENT is required. Use 'Name email@example.com'.")

    if args.mode != "build-only":
        start = "2020q1" if args.mode == "quick" else "2016q1"
        run_module("src.download_data", "--sec-start", start, "--sec-end", "2026q1")

    run_module("src.build_prices", "--start-date", "2016-01-01")
    run_module("src.build_entity_master")
    run_module("src.build_sec_features")
    run_module("src.build_panel")
    run_module("src.run_tournament", "--period", "discovery")
    run_module("src.run_tournament", "--period", "validation")
    run_module("src.run_current_selector", "--target", "T63", "--top-k", "20")
    try:
        run_module("src.prospective", "seal")
    except subprocess.CalledProcessError:
        print("Prospective seal was not overwritten. Check outputs/prospective for an existing dated receipt.")
    print("\nCOMPLETE: operational shadow shortlist and prospective receipt path processed.")
    print("PAPER/LIVE are still blocked until lockbox and future outcomes pass.")


if __name__ == "__main__":
    main()
