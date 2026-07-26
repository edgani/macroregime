from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
import json

from .contracts import ResearchObservationTicket
from .data import OHLCVBar
from .hashing import canonical_hash, file_hash
from .mtf import fuse_mtf
from .pipeline import build_research_observation
from .providers import BinanceSpotProvider, ProviderRegistry, RetrievalMode, ProviderError
from .registry import load_registry
from .storage import atomic_write, atomic_replace, append_line, load_jsonl, read_scope_bars, verify_chain, verify_store, write_batch, GENESIS

_TIMEFRAME_SECONDS={"15m":900,"1h":3600,"4h":14400,"1d":86400}
_ROLE_FRAME={"structural":"1d","trend":"4h","tactical":"1h","execution":"15m"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if isinstance(value, datetime): return value.astimezone(timezone.utc).isoformat()
    if is_dataclass(value): return {k:_jsonable(v) for k,v in asdict(value).items()}
    if isinstance(value, dict): return {str(k):_jsonable(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_jsonable(v) for v in value]
    return value


def load_formula_hashes(root: str | Path) -> dict[str,str]:
    reg=load_registry(Path(root)/"evidence/formula_registry_active.json")
    aliases={"mqa_benchmarks":"mqa","momentum_axes":"momentum","mtf_research":"mtf","mqa":"mqa","momentum":"momentum","mtf":"mtf"}
    out={}
    for row in reg["entries"]:
        key=aliases.get(row["component"])
        if key: out[key]=row["formula_hash"]
    if "mqa" not in out or "momentum" not in out:
        raise ValueError("active formula registry missing mqa/momentum")
    return out


def load_seal(root: str | Path) -> dict:
    path=Path(root)/"prospective/SEAL.json"
    payload=json.loads(path.read_text(encoding="utf-8"))
    expected=payload.get("seal_hash")
    body={k:v for k,v in payload.items() if k!="seal_hash"}
    if expected!=canonical_hash(body): raise ValueError("prospective seal hash mismatch")
    return payload


def _scope_latest(root: Path, tier: str, asset: str, timeframe: str) -> datetime | None:
    bars=read_scope_bars(root/"runtime",tier=tier,asset=asset,timeframe=timeframe)
    return bars[-1].observed_at if bars else None


def _filter_after(bars: list[OHLCVBar], cutoff: datetime | None) -> list[OHLCVBar]:
    return bars if cutoff is None else [b for b in bars if b.observed_at>cutoff]


def bootstrap_binance_scope(root: str | Path, *, asset: str, timeframe: str, limit: int=500, now: datetime | None=None, provider: BinanceSpotProvider | None=None) -> dict:
    root=Path(root); now=now or datetime.now(timezone.utc); provider=provider or BinanceSpotProvider()
    registry=ProviderRegistry.load(root/"config/providers.json"); approval=registry.get(provider.provider_id)
    ok,reasons=approval.authorize(mode=RetrievalMode.BOOTSTRAP,asset=asset,timeframe=timeframe,venue=provider.venue)
    if not ok: return {"status":"BLOCKED","reason_codes":list(reasons)}
    payload=provider.fetch_latest(asset=asset,timeframe=timeframe,limit=limit,approval=approval,end_at=now,mode=RetrievalMode.BOOTSTRAP)
    bars=provider.normalize(payload,asset=asset,timeframe=timeframe,as_of=now)
    latest=_scope_latest(root,"bootstrap",asset,timeframe)
    fresh=_filter_after(bars,latest)
    if not fresh: return {"status":"NO_NEW_FINALIZED_BAR","asset":asset,"timeframe":timeframe,"rows":0}
    stored=write_batch(root=root/"runtime",tier="bootstrap",provider_id=provider.provider_id,source_uri=payload.source_uri,raw=payload.raw,bars=fresh,fetched_at=payload.fetched_at)
    build_latest_scope_observation(root,asset=asset,timeframe=timeframe,record=False)
    return {"status":"BOOTSTRAPPED","rows":stored.rows,"batch_id":stored.batch_id,"asset":asset,"timeframe":timeframe}


def collect_binance_scope(root: str | Path, *, asset: str, timeframe: str, now: datetime | None=None, provider: BinanceSpotProvider | None=None) -> dict:
    root=Path(root); now=now or datetime.now(timezone.utc); provider=provider or BinanceSpotProvider()
    seal=load_seal(root)
    if seal.get("status")!="ARMED": return {"status":"BLOCKED","reason_codes":["SEAL_NOT_ARMED"]}
    starts=datetime.fromisoformat(seal["collection_starts_at"])
    if now<starts: return {"status":"NOT_READY","reason_codes":["BEFORE_SEAL_START"],"collection_starts_at":starts.isoformat()}
    registry=ProviderRegistry.load(root/"config/providers.json"); approval=registry.get(provider.provider_id)
    ok,reasons=approval.authorize(mode=RetrievalMode.PROSPECTIVE,asset=asset,timeframe=timeframe,venue=provider.venue)
    if not ok: return {"status":"BLOCKED","reason_codes":list(reasons)}
    latest=_scope_latest(root,"prospective",asset,timeframe)
    # Fetch enough bars to survive timer gaps, then admit only bars after both the seal and the scope head.
    payload=provider.fetch_latest(asset=asset,timeframe=timeframe,limit=100,approval=approval,end_at=now,mode=RetrievalMode.PROSPECTIVE)
    bars=provider.normalize(payload,asset=asset,timeframe=timeframe,as_of=now)
    cutoff=max([d for d in (latest,starts) if d is not None])
    fresh=[b for b in bars if b.observed_at>cutoff]
    if not fresh: return {"status":"NO_NEW_FINALIZED_BAR","asset":asset,"timeframe":timeframe,"rows":0}
    stored=write_batch(root=root/"runtime",tier="prospective",provider_id=provider.provider_id,source_uri=payload.source_uri,raw=payload.raw,bars=fresh,fetched_at=payload.fetched_at)
    observations=[]
    for bar in fresh:
        ticket=build_scope_observation_at(root,asset=asset,timeframe=timeframe,cutoff=bar.observed_at)
        observations.append(write_observation(root,ticket=ticket,tier="prospective"))
    build_asset_snapshot(root,asset=asset)
    mature_outcomes(root,asset=asset,timeframe=timeframe,now=now)
    return {"status":"COLLECTED","rows":stored.rows,"batch_id":stored.batch_id,"observations":len(observations),"asset":asset,"timeframe":timeframe}


def _combined_bars(root: Path, asset: str, timeframe: str) -> list[OHLCVBar]:
    merged={}
    for tier in ("bootstrap","prospective"):
        for bar in read_scope_bars(root/"runtime",tier=tier,asset=asset,timeframe=timeframe):
            merged[bar.observed_at]=bar
    return [merged[k] for k in sorted(merged)]


def build_scope_observation_at(root: str | Path, *, asset: str, timeframe: str, cutoff: datetime) -> ResearchObservationTicket:
    root=Path(root); bars=[b for b in _combined_bars(root,asset,timeframe) if b.available_at<=cutoff]
    if len(bars)<100: raise ValueError(f"INSUFFICIENT_WARMUP:{len(bars)}")
    return build_research_observation(bars,formula_hashes=load_formula_hashes(root))


def build_latest_scope_observation(root: str | Path, *, asset: str, timeframe: str, record: bool=True) -> ResearchObservationTicket:
    root=Path(root); bars=_combined_bars(root,asset,timeframe)
    if len(bars)<100: raise ValueError(f"INSUFFICIENT_WARMUP:{len(bars)}")
    ticket=build_research_observation(bars,formula_hashes=load_formula_hashes(root))
    if record: write_observation(root,ticket=ticket,tier="latest")
    return ticket


def write_observation(root: str | Path, *, ticket: ResearchObservationTicket, tier: str) -> dict:
    root=Path(root); payload=_jsonable(ticket); ticket_hash=canonical_hash(payload)
    rel=Path("observations")/tier/f"{ticket.asset}__{ticket.timeframe}"/f"{ticket.observation_id}.json"
    atomic_write(root/"runtime"/rel,json.dumps(payload,sort_keys=True,indent=2).encode())
    journal=root/"runtime/observations/journal.jsonl"; entries=load_jsonl(journal)
    errors=verify_chain(entries)
    if errors: raise ValueError("OBSERVATION_JOURNAL_INVALID:"+",".join(errors))
    if any(e["ticket_sha256"]==ticket_hash for e in entries):
        return next(e for e in entries if e["ticket_sha256"]==ticket_hash)
    scope=f"{ticket.asset}:{ticket.timeframe}"; previous=entries[-1]["entry_hash"] if entries else GENESIS
    scope_prev=next((e["entry_hash"] for e in reversed(entries) if e["scope_id"]==scope),GENESIS)
    row={"sequence":len(entries)+1,"scope_id":scope,"asset":ticket.asset,"timeframe":ticket.timeframe,
         "as_of":ticket.as_of,"ticket_sha256":ticket_hash,"ticket_path":rel.as_posix(),
         "previous_entry_hash":previous,"previous_scope_hash":scope_prev}
    row["entry_hash"]=canonical_hash(row)
    append_line(journal,json.dumps(row,sort_keys=True,separators=(",",":")))
    return row


def _direction_label(ticket: ResearchObservationTicket) -> str:
    state=ticket.component_states.get("momentum_axes",{})
    value=state.get("trend_context")
    if value is None: return "UNAVAILABLE"
    return "BULLISH" if value>=0.5 else "BEARISH" if value<=-0.5 else "NEUTRAL"


def _latest_ticket_file(root: Path, asset: str, timeframe: str) -> dict | None:
    # Prefer deterministic prospective observation; otherwise compute from bootstrap.
    try:
        ticket=build_latest_scope_observation(root,asset=asset,timeframe=timeframe,record=False)
        return _jsonable(ticket)
    except (ValueError,FileNotFoundError):
        return None


def build_asset_snapshot(root: str | Path, *, asset: str) -> dict:
    root=Path(root); tickets={tf:_latest_ticket_file(root,asset,tf) for tf in _ROLE_FRAME.values()}
    states={role:("UNAVAILABLE" if tickets[tf] is None else _direction_label_dict(tickets[tf])) for role,tf in _ROLE_FRAME.items()}
    mtf=fuse_mtf(**states)
    last_prices={tf:(None if tickets[tf] is None else tickets[tf]["component_states"]["mqa_benchmarks"]["close"]) for tf in tickets}
    payload={
        "asset":asset,"generated_at":datetime.now(timezone.utc).isoformat(),"claim_ceiling":"DESCRIPTIVE_ONLY",
        "actionable":False,"timeframes":tickets,"last_prices":last_prices,"mtf":_jsonable(mtf),
        "reason_codes":["NO_CALIBRATED_PROBABILITY","NO_EXECUTION_MAP","SCOPE_NOT_EVALUATED"],
    }
    payload["snapshot_hash"]=canonical_hash(payload)
    atomic_replace(root/f"runtime/observations/assets/{asset}.json",json.dumps(payload,sort_keys=True,indent=2).encode())
    return payload


def _direction_label_dict(ticket: dict) -> str:
    value=ticket.get("component_states",{}).get("momentum_axes",{}).get("trend_context")
    if value is None: return "UNAVAILABLE"
    return "BULLISH" if value>=0.5 else "BEARISH" if value<=-0.5 else "NEUTRAL"


def mature_outcomes(root: str | Path, *, asset: str, timeframe: str, now: datetime | None=None, horizons: tuple[int,...]=(1,4,16)) -> dict:
    root=Path(root); now=now or datetime.now(timezone.utc)
    prospective=read_scope_bars(root/"runtime",tier="prospective",asset=asset,timeframe=timeframe)
    index={b.observed_at:i for i,b in enumerate(prospective)}
    obs=[e for e in load_jsonl(root/"runtime/observations/journal.jsonl") if e["scope_id"]==f"{asset}:{timeframe}"]
    journal=root/"runtime/outcomes/journal.jsonl"; existing=load_jsonl(journal); keys={(e["ticket_sha256"],e["horizon_bars"]) for e in existing}
    added=0
    for entry in obs:
        origin=datetime.fromisoformat(entry["as_of"])
        if origin not in index: continue
        oi=index[origin]
        for horizon in horizons:
            if (entry["ticket_sha256"],horizon) in keys or oi+horizon>=len(prospective): continue
            path=prospective[oi+1:oi+horizon+1]; target=path[-1]; origin_bar=prospective[oi]
            row={"ticket_sha256":entry["ticket_sha256"],"asset":asset,"timeframe":timeframe,
                 "origin_close_at":origin.isoformat(),"target_close_at":target.observed_at.isoformat(),
                 "evaluated_at":now.isoformat(),"horizon_bars":horizon,"origin_close":origin_bar.close,
                 "target_close":target.close,"forward_return":target.close/origin_bar.close-1,
                 "maximum_favorable_excursion":max(b.high/origin_bar.close-1 for b in path),
                 "maximum_adverse_excursion":min(b.low/origin_bar.close-1 for b in path),
                 "claim_ceiling":"REALIZED_OUTCOME_ONLY"}
            row["outcome_hash"]=canonical_hash(row); append_line(journal,json.dumps(row,sort_keys=True,separators=(",",":")))
            keys.add((entry["ticket_sha256"],horizon)); added+=1
    return {"added":added,"total":len(existing)+added}


def system_status(root: str | Path) -> dict:
    root=Path(root); seal=load_seal(root)
    providers=ProviderRegistry.load(root/"config/providers.json")
    scopes=[]
    for asset in ("BTCUSDT","ETHUSDT"):
        for timeframe in ("15m","1h","4h","1d"):
            bootstrap=_combined_bars(root,asset,timeframe)
            latest=bootstrap[-1].observed_at if bootstrap else None
            age=None if latest is None else (datetime.now(timezone.utc)-latest).total_seconds()
            scopes.append({"asset":asset,"timeframe":timeframe,"bars":len(bootstrap),"last_bar":None if latest is None else latest.isoformat(),
                           "fresh":False if age is None else age<=2*_TIMEFRAME_SECONDS[timeframe]})
    from .trading import paper_journal_summary, verify_paper_journal
    paper_errors=list(verify_paper_journal(root))
    paper_summary=paper_journal_summary(root) if not paper_errors else {"total":0,"open":0,"closed":0,"realized_pnl":0.0}
    store_errors=list(verify_store(root/"runtime","prospective"))+[f"paper:{e}" for e in paper_errors]
    return {
        "system":"War Room OS v3","mode":"RESEARCH_ONLY","actionable":False,
        "streamlit_ready":True,"manual_planner_ready":True,"broker_execution":False,
        "seal_status":seal["status"],"collection_starts_at":seal["collection_starts_at"],
        "provider_registry_hash":providers.snapshot_hash,"scopes":scopes,
        "prospective_batches":len(load_jsonl(root/"runtime/prospective/journal.jsonl")),
        "observations":len(load_jsonl(root/"runtime/observations/journal.jsonl")),
        "outcomes":len(load_jsonl(root/"runtime/outcomes/journal.jsonl")),
        "paper_journal":paper_summary,
        "store_errors":store_errors,
        "reason_codes":["FORMULAS_NOT_EVALUATED","AUTONOMOUS_PAPER_BLOCKED","LIVE_BLOCKED"],
    }


def import_canonical_csv(root: str | Path, *, csv_path: str | Path, tier: str="bootstrap", now: datetime | None=None) -> dict:
    from .data import load_canonical_csv
    root=Path(root); source=Path(csv_path); now=now or datetime.now(timezone.utc)
    if tier not in ("bootstrap","prospective"):
        raise ValueError("tier must be bootstrap or prospective")
    bars,quality=load_canonical_csv(source,ingested_at=now,as_of=now)
    if not quality.accepted: raise ValueError("DATA_QUALITY_FAILED:"+",".join(quality.reason_codes))
    registry=ProviderRegistry.load(root/"config/providers.json"); approval=registry.get("LOCAL_CANONICAL_CSV_PIT_V1")
    mode=RetrievalMode.PROSPECTIVE if tier=="prospective" else RetrievalMode.MANUAL_PIT
    ok,reasons=approval.authorize(mode=mode,asset=bars[0].asset,timeframe=bars[0].timeframe,venue="LOCAL_FILE")
    if not ok: raise ValueError(";".join(reasons))
    if tier=="prospective":
        seal=load_seal(root); starts=datetime.fromisoformat(seal["collection_starts_at"])
        if seal["status"]!="ARMED" or now<starts: raise ValueError("PROSPECTIVE_SEAL_NOT_ACTIVE")
        if any(b.observed_at<=starts for b in bars): raise ValueError("PRE_SEAL_BAR_IN_PROSPECTIVE_IMPORT")
    latest=_scope_latest(root,tier,bars[0].asset,bars[0].timeframe)
    fresh=_filter_after(bars,latest)
    if not fresh: return {"status":"NO_NEW_FINALIZED_BAR","rows":0}
    stored=write_batch(root=root/"runtime",tier=tier,provider_id=approval.provider_id,source_uri=source.resolve().as_uri(),raw=source.read_bytes(),bars=fresh,fetched_at=now)
    if tier=="prospective":
        for bar in fresh:
            ticket=build_scope_observation_at(root,asset=bar.asset,timeframe=bar.timeframe,cutoff=bar.observed_at)
            write_observation(root,ticket=ticket,tier="prospective")
        build_asset_snapshot(root,asset=fresh[0].asset)
        mature_outcomes(root,asset=fresh[0].asset,timeframe=fresh[0].timeframe,now=now)
    return {"status":"IMPORTED","tier":tier,"rows":stored.rows,"batch_id":stored.batch_id,"asset":fresh[0].asset,"timeframe":fresh[0].timeframe}


def get_scope_bars(root: str | Path, *, asset: str, timeframe: str) -> list[OHLCVBar]:
    """Return deduplicated bootstrap + prospective bars for UI/replay use."""
    return _combined_bars(Path(root), asset.upper(), timeframe)


def get_scope_dashboard_payload(root: str | Path, *, asset: str, timeframe: str) -> dict:
    """Build a read-only payload for trading workstations without promoting evidence."""
    root = Path(root)
    bars = get_scope_bars(root, asset=asset, timeframe=timeframe)
    if len(bars) < 100:
        return {
            "asset": asset.upper(), "timeframe": timeframe, "status": "UNAVAILABLE",
            "bars": len(bars), "reason_codes": [f"INSUFFICIENT_WARMUP:{len(bars)}"],
            "actionable": False, "claim_ceiling": "DESCRIPTIVE_ONLY",
        }
    ticket = build_latest_scope_observation(root, asset=asset.upper(), timeframe=timeframe, record=False)
    payload = _jsonable(ticket)
    payload.update({
        "status": "RESEARCH_ONLY",
        "bars": len(bars),
        "last_bar": bars[-1].observed_at.isoformat(),
        "last_available_at": bars[-1].available_at.isoformat(),
        "actionable": False,
    })
    return payload
