from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable
import csv, math

from .hashing import canonical_hash, file_hash


class EvidenceTier(str, Enum):
    UNIT_FIXTURE = "UNIT_FIXTURE"
    DEVELOPMENT = "DEVELOPMENT"
    EXTERNAL_HISTORICAL = "EXTERNAL_HISTORICAL"
    SEALED_HIDDEN = "SEALED_HIDDEN"
    PROSPECTIVE = "PROSPECTIVE"


class ClaimCeiling(str, Enum):
    ENGINEERING_ONLY = "ENGINEERING_ONLY"
    DEVELOPMENT_ONLY = "DEVELOPMENT_ONLY"
    EXTERNAL_HISTORICAL_ONLY = "EXTERNAL_HISTORICAL_ONLY"
    SEALED_HIDDEN_ELIGIBLE = "SEALED_HIDDEN_ELIGIBLE"
    PROSPECTIVE_ELIGIBLE = "PROSPECTIVE_ELIGIBLE"


class RevisionPolicy(str, Enum):
    IMMUTABLE = "IMMUTABLE"
    VINTAGE = "VINTAGE"
    LATEST_ONLY = "LATEST_ONLY"


_TIER_CEILING = {
    EvidenceTier.UNIT_FIXTURE: ClaimCeiling.ENGINEERING_ONLY,
    EvidenceTier.DEVELOPMENT: ClaimCeiling.DEVELOPMENT_ONLY,
    EvidenceTier.EXTERNAL_HISTORICAL: ClaimCeiling.EXTERNAL_HISTORICAL_ONLY,
    EvidenceTier.SEALED_HIDDEN: ClaimCeiling.SEALED_HIDDEN_ELIGIBLE,
    EvidenceTier.PROSPECTIVE: ClaimCeiling.PROSPECTIVE_ELIGIBLE,
}


def parse_utc(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class OHLCVBar:
    asset: str
    timeframe: str
    observed_at: datetime
    available_at: datetime
    ingested_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source_record_id: str
    revision_id: str = "0"

    def __post_init__(self) -> None:
        for name in ("asset", "timeframe", "source_record_id", "revision_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("observed_at", "available_at", "ingested_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.ingested_at < self.available_at:
            raise ValueError("ingested_at cannot precede available_at")
        values = [self.open, self.high, self.low, self.close]
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("OHLC must be finite and positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close) or self.high < self.low:
            raise ValueError("impossible OHLC geometry")
        if self.volume is not None and (not math.isfinite(self.volume) or self.volume < 0):
            raise ValueError("volume must be finite and non-negative")

    def canonical_record(self) -> dict:
        out = asdict(self)
        for key in ("observed_at", "available_at", "ingested_at"):
            out[key] = getattr(self, key).astimezone(timezone.utc).isoformat()
        return out


@dataclass(frozen=True)
class DataQualityReport:
    accepted: bool
    rows: int
    reason_codes: tuple[str, ...] = ()
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    payload_hash: str | None = None


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    source_zip_sha256: str
    source_file: str
    source_file_sha256: str
    normalized_payload_sha256: str
    asset: str
    timeframe: str
    evidence_tier: EvidenceTier
    claim_ceiling: ClaimCeiling
    point_in_time_complete: bool
    revision_policy: RevisionPolicy
    burned_windows: tuple[tuple[str, str], ...] = ()
    allowed_uses: tuple[str, ...] = ()
    forbidden_uses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.claim_ceiling != _TIER_CEILING[self.evidence_tier]:
            raise ValueError("claim ceiling does not match evidence tier")
        if self.evidence_tier in (EvidenceTier.SEALED_HIDDEN, EvidenceTier.PROSPECTIVE):
            if not self.point_in_time_complete or self.revision_policy == RevisionPolicy.LATEST_ONLY:
                raise ValueError("hidden/prospective datasets require complete PIT semantics")

    @property
    def manifest_hash(self) -> str:
        payload = asdict(self)
        for key in ("evidence_tier", "claim_ceiling", "revision_policy"):
            payload[key] = getattr(self, key).value
        return canonical_hash(payload)


def validate_bars(bars: Iterable[OHLCVBar], *, as_of: datetime | None = None, require_volume: bool = False) -> DataQualityReport:
    seq = list(bars)
    reasons: list[str] = []
    if not seq:
        return DataQualityReport(False, 0, ("NO_ROWS",))
    assets = {b.asset for b in seq}; frames = {b.timeframe for b in seq}
    if len(assets) != 1: reasons.append("MIXED_ASSET")
    if len(frames) != 1: reasons.append("MIXED_TIMEFRAME")
    times = [b.observed_at for b in seq]
    if times != sorted(times): reasons.append("UNSORTED_TIMESTAMPS")
    if len(times) != len(set(times)): reasons.append("DUPLICATE_TIMESTAMPS")
    if require_volume and any(b.volume is None for b in seq): reasons.append("MISSING_REQUIRED_VOLUME")
    if as_of is not None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if any(b.available_at > as_of for b in seq): reasons.append("AS_OF_VIOLATION")
    payload_hash = canonical_hash([b.canonical_record() for b in seq])
    return DataQualityReport(
        accepted=not reasons,
        rows=len(seq),
        reason_codes=tuple(reasons),
        first_observed_at=min(times).astimezone(timezone.utc).isoformat(),
        last_observed_at=max(times).astimezone(timezone.utc).isoformat(),
        payload_hash=payload_hash,
    )


def load_canonical_csv(path: str | Path, *, ingested_at: datetime, as_of: datetime | None = None) -> tuple[list[OHLCVBar], DataQualityReport]:
    if ingested_at.tzinfo is None or ingested_at.utcoffset() is None:
        raise ValueError("ingested_at must be timezone-aware")
    bars: list[OHLCVBar] = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"asset","timeframe","observed_at","available_at","open","high","low","close","volume","source_record_id"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        for row in reader:
            volume = None if row["volume"].strip() == "" else float(row["volume"])
            bars.append(OHLCVBar(
                asset=row["asset"].strip(), timeframe=row["timeframe"].strip(),
                observed_at=parse_utc(row["observed_at"]), available_at=parse_utc(row["available_at"]),
                ingested_at=ingested_at, open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]), volume=volume,
                source_record_id=row["source_record_id"].strip(), revision_id=row.get("revision_id", "0").strip() or "0",
            ))
    return bars, validate_bars(bars, as_of=as_of)
