from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Any
import json, os, tempfile, hashlib

from .data import OHLCVBar, validate_bars
from .hashing import canonical_hash, file_hash

GENESIS="0"*64


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k):_jsonable(v) for k,v in value.items()}
    return value


def atomic_write(path: str | Path, data: bytes) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=data:
            raise ValueError(f"immutable path already contains different bytes: {target}")
        return
    fd,tmp=tempfile.mkstemp(prefix=f".{target.name}.",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)



def atomic_replace(path: str | Path, data: bytes) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=f".{target.name}.",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def append_line(path: str | Path, line: str) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("a",encoding="utf-8") as fh:
        fh.write(line.rstrip("\n")+"\n"); fh.flush(); os.fsync(fh.fileno())


def load_jsonl(path: str | Path) -> list[dict]:
    target=Path(path)
    if not target.exists(): return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_chain(entries: Iterable[dict]) -> tuple[str,...]:
    errors=[]; previous=GENESIS; scope_heads={}
    for expected,row in enumerate(entries,start=1):
        if row.get("sequence")!=expected: errors.append(f"SEQUENCE:{expected}")
        if row.get("previous_entry_hash")!=previous: errors.append(f"GLOBAL_PREVIOUS:{expected}")
        scope=row.get("scope_id","")
        expected_scope=scope_heads.get(scope,GENESIS)
        if row.get("previous_scope_hash")!=expected_scope: errors.append(f"SCOPE_PREVIOUS:{expected}")
        payload={k:v for k,v in row.items() if k!="entry_hash"}
        if row.get("entry_hash")!=canonical_hash(payload): errors.append(f"ENTRY_HASH:{expected}")
        previous=row.get("entry_hash",""); scope_heads[scope]=previous
    return tuple(errors)


@dataclass(frozen=True)
class StoredBatch:
    tier: str
    batch_id: str
    scope_id: str
    asset: str
    timeframe: str
    provider_id: str
    source_uri: str
    fetched_at: str
    first_observed_at: str
    last_observed_at: str
    rows: int
    raw_sha256: str
    normalized_sha256: str
    quality_sha256: str
    batch_path: str
    entry_hash: str


def _bar_record(bar: OHLCVBar) -> dict:
    return bar.canonical_record()


def write_batch(*, root: str | Path, tier: str, provider_id: str, source_uri: str, raw: bytes, bars: list[OHLCVBar], fetched_at: datetime) -> StoredBatch:
    quality=validate_bars(bars,as_of=fetched_at,require_volume=True)
    if not quality.accepted:
        raise ValueError("DATA_QUALITY_FAILED:"+",".join(quality.reason_codes))
    scope=f"{bars[0].asset}:{bars[0].timeframe}"
    normalized=[_bar_record(b) for b in bars]
    identity={"tier":tier,"scope":scope,"provider":provider_id,"source":source_uri,"raw":hashlib.sha256(raw).hexdigest(),"normalized":quality.payload_hash}
    batch_id=canonical_hash(identity)
    relative=Path(tier)/scope.replace(":","__")/batch_id
    batch_dir=Path(root)/relative
    normalized_bytes=("\n".join(json.dumps(r,sort_keys=True,separators=(",",":")) for r in normalized)+"\n").encode()
    quality_payload=_jsonable(asdict(quality))
    quality_bytes=json.dumps(quality_payload,sort_keys=True,indent=2).encode()
    receipt={
        "batch_id":batch_id,"tier":tier,"scope_id":scope,"asset":bars[0].asset,"timeframe":bars[0].timeframe,
        "provider_id":provider_id,"source_uri":source_uri,"fetched_at":fetched_at.astimezone(timezone.utc).isoformat(),
        "rows":len(bars),"first_observed_at":bars[0].observed_at.astimezone(timezone.utc).isoformat(),
        "last_observed_at":bars[-1].observed_at.astimezone(timezone.utc).isoformat(),
        "raw_sha256":hashlib.sha256(raw).hexdigest(),"normalized_sha256":canonical_hash(normalized),
        "quality_sha256":canonical_hash(quality_payload),
    }
    atomic_write(batch_dir/"raw.payload",raw)
    atomic_write(batch_dir/"normalized.jsonl",normalized_bytes)
    atomic_write(batch_dir/"quality.json",quality_bytes)
    atomic_write(batch_dir/"receipt.json",json.dumps(receipt,sort_keys=True,indent=2).encode())
    journal=Path(root)/tier/"journal.jsonl"
    entries=load_jsonl(journal)
    errors=verify_chain(entries)
    if errors: raise ValueError("JOURNAL_INVALID:"+",".join(errors))
    previous=entries[-1]["entry_hash"] if entries else GENESIS
    scope_previous=next((e["entry_hash"] for e in reversed(entries) if e["scope_id"]==scope),GENESIS)
    if any(e["batch_id"]==batch_id for e in entries):
        existing=next(e for e in entries if e["batch_id"]==batch_id)
        return StoredBatch(**{k:existing[k] for k in StoredBatch.__dataclass_fields__})
    last_scope=next((e for e in reversed(entries) if e["scope_id"]==scope),None)
    if last_scope and receipt["first_observed_at"] <= last_scope["last_observed_at"]:
        raise ValueError("SCOPE_WINDOW_OVERLAP_OR_REWRITE")
    row={**receipt,"batch_path":relative.as_posix(),"sequence":len(entries)+1,
         "previous_entry_hash":previous,"previous_scope_hash":scope_previous}
    row["entry_hash"]=canonical_hash(row)
    append_line(journal,json.dumps(row,sort_keys=True,separators=(",",":")))
    return StoredBatch(**{k:row[k] for k in StoredBatch.__dataclass_fields__})


def read_scope_bars(root: str | Path, *, tier: str, asset: str, timeframe: str) -> list[OHLCVBar]:
    scope=f"{asset.upper()}:{timeframe}"
    entries=[e for e in load_jsonl(Path(root)/tier/"journal.jsonl") if e["scope_id"]==scope]
    rows_by_time={}
    for entry in entries:
        path=Path(root)/entry["batch_path"]/"normalized.jsonl"
        if not path.exists(): raise ValueError(f"MISSING_BATCH_FILE:{path}")
        for row in load_jsonl(path):
            bar=OHLCVBar(
                asset=row["asset"],timeframe=row["timeframe"],
                observed_at=datetime.fromisoformat(row["observed_at"]),available_at=datetime.fromisoformat(row["available_at"]),
                ingested_at=datetime.fromisoformat(row["ingested_at"]),open=float(row["open"]),high=float(row["high"]),
                low=float(row["low"]),close=float(row["close"]),volume=None if row["volume"] is None else float(row["volume"]),
                source_record_id=row["source_record_id"],revision_id=row.get("revision_id","0"))
            rows_by_time[bar.observed_at]=bar
    return [rows_by_time[k] for k in sorted(rows_by_time)]


def verify_store(root: str | Path, tier: str) -> tuple[str,...]:
    base=Path(root); journal=base/tier/"journal.jsonl"; entries=load_jsonl(journal)
    errors=list(verify_chain(entries))
    for i,e in enumerate(entries,start=1):
        batch=base/e["batch_path"]
        for name in ("raw.payload","normalized.jsonl","quality.json","receipt.json"):
            if not (batch/name).exists(): errors.append(f"MISSING:{i}:{name}")
        if (batch/"raw.payload").exists() and hashlib.sha256((batch/"raw.payload").read_bytes()).hexdigest()!=e["raw_sha256"]:
            errors.append(f"RAW_HASH:{i}")
        if (batch/"normalized.jsonl").exists():
            rows=load_jsonl(batch/"normalized.jsonl")
            if canonical_hash(rows)!=e["normalized_sha256"]: errors.append(f"NORMALIZED_HASH:{i}")
    return tuple(errors)
