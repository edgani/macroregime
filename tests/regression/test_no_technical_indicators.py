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


def test_command_center_contains_no_historical_price_chart() -> None:
    app_root = Path(__file__).parents[2] / "src" / "eros" / "app"
    command_center = (app_root / "command_center.py").read_text(encoding="utf-8")
    research_lab = (app_root / "research_lab.py").read_text(encoding="utf-8")

    assert "LIVE 5-DAY MARKET PATHS" not in command_center
    assert "LIVE 5-DAY MARKET PATHS" in research_lab


def test_publishable_audit_contains_no_user_local_paths() -> None:
    audit = (
        Path(__file__).parents[2]
        / "docs"
        / "audits"
        / "eros_v3_deep_requirements_audit_2026-08-03.md"
    ).read_text(encoding="utf-8")

    assert "C:\\Users\\" not in audit
    assert "AppData" not in audit
    assert "doc_b46c" not in audit
    assert "img_f8ba" not in audit
    assert "`BLOCKED_MISSING_HISTORICAL_SOURCE_COVERAGE`" not in audit
