from pathlib import Path


def test_production_code_contains_no_banned_directional_indicators() -> None:
    banned = {"rsi", "macd", "bollinger", "candlestick", "moving_average", "price_momentum"}
    root = Path(__file__).parents[2] / "src" / "eros"
    violations = [f"{path.relative_to(root)}:{term}" for path in root.rglob("*.py") for term in banned if term in path.read_text(encoding="utf-8").lower()]
    assert violations == []
