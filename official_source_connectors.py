"""Official-source connectors for point-in-time evidence collection.

These functions collect raw records and preserve publication/filing timestamps. They do not
construct signals, rankings or directions. Every connector fails closed when credentials,
identity fields or timestamps are missing.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from typing import Any

UTC = dt.timezone.utc


class SourceError(RuntimeError):
    pass


def _json_get(url: str, *, headers: dict[str, str] | None = None, timeout: float = 20.0) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise SourceError(f"HTTP {response.status} from {url}")
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        if isinstance(exc, SourceError):
            raise
        raise SourceError(f"{type(exc).__name__}: {exc}") from exc


def sec_headers() -> dict[str, str]:
    user_agent = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    if not user_agent or "@" not in user_agent:
        raise SourceError("WARROOM_SEC_USER_AGENT must identify the application and include a contact email")
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Host": "data.sec.gov"}


def fetch_sec_submissions(cik: str, *, timeout: float = 20.0) -> dict[str, Any]:
    digits = "".join(character for character in str(cik) if character.isdigit())
    if not digits:
        raise SourceError("CIK is required")
    url = f"https://data.sec.gov/submissions/CIK{int(digits):010d}.json"
    data = _json_get(url, headers=sec_headers(), timeout=timeout)
    if not isinstance(data, dict) or "filings" not in data:
        raise SourceError("Malformed SEC submissions response")
    return data


def fetch_sec_companyfacts(cik: str, *, timeout: float = 20.0) -> dict[str, Any]:
    digits = "".join(character for character in str(cik) if character.isdigit())
    if not digits:
        raise SourceError("CIK is required")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(digits):010d}.json"
    data = _json_get(url, headers=sec_headers(), timeout=timeout)
    if not isinstance(data, dict) or "facts" not in data:
        raise SourceError("Malformed SEC companyfacts response")
    return data


def normalize_sec_recent_filings(submissions: dict[str, Any], *, ingested_at: str | None = None) -> list[dict[str, Any]]:
    recent = ((submissions.get("filings") or {}).get("recent") or {})
    required = ["accessionNumber", "filingDate", "acceptanceDateTime", "form", "primaryDocument"]
    if any(key not in recent for key in required):
        raise SourceError("SEC recent filing fields are incomplete")
    n = len(recent["accessionNumber"])
    if any(len(recent[key]) != n for key in required):
        raise SourceError("SEC recent filing arrays have inconsistent lengths")
    ingested_at = ingested_at or dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")
    cik = str(submissions.get("cik") or "")
    rows = []
    for index in range(n):
        accepted = str(recent["acceptanceDateTime"][index])
        if len(accepted) == 14 and accepted.isdigit():
            accepted = dt.datetime.strptime(accepted, "%Y%m%d%H%M%S").replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
        rows.append({
            "market": "US_STOCKS",
            "security_id": f"CIK{int(cik):010d}" if cik.isdigit() else cik,
            "observation_at": str(recent["filingDate"][index]) + "T00:00:00Z",
            "available_at": accepted,
            "source_id": "SEC_EDGAR_SUBMISSIONS",
            "source_record_id": str(recent["accessionNumber"][index]),
            "field_id": "FILING_FORM",
            "value": 1.0,
            "unit": str(recent["form"][index]),
            "revision_id": str(recent["primaryDocument"][index]),
            "ingested_at": ingested_at,
        })
    return rows


def fetch_fred_alfred_observations(
    series_id: str,
    *,
    realtime_start: str,
    realtime_end: str,
    observation_start: str = "1776-07-04",
    observation_end: str = "9999-12-31",
    timeout: float = 20.0,
) -> dict[str, Any]:
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        raise SourceError("FRED_API_KEY is required for ALFRED vintage collection")
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "realtime_start": realtime_start,
        "realtime_end": realtime_end,
        "observation_start": observation_start,
        "observation_end": observation_end,
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
    data = _json_get(url, timeout=timeout)
    if not isinstance(data, dict) or "observations" not in data:
        raise SourceError("Malformed FRED/ALFRED response")
    return data


def fetch_eia_v2(route: str, *, facets: dict[str, list[str]] | None = None, frequency: str | None = None,
                 start: str | None = None, end: str | None = None, timeout: float = 20.0) -> dict[str, Any]:
    api_key = os.getenv("EIA_API_KEY", "").strip()
    if not api_key:
        raise SourceError("EIA_API_KEY is required")
    route = route.strip("/")
    params: list[tuple[str, str]] = [("api_key", api_key)]
    if frequency:
        params.append(("frequency", frequency))
    if start:
        params.append(("start", start))
    if end:
        params.append(("end", end))
    for name, values in (facets or {}).items():
        for value in values:
            params.append((f"facets[{name}][]", value))
    url = f"https://api.eia.gov/v2/{route}/data/?" + urllib.parse.urlencode(params)
    data = _json_get(url, timeout=timeout)
    if not isinstance(data, dict) or not isinstance(data.get("response"), dict):
        raise SourceError("Malformed EIA response")
    return data


def fetch_cftc_socrata(dataset_id: str, *, where: str | None = None, limit: int = 50000,
                        timeout: float = 30.0) -> list[dict[str, Any]]:
    dataset_id = str(dataset_id).strip()
    if not dataset_id:
        raise SourceError("CFTC Socrata dataset ID is required")
    params = {"$limit": str(min(max(int(limit), 1), 50000))}
    if where:
        params["$where"] = where
    token = os.getenv("CFTC_APP_TOKEN", "").strip()
    headers = {"X-App-Token": token} if token else {}
    url = f"https://publicreporting.cftc.gov/resource/{dataset_id}.json?" + urllib.parse.urlencode(params)
    data = _json_get(url, headers=headers, timeout=timeout)
    if not isinstance(data, list):
        raise SourceError("Malformed CFTC Socrata response")
    return [row for row in data if isinstance(row, dict)]


def fetch_bls_series(series_ids: list[str], start_year: int, end_year: int, *, timeout: float = 20.0) -> dict[str, Any]:
    clean = [str(value).strip() for value in series_ids if str(value).strip()]
    if not clean or len(clean) > 50:
        raise SourceError("BLS series list must contain 1-50 IDs")
    payload = json.dumps({"seriesid": clean, "startyear": str(start_year), "endyear": str(end_year)}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "WarRoomOS/8.5 evidence collector"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise SourceError(f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict) or data.get("status") != "REQUEST_SUCCEEDED":
        raise SourceError(f"BLS request failed: {data.get('message') if isinstance(data, dict) else 'malformed response'}")
    return data


def fetch_deribit_book_summary(currency: str, *, kind: str | None = None, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Fetch current venue-level derivatives/spot summary from Deribit public JSON-RPC REST.

    The response is raw positioning/liquidity context. It is not a directional signal and does not
    provide historical point-in-time proof by itself.
    """
    currency = str(currency or "").upper().strip()
    if currency not in {"BTC", "ETH", "USDC", "USDT", "EURR"}:
        raise SourceError("Unsupported Deribit currency")
    params = {"currency": currency}
    if kind:
        kind = str(kind).lower().strip()
        if kind not in {"future", "option", "spot", "future_combo", "option_combo"}:
            raise SourceError("Unsupported Deribit instrument kind")
        params["kind"] = kind
    url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?" + urllib.parse.urlencode(params)
    data = _json_get(url, timeout=timeout)
    if not isinstance(data, dict) or not isinstance(data.get("result"), list):
        raise SourceError("Malformed Deribit book summary response")
    return [row for row in data["result"] if isinstance(row, dict)]


def fetch_deribit_last_trades(currency: str, *, kind: str | None = None, count: int = 1000,
                               timeout: float = 20.0) -> dict[str, Any]:
    currency = str(currency or "").upper().strip()
    if currency not in {"BTC", "ETH", "USDC", "USDT", "EURR"}:
        raise SourceError("Unsupported Deribit currency")
    params: dict[str, Any] = {"currency": currency, "count": min(max(int(count), 1), 1000)}
    if kind:
        kind = str(kind).lower().strip()
        if kind not in {"future", "option", "spot", "future_combo", "option_combo"}:
            raise SourceError("Unsupported Deribit instrument kind")
        params["kind"] = kind
    url = "https://www.deribit.com/api/v2/public/get_last_trades_by_currency?" + urllib.parse.urlencode(params)
    data = _json_get(url, timeout=timeout)
    if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
        raise SourceError("Malformed Deribit last-trades response")
    return data["result"]
