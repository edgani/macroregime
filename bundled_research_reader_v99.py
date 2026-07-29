"""Read the real research/reference artefacts bundled with War Room OS V9.9.

This module is deliberately separate from capital proof.  A file can be real, hash-valid and useful
for research while still being stale, survivor-biased, non-point-in-time, or unsuitable for an
executable trade.  The dashboard therefore reports two independent states:

* research_data_status
* capital_permission

No synthetic series are created here and no price transform is used as an alpha decision input.
"""
from __future__ import annotations

import functools
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE / "research"
DATA = HERE / "data"
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _safe_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _file_row(path: Path, *, dataset: str, market: str, role: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "provider": "BUNDLED_RESEARCH",
        "dataset": dataset,
        "market": market,
        "role": role,
        "path": path.relative_to(HERE).as_posix(),
        "state": "MISSING",
        "valid_items": 0,
        "capital_eligible": False,
        "point_in_time_eligible": False,
        "note": "File is not present.",
    }
    if not path.is_file() or path.stat().st_size <= 0:
        return row
    row.update({
        "state": "FILE_PRESENT",
        "valid_items": 1,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "note": "Real bundled research artefact. Presence and hash do not prove live alpha or point-in-time eligibility.",
    })
    return row


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
        return ts.isoformat()
    except Exception:
        return str(value)


def _parquet_frame(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    if not path.is_file():
        return None, "file missing"
    try:
        return pd.read_parquet(path), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


@functools.lru_cache(maxsize=1)
def inventory() -> dict[str, Any]:
    specs = [
        (RESEARCH / "sp500_panel.parquet", "sp500_historical_ohlcv", "us", "historical_outcome_and_research_panel"),
        (RESEARCH / "macro_panel.parquet", "macro_cross_asset_panel", "macro", "historical_macro_and_cross_asset_context"),
        (RESEARCH / "macro_attribution.parquet", "macro_attribution", "macro", "historical_attribution_research"),
        (RESEARCH / "factor_ic.parquet", "factor_ic_results", "us", "saved_validation_result"),
        (RESEARCH / "validated_tickers.parquet", "ticker_validation_results", "us", "saved_validation_result"),
        (RESEARCH / "bt_nobootstrap.parquet", "backtest_summary", "us", "saved_validation_result"),
        (RESEARCH / "vix.csv", "vix_history", "macro", "historical_risk_context"),
        (RESEARCH / "shiller.csv", "shiller_history", "macro", "long_horizon_valuation_context"),
        (HERE / "research_results.json", "disciplined_factor_research", "us", "multiple_testing_research_result"),
        (HERE / "metric_grades.json", "metric_grade_registry", "all", "claim_and_emission_limits"),
        (DATA / "extended_universe.json", "extended_universe", "us", "causal_research_universe"),
        (DATA / "chain_reactions.json", "chain_reactions", "all", "causal_chain_reference"),
        (DATA / "ihsg_conglomerates.json", "ihsg_conglomerate_map", "idx", "issuer_controller_reference"),
        (HERE / "bottleneck_reference.json", "bottleneck_reference", "us", "narrative_and_bottleneck_reference"),
    ]
    rows = [_file_row(spec[0], dataset=spec[1], market=spec[2], role=spec[3]) for spec in specs]

    # CSVs and JSONs are inspected directly.  Parquet inspection is best-effort because pyarrow is
    # an explicit runtime dependency but may be absent in a minimal validation container.
    for row in rows:
        path = HERE / row["path"]
        if row["state"] == "MISSING":
            continue
        try:
            if path.suffix.lower() == ".csv":
                frame = pd.read_csv(path)
                row["rows"] = int(len(frame)); row["columns"] = list(map(str, frame.columns))
                date_col = next((c for c in frame.columns if str(c).lower() in {"date", "datetime", "timestamp"}), None)
                if date_col is not None and len(frame):
                    dates = pd.to_datetime(frame[date_col], errors="coerce").dropna()
                    if not dates.empty:
                        row["date_min"] = _date_text(dates.min()); row["date_max"] = _date_text(dates.max())
                row["state"] = "LOADED"
            elif path.suffix.lower() == ".json":
                payload = _safe_json(path, None)
                if payload is not None:
                    row["top_level_type"] = type(payload).__name__
                    row["top_level_items"] = len(payload) if hasattr(payload, "__len__") else None
                    row["state"] = "LOADED"
            elif path.suffix.lower() == ".parquet":
                frame, error = _parquet_frame(path)
                if frame is not None:
                    row["rows"] = int(len(frame)); row["columns"] = list(map(str, frame.columns)); row["state"] = "LOADED"
                    if isinstance(frame.index, pd.DatetimeIndex) and len(frame.index):
                        row["date_min"] = _date_text(frame.index.min()); row["date_max"] = _date_text(frame.index.max())
                    elif "date" in frame.columns:
                        dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
                        if not dates.empty:
                            row["date_min"] = _date_text(dates.min()); row["date_max"] = _date_text(dates.max())
                else:
                    row["state"] = "FILE_PRESENT_READER_UNAVAILABLE"
                    row["reader_error"] = error
                    row["note"] += " Install requirements.txt (pyarrow) to inspect rows in-app."
        except Exception as exc:
            row["state"] = "FILE_PRESENT_READ_ERROR"
            row["reader_error"] = f"{type(exc).__name__}: {exc}"

    present = sum(r["state"] not in {"MISSING"} for r in rows)
    loaded = sum(r["state"] == "LOADED" for r in rows)
    return {
        "schema": "warroom.v99.bundled_research_inventory.v1",
        "datasets": rows,
        "datasets_present": present,
        "datasets_loaded": loaded,
        "datasets_total": len(rows),
        "claim_limit": "Bundled historical/reference data can support research context and validation. It does not by itself authorize capital.",
    }


@functools.lru_cache(maxsize=1)
def macro_context() -> dict[str, Any]:
    observations: dict[str, dict[str, Any]] = {}

    vix_path = RESEARCH / "vix.csv"
    try:
        vix = pd.read_csv(vix_path)
        vix["DATE"] = pd.to_datetime(vix["DATE"], errors="coerce")
        vix["CLOSE"] = pd.to_numeric(vix["CLOSE"], errors="coerce")
        vix = vix.dropna(subset=["DATE", "CLOSE"]).sort_values("DATE")
        if not vix.empty:
            last = vix.iloc[-1]
            observations["BUNDLED_VIX"] = {
                "label": "VIX close (bundled historical context)",
                "value": float(last["CLOSE"]),
                "observation_timestamp": _date_text(last["DATE"]),
                "available_at": None,
                "source": "research/vix.csv",
                "point_in_time_eligible": False,
                "availability_semantics": "Historical/reference context; not reconstructed release-time evidence and not a directional trading input.",
                "history_rows": int(len(vix)),
            }
    except Exception:
        pass

    shiller_path = RESEARCH / "shiller.csv"
    try:
        shiller = pd.read_csv(shiller_path)
        shiller["Date"] = pd.to_datetime(shiller["Date"], errors="coerce")
        shiller = shiller.dropna(subset=["Date"]).sort_values("Date")
        if not shiller.empty:
            last = shiller.iloc[-1]
            for col, sid, label in (
                ("SP500", "BUNDLED_SHILLER_SP500", "Shiller S&P 500 monthly level"),
                ("PE10", "BUNDLED_CAPE", "Shiller PE10 / CAPE"),
                ("Long Interest Rate", "BUNDLED_LONG_RATE", "Shiller long interest rate"),
            ):
                value = pd.to_numeric(pd.Series([last.get(col)]), errors="coerce").iloc[0]
                if pd.notna(value):
                    observations[sid] = {
                        "label": label,
                        "value": float(value),
                        "observation_timestamp": _date_text(last["Date"]),
                        "available_at": None,
                        "source": "research/shiller.csv",
                        "point_in_time_eligible": False,
                        "availability_semantics": "Long-horizon historical valuation context. CAPE is not a near-term crash timer.",
                        "history_rows": int(len(shiller)),
                    }
    except Exception:
        pass

    macro_path = RESEARCH / "macro_panel.parquet"
    macro, error = _parquet_frame(macro_path)
    macro_state = "FILE_PRESENT_READER_UNAVAILABLE" if macro_path.is_file() else "MISSING"
    if macro is not None and not macro.empty:
        macro = macro.sort_index()
        last = macro.iloc[-1]
        obs_date = _date_text(macro.index[-1])
        for col in ("spx", "cape", "cpi_yoy", "rate", "gold", "oil", "gas", "dxy"):
            if col in macro.columns:
                value = pd.to_numeric(pd.Series([last.get(col)]), errors="coerce").iloc[0]
                if pd.notna(value):
                    observations[f"BUNDLED_MACRO_{col.upper()}"] = {
                        "label": f"Bundled macro panel: {col}",
                        "value": float(value),
                        "observation_timestamp": obs_date,
                        "available_at": None,
                        "source": "research/macro_panel.parquet",
                        "point_in_time_eligible": False,
                        "availability_semantics": "Historical research context; no release-vintage reconstruction.",
                        "history_rows": int(len(macro)),
                    }
        macro_state = "LOADED"
    return {
        "schema": "warroom.v99.bundled_macro_context.v1",
        "observations": observations,
        "macro_panel_state": macro_state,
        "macro_panel_reader_error": error,
        "claim_limit": "Raw historical observations are shown as context. They are not converted into an unproven current regime call.",
    }


@functools.lru_cache(maxsize=1)
def validation_context() -> dict[str, Any]:
    results = _safe_json(HERE / "research_results.json", {})
    grades = _safe_json(HERE / "metric_grades.json", {})
    grade_rows = []
    for name, row in grades.items() if isinstance(grades, Mapping) else []:
        if not isinstance(row, Mapping):
            continue
        grade_rows.append({
            "metric": name,
            "grade": row.get("grade", "UNKNOWN"),
            "emit": row.get("emit"),
            "oos": row.get("oos"),
            "note": row.get("note", ""),
        })
    return {
        "schema": "warroom.v99.validation_context.v1",
        "research_results": results if isinstance(results, Mapping) else {},
        "metric_grades": grade_rows,
        "validated_metrics": [r["metric"] for r in grade_rows if r["grade"] == "VALIDATED"],
        "partial_metrics": [r["metric"] for r in grade_rows if r["grade"] == "PARTIAL"],
        "rejected_metrics": [r["metric"] for r in grade_rows if r["grade"] == "REJECTED"],
        "feed_gated_metrics": [r["metric"] for r in grade_rows if r["grade"] == "FEED_GATED"],
        "claim_limit": "Saved validation results describe the tested sample and exact function only; they are not blanket ticker recommendations.",
    }


@functools.lru_cache(maxsize=1)
def _references() -> dict[str, Any]:
    return {
        "extended": _safe_json(DATA / "extended_universe.json", {}),
        "chains": _safe_json(DATA / "chain_reactions.json", {}),
        "idx": _safe_json(DATA / "ihsg_conglomerates.json", {}),
        "bottleneck": _safe_json(HERE / "bottleneck_reference.json", {}),
    }


def _iter_chain_tickers() -> Iterable[tuple[str, Mapping[str, Any], Mapping[str, Any]]]:
    refs = _references(); chains = refs.get("chains") or {}
    for chain in chains.get("chains") or []:
        if not isinstance(chain, Mapping):
            continue
        for step in chain.get("propagation_sequence") or []:
            if not isinstance(step, Mapping):
                continue
            for ticker in step.get("tickers") or []:
                yield str(ticker).upper(), chain, step


@functools.lru_cache(maxsize=1)
def ticker_context_map() -> dict[str, dict[str, Any]]:
    refs = _references()
    out: dict[str, dict[str, Any]] = {}

    extended = refs.get("extended") or {}
    for bucket in ("tier_2_discovered", "tier_3_user_requested"):
        for ticker, row in (extended.get(bucket) or {}).items():
            if not isinstance(row, Mapping):
                continue
            t = str(ticker).upper()
            out.setdefault(t, {}).update({
                "ticker": t,
                "market": "us",
                "research_universe_source": bucket,
                "discovered_date": row.get("discovered_date"),
                "source": row.get("source"),
                "alpha_context": dict(row.get("alpha_context") or {}),
                "fetch_priority": row.get("fetch_priority"),
            })

    for ticker, chain, step in _iter_chain_tickers():
        row = out.setdefault(ticker, {"ticker": ticker, "market": "us"})
        row.setdefault("chains", []).append({
            "chain_id": chain.get("chain_id"),
            "name": chain.get("name"),
            "trigger_event": chain.get("trigger_event"),
            "mechanism": chain.get("mechanism"),
            "horizon": chain.get("horizon"),
            "trigger_status": chain.get("trigger_status"),
            "tier": step.get("tier"),
            "step": step.get("step"),
            "role": step.get("role"),
            "expected_multiplier": step.get("expected_multiplier"),
            "rationale": step.get("rationale"),
        })

    bottleneck = refs.get("bottleneck") or {}
    for item in bottleneck.get("consensus_heatmap") or []:
        if not isinstance(item, Mapping) or not item.get("ticker"):
            continue
        t = str(item["ticker"]).upper(); row = out.setdefault(t, {"ticker": t, "market": "us"})
        row["bottleneck_reference"] = dict(item)
    for item in bottleneck.get("entry_prices") or []:
        if not isinstance(item, Mapping) or not item.get("ticker"):
            continue
        t = str(item["ticker"]).upper(); row = out.setdefault(t, {"ticker": t, "market": "us"})
        row.setdefault("historical_reference_entries", []).append(dict(item))

    idx = refs.get("idx") or {}
    for group_id, group in (idx.get("conglomerates") or {}).items():
        if not isinstance(group, Mapping):
            continue
        tickers: set[str] = set()
        for values in (group.get("tickers") or {}).values():
            if isinstance(values, list):
                tickers.update(str(x).upper() for x in values)
        for values in (group.get("new_armada"), group.get("seven_samurai_legacy")):
            if isinstance(values, list):
                tickers.update(str(x).upper() for x in values)
        for t in tickers:
            row = out.setdefault(t, {"ticker": t, "market": "idx"})
            row.setdefault("idx_groups", []).append({
                "group_id": group_id,
                "patriarch": group.get("patriarch"),
                "holding": group.get("holding"),
                "broker_affiliate": group.get("broker_affiliate"),
                "play_patterns": group.get("characteristic_play_patterns") or [],
            })
    out.setdefault("HUMI", {"ticker": "HUMI", "market": "idx", "research_universe_source": "user_requested_full_idx_candidate"})
    return out


@functools.lru_cache(maxsize=1)
def _sp500_history_map() -> dict[str, dict[str, Any]]:
    path = RESEARCH / "sp500_panel.parquet"
    frame, error = _parquet_frame(path)
    if frame is None or frame.empty:
        return {"__meta__": {"state": "FILE_PRESENT_READER_UNAVAILABLE" if path.is_file() else "MISSING", "error": error}}
    required = {"Name", "date", "close"}
    if not required.issubset(frame.columns):
        return {"__meta__": {"state": "INVALID_SCHEMA", "columns": list(map(str, frame.columns))}}
    frame = frame.copy(); frame["date"] = pd.to_datetime(frame["date"], errors="coerce"); frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    out: dict[str, dict[str, Any]] = {"__meta__": {"state": "LOADED", "rows": int(len(frame))}}
    for ticker, group in frame.dropna(subset=["date", "close"]).groupby("Name", sort=False):
        group = group.sort_values("date")
        out[str(ticker).upper()] = {
            "state": "HISTORICAL_PANEL_AVAILABLE",
            "rows": int(len(group)),
            "date_min": _date_text(group["date"].iloc[0]),
            "date_max": _date_text(group["date"].iloc[-1]),
            "last_historical_price": float(group["close"].iloc[-1]),
            "source": "research/sp500_panel.parquet",
            "claim_limit": "Panel ends in 2018 and is a fixed-constituent sample; it is outcome/research context, not a current execution quote.",
        }
    return out


def ticker_context(ticker: str, market: str) -> dict[str, Any]:
    t = str(ticker).upper()
    alias = {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD", "WTI_REFERENCE": "CL=F", "BRENT_REFERENCE": "BZ=F"}
    lookup = alias.get(t, t)
    row = dict(ticker_context_map().get(lookup) or {"ticker": t, "market": market})
    row["ticker"] = t
    if market == "us":
        history = _sp500_history_map().get(t)
        if history:
            row["historical_price_context"] = history
    row["market"] = market
    return row


def _quarantine() -> set[str]:
    """Tickers verified as invalid references (absent from the IDX registry and
    unresolvable on public quote sources).  Fail-closed: skip, don't guess."""
    try:
        payload = json.loads((HERE / "universe_quarantine.json").read_text(encoding="utf-8"))
        return {str(t).strip().upper() for t in (payload.get("tickers") or [])}
    except Exception:
        return set()


def packet_universe() -> dict[str, list[dict[str, Any]]]:
    """Research packet universe.  This is deliberately distinct from the quote-collection universe."""
    contexts = ticker_context_map()
    out: dict[str, list[dict[str, Any]]] = {m: [] for m in MARKETS}
    non_us_reference_names = {
        "AIR PRODUCTS", "ASIA METAL", "FUJIBO", "HARMONIC DRIVE", "HELIUM ONE", "KEYENCE",
        "NABTESCO", "PULSAR HELIUM", "SAMSUNG", "SEAGATE", "SK HYNIX", "SYTECH", "YASKAWA",
        "FANUC", "LINDE", "TSMC", "HYNIX", "SMIC", "SMC", "AMEC",
    }
    for ticker, row in contexts.items():
        market = str(row.get("market") or "us")
        if ticker.endswith(".JK"):
            market = "idx"; ticker = ticker[:-3]
        if ticker in {"BTC-USD", "ETH-USD", "SOL-USD", "CL=F", "BZ=F"}:
            continue
        if ticker.upper() in _quarantine():
            continue
        if market == "us" and (not re.fullmatch(r"[A-Z]{1,5}", ticker) or ticker in non_us_reference_names):
            continue
        if market == "idx" and not re.fullmatch(r"[A-Z]{2,5}", ticker):
            continue
        if market not in out:
            continue
        symbol = f"{ticker}.JK" if market == "idx" else ticker
        out[market].append({
            "instrument": ticker,
            "provider": "YAHOO",
            "provider_symbol": symbol,
            "asset_type": "IDX_CASH_EQUITY" if market == "idx" else "US_CASH_EQUITY_RESEARCH",
            "research_only": True,
        })

    crypto = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT", "AVAXUSDT"]
    out["crypto"] = [{"instrument": t, "provider": "BINANCE", "provider_symbol": t, "asset_type": "CRYPTO_SPOT_RESEARCH", "research_only": True} for t in crypto]
    out["commodity"] = [
        {"instrument": "WTI_REFERENCE", "provider": "YAHOO", "provider_symbol": "CL=F", "asset_type": "COMMODITY_REFERENCE", "research_only": True},
        {"instrument": "BRENT_REFERENCE", "provider": "YAHOO", "provider_symbol": "BZ=F", "asset_type": "COMMODITY_REFERENCE", "research_only": True},
        {"instrument": "GOLD_REFERENCE", "provider": "YAHOO", "provider_symbol": "GC=F", "asset_type": "COMMODITY_REFERENCE", "research_only": True},
        {"instrument": "COPPER_REFERENCE", "provider": "YAHOO", "provider_symbol": "HG=F", "asset_type": "COMMODITY_REFERENCE", "research_only": True},
        {"instrument": "NATGAS_REFERENCE", "provider": "YAHOO", "provider_symbol": "NG=F", "asset_type": "COMMODITY_REFERENCE", "research_only": True},
    ]
    out["fx"] = [
        {"instrument": "EURUSD_REFERENCE", "provider": "YAHOO", "provider_symbol": "EURUSD=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "USDJPY_REFERENCE", "provider": "YAHOO", "provider_symbol": "JPY=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "GBPUSD_REFERENCE", "provider": "YAHOO", "provider_symbol": "GBPUSD=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "AUDUSD_REFERENCE", "provider": "YAHOO", "provider_symbol": "AUDUSD=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "USDCAD_REFERENCE", "provider": "YAHOO", "provider_symbol": "CAD=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "USDIDR_REFERENCE", "provider": "YAHOO", "provider_symbol": "IDR=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "USDCHF_REFERENCE", "provider": "YAHOO", "provider_symbol": "CHF=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "AUDJPY_REFERENCE", "provider": "YAHOO", "provider_symbol": "AUDJPY=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "CADJPY_REFERENCE", "provider": "YAHOO", "provider_symbol": "CADJPY=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "GBPJPY_REFERENCE", "provider": "YAHOO", "provider_symbol": "GBPJPY=X", "asset_type": "FX_REFERENCE", "research_only": True},
        {"instrument": "EURJPY_REFERENCE", "provider": "YAHOO", "provider_symbol": "EURJPY=X", "asset_type": "FX_REFERENCE", "research_only": True},
    ]
    for market in out:
        seen = set(); deduped = []
        for row in out[market]:
            key = row["instrument"]
            if key in seen:
                continue
            seen.add(key); deduped.append(row)
        out[market] = sorted(deduped, key=lambda x: x["instrument"])
    return out


def market_coverage() -> dict[str, Any]:
    inv = inventory(); datasets = inv["datasets"]
    by_name = {row["dataset"]: row for row in datasets}
    refs = _references(); tmap = ticker_context_map(); packet = packet_universe()

    def present(name: str) -> bool:
        return by_name.get(name, {}).get("state") not in {None, "MISSING"}

    us_domains = {
        "historical_equity_panel": present("sp500_historical_ohlcv"),
        "saved_validation_results": all(present(x) for x in ("factor_ic_results", "ticker_validation_results", "backtest_summary")),
        "causal_universe": present("extended_universe") and present("chain_reactions"),
        "bottleneck_reference": present("bottleneck_reference"),
    }
    idx_domains = {"controller_conglomerate_reference": present("ihsg_conglomerate_map"), "issuer_timeseries": False, "broker_inventory_timeseries": False}
    commodity_domains = {"historical_macro_cross_asset_file": present("macro_cross_asset_panel"), "physical_release_vintages": False, "exact_contract_history": False}
    fx_domains = {"historical_macro_cross_asset_file": present("macro_cross_asset_panel"), "pair_specific_pit_panel": False, "carry_and_intervention_history": False}
    crypto_domains = {"causal_reference": present("chain_reactions"), "onchain_history": False, "venue_derivatives_history": False}
    domain_map = {"us": us_domains, "idx": idx_domains, "commodity": commodity_domains, "fx": fx_domains, "crypto": crypto_domains}
    result = {}
    for market, domains in domain_map.items():
        observed = sum(bool(v) for v in domains.values()); total = len(domains)
        result[market] = {
            "state": "AVAILABLE_HISTORICAL_RESEARCH" if observed == total else "PARTIAL_RESEARCH_CONTEXT" if observed else "NO_DATA",
            "observed_domains": observed,
            "total_domains": total,
            "domains": domains,
            "packet_universe_count": len(packet.get(market) or []),
            "capital_permission": "BLOCKED",
        }
    result["_meta"] = {
        "us_context_tickers": sum(1 for r in tmap.values() if r.get("market") == "us"),
        "idx_context_tickers": sum(1 for r in tmap.values() if r.get("market") == "idx"),
        "chain_count": len((refs.get("chains") or {}).get("chains") or []),
        "conglomerate_count": len((refs.get("idx") or {}).get("conglomerates") or {}),
        "datasets_present": inv["datasets_present"],
    }
    return result


def all_context() -> dict[str, Any]:
    return {
        "inventory": inventory(),
        "macro": macro_context(),
        "validation": validation_context(),
        "market_coverage": market_coverage(),
        "packet_universe": packet_universe(),
        "reference_counts": {
            "ticker_contexts": len(ticker_context_map()),
            "chains": len((_references().get("chains") or {}).get("chains") or []),
            "ihsg_conglomerates": len((_references().get("idx") or {}).get("conglomerates") or {}),
            "bottleneck_heatmap": len((_references().get("bottleneck") or {}).get("consensus_heatmap") or []),
        },
    }
