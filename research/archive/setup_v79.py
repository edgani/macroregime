"""Interactive, fail-safe setup for the V7.9 exact-scope strategy sleeve."""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
ALLOWED = {"SPY", "VOO", "IVV"}


def ask(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw or default


def parse_fraction(raw: str, name: str, allow_blank: bool = False) -> str:
    if allow_blank and raw.strip() == "":
        return ""
    value = float(raw)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    if name == "sleeve fraction" and value <= 0:
        raise ValueError("sleeve fraction must be greater than 0")
    return f"{value:.6g}"


def update_env(values: dict[str, str]) -> None:
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    for key, value in values.items():
        line = f"{key}={value}"
        pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
        if pattern.search(text):
            text = pattern.sub(line, text)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += line + "\n"
    ENV_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    print("\nWAR ROOM OS V7.9 — FINAL EXACT-SCOPE SETUP")
    print("This system manages only one dedicated broad-US-equity long/cash sleeve.")
    print("It does not trade individual stocks, IHSG, FX, commodities, or crypto.\n")

    instrument = ask("Equity instrument (SPY/VOO/IVV)", "SPY").upper()
    if instrument not in ALLOWED:
        raise ValueError(f"instrument must be one of {sorted(ALLOWED)}")
    sleeve = parse_fraction(ask("Fraction of your total account assigned to this sleeve (0-1)", "0.25"), "sleeve fraction")
    current_raw = ask("Current equity weight inside this sleeve (0=cash, 1=equity, blank=unknown)", "")
    current = parse_fraction(current_raw, "current equity weight", allow_blank=True)
    cost = float(ask("Estimated one-way total execution cost in bps", "10"))
    if not 0 <= cost <= 25:
        raise ValueError("estimated one-way cost must be between 0 and 25 bps")

    print("\nAuthorization is intentionally explicit.")
    print(f"Instrument: {instrument}")
    print(f"Strategy sleeve: {float(sleeve) * 100:.2f}% of account")
    print(f"Current sleeve equity weight: {current or 'unknown'}")
    print(f"Estimated one-way cost: {cost:.2f} bps")
    phrase = input("Type exactly AUTHORIZE V79 to activate this sleeve, or press Enter to keep NO ORDER: ").strip()
    authorized = "1" if phrase == "AUTHORIZE V79" else "0"

    update_env({
        "WARROOM_V79_BASELINE_AUTHORIZED": authorized,
        "WARROOM_V79_EQUITY_INSTRUMENT": instrument,
        "WARROOM_V79_SLEEVE_FRACTION": sleeve,
        "WARROOM_V79_CURRENT_EQUITY_WEIGHT": current,
        "WARROOM_V79_ESTIMATED_ONE_WAY_COST_BPS": f"{cost:.6g}",
    })
    print(f"\nSaved to {ENV_PATH}")
    if authorized == "1":
        print("V7.9 sleeve is authorized. Run RUN_FINAL_CORE.bat after the latest month has completed.")
    else:
        print("Authorization remains OFF. The system will emit NO ORDER.")


if __name__ == "__main__":
    main()
