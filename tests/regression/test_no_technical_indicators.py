"""Regression guard against directional technical indicators in production code."""

import re
from pathlib import Path


def test_production_code_contains_no_banned_directional_indicators() -> None:
    banned = {
        "rsi",
        "macd",
        "bollinger",
        "candlestick",
        "moving_average",
        "price_momentum",
    }
    root = Path(__file__).parents[2] / "src" / "eros"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in banned:
            if re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", text):
                violations.append(f"{path.relative_to(root)}:{term}")

    assert violations == []
