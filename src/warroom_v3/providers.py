from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener
import json

from .data import OHLCVBar
from .hashing import canonical_hash


class RetrievalMode(str, Enum):
    BOOTSTRAP = "BOOTSTRAP"
    PROSPECTIVE = "PROSPECTIVE"
    MANUAL_PIT = "MANUAL_PIT"


class ProviderStatus(str, Enum):
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ProviderApproval:
    provider_id: str
    adapter_type: str
    status: ProviderStatus
    approved_modes: tuple[RetrievalMode, ...]
    allowed_hosts: tuple[str, ...]
    allowed_assets: tuple[str, ...]
    allowed_timeframes: tuple[str, ...]
    venue: str
    max_response_bytes: int = 8_000_000
    max_rows_per_request: int = 1000
    publication_lag_seconds: int = 0
    notes: tuple[str, ...] = ()

    def authorize(self, *, mode: RetrievalMode, asset: str, timeframe: str, venue: str, source_uri: str | None = None) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if self.status != ProviderStatus.APPROVED:
            reasons.append(f"PROVIDER_NOT_APPROVED:{self.status.value}")
        if mode not in self.approved_modes:
            reasons.append(f"MODE_NOT_APPROVED:{mode.value}")
        if not any(fnmatchcase(asset, pattern) for pattern in self.allowed_assets):
            reasons.append(f"ASSET_NOT_APPROVED:{asset}")
        if timeframe not in self.allowed_timeframes:
            reasons.append(f"TIMEFRAME_NOT_APPROVED:{timeframe}")
        if venue != self.venue:
            reasons.append(f"VENUE_MISMATCH:{venue}")
        if source_uri and self.allowed_hosts:
            host = (urlparse(source_uri).hostname or "").lower()
            if host not in {h.lower() for h in self.allowed_hosts}:
                reasons.append(f"HOST_NOT_APPROVED:{host}")
        return not reasons, tuple(reasons)


@dataclass(frozen=True)
class ProviderRegistry:
    registry_id: str
    records: tuple[ProviderApproval, ...]

    @classmethod
    def load(cls, path: str | Path) -> "ProviderRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        records = []
        for row in payload["records"]:
            records.append(ProviderApproval(
                provider_id=row["provider_id"], adapter_type=row["adapter_type"],
                status=ProviderStatus(row["status"]),
                approved_modes=tuple(RetrievalMode(v) for v in row["approved_modes"]),
                allowed_hosts=tuple(row.get("allowed_hosts", [])),
                allowed_assets=tuple(row["allowed_assets"]),
                allowed_timeframes=tuple(row["allowed_timeframes"]),
                venue=row["venue"], max_response_bytes=int(row.get("max_response_bytes", 8_000_000)),
                max_rows_per_request=int(row.get("max_rows_per_request", 1000)),
                publication_lag_seconds=int(row.get("publication_lag_seconds", 0)),
                notes=tuple(row.get("notes", [])),
            ))
        obj = cls(registry_id=payload["registry_id"], records=tuple(records))
        if payload.get("registry_hash") != obj.snapshot_hash:
            raise ValueError("provider registry hash mismatch")
        if len({r.provider_id for r in obj.records}) != len(obj.records):
            raise ValueError("duplicate provider_id")
        return obj

    @property
    def snapshot_hash(self) -> str:
        rows=[]
        for r in self.records:
            row=asdict(r)
            row["status"]=r.status.value
            row["approved_modes"]=[m.value for m in r.approved_modes]
            rows.append(row)
        return canonical_hash(rows)

    def get(self, provider_id: str) -> ProviderApproval:
        for record in self.records:
            if record.provider_id == provider_id:
                return record
        raise KeyError(provider_id)


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class HTTPResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


class HTTPTransport(Protocol):
    def get(self, url: str, *, timeout_seconds: float, max_bytes: int, allowed_hosts: tuple[str, ...]) -> HTTPResponse: ...


class UrllibTransport:
    def get(self, url: str, *, timeout_seconds: float, max_bytes: int, allowed_hosts: tuple[str, ...]) -> HTTPResponse:
        parsed=urlparse(url)
        allowed={h.lower() for h in allowed_hosts}
        if parsed.scheme != "https":
            raise ProviderError("ONLY_HTTPS_ALLOWED")
        if (parsed.hostname or "").lower() not in allowed:
            raise ProviderError("HOST_NOT_ALLOWLISTED")
        req=Request(url, headers={"User-Agent":"WarRoomOS-v3/ResearchCollector", "Accept":"application/json"})
        try:
            with build_opener().open(req, timeout=timeout_seconds) as response:
                final_url=response.geturl()
                if (urlparse(final_url).hostname or "").lower() not in allowed:
                    raise ProviderError("REDIRECT_HOST_NOT_ALLOWLISTED")
                status=int(getattr(response,"status",200))
                if status != 200:
                    raise ProviderError(f"HTTP_STATUS:{status}")
                body=response.read(max_bytes+1)
                if len(body)>max_bytes:
                    raise ProviderError("RESPONSE_TOO_LARGE")
                return HTTPResponse(final_url,status,{k.lower():v for k,v in response.headers.items()},body)
        except HTTPError as exc:
            raise ProviderError(f"HTTP_ERROR:{exc.code}") from exc
        except URLError as exc:
            raise ProviderError(f"NETWORK_ERROR:{exc.reason}") from exc


_TIMEFRAME_SECONDS={"15m":900,"1h":3600,"4h":14400,"1d":86400}


@dataclass(frozen=True)
class ProviderPayload:
    provider_id: str
    source_uri: str
    fetched_at: datetime
    raw: bytes
    metadata: Mapping[str,str]


@dataclass(frozen=True)
class BinanceSpotProvider:
    transport: HTTPTransport = UrllibTransport()
    provider_id: str = "BINANCE_SPOT_PUBLIC_KLINES_V1"
    base_url: str = "https://data-api.binance.vision"
    venue: str = "BINANCE_SPOT"

    def fetch_latest(self, *, asset: str, timeframe: str, limit: int, approval: ProviderApproval, end_at: datetime | None = None, mode: RetrievalMode = RetrievalMode.BOOTSTRAP) -> ProviderPayload:
        if timeframe not in _TIMEFRAME_SECONDS:
            raise ProviderError(f"UNSUPPORTED_TIMEFRAME:{timeframe}")
        if not 1 <= limit <= approval.max_rows_per_request:
            raise ProviderError("INVALID_LIMIT")
        params={"symbol":asset.upper(),"interval":timeframe,"limit":str(limit),"timeZone":"0"}
        if end_at is not None:
            if end_at.tzinfo is None or end_at.utcoffset() is None:
                raise ProviderError("END_AT_MUST_BE_AWARE")
            params["endTime"]=str(int(end_at.timestamp()*1000)-1)
        url=f"{self.base_url}/api/v3/klines?{urlencode(params)}"
        ok,reasons=approval.authorize(mode=mode,asset=asset,timeframe=timeframe,venue=self.venue,source_uri=url)
        if not ok:
            raise ProviderError(";".join(reasons))
        fetched=datetime.now(timezone.utc)
        response=self.transport.get(url,timeout_seconds=15,max_bytes=approval.max_response_bytes,allowed_hosts=approval.allowed_hosts)
        return ProviderPayload(self.provider_id,response.url,fetched,response.body,{
            "http_status":str(response.status),"content_type":response.headers.get("content-type",""),
            "used_weight_1m":response.headers.get("x-mbx-used-weight-1m","")})

    def normalize(self, payload: ProviderPayload, *, asset: str, timeframe: str, as_of: datetime | None = None) -> list[OHLCVBar]:
        try:
            rows=json.loads(payload.raw)
        except json.JSONDecodeError as exc:
            raise ProviderError("INVALID_JSON") from exc
        if not isinstance(rows,list):
            raise ProviderError("UNEXPECTED_PAYLOAD")
        cutoff=as_of or payload.fetched_at
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ProviderError("AS_OF_MUST_BE_AWARE")
        bars=[]
        for row in rows:
            if not isinstance(row,list) or len(row)<7:
                raise ProviderError("INVALID_KLINE_ROW")
            close_at=datetime.fromtimestamp((int(row[6])+1)/1000,tz=timezone.utc)
            if close_at>cutoff:
                continue
            open_at=datetime.fromtimestamp(int(row[0])/1000,tz=timezone.utc)
            bars.append(OHLCVBar(
                asset=asset.upper(), timeframe=timeframe, observed_at=close_at, available_at=close_at,
                ingested_at=payload.fetched_at, open=float(row[1]), high=float(row[2]), low=float(row[3]),
                close=float(row[4]), volume=float(row[5]),
                source_record_id=f"{asset.upper()}:{timeframe}:{int(row[0])}", revision_id="0",
            ))
            if open_at >= close_at:
                raise ProviderError("INVALID_KLINE_BOUNDARY")
        if not bars:
            raise ProviderError("NO_FINALIZED_BARS")
        return sorted(bars,key=lambda b:b.observed_at)
