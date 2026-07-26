"""Safe, tamper-evident JSON snapshots for War Room OS.

Persistent pickle is intentionally forbidden.  This codec supports the small set of pandas/numpy
objects used by the application, writes atomically, and records both a canonical content hash and a
file hash sidecar.  Unknown tagged types fail closed.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import gzip
import hashlib
import json
import math
import os
import time

try:
    import numpy as np
except Exception:  # pragma: no cover - dependency gate will report it
    np = None
try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

SCHEMA_VERSION = "warroom.safe_snapshot.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite_float(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def encode_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return _finite_float(value)
    if np is not None:
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return _finite_float(float(value))
        if isinstance(value, np.ndarray):
            return {"__type__": "ndarray", "dtype": str(value.dtype), "shape": list(value.shape), "data": encode_value(value.tolist())}
    if isinstance(value, (datetime, date)):
        return {"__type__": "datetime", "value": value.isoformat()}
    if pd is not None:
        if isinstance(value, pd.Timestamp):
            return {"__type__": "datetime", "value": value.isoformat()}
        if isinstance(value, pd.DataFrame):
            return {
                "__type__": "DataFrame",
                "columns": [str(x) for x in value.columns],
                "index": encode_value(list(value.index)),
                "index_name": value.index.name,
                "data": encode_value(value.to_numpy(dtype=object).tolist()),
                "dtypes": {str(k): str(v) for k, v in value.dtypes.items()},
            }
        if isinstance(value, pd.Series):
            return {
                "__type__": "Series",
                "name": value.name,
                "index": encode_value(list(value.index)),
                "index_name": value.index.name,
                "data": encode_value(value.tolist()),
                "dtype": str(value.dtype),
            }
        if isinstance(value, pd.Index):
            return {"__type__": "Index", "name": value.name, "data": encode_value(list(value))}
    if isinstance(value, dict):
        return {str(k): encode_value(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return {"__type__": "tuple", "data": [encode_value(v) for v in value]}
    if isinstance(value, set):
        return {"__type__": "set", "data": sorted((encode_value(v) for v in value), key=lambda x: canonical_json(x))}
    if isinstance(value, list):
        return [encode_value(v) for v in value]
    raise TypeError(f"safe snapshot cannot encode {type(value).__name__}")


def _restore_datetime(value: str) -> Any:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return value


def decode_value(value: Any) -> Any:
    if isinstance(value, list):
        return [decode_value(v) for v in value]
    if not isinstance(value, dict):
        return value
    tag = value.get("__type__")
    if not tag:
        return {k: decode_value(v) for k, v in value.items()}
    if tag == "datetime":
        return _restore_datetime(str(value.get("value") or ""))
    if tag == "tuple":
        return tuple(decode_value(v) for v in value.get("data") or [])
    if tag == "set":
        return set(decode_value(v) for v in value.get("data") or [])
    if tag == "Index":
        data = decode_value(value.get("data") or [])
        return pd.Index(data, name=value.get("name")) if pd is not None else data
    if tag == "ndarray":
        data = decode_value(value.get("data") or [])
        if np is None:
            return data
        arr = np.array(data, dtype=value.get("dtype") or None)
        shape = tuple(int(x) for x in value.get("shape") or arr.shape)
        return arr.reshape(shape)
    if tag in {"DataFrame", "Series"}:
        if pd is None:
            raise RuntimeError("pandas is required to decode pandas snapshots")
        index = decode_value(value.get("index") or [])
        if tag == "Series":
            out = pd.Series(decode_value(value.get("data") or []), index=index, name=value.get("name"))
            out.index.name = value.get("index_name")
            return out
        out = pd.DataFrame(decode_value(value.get("data") or []), columns=value.get("columns") or [], index=index)
        out.index.name = value.get("index_name")
        for col, dtype in (value.get("dtypes") or {}).items():
            if col not in out.columns:
                continue
            try:
                if str(dtype).startswith("datetime"):
                    out[col] = pd.to_datetime(out[col], errors="coerce")
                else:
                    out[col] = out[col].astype(dtype)
            except Exception:
                pass
        return out
    raise ValueError(f"unknown safe snapshot type tag: {tag}")


def _write_raw(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def write_safe_snapshot(path: str | Path, payload: Any, *, schema: str, source: str = "warroom", write_sidecar: bool = True) -> dict:
    path = Path(path)
    encoded = encode_value(payload)
    content_text = canonical_json(encoded)
    envelope = {
        "snapshot_schema": SCHEMA_VERSION,
        "payload_schema": schema,
        "created_at": utc_now(),
        "source": source,
        "content_sha256": sha256_bytes(content_text.encode("utf-8")),
        "payload": encoded,
    }
    raw = canonical_json(envelope).encode("utf-8")
    stored = gzip.compress(raw, compresslevel=6, mtime=0) if path.suffix == ".gz" else raw
    _write_raw(path, stored)
    meta = {
        "snapshot_schema": SCHEMA_VERSION,
        "payload_schema": schema,
        "created_at": envelope["created_at"],
        "content_sha256": envelope["content_sha256"],
        "file_sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if write_sidecar:
        _write_raw(path.with_name(path.name + ".sha256.json"), canonical_json(meta).encode("utf-8"))
    return meta


def read_safe_snapshot(path: str | Path, *, expected_schema: str | None = None, max_age_seconds: float | None = None,
                       require_sidecar: bool = True) -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if max_age_seconds is not None and time.time() - path.stat().st_mtime > float(max_age_seconds):
        raise ValueError("snapshot stale")
    sidecar = path.with_name(path.name + ".sha256.json")
    if require_sidecar:
        if not sidecar.exists():
            raise ValueError("snapshot hash sidecar missing")
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        if meta.get("file_sha256") != sha256_file(path):
            raise ValueError("snapshot file hash mismatch")
    stored = path.read_bytes()
    raw = gzip.decompress(stored) if path.suffix == ".gz" else stored
    envelope = json.loads(raw.decode("utf-8"))
    if envelope.get("snapshot_schema") != SCHEMA_VERSION:
        raise ValueError("snapshot schema mismatch")
    if expected_schema and envelope.get("payload_schema") != expected_schema:
        raise ValueError("payload schema mismatch")
    payload = envelope.get("payload")
    digest = sha256_bytes(canonical_json(payload).encode("utf-8"))
    if digest != envelope.get("content_sha256"):
        raise ValueError("snapshot content hash mismatch")
    return decode_value(payload)
