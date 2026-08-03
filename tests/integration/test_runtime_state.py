"""Integration contracts for runtime dashboard state."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eros.app.state import build_public_data_state, load_dashboard_state
from eros.data.public_markets import (
    MARKET_GROUPS,
    MarketObservation,
    MarketSnapshot,
    _freshness_status,
    _write_cache,
    fetch_public_market_snapshot,
)


def test_dashboard_loads_every_configured_country_and_asset_class() -> None:
    state = load_dashboard_state()

    assert len(state.countries) == 15
    assert {row["market"] for row in state.countries} >= {
        "United States",
        "Indonesia",
        "Japan",
        "China",
        "Eurozone",
        "Brazil",
    }
    assert len(state.asset_classes) == 19
    assert {row["asset_class"] for row in state.asset_classes} >= {
        "equities",
        "fx",
        "commodities",
        "crypto",
        "freight",
        "power",
    }


def test_complete_public_snapshot_marks_all_market_feeds_live_without_unlocking_execution() -> None:
    instruments = (
        ("US", "S&P 500", "^GSPC", 6400.0, "USD"),
        ("US", "Nasdaq", "^IXIC", 21000.0, "USD"),
        ("IHSG", "Jakarta Composite", "^JKSE", 8200.0, "IDR"),
        ("Crypto", "Bitcoin", "BTC-USD", 63000.0, "USD"),
        ("Crypto", "Ethereum", "ETH-USD", 1800.0, "USD"),
        ("FX", "USD/IDR", "USDIDR", 18000.0, "IDR"),
        ("FX", "EUR/USD", "EURUSD", 1.14, "USD"),
        ("FX", "USD/JPY", "USDJPY", 160.0, "JPY"),
        ("Commodities", "Gold", "GC=F", 3400.0, "USD"),
        ("Commodities", "WTI", "CL=F", 84.0, "USD"),
        ("Rates & Volatility", "US 10Y", "DGS10", 4.68, "%"),
        ("Rates & Volatility", "VIX", "^VIX", 16.0, "USD"),
    )
    observations = [
        MarketObservation(
            market_group=group,
            instrument=instrument,
            symbol=symbol,
            value=value,
            currency=currency,
            change_pct=0.5,
            observed_at="2026-08-02T16:00:00Z",
            fetched_at="2026-08-02T16:01:00Z",
            provider="public-test",
            status="LIVE",
        )
        for group, instrument, symbol, value, currency in instruments
    ]
    snapshot = MarketSnapshot(
        fetched_at="2026-08-02T16:01:00Z",
        observations=observations,
        failures={},
    )

    state = build_public_data_state(load_dashboard_state(), snapshot)

    assert state.mode == "PUBLIC_DATA"
    assert state.data_health.overall_status == "LIVE"
    assert state.data_health.live_feeds == 6
    assert {feed.status for feed in state.data_health.feeds} == {"LIVE"}
    assert len(state.market_snapshot) == 12
    assert state.feed_failures == {}
    assert {row["coverage"] for row in state.countries if row["market"] == "Indonesia"} == {"LIVE"}
    assert {row["state"] for row in state.asset_classes if row["asset_class"] == "crypto"} == {
        "OBSERVED"
    }
    assert state.execution.permission == "LOCKED"
    assert all(item.state == "UNKNOWN" for item in state.regime_dimensions)


def test_partial_rates_feed_does_not_overstate_health_or_bond_coverage() -> None:
    snapshot = MarketSnapshot(
        fetched_at="2026-08-02T16:01:00Z",
        observations=[
            MarketObservation(
                market_group="Rates & Volatility",
                instrument="VIX",
                symbol="^VIX",
                value=16.0,
                currency="USD",
                observed_at="2026-08-02T16:00:00Z",
                fetched_at="2026-08-02T16:01:00Z",
                provider="public-test",
                status="LIVE",
            )
        ],
        failures={"FRED rates": "provider unavailable"},
    )

    state = build_public_data_state(load_dashboard_state(), snapshot)
    rates_feed = next(feed for feed in state.data_health.feeds if feed.name == "Rates & Volatility")
    sovereign_bonds = next(
        row for row in state.asset_classes if row["asset_class"] == "sovereign_bonds"
    )
    volatility = next(
        row for row in state.asset_classes if row["asset_class"] == "volatility_products"
    )

    assert state.data_health.overall_status == "PARTIAL"
    assert state.data_health.live_feeds == 0
    assert rates_feed.status == "PARTIAL"
    assert sovereign_bonds["state"] == "UNKNOWN"
    assert volatility["state"] == "OBSERVED"


def test_public_fetcher_loads_every_market_group_from_provider_payloads() -> None:
    def fake_request(url: str) -> bytes:
        if "finance.yahoo.com" in url:
            encoded_symbol = url.split("/chart/", 1)[1].split("?", 1)[0]
            symbols = {
                "%5EGSPC": ("^GSPC", "USD"),
                "%5EIXIC": ("^IXIC", "USD"),
                "%5EJKSE": ("^JKSE", "IDR"),
                "GC%3DF": ("GC=F", "USD"),
                "CL%3DF": ("CL=F", "USD"),
                "%5EVIX": ("^VIX", "USD"),
            }
            symbol, currency = symbols[encoded_symbol]
            return json.dumps(
                {
                    "chart": {
                        "result": [
                            {
                                "meta": {"symbol": symbol, "currency": currency},
                                "timestamp": [1785600000, 1785686400],
                                "indicators": {"quote": [{"close": [100.0, 101.0]}]},
                            }
                        ],
                        "error": None,
                    }
                }
            ).encode()
        if "coingecko" in url:
            return json.dumps(
                {
                    "bitcoin": {
                        "usd": 63135,
                        "usd_24h_change": 0.4,
                        "last_updated_at": 1785686400,
                    },
                    "ethereum": {
                        "usd": 1862,
                        "usd_24h_change": -0.3,
                        "last_updated_at": 1785686400,
                    },
                }
            ).encode()
        if "frankfurter" in url:
            return json.dumps(
                {"date": "2026-08-02", "rates": {"EUR": 0.87, "IDR": 18052, "JPY": 160.24}}
            ).encode()
        if "fred" in url:
            return b"observation_date,DGS10\n2026-07-30,4.68\n2026-07-31,4.70\n"
        raise AssertionError(f"Unexpected URL: {url}")

    snapshot = fetch_public_market_snapshot(
        request=fake_request,
        now=datetime(2026, 8, 2, 17, 0, tzinfo=UTC),
        cache_path=None,
    )

    assert {item.market_group for item in snapshot.observations} == set(MARKET_GROUPS)
    assert len(snapshot.observations) == 12
    assert snapshot.failures == {}
    assert all(item.provider for item in snapshot.observations)
    assert all(item.status == "LIVE" for item in snapshot.observations)
    spx = next(item for item in snapshot.observations if item.symbol == "^GSPC")
    assert [point.value for point in spx.history] == [100.0, 101.0]
    assert [point.observed_at for point in spx.history] == [
        "2026-08-01T16:00:00Z",
        "2026-08-02T16:00:00Z",
    ]


def test_public_fetcher_uses_stale_last_good_data_when_providers_fail(tmp_path) -> None:
    cached = MarketSnapshot(
        fetched_at="2026-08-02T16:00:00Z",
        observations=[
            MarketObservation(
                market_group=group,
                instrument=f"{group} benchmark",
                symbol=group,
                value=100.0,
                currency="USD",
                observed_at="2026-08-02T16:00:00Z",
                fetched_at="2026-08-02T16:00:00Z",
                provider="cached-provider",
                status="LIVE",
            )
            for group in MARKET_GROUPS
        ],
    )
    cache_path = tmp_path / "public_market_snapshot.json"
    cache_path.write_text(cached.model_dump_json(), encoding="utf-8")

    def failed_request(url: str) -> bytes:
        raise OSError(f"provider unavailable: {url.split('/')[2]}")

    snapshot = fetch_public_market_snapshot(
        request=failed_request,
        now=datetime(2026, 8, 2, 17, 0, tzinfo=UTC),
        cache_path=cache_path,
    )

    assert len(snapshot.observations) == 6
    assert {item.status for item in snapshot.observations} == {"STALE"}
    assert snapshot.failures
    assert all(item.provider.endswith("(last good cache)") for item in snapshot.observations)

    second_snapshot = fetch_public_market_snapshot(
        request=failed_request,
        now=datetime(2026, 8, 2, 18, 0, tzinfo=UTC),
        cache_path=cache_path,
    )
    persisted = MarketSnapshot.model_validate_json(cache_path.read_text(encoding="utf-8"))

    assert all(
        item.provider.count("(last good cache)") == 1 for item in second_snapshot.observations
    )
    assert {item.provider for item in persisted.observations} == {"cached-provider"}
    stale_state = build_public_data_state(load_dashboard_state(), second_snapshot)
    assert stale_state.data_health.overall_status == "PARTIAL"
    assert stale_state.data_health.live_feeds == 0
    assert "CAUSAL REGIME UNKNOWN" in stale_state.banner


def test_unsupported_cached_market_group_is_rejected_without_crashing(tmp_path) -> None:
    cache_path = tmp_path / "public_market_snapshot.json"
    cache_path.write_text(
        json.dumps(
            {
                "fetched_at": "2026-08-02T16:00:00Z",
                "observations": [
                    {
                        "market_group": "Legacy",
                        "instrument": "Unsupported",
                        "symbol": "OLD",
                        "value": 1.0,
                        "currency": "USD",
                        "observed_at": "2026-08-02T16:00:00Z",
                        "fetched_at": "2026-08-02T16:00:00Z",
                        "provider": "old-cache",
                        "status": "LIVE",
                    }
                ],
                "failures": {},
            }
        ),
        encoding="utf-8",
    )

    def failed_request(url: str) -> bytes:
        raise OSError(f"offline: {url}")

    snapshot = fetch_public_market_snapshot(
        request=failed_request,
        now=datetime(2026, 8, 2, 17, 0, tzinfo=UTC),
        cache_path=cache_path,
    )

    assert snapshot.observations == []
    assert snapshot.failures


def test_95_hour_old_and_future_observations_are_stale() -> None:
    now = datetime(2026, 8, 2, 17, 0, tzinfo=UTC)

    assert _freshness_status(datetime(2026, 7, 29, 18, 0, tzinfo=UTC), now, "US") == "STALE"
    assert _freshness_status(datetime(2026, 8, 2, 17, 6, tzinfo=UTC), now, "US") == "STALE"


def test_non_crypto_freshness_requires_latest_completed_business_date() -> None:
    monday = datetime(2026, 8, 3, 3, 0, tzinfo=UTC)

    assert (
        _freshness_status(datetime(2026, 7, 30, 0, 0, tzinfo=UTC), monday, "Rates & Volatility")
        == "STALE"
    )
    assert _freshness_status(datetime(2026, 7, 31, 0, 0, tzinfo=UTC), monday, "FX") == "LIVE"
    assert _freshness_status(datetime(2026, 8, 2, 23, 0, tzinfo=UTC), monday, "Crypto") == "STALE"


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf"), float("-inf")])
def test_market_observation_rejects_non_finite_values(invalid_value: float) -> None:
    with pytest.raises(ValidationError):
        MarketObservation(
            market_group="US",
            instrument="S&P 500",
            symbol="^GSPC",
            value=invalid_value,
            currency="USD",
            change_pct=invalid_value,
            observed_at="2026-08-02T16:00:00Z",
            fetched_at="2026-08-02T16:01:00Z",
            provider="non-finite-test",
            status="LIVE",
        )


def test_last_good_cache_supports_concurrent_atomic_writes(tmp_path) -> None:
    cache_path = tmp_path / "public_market_snapshot.json"
    snapshots = [
        MarketSnapshot(
            fetched_at=f"2026-08-02T17:00:0{index}Z",
            observations=[
                MarketObservation(
                    market_group="Crypto",
                    instrument="Bitcoin",
                    symbol="BTC-USD",
                    value=63_000 + index,
                    currency="USD",
                    observed_at="2026-08-02T17:00:00Z",
                    fetched_at=f"2026-08-02T17:00:0{index}Z",
                    provider="concurrency-test",
                    status="LIVE",
                )
            ],
        )
        for index in range(8)
    ]

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda snapshot: _write_cache(cache_path, snapshot), snapshots))

    persisted = MarketSnapshot.model_validate_json(cache_path.read_text(encoding="utf-8"))
    assert persisted.observations[0].provider == "concurrency-test"


def test_cache_write_failure_is_reported_without_raising(tmp_path) -> None:
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("blocked", encoding="utf-8")
    snapshot = MarketSnapshot(
        fetched_at="2026-08-02T17:00:00Z",
        observations=[
            MarketObservation(
                market_group="Crypto",
                instrument="Bitcoin",
                symbol="BTC-USD",
                value=63_000,
                currency="USD",
                observed_at="2026-08-02T17:00:00Z",
                fetched_at="2026-08-02T17:00:00Z",
                provider="cache-failure-test",
                status="LIVE",
            )
        ],
    )

    failure = _write_cache(blocked_parent / "snapshot.json", snapshot)

    assert failure is not None
    assert "Error" in failure
