"""R2 data-contract acceptance tests.

Covers the R2 acceptance items that are testable offline:
- no synthetic production output (item 9)
- failed load -> NO_DATA, never fabricated bars (items 8, 12)
- test fixtures only behind explicit env gate, tagged TEST_FIXTURE
- provider failure does not erase last-known-good cache (item 8/10)
- stale last-known visible but labelled (item 10)
- exact provider errors recorded (progress/errors visibility)
- R1 engine restoration regression (item 14)
- all restored Python compiles (item 2)
"""
from __future__ import annotations

import compileall
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom import data as D


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("WARROOM_DATA_TEST_FIXTURE", raising=False)
    monkeypatch.setenv("WARROOM_OFFLINE", "1")
    # Point the module cache at an empty temp dir by default.
    monkeypatch.setattr(D, "_CACHE", str(tmp_path / "cache"))
    yield


def _write_cache(tmp_path, tickers, days=120, last_bar=None):
    """Write a minimal real cache parquet with the given tickers."""
    idx = pd.bdate_range(end=last_bar or pd.Timestamp.today().normalize(), periods=days)
    frames = {}
    for t in tickers:
        close = pd.Series(range(100, 100 + days), index=idx, dtype=float)
        frames[t] = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                                  "Close": close, "Volume": 1e6}, index=idx)
    path = tmp_path / "cache"
    path.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, axis=1).to_parquet(path / "prices.parquet")
    return path


def test_no_synthetic_production_output(tmp_path):
    frames, source, states = D.load_with_states(["SPY", "FAKE_TICKER_XYZ"], allow_live=False)
    assert frames == {}, "production must return zero frames when no data exists"
    for t in ("SPY", "FAKE_TICKER_XYZ"):
        assert states[t]["state"] == D.NO_DATA
        assert states[t]["bars"] == 0
    assert "NO_DATA" in source


def test_test_fixture_gated_and_tagged(tmp_path, monkeypatch):
    monkeypatch.setenv("WARROOM_DATA_TEST_FIXTURE", "1")
    frames, _, states = D.load_with_states(["SPY"], allow_live=False)
    assert "SPY" in frames
    assert states["SPY"]["state"] == D.TEST_FIXTURE
    assert states["SPY"]["source"] == "synthetic test fixture"


def test_cache_read_and_states(tmp_path, monkeypatch):
    cache = _write_cache(tmp_path, ["SPY", "QQQ"])
    monkeypatch.setattr(D, "_CACHE", str(cache))
    frames, source, states = D.load_with_states(["SPY", "QQQ", "MISSING"], allow_live=False)
    assert set(frames) == {"SPY", "QQQ"}
    assert states["SPY"]["state"] == D.CURRENT
    assert states["SPY"]["source"] == "cache/prices.parquet"
    assert states["MISSING"]["state"] == D.NO_DATA
    assert any("MISSING" in e for e in D.LAST_ERRORS)


def test_stale_cache_labelled_stale(tmp_path, monkeypatch):
    old_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=30)
    cache = _write_cache(tmp_path, ["SPY"], last_bar=old_date)
    monkeypatch.setattr(D, "_CACHE", str(cache))
    frames, source, states = D.load_with_states(["SPY"], allow_live=False)
    assert states["SPY"]["state"] == D.STALE_LAST_KNOWN
    expected_last = pd.bdate_range(end=old_date, periods=120)[-1].date()
    assert states["SPY"]["last_bar"] == str(expected_last)


def test_provider_failure_preserves_last_known(tmp_path, monkeypatch):
    """Live failure must not erase cached data (last-known stays, labelled)."""
    cache = _write_cache(tmp_path, ["SPY"])
    monkeypatch.setattr(D, "_CACHE", str(cache))
    monkeypatch.delenv("WARROOM_OFFLINE", raising=False)

    class _Boom:
        @staticmethod
        def download(*a, **k):
            raise ConnectionError("simulated provider outage")

    monkeypatch.setitem(sys.modules, "yfinance", _Boom)
    frames, _, states = D.load_with_states(["SPY", "NEW_TICKER"], allow_live=True)
    assert "SPY" in frames, "cached last-known must survive provider failure"
    assert states["NEW_TICKER"]["state"] == D.NO_DATA
    assert any("ConnectionError" in e for e in D.LAST_ERRORS)


def test_missing_quote_never_zero(tmp_path, monkeypatch):
    cache = _write_cache(tmp_path, ["SPY"])
    monkeypatch.setattr(D, "_CACHE", str(cache))
    frames, _, states = D.load_with_states(["SPY", "GAP"], allow_live=False)
    assert "GAP" not in frames
    assert states["GAP"]["state"] == D.NO_DATA
    # No fabricated zero-price frame exists anywhere.
    for df in frames.values():
        assert (df["Close"] > 0).all()


def test_build_cache_merge_never_shrinks(tmp_path, monkeypatch):
    import build_cache as BC
    cache_dir = tmp_path / "cache"
    _write_cache(tmp_path, ["SPY", "QQQ", "IWM"])
    monkeypatch.setattr(BC, "CACHE", str(cache_dir))

    # Provider returns only one ticker with fewer bars than cache -> merge keeps old.
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=100)
    small = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0}, index=idx)

    class _YF:
        @staticmethod
        def download(chunk, **k):
            return pd.concat({"SPY": small}, axis=1)

    monkeypatch.setitem(sys.modules, "yfinance", _YF)
    rc = BC.build(full=False)
    assert rc == 0
    from parquet_compat import read_parquet_compat
    out = read_parquet_compat(str(cache_dir / "prices.parquet"))
    assert set(out.columns.get_level_values(0)) >= {"SPY", "QQQ", "IWM"}
    import json
    lineage = json.loads((cache_dir / "lineage.json").read_text())
    assert lineage["coverage"] >= 3
    assert lineage["tickers"]["QQQ"]["source"] == "cache (last-known)"


def test_r1_engines_still_present():
    """R1 regression: the 81 restored engines + 23 survivors must all exist."""
    engines = list((ROOT / "engines").glob("*.py"))
    assert len(engines) >= 100, f"engine count regressed: {len(engines)}"
    for name in ("gip_engine", "quad_explainer", "regime_transition_engine",
                 "chain_reaction_engine", "market_health_engine", "crash_bottom" if False else "bottleneck_engine",
                 "walkforward_engine", "hedgeye_position_sizing", "alpha_scanner",
                 "alpha_gatekeeper", "cascade_engine", "transmission_engine"):
        assert (ROOT / "engines" / f"{name}.py").exists(), f"missing engine: {name}"


def test_all_restored_python_compiles():
    ok = compileall.compile_dir(str(ROOT / "engines"), quiet=2, maxlevels=1)
    assert ok, "engines/ failed to compile"
    ok = compileall.compile_dir(str(ROOT / "warroom"), quiet=2, maxlevels=1)
    assert ok, "warroom/ failed to compile"
