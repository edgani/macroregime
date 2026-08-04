"""Assemble the full proven-meters snapshot for the decision surface.

Fetches every required series, computes GROWTH/INFL/TILT/GOLD/DOLLAR/DURATION/
FEAR-ENTRY/BCM/FRAGILITY/R2, and reports per-meter status honestly. Any source
failure degrades the affected meter only; nothing is imputed.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from eros.meters.engines import (
    MeterReading,
    _as_of,
    _latest,
    bcm_stress,
    dollar_meter,
    fear_entry_signal,
    fragility,
    gold_meter,
    growth_index,
    inflation_index,
    r2_exposure_state,
    spx_realized_vol,
    tilt_weights,
)
from eros.meters.fred import PUBLICATION_LAG_DAYS, fetch_many
from eros.meters.transforms import apply_publication_lag, expanding_pct

RequestBytes = Callable[[str], bytes]

FRED_SERIES = [
    "CFNAI",
    "NEWORDER",
    "UNRATE",
    "ICSA",
    "CPIAUCSL",
    "DCOILWTICO",
    "T5YIFR",
    "DFII10",
    "M2SL",
    "DRCLACBS",
    "NFCI",
    "EVZCLS",
    "FEDFUNDS",
    "T10Y3M",
    "STLFSI4",
    "KCFSI",
    "BAA10Y",
    "DRTSCILM",
    "VIXCLS",
    "BOGZ1FL893064105Q",
    "GDP",
    "SP500",
]

SHILLER_URL = "https://www.econ.yale.edu/~shiller/data/ie_data.xls"
ACM_URL = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"


class MetersSnapshot(BaseModel):
    """Everything the decision surface needs from the proven engines."""

    fetched_at: str
    growth: MeterReading
    inflation: MeterReading
    tilt: dict[str, float] = Field(default_factory=dict)
    gold: MeterReading
    dollar: MeterReading
    duration: MeterReading
    bcm: MeterReading
    fragility_reading: MeterReading
    exposure: float | None
    fear_entry: bool | None
    blocks: dict[str, float] = Field(default_factory=dict)
    failures: dict[str, str] = Field(default_factory=dict)
    checksum_status: Literal["UNVERIFIED_PORT", "MATCH", "DIFFERS"] = "UNVERIFIED_PORT"
    checksum_note: str = ""


def _reading(
    meter_id: str,
    label: str,
    series: pd.Series,
    evidence: str,
    required: list[str],
    failures: dict[str, str],
    note: str = "",
) -> MeterReading:
    missing = [name for name in required if name in failures]
    status: Literal["LIVE", "PARTIAL", "NO_DATA"]
    value = _latest(series)
    if value is None:
        status = "NO_DATA"
    elif missing:
        status = "PARTIAL"
    else:
        status = "LIVE"
    return MeterReading(
        meter_id=meter_id,
        label=label,
        value=value,
        status=status,
        components={},
        missing=missing,
        as_of=_as_of(series) or "NO_DATA",
        evidence=evidence,
        note=note,
    )


BCM_REFERENCE = 0.388
GOLD_REFERENCE = 0.966
CHECKSUM_TOLERANCE = 0.03


def checksum_verdict(
    bcm_value: float | None,
    gold_value: float | None,
    *,
    bcm_blocked: bool,
) -> tuple[Literal["UNVERIFIED_PORT", "MATCH", "DIFFERS"], str]:
    """Pure checksum verdict: MATCH only from a complete, unblocked BCM read."""

    if bcm_value is None:
        return "UNVERIFIED_PORT", "No live BCM value; checksum not evaluated."
    if bcm_blocked:
        return (
            "UNVERIFIED_PORT",
            (
                f"BCM port {bcm_value:.4f} computed from degraded components "
                "(cache/failures present) — checksum not claimed."
            ),
        )
    delta = abs(bcm_value - BCM_REFERENCE)
    status: Literal["UNVERIFIED_PORT", "MATCH", "DIFFERS"] = (
        "MATCH" if delta <= CHECKSUM_TOLERANCE else "DIFFERS"
    )
    gold_text = f"{gold_value:.4f}" if gold_value is not None else "NO_DATA"
    return status, (
        f"BCM port {bcm_value:.4f} vs research reference {BCM_REFERENCE:.3f} "
        f"(July 2026): delta {delta:.4f}, tolerance {CHECKSUM_TOLERANCE}. "
        f"Gold Meter port {gold_text} vs reference {GOLD_REFERENCE}."
    )


def _fetch_shiller_cape(request: RequestBytes) -> pd.Series | None:
    """Compute CAPE from Shiller's public workbook; None when unavailable."""

    try:
        payload = request(SHILLER_URL)
        frame = pd.read_excel(io.BytesIO(payload), sheet_name="Data", skiprows=7)
        frame = frame.rename(columns={frame.columns[0]: "date"})
        frame = frame[["date", "P", "E", "CPI"]].dropna()
        frame["date"] = pd.to_datetime(frame["date"].astype(str), format="%Y.%m", errors="coerce")
        frame = frame.dropna(subset=["date"])
        real_price = frame["P"].astype(float) / frame["CPI"].astype(float)
        real_earnings = frame["E"].astype(float) / frame["CPI"].astype(float)
        cape = real_price / real_earnings.rolling(120, min_periods=120).mean()
        return pd.Series(
            cape.to_numpy(),
            index=pd.DatetimeIndex(frame["date"], name="date"),
            name="CAPE",
        ).dropna()
    except Exception:
        return None


def _fetch_acm_term_premium(request: RequestBytes) -> pd.Series | None:
    """NY Fed ACM 10Y term premium; None when unavailable."""

    try:
        payload = request(ACM_URL)
        frame = pd.read_excel(io.BytesIO(payload))
        date_col = next(col for col in frame.columns if "DATE" in str(col).upper())
        tp_col = next(col for col in frame.columns if "ACMTP10" in str(col).upper())
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
        frame = frame.dropna(subset=[date_col])
        return pd.Series(
            pd.to_numeric(frame[tp_col], errors="coerce").to_numpy(),
            index=pd.DatetimeIndex(frame[date_col], name="date"),
            name="ACMTP10",
        ).dropna()
    except Exception:
        return None


def compute_meters_snapshot(
    *,
    request: RequestBytes | None = None,
    now: datetime | None = None,
) -> MetersSnapshot:
    """Compute every proven meter from live sources with explicit status."""

    from eros.meters.fred import _default_request

    req = request or _default_request
    fetched_at = now or datetime.now(UTC)
    series, failures = fetch_many(FRED_SERIES, request=req)
    lags = PUBLICATION_LAG_DAYS

    def need(sid: str) -> pd.Series:
        if sid not in series:
            failures.setdefault(sid, "fetch failed")
            return pd.Series(dtype="float64")
        return series[sid]

    growth = growth_index(need("CFNAI"), need("NEWORDER"), need("UNRATE"), need("ICSA"), lags)
    infl = inflation_index(need("CPIAUCSL"), need("DCOILWTICO"), need("T5YIFR"), lags)
    tilt_frame = tilt_weights(growth, infl)
    tilt = (
        {name: float(tilt_frame[name].iloc[-1]) for name in tilt_frame.columns}
        if not tilt_frame.empty
        else {}
    )

    gold = gold_meter(need("DFII10"), need("M2SL"), need("DRCLACBS"), lags)
    dollar = dollar_meter(need("NFCI"), need("EVZCLS"), need("FEDFUNDS"), infl, lags)

    acm = _fetch_acm_term_premium(req)
    duration_series = pd.Series(dtype="float64") if acm is None else expanding_pct(acm)
    if acm is None:
        failures["ACMTP10"] = "NY Fed ACM workbook unavailable"

    fear = fear_entry_signal(need("VIXCLS"), infl, lags)
    fear_value = bool(fear.iloc[-1]) if not fear.dropna().empty else None

    spx = need("SP500")
    rv21 = spx_realized_vol(spx) if not spx.empty else pd.Series(dtype="float64")
    blocks_frame = bcm_stress(
        need("FEDFUNDS"),
        need("T10Y3M"),
        need("NFCI"),
        need("STLFSI4"),
        need("KCFSI"),
        need("BAA10Y"),
        need("DRCLACBS"),
        need("DRTSCILM"),
        growth,
        need("M2SL"),
        rv21,
        need("VIXCLS"),
        lags,
    )
    bcm_series = blocks_frame["BCM"] if "BCM" in blocks_frame else pd.Series(dtype="float64")
    blocks = (
        {name: float(blocks_frame[name].iloc[-1]) for name in blocks_frame.columns if name != "BCM"}
        if not blocks_frame.empty
        else {}
    )

    buffett = pd.Series(dtype="float64")
    if "BOGZ1FL893064105Q" in series and "GDP" in series and not series["GDP"].empty:
        equities = series["BOGZ1FL893064105Q"]
        gdp = series["GDP"].reindex(equities.index).ffill()
        # Align on reference dates first, then shift the finished ratio by the
        # slowest component's publication lag.
        buffett = apply_publication_lag(equities / gdp, lags.get("BOGZ1FL893064105Q", 0))
    else:
        failures.setdefault("BUFFETT", "market cap or GDP series unavailable")
    cape = _fetch_shiller_cape(req)
    if cape is not None:
        cape = apply_publication_lag(cape, 14)
    else:
        failures.setdefault("CAPE", "Shiller workbook unavailable; FRAGILITY is Buffett-only")
    frag_series, _frag_status = fragility(buffett, cape)

    exposure_series = r2_exposure_state(bcm_series, frag_series)
    exposure = _latest(exposure_series)

    bcm_components = [
        "FEDFUNDS", "T10Y3M", "NFCI", "STLFSI4", "KCFSI", "BAA10Y",
        "DRCLACBS", "DRTSCILM", "M2SL", "SP500", "VIXCLS",
        # GROWTH feeds the REAL block; a growth-input failure must void the checksum.
        "CFNAI", "NEWORDER", "UNRATE", "ICSA",
    ]
    checksum_status, checksum_note = checksum_verdict(
        _latest(bcm_series),
        _latest(gold),
        bcm_blocked=any(name in failures for name in bcm_components),
    )

    return MetersSnapshot(
        fetched_at=(
            fetched_at.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        ),
        growth=_reading(
            "GROWTH", "Economic growth composite", growth, "PROVEN_CONTEXT",
            ["CFNAI", "NEWORDER", "UNRATE", "ICSA"], failures,
        ),
        inflation=_reading(
            "INFL", "Inflation pressure composite", infl, "PROVEN_CONTEXT",
            ["CPIAUCSL", "DCOILWTICO", "T5YIFR"], failures,
        ),
        tilt=tilt,
        gold=_reading(
            "GOLD", "Gold Meter v2", gold, "PROVEN", ["DFII10", "M2SL", "DRCLACBS"], failures,
        ),
        dollar=_reading(
            "DOLLAR", "Dollar Meter v1", dollar, "PROVEN", ["NFCI", "EVZCLS", "FEDFUNDS"],
            failures,
        ),
        duration=_reading(
            "DURATION", "Duration Dial (ACM term premium)", duration_series, "PROVEN",
            ["ACMTP10"], failures,
        ),
        bcm=_reading(
            "BCM", "BCM v3.2 stress axis", bcm_series, "PROVEN_SCOPE_LIMITED",
            [
                "FEDFUNDS", "T10Y3M", "NFCI", "STLFSI4", "KCFSI", "BAA10Y", "DRCLACBS",
                "DRTSCILM", "M2SL", "SP500", "VIXCLS",
            ],
            failures,
            note="Port from sealed formula; checksum against research reference pending",
        ),
        fragility_reading=_reading(
            "FRAGILITY", "Fragility axis (Buffett x CAPE)", frag_series,
            "PROVEN_SCOPE_LIMITED",
            ["BUFFETT"] + ([] if cape is not None else ["CAPE"]), failures,
        ),
        exposure=exposure,
        fear_entry=fear_value,
        blocks=blocks,
        failures=failures,
        checksum_status=checksum_status,
        checksum_note=checksum_note,
    )
