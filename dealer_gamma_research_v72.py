"""Fail-closed Cboe C1 SPX/SPXW signed-dealer research pipeline (V72).

This module is an implementation of the frozen V72 protocol.  It does not ship or fetch
proprietary data and it never emits a trade.  Its purpose is to validate licensed Cboe TBT/GRK
records, reconstruct aggregate options-market-maker positions from signed trade flow, join the
official trade-level Greeks, and produce research-only exposure tables.

The module intentionally rejects:
* gross-open-interest dealer-sign assumptions;
* incomplete daily file calendars;
* rows outside C1 SPX/SPXW RTH;
* exact duplicates, provisional records, stale/mismatched GRK joins;
* series whose history is not known from inception;
* any attempt to attach live/capital permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import json
import math
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PROTOCOL_PATH = ROOT / "research_v56" / "V72_SPX_SIGNED_DEALER_PROTOCOL_FROZEN.json"

TBT_REQUIRED = (
    "transact_time", "trading_dt", "underlying", "osi_root", "expire_date",
    "call_put_flag", "strike_price", "size", "price", "nbbo_bid", "nbbo_ask",
    "bbo_bid", "bbo_ask", "side", "open_close", "capacity", "trade_type",
    "exec_id", "complex_exec_id", "session", "trading_segment",
)
GRK_REQUIRED = (
    "transact_time", "trading_dt", "formatted_symbol", "price", "delta", "gamma",
    "vega", "rho", "theta", "theo_price",
)
QUOTE_REQUIRED = (
    "underlying_symbol", "quote_datetime", "root", "expiration", "strike", "option_type",
    "bid_size", "bid", "ask_size", "ask", "open_interest", "active_underlying_price",
    "implied_volatility", "delta", "gamma", "theta", "vega", "rho",
)
UNDERLIER_REQUIRED = (
    "transact_time", "trading_dt", "spot", "es_traded_notional", "es_depth_notional",
)
MM_CAPACITY = {"M", "N", "MARKETMAKER", "MARKET_MAKER", "MARKET MAKER"}
ALLOWED_ROOTS = {"SPX", "SPXW"}
ALLOWED_SESSIONS = {"RTH"}
PROVISIONAL_TRADE_TYPES = {"57", "PROVISIONAL"}
CONTRACT_MULTIPLIER = 100.0


class V72DataError(ValueError):
    """A fail-closed source, schema, lineage, or reconstruction error."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def protocol_sha256(path: Path = PROTOCOL_PATH) -> str:
    return file_sha256(path)


def _require_columns(df: pd.DataFrame, required: Sequence[str], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise V72DataError(f"{label} missing required columns: {missing}")


def _as_utc(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce", utc=True)
    if out.isna().any():
        bad = int(out.isna().sum())
        raise V72DataError(f"{label} contains {bad} invalid timestamps")
    return out


def _as_date(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce").dt.date
    if out.isna().any():
        raise V72DataError(f"{label} contains invalid dates")
    return out


def _numeric(df: pd.DataFrame, columns: Sequence[str], label: str) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        if out[col].isna().any() or not np.isfinite(out[col].to_numpy(dtype=float)).all():
            raise V72DataError(f"{label}.{col} contains non-finite values")
    return out


def _normalize_capacity(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_")


def _format_strike(value: Any) -> str:
    x = float(value)
    if not math.isfinite(x):
        raise V72DataError("non-finite strike")
    if x.is_integer():
        return str(int(x))
    return (f"{x:.10f}").rstrip("0").rstrip(".")


def build_formatted_symbol(tbt: pd.DataFrame) -> pd.Series:
    exp = pd.to_datetime(tbt["expire_date"], errors="coerce")
    if exp.isna().any():
        raise V72DataError("TBT expire_date invalid")
    roots = tbt["osi_root"].astype(str).str.strip().str.upper()
    cp = tbt["call_put_flag"].astype(str).str.strip().str.upper()
    strikes = tbt["strike_price"].map(_format_strike)
    return roots + exp.dt.strftime("%y%m%d") + cp + strikes


def _exact_duplicate_subset_tbt() -> list[str]:
    return [
        "transact_time", "trading_dt", "osi_root", "expire_date", "call_put_flag",
        "strike_price", "size", "price", "side", "open_close", "capacity",
        "trade_type", "exec_id", "complex_exec_id", "session", "trading_segment",
    ]


def validate_tbt(tbt: pd.DataFrame, *, final_corrections_confirmed: bool = False) -> pd.DataFrame:
    _require_columns(tbt, TBT_REQUIRED, "TBT")
    out = tbt.loc[:, list(dict.fromkeys(TBT_REQUIRED))].copy()
    out["transact_time"] = _as_utc(out["transact_time"], "TBT.transact_time")
    out["trading_dt"] = _as_date(out["trading_dt"], "TBT.trading_dt")
    out["expire_date"] = _as_date(out["expire_date"], "TBT.expire_date")
    out = _numeric(out, ["strike_price", "size", "price", "nbbo_bid", "nbbo_ask", "bbo_bid", "bbo_ask"], "TBT")

    out["underlying"] = out["underlying"].astype(str).str.strip().str.upper()
    out["osi_root"] = out["osi_root"].astype(str).str.strip().str.upper()
    out["call_put_flag"] = out["call_put_flag"].astype(str).str.strip().str.upper()
    out["side"] = out["side"].astype(str).str.strip().str.upper()
    out["open_close"] = out["open_close"].astype(str).str.strip().str.upper()
    out["capacity_norm"] = out["capacity"].map(_normalize_capacity)
    out["session"] = out["session"].astype(str).str.strip().str.upper()
    out["trade_type_norm"] = out["trade_type"].astype(str).str.strip().str.upper()

    if not set(out["underlying"]).issubset({"SPX"}):
        raise V72DataError(f"TBT contains non-SPX underlying: {sorted(set(out['underlying']) - {'SPX'})}")
    if not set(out["osi_root"]).issubset(ALLOWED_ROOTS):
        raise V72DataError(f"TBT contains unsupported OSI root: {sorted(set(out['osi_root']) - ALLOWED_ROOTS)}")
    if not set(out["session"]).issubset(ALLOWED_SESSIONS):
        raise V72DataError(f"TBT contains non-RTH sessions: {sorted(set(out['session']) - ALLOWED_SESSIONS)}")
    if not set(out["call_put_flag"]).issubset({"C", "P"}):
        raise V72DataError("TBT call_put_flag must be C or P")
    if not set(out["side"]).issubset({"B", "S"}):
        raise V72DataError("TBT side must be B or S")
    if not set(out["open_close"]).issubset({"O", "C"}):
        raise V72DataError("TBT open_close must be O or C")
    if (out["size"] <= 0).any() or (out["price"] < 0).any() or (out["strike_price"] <= 0).any():
        raise V72DataError("TBT size/price/strike constraints violated")
    if (out["nbbo_ask"] < out["nbbo_bid"]).any() or (out["bbo_ask"] < out["bbo_bid"]).any():
        raise V72DataError("TBT contains crossed quotes")
    if not final_corrections_confirmed and out["trade_type_norm"].isin(PROVISIONAL_TRADE_TYPES).any():
        raise V72DataError("TBT contains provisional trades without final-correction confirmation")

    dup = out.duplicated(_exact_duplicate_subset_tbt(), keep=False)
    if dup.any():
        raise V72DataError(f"TBT contains {int(dup.sum())} exact duplicate rows")

    out["formatted_symbol"] = build_formatted_symbol(out)
    out["is_market_maker"] = out["capacity_norm"].isin(MM_CAPACITY)
    out["signed_contracts"] = np.where(out["side"].eq("B"), out["size"], -out["size"])
    out["signed_mm_contracts"] = np.where(out["is_market_maker"], out["signed_contracts"], 0.0)
    return out.sort_values(["trading_dt", "transact_time", "formatted_symbol", "exec_id", "side"], kind="mergesort").reset_index(drop=True)


def validate_grk(grk: pd.DataFrame) -> pd.DataFrame:
    _require_columns(grk, GRK_REQUIRED, "GRK")
    out = grk.loc[:, list(GRK_REQUIRED)].copy()
    out["transact_time"] = _as_utc(out["transact_time"], "GRK.transact_time")
    out["trading_dt"] = _as_date(out["trading_dt"], "GRK.trading_dt")
    out["formatted_symbol"] = out["formatted_symbol"].astype(str).str.strip().str.upper()
    out = _numeric(out, ["price", "delta", "gamma", "vega", "rho", "theta", "theo_price"], "GRK")
    if (out["price"] < 0).any() or (out["gamma"] < 0).any():
        raise V72DataError("GRK price/gamma constraints violated")
    keys = ["trading_dt", "formatted_symbol", "price", "transact_time"]
    if out.duplicated(keys, keep=False).any():
        raise V72DataError("GRK contains duplicate natural keys")
    return out.sort_values(["trading_dt", "formatted_symbol", "price", "transact_time"], kind="mergesort").reset_index(drop=True)


def join_tbt_grk(tbt: pd.DataFrame, grk: pd.DataFrame, *, tolerance_seconds: int = 5,
                 minimum_match_rate: float = 0.995) -> tuple[pd.DataFrame, dict[str, Any]]:
    t = validate_tbt(tbt) if "formatted_symbol" not in tbt.columns else tbt.copy()
    g = validate_grk(grk) if "gamma" in grk.columns and not pd.api.types.is_datetime64_any_dtype(grk["transact_time"]) else grk.copy()

    # merge_asof requires a global ordering on the timestamp key. Equality keys prevent cross-contract joins.
    t = t.sort_values(["transact_time", "trading_dt", "formatted_symbol", "price"], kind="mergesort").reset_index(drop=True)
    g = g.sort_values(["transact_time", "trading_dt", "formatted_symbol", "price"], kind="mergesort").reset_index(drop=True)
    merged = pd.merge_asof(
        t,
        g[["transact_time", "trading_dt", "formatted_symbol", "price", "delta", "gamma", "vega", "rho", "theta", "theo_price"]].rename(columns={"transact_time": "grk_transact_time"}),
        left_on="transact_time",
        right_on="grk_transact_time",
        by=["trading_dt", "formatted_symbol", "price"],
        direction="forward",
        tolerance=pd.Timedelta(seconds=tolerance_seconds),
        allow_exact_matches=True,
    )
    merged["grk_dt_seconds"] = (merged["grk_transact_time"] - merged["transact_time"]).dt.total_seconds()
    invalid_backward = merged["grk_dt_seconds"].notna() & (merged["grk_dt_seconds"] < 0)
    invalid_stale = merged["grk_dt_seconds"].notna() & (merged["grk_dt_seconds"] > tolerance_seconds)
    if invalid_backward.any() or invalid_stale.any():
        raise V72DataError("GRK join violated forward/tolerance contract")
    match_rate = float(merged["gamma"].notna().mean()) if len(merged) else 0.0
    if match_rate < minimum_match_rate:
        raise V72DataError(f"GRK match rate {match_rate:.6f} below frozen minimum {minimum_match_rate:.6f}")
    diagnostics = {
        "schema": "warroom.v72_tbt_grk_join_diagnostics",
        "rows": int(len(merged)),
        "matched_rows": int(merged["gamma"].notna().sum()),
        "match_rate": match_rate,
        "maximum_join_seconds": float(merged["grk_dt_seconds"].max()) if merged["grk_dt_seconds"].notna().any() else None,
        "direction": "FORWARD_ASOF",
        "tolerance_seconds": tolerance_seconds,
        "status": "PASS",
    }
    return merged, diagnostics


def validate_source_manifest(manifest: Mapping[str, Any], *, base_dir: Path,
                             expected_dates: Sequence[date] | None = None) -> dict[str, Any]:
    rows = manifest.get("files") if isinstance(manifest, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise V72DataError("source manifest has no files")
    seen_paths: set[str] = set()
    coverage: dict[str, set[date]] = {"TBT": set(), "QUOTES": set(), "UNDERLIER": set(), "GRK": set()}
    checked = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise V72DataError("source manifest row is not an object")
        rel = str(row.get("path") or "")
        p = Path(rel)
        if not rel or p.is_absolute() or ".." in p.parts or rel in seen_paths:
            raise V72DataError(f"unsafe or duplicate source path: {rel}")
        seen_paths.add(rel)
        full = base_dir / p
        if not full.is_file():
            raise V72DataError(f"missing source file: {rel}")
        expected_hash = str(row.get("sha256") or "").lower()
        actual_hash = file_sha256(full)
        if len(expected_hash) != 64 or expected_hash != actual_hash:
            raise V72DataError(f"source hash mismatch: {rel}")
        if int(row.get("bytes", -1)) != full.stat().st_size:
            raise V72DataError(f"source size mismatch: {rel}")
        product = str(row.get("product") or "").upper()
        if product not in coverage:
            raise V72DataError(f"unsupported source product: {product}")
        d = pd.to_datetime(row.get("trading_dt"), errors="coerce")
        if pd.isna(d):
            raise V72DataError(f"invalid trading_dt in manifest: {rel}")
        coverage[product].add(d.date())
        checked.append({"path": rel, "product": product, "trading_dt": d.date().isoformat(), "sha256": actual_hash})
    if expected_dates:
        expected = set(expected_dates)
        for product in ("TBT", "QUOTES", "UNDERLIER"):
            dates = coverage[product]
            missing = sorted(expected - dates)
            if missing:
                raise V72DataError(f"{product} missing {len(missing)} expected dates; first={missing[0]}")
    return {
        "schema": "warroom.v72_source_manifest_validation",
        "status": "PASS",
        "files_checked": len(checked),
        "coverage_counts": {k: len(v) for k, v in coverage.items()},
        "manifest_digest_sha256": sha256_bytes(canonical(checked)),
    }


def reconstruct_omm_positions(joined: pd.DataFrame, *, acquisition_start: date = date(2019, 10, 7),
                              analysis_start: date = date(2020, 7, 1)) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["trading_dt", "transact_time", "formatted_symbol", "expire_date", "signed_mm_contracts", "gamma"]
    _require_columns(joined, required, "TBTWG")
    out = joined.copy().sort_values(["formatted_symbol", "transact_time"], kind="mergesort")
    first_seen = out.groupby("formatted_symbol", sort=False)["trading_dt"].min()
    # A series first seen on the acquisition start may have existed before the licensed archive; quarantine it.
    legacy = set(first_seen[first_seen <= acquisition_start].index)
    out["series_history_state"] = np.where(out["formatted_symbol"].isin(legacy), "LEGACY_PREEXISTING_QUARANTINED", "COMPLETE_FROM_FIRST_OBSERVED_TRADE")
    out["omm_net_contracts"] = out.groupby("formatted_symbol", sort=False)["signed_mm_contracts"].cumsum()
    out["raw_position_gamma"] = out["omm_net_contracts"] * CONTRACT_MULTIPLIER * out["gamma"]
    out["analysis_eligible"] = (
        (out["trading_dt"] >= analysis_start)
        & ~out["formatted_symbol"].isin(legacy)
        & out["gamma"].notna()
    )
    diagnostics = {
        "schema": "warroom.v72_position_reconstruction_diagnostics",
        "status": "PASS",
        "series": int(first_seen.size),
        "legacy_series_quarantined": int(len(legacy)),
        "eligible_rows": int(out["analysis_eligible"].sum()),
        "position_rule": "MM buy +size; MM sell -size; cumulative by exact formatted_symbol",
        "capital_permission": "BLOCKED",
    }
    return out.sort_values(["trading_dt", "transact_time", "formatted_symbol"], kind="mergesort").reset_index(drop=True), diagnostics



def reconstruct_positions_from_tbt(tbt: pd.DataFrame, *, acquisition_start: date = date(2019, 10, 7),
                                   analysis_start: date = date(2020, 7, 1)) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconstruct exact OMM position states without using Greeks.

    Gamma is intentionally marked later from the full one-minute quote surface. Trade-level GRK
    is not used as a substitute for untraded active series.
    """
    out = validate_tbt(tbt) if "signed_mm_contracts" not in tbt.columns else tbt.copy()
    out = out.sort_values(["formatted_symbol", "transact_time"], kind="mergesort")
    first_seen = out.groupby("formatted_symbol", sort=False)["trading_dt"].min()
    legacy = set(first_seen[first_seen <= acquisition_start].index)
    out["series_history_state"] = np.where(
        out["formatted_symbol"].isin(legacy),
        "LEGACY_PREEXISTING_QUARANTINED",
        "COMPLETE_FROM_FIRST_OBSERVED_TRADE",
    )
    out["omm_net_contracts"] = out.groupby("formatted_symbol", sort=False)["signed_mm_contracts"].cumsum()
    out["analysis_eligible"] = (out["trading_dt"] >= analysis_start) & ~out["formatted_symbol"].isin(legacy)
    return out.reset_index(drop=True), {
        "schema": "warroom.v72_position_only_reconstruction_diagnostics",
        "status": "PASS",
        "series": int(first_seen.size),
        "legacy_series_quarantined": int(len(legacy)),
        "position_rule": "MM buy +size; MM sell -size; cumulative by exact formatted_symbol",
        "gamma_mark_source": "MANDATORY_COMPLETE_ONE_MINUTE_OPTION_QUOTES_CALCS",
        "trade_grk_surface_substitute": False,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }


def validate_option_quotes(quotes: pd.DataFrame) -> pd.DataFrame:
    _require_columns(quotes, QUOTE_REQUIRED, "QUOTES")
    out = quotes.loc[:, list(QUOTE_REQUIRED)].copy()
    out["quote_datetime"] = _as_utc(out["quote_datetime"], "QUOTES.quote_datetime")
    out["trading_dt"] = out["quote_datetime"].dt.tz_convert("America/New_York").dt.date
    out["expiration"] = _as_date(out["expiration"], "QUOTES.expiration")
    numeric = [
        "strike", "bid_size", "bid", "ask_size", "ask", "open_interest", "active_underlying_price",
        "implied_volatility", "delta", "gamma", "theta", "vega", "rho",
    ]
    out = _numeric(out, numeric, "QUOTES")
    out["underlying_symbol"] = out["underlying_symbol"].astype(str).str.strip().str.upper()
    out["root"] = out["root"].astype(str).str.strip().str.upper()
    out["option_type"] = out["option_type"].astype(str).str.strip().str.upper().str[0]
    if not set(out["underlying_symbol"]).issubset({"SPX", "^SPX"}):
        raise V72DataError("QUOTES contains non-SPX underlying")
    if not set(out["root"]).issubset(ALLOWED_ROOTS):
        raise V72DataError("QUOTES contains unsupported root")
    if not set(out["option_type"]).issubset({"C", "P"}):
        raise V72DataError("QUOTES option_type must be C or P")
    if (out[["strike", "active_underlying_price"]] <= 0).any().any():
        raise V72DataError("QUOTES strike/underlying price must be positive")
    if (out[["bid_size", "ask_size"]] < 0).any().any() or (out[["bid", "ask"]] < 0).any().any():
        raise V72DataError("QUOTES negative quote value")
    if (out["open_interest"] < 0).any():
        raise V72DataError("QUOTES open_interest must be non-negative")
    if (out["ask"] < out["bid"]).any():
        raise V72DataError("QUOTES crossed NBBO")
    if (out["gamma"] < 0).any() or (out["implied_volatility"] <= 0).any():
        raise V72DataError("QUOTES gamma/IV constraints violated")
    out["formatted_symbol"] = (
        out["root"]
        + pd.to_datetime(out["expiration"]).dt.strftime("%y%m%d")
        + out["option_type"]
        + out["strike"].map(_format_strike)
    )
    keys = ["quote_datetime", "formatted_symbol"]
    if out.duplicated(keys, keep=False).any():
        raise V72DataError("QUOTES duplicate series-minute rows")
    return out.sort_values(["quote_datetime", "formatted_symbol"], kind="mergesort").reset_index(drop=True)


def aggregate_quote_surface_exposure(position_events: pd.DataFrame, quotes: pd.DataFrame,
                                     liquidity: pd.DataFrame, *,
                                     acquisition_start: date = date(2019, 10, 7),
                                     analysis_start: date = date(2020, 7, 1),
                                     liquidity_tolerance_seconds: int = 60) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Mark every active series position on the complete one-minute quote surface."""
    pos = reconstruct_positions_from_tbt(position_events, acquisition_start=acquisition_start, analysis_start=analysis_start)[0] if "omm_net_contracts" not in position_events.columns else position_events.copy()
    q = validate_option_quotes(quotes)
    liq = validate_underlier(liquidity)

    # Determine quote-surface inception. A series visible on the first acquisition date is legacy
    # unless its TBT history proves later inception; these rows are quarantined through expiry.
    quote_first = q.groupby("formatted_symbol", sort=False)["trading_dt"].min()
    legacy_quote = set(quote_first[quote_first <= acquisition_start].index)
    complete_from_tbt = set(pos.loc[pos["series_history_state"].eq("COMPLETE_FROM_FIRST_OBSERVED_TRADE"), "formatted_symbol"])
    legacy_quote -= complete_from_tbt

    pos_state = pos[["formatted_symbol", "transact_time", "omm_net_contracts", "series_history_state"]].copy()
    pos_state = pos_state.sort_values(["transact_time", "formatted_symbol"], kind="mergesort")
    q_sorted = q.sort_values(["quote_datetime", "formatted_symbol"], kind="mergesort")
    marked = pd.merge_asof(
        q_sorted,
        pos_state,
        left_on="quote_datetime",
        right_on="transact_time",
        by="formatted_symbol",
        direction="backward",
        allow_exact_matches=True,
    )
    # A complete series with no prior market-maker trade has position zero. Legacy series are not inferred.
    marked["series_history_state"] = marked["series_history_state"].fillna(
        pd.Series(np.where(marked["formatted_symbol"].isin(legacy_quote), "LEGACY_PREEXISTING_QUARANTINED", "COMPLETE_NO_MM_FLOW_YET"), index=marked.index)
    )
    zero_ok = ~marked["formatted_symbol"].isin(legacy_quote)
    marked.loc[zero_ok & marked["omm_net_contracts"].isna(), "omm_net_contracts"] = 0.0
    marked["analysis_eligible"] = (
        (marked["trading_dt"] >= analysis_start)
        & ~marked["formatted_symbol"].isin(legacy_quote)
        & marked["omm_net_contracts"].notna()
    )
    eligible = marked[marked["analysis_eligible"]].copy()
    if eligible.empty:
        raise V72DataError("no eligible full-surface quote rows")

    liq = liq.rename(columns={"transact_time": "liquidity_time"}).sort_values("liquidity_time", kind="mergesort")
    eligible = eligible.sort_values("quote_datetime", kind="mergesort")
    eligible = pd.merge_asof(
        eligible,
        liq,
        left_on="quote_datetime",
        right_on="liquidity_time",
        by="trading_dt",
        direction="backward",
        tolerance=pd.Timedelta(seconds=liquidity_tolerance_seconds),
    )
    if eligible[["es_traded_notional", "es_depth_notional"]].isna().any().any():
        raise V72DataError("liquidity join incomplete for quote surface")
    # Use the option-surface active underlying price for Greek notional alignment.
    eligible["dollar_gamma_per_1pct"] = (
        eligible["omm_net_contracts"] * CONTRACT_MULTIPLIER * eligible["gamma"]
        * eligible["active_underlying_price"] ** 2 * 0.01
    )
    eligible["abs_dollar_gamma_per_1pct"] = eligible["dollar_gamma_per_1pct"].abs()
    eligible["oi_abs_dollar_gamma_per_1pct"] = (
        eligible["open_interest"] * CONTRACT_MULTIPLIER * eligible["gamma"].abs()
        * eligible["active_underlying_price"] ** 2 * 0.01
    )
    minute = eligible.groupby(["trading_dt", "quote_datetime"], as_index=False).agg(
        signed_omm_gamma=("dollar_gamma_per_1pct", "sum"),
        gross_omm_gamma=("abs_dollar_gamma_per_1pct", "sum"),
        unsigned_gamma_magnitude=("oi_abs_dollar_gamma_per_1pct", "sum"),
        max_series_unsigned_gamma=("oi_abs_dollar_gamma_per_1pct", "max"),
        marked_series=("formatted_symbol", "nunique"),
        active_underlying_price=("active_underlying_price", "median"),
        es_traded_notional=("es_traded_notional", "median"),
        es_depth_notional=("es_depth_notional", "median"),
    )
    minute["gross_oi_topology"] = np.where(
        minute["unsigned_gamma_magnitude"] > 0,
        minute["max_series_unsigned_gamma"] / minute["unsigned_gamma_magnitude"],
        0.0,
    )
    minute["gamma_to_depth"] = minute["signed_omm_gamma"] / minute["es_depth_notional"]
    minute["gamma_to_traded_notional"] = minute["signed_omm_gamma"] / minute["es_traded_notional"]
    minute["hedge_regime"] = np.where(minute["signed_omm_gamma"] > 0, "DAMPING_CONTEXT", np.where(minute["signed_omm_gamma"] < 0, "AMPLIFICATION_CONTEXT", "NEUTRAL_CONTEXT"))
    minute["standalone_direction"] = "WITHHELD"
    minute["live_decision_weight"] = 0.0
    minute["capital_permission"] = "BLOCKED"
    coverage = float(eligible["formatted_symbol"].nunique() / max(1, q[~q["formatted_symbol"].isin(legacy_quote)]["formatted_symbol"].nunique()))
    diag = {
        "schema": "warroom.v72_full_quote_surface_exposure_diagnostics",
        "status": "PASS",
        "quote_rows": int(len(q)),
        "eligible_quote_rows": int(len(eligible)),
        "minutes": int(len(minute)),
        "marked_series": int(eligible["formatted_symbol"].nunique()),
        "legacy_quote_series_quarantined": int(len(legacy_quote)),
        "series_mark_coverage": coverage,
        "trade_level_grk_used_as_surface": False,
        "surface_source": "ONE_MINUTE_OPTION_QUOTES_WITH_CALCS_AND_OPEN_INTEREST",
        "gross_open_interest_used_only_as_unsigned_baseline": True,
        "standalone_direction": "WITHHELD",
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    return minute, diag

def validate_underlier(underlier: pd.DataFrame) -> pd.DataFrame:
    _require_columns(underlier, UNDERLIER_REQUIRED, "UNDERLIER")
    out = underlier.loc[:, list(UNDERLIER_REQUIRED)].copy()
    out["transact_time"] = _as_utc(out["transact_time"], "UNDERLIER.transact_time")
    out["trading_dt"] = _as_date(out["trading_dt"], "UNDERLIER.trading_dt")
    out = _numeric(out, ["spot", "es_traded_notional", "es_depth_notional"], "UNDERLIER")
    if (out[["spot", "es_traded_notional", "es_depth_notional"]] <= 0).any().any():
        raise V72DataError("UNDERLIER values must be positive")
    if out.duplicated(["trading_dt", "transact_time"], keep=False).any():
        raise V72DataError("UNDERLIER duplicate timestamps")
    return out.sort_values("transact_time", kind="mergesort").reset_index(drop=True)


def aggregate_exposure(positions: pd.DataFrame, underlier: pd.DataFrame, *, tolerance_seconds: int = 60) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Legacy trade-time diagnostic only; not valid as aggregate minute-level dealer gamma.

    Production V72 research must call aggregate_quote_surface_exposure.
    """
    pos = positions[positions["analysis_eligible"]].copy().sort_values("transact_time", kind="mergesort")
    und = validate_underlier(underlier).sort_values("transact_time", kind="mergesort")
    if pos.empty:
        raise V72DataError("no analysis-eligible position rows")
    merged = pd.merge_asof(
        pos,
        und.rename(columns={"transact_time": "underlier_time"}),
        left_on="transact_time",
        right_on="underlier_time",
        by="trading_dt",
        direction="backward",
        tolerance=pd.Timedelta(seconds=tolerance_seconds),
    )
    if merged["spot"].isna().any():
        raise V72DataError("underlier join incomplete")
    merged["dollar_gamma_per_1pct"] = merged["omm_net_contracts"] * CONTRACT_MULTIPLIER * merged["gamma"] * merged["spot"] ** 2 * 0.01
    merged["abs_dollar_gamma_per_1pct"] = merged["dollar_gamma_per_1pct"].abs()

    minute = merged["transact_time"].dt.floor("min")
    merged["minute"] = minute
    # Position exposure is a state. Keep the last state per series per minute, then sum across series.
    state = merged.sort_values("transact_time", kind="mergesort").groupby(["trading_dt", "minute", "formatted_symbol"], as_index=False).tail(1)
    aggregates = state.groupby(["trading_dt", "minute"], as_index=False).agg(
        signed_omm_gamma=("dollar_gamma_per_1pct", "sum"),
        gross_omm_gamma=("abs_dollar_gamma_per_1pct", "sum"),
        active_series=("formatted_symbol", "nunique"),
        spot=("spot", "median"),
        es_traded_notional=("es_traded_notional", "median"),
        es_depth_notional=("es_depth_notional", "median"),
    )
    aggregates["gamma_to_depth"] = aggregates["signed_omm_gamma"] / aggregates["es_depth_notional"]
    aggregates["gamma_to_traded_notional"] = aggregates["signed_omm_gamma"] / aggregates["es_traded_notional"]
    aggregates["hedge_regime"] = np.where(aggregates["signed_omm_gamma"] > 0, "DAMPING_CONTEXT", np.where(aggregates["signed_omm_gamma"] < 0, "AMPLIFICATION_CONTEXT", "NEUTRAL_CONTEXT"))
    aggregates["standalone_direction"] = "WITHHELD"
    aggregates["live_decision_weight"] = 0.0
    aggregates["capital_permission"] = "BLOCKED"
    diagnostics = {
        "schema": "warroom.v72_exposure_aggregation_diagnostics",
        "status": "PASS",
        "minutes": int(len(aggregates)),
        "dates": int(aggregates["trading_dt"].nunique()),
        "active_series_max": int(aggregates["active_series"].max()),
        "signed_gamma_min": float(aggregates["signed_omm_gamma"].min()),
        "signed_gamma_max": float(aggregates["signed_omm_gamma"].max()),
        "standalone_direction": "WITHHELD",
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    return aggregates, diagnostics


def read_single_csv_or_zip(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv") and not n.startswith("__MACOSX/")]
            if len(names) != 1:
                raise V72DataError(f"{path.name} must contain exactly one CSV")
            info = z.getinfo(names[0])
            if info.file_size > 20_000_000_000:
                raise V72DataError("source CSV exceeds safety limit")
            if Path(names[0]).is_absolute() or ".." in Path(names[0]).parts:
                raise V72DataError("unsafe ZIP member")
            with z.open(info) as f:
                return pd.read_csv(f)
    return pd.read_csv(path)


def research_status(*, licensed_data_present: bool, historical_outcomes_evaluated: bool,
                    prospective_observations: int = 0) -> dict[str, Any]:
    if not licensed_data_present:
        state = "DATA_LICENSE_REQUIRED"
    elif not historical_outcomes_evaluated:
        state = "READY_TO_EVALUATE_FROZEN_PROTOCOL"
    else:
        state = "EVALUATED_SEE_FROZEN_RESULTS"
    return {
        "schema": "warroom.v72_signed_dealer_research_status",
        "status": state,
        "protocol_sha256": protocol_sha256(),
        "historical_edge": "NOT_EVALUATED" if not historical_outcomes_evaluated else "SEE_RESULTS",
        "prospective_observations": int(prospective_observations),
        "prospective_profitability": "NOT_MATURED" if prospective_observations < 1000 else "ELIGIBLE_FOR_FROZEN_EVALUATION",
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
