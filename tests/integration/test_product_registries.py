"""Integration contracts for configuration-driven global coverage."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def _load(relative: str) -> dict[str, object]:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_universe_is_registry_driven_and_global() -> None:
    universe = _load("config/universe.yaml")
    markets = universe["markets"]
    names = {market["name"] for market in markets}

    assert {"United States", "Indonesia", "Japan", "China", "Eurozone"} <= names
    assert {market["classification"] for market in markets} >= {"developed", "emerging"}
    assert all("effective_at" in market and "classification_source" in market for market in markets)


def test_dataset_registry_declares_license_and_fail_closed_state() -> None:
    datasets = _load("registries/datasets/core.yaml")["datasets"]

    assert datasets
    assert all(dataset["license"] for dataset in datasets)
    assert all(dataset["status"] in {"ACTIVE", "DATA_DEBT", "DISABLED"} for dataset in datasets)
    assert any(dataset["vintage_available"] for dataset in datasets)
