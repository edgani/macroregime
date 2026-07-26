from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json, shutil, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from fastapi.testclient import TestClient
from warroom_v3.api import create_app
from warroom_v3.data import OHLCVBar
from warroom_v3.hashing import canonical_hash
from warroom_v3.providers import (
    BinanceSpotProvider, HTTPResponse, ProviderRegistry, RetrievalMode, ProviderError,
)
from warroom_v3.runtime import (
    bootstrap_binance_scope, build_asset_snapshot, collect_binance_scope,
    import_canonical_csv, load_seal, system_status,
)
from warroom_v3.storage import load_jsonl, read_scope_bars, verify_chain, verify_store, write_batch


class FakeTransport:
    def __init__(self, body: bytes): self.body=body; self.calls=[]
    def get(self,url,*,timeout_seconds,max_bytes,allowed_hosts):
        self.calls.append(url)
        return HTTPResponse(url=url,status=200,headers={'content-type':'application/json'},body=self.body)


def kline_payload(start: datetime, count: int, seconds: int, base: float=100.0) -> bytes:
    rows=[]
    for i in range(count):
        open_at=start+timedelta(seconds=i*seconds)
        close_at=open_at+timedelta(seconds=seconds)
        price=base+i*0.15
        rows.append([
            int(open_at.timestamp()*1000),str(price),str(price+1),str(price-1),str(price+0.2),str(10+i),
            int(close_at.timestamp()*1000)-1,'0','0','0','0','0'
        ])
    return json.dumps(rows).encode()


def temp_root() -> tuple[TemporaryDirectory,Path]:
    td=TemporaryDirectory(); root=Path(td.name)
    for rel in ('config','evidence','prospective','validation','specs','static'):
        shutil.copytree(ROOT/rel,root/rel)
    (root/'runtime').mkdir()
    for rel in ('bootstrap','prospective','observations','outcomes','incidents','quarantine'):
        (root/'runtime'/rel).mkdir(parents=True,exist_ok=True)
    return td,root


def arm(root: Path, start: datetime) -> None:
    payload={
        'seal_id':'TEST-SEAL','status':'ARMED','collection_starts_at':start.isoformat(),
        'paper_live_eligible':False,'reason_codes':['FORMULAS_NOT_EVALUATED'],
        'system_release_hash':'0'*64,'formula_registry_hash':json.loads((root/'evidence/formula_registry_active.json').read_text())['registry_hash'],
        'provider_registry_hash':ProviderRegistry.load(root/'config/providers.json').snapshot_hash,
    }
    payload['seal_hash']=canonical_hash(payload)
    (root/'prospective/SEAL.json').write_text(json.dumps(payload,sort_keys=True,indent=2))


def test_provider_registry_hash_and_authorization():
    registry=ProviderRegistry.load(ROOT/'config/providers.json')
    record=registry.get('BINANCE_SPOT_PUBLIC_KLINES_V1')
    ok,reasons=record.authorize(mode=RetrievalMode.PROSPECTIVE,asset='BTCUSDT',timeframe='1h',venue='BINANCE_SPOT')
    assert ok and not reasons
    ok,reasons=record.authorize(mode=RetrievalMode.PROSPECTIVE,asset='AAPL',timeframe='1h',venue='BINANCE_SPOT')
    assert not ok and 'ASSET_NOT_APPROVED:AAPL' in reasons


def test_binance_normalizes_only_finalized_bars():
    now=datetime(2026,7,12,12,tzinfo=timezone.utc)
    raw=kline_payload(now-timedelta(hours=3),3,3600)
    provider=BinanceSpotProvider(transport=FakeTransport(raw))
    approval=ProviderRegistry.load(ROOT/'config/providers.json').get(provider.provider_id)
    payload=provider.fetch_latest(asset='BTCUSDT',timeframe='1h',limit=3,approval=approval,end_at=now)
    bars=provider.normalize(payload,asset='BTCUSDT',timeframe='1h',as_of=now)
    assert len(bars)==3
    assert bars[-1].available_at==now
    assert bars[-1].source_record_id.startswith('BTCUSDT:1h:')


def test_binance_rejects_unsupported_timeframe():
    provider=BinanceSpotProvider(transport=FakeTransport(b'[]'))
    approval=ProviderRegistry.load(ROOT/'config/providers.json').get(provider.provider_id)
    try: provider.fetch_latest(asset='BTCUSDT',timeframe='5m',limit=3,approval=approval)
    except ProviderError as exc: assert 'UNSUPPORTED_TIMEFRAME' in str(exc)
    else: raise AssertionError('expected rejection')


def test_storage_global_and_scope_chain_allow_cross_scope_overlap():
    with TemporaryDirectory() as td:
        root=Path(td); now=datetime(2026,7,12,12,tzinfo=timezone.utc)
        def bars(asset):
            return [OHLCVBar(asset,'1h',now,now,now+timedelta(seconds=1),100,101,99,100.5,10,f'{asset}:1')]
        write_batch(root=root,tier='prospective',provider_id='P',source_uri='https://x',raw=b'a',bars=bars('BTCUSDT'),fetched_at=now+timedelta(seconds=1))
        write_batch(root=root,tier='prospective',provider_id='P',source_uri='https://x',raw=b'b',bars=bars('ETHUSDT'),fetched_at=now+timedelta(seconds=1))
        entries=load_jsonl(root/'prospective/journal.jsonl')
        assert len(entries)==2 and not verify_chain(entries)


def test_storage_rejects_same_scope_rewrite():
    with TemporaryDirectory() as td:
        root=Path(td); now=datetime(2026,7,12,12,tzinfo=timezone.utc)
        bar=OHLCVBar('BTCUSDT','1h',now,now,now+timedelta(seconds=1),100,101,99,100.5,10,'x')
        write_batch(root=root,tier='prospective',provider_id='P',source_uri='https://x',raw=b'a',bars=[bar],fetched_at=now+timedelta(seconds=1))
        bar2=OHLCVBar('BTCUSDT','1h',now,now,now+timedelta(seconds=2),100,102,99,101,10,'x2')
        try: write_batch(root=root,tier='prospective',provider_id='P',source_uri='https://x',raw=b'b',bars=[bar2],fetched_at=now+timedelta(seconds=2))
        except ValueError as exc: assert 'OVERLAP' in str(exc)
        else: raise AssertionError('rewrite must fail')


def test_bootstrap_builds_descriptive_snapshot():
    td,root=temp_root()
    try:
        now=datetime(2026,7,12,12,tzinfo=timezone.utc)
        raw=kline_payload(now-timedelta(hours=150),150,3600)
        provider=BinanceSpotProvider(transport=FakeTransport(raw))
        result=bootstrap_binance_scope(root,asset='BTCUSDT',timeframe='1h',limit=150,now=now,provider=provider)
        assert result['status']=='BOOTSTRAPPED'
        bars=read_scope_bars(root/'runtime',tier='bootstrap',asset='BTCUSDT',timeframe='1h')
        assert len(bars)==150
        status=system_status_with_unarmed(root)
        assert status['actionable'] is False
    finally: td.cleanup()


def system_status_with_unarmed(root: Path):
    # Operational package always contains SEAL.json; tests create a harmless armed seal for status parsing.
    arm(root,datetime(2026,7,13,tzinfo=timezone.utc))
    return system_status(root)


def test_prospective_collection_blocks_before_start():
    td,root=temp_root()
    try:
        now=datetime(2026,7,12,12,tzinfo=timezone.utc); arm(root,now+timedelta(hours=1))
        raw=kline_payload(now-timedelta(hours=3),3,3600)
        provider=BinanceSpotProvider(transport=FakeTransport(raw))
        result=collect_binance_scope(root,asset='BTCUSDT',timeframe='1h',now=now,provider=provider)
        assert result['status']=='NOT_READY'
        assert not load_jsonl(root/'runtime/prospective/journal.jsonl')
    finally: td.cleanup()


def test_collect_writes_observation_after_warmup():
    td,root=temp_root()
    try:
        start=datetime(2026,7,12,12,tzinfo=timezone.utc); now=start+timedelta(hours=2)
        bootstrap_raw=kline_payload(start-timedelta(hours=150),150,3600)
        bootstrap_binance_scope(root,asset='BTCUSDT',timeframe='1h',limit=150,now=start,provider=BinanceSpotProvider(transport=FakeTransport(bootstrap_raw)))
        arm(root,start-timedelta(seconds=1))
        prospective_raw=kline_payload(start,2,3600,base=130)
        result=collect_binance_scope(root,asset='BTCUSDT',timeframe='1h',now=now,provider=BinanceSpotProvider(transport=FakeTransport(prospective_raw)))
        assert result['status']=='COLLECTED' and result['observations']==2
        obs=load_jsonl(root/'runtime/observations/journal.jsonl')
        assert len(obs)==2 and not verify_chain(obs)
        assert not verify_store(root/'runtime','prospective')
    finally: td.cleanup()


def test_asset_snapshot_never_contains_execution_keys():
    td,root=temp_root()
    try:
        now=datetime(2026,7,12,12,tzinfo=timezone.utc)
        for tf,seconds in [('15m',900),('1h',3600),('4h',14400),('1d',86400)]:
            raw=kline_payload(now-timedelta(seconds=150*seconds),150,seconds)
            bootstrap_binance_scope(root,asset='BTCUSDT',timeframe=tf,limit=150,now=now,provider=BinanceSpotProvider(transport=FakeTransport(raw)))
        snap=build_asset_snapshot(root,asset='BTCUSDT')
        forbidden={'entry_zone','invalidation_price','targets','probability','position_size'}
        def keys(value):
            out=set()
            if isinstance(value,dict):
                out.update(str(k).lower() for k in value)
                for child in value.values(): out.update(keys(child))
            elif isinstance(value,list):
                for child in value: out.update(keys(child))
            return out
        assert not (forbidden & keys(snap))
        assert snap['actionable'] is False
    finally: td.cleanup()


def test_api_health_and_dashboard_when_empty():
    td,root=temp_root()
    try:
        arm(root,datetime(2026,7,13,tzinfo=timezone.utc))
        client=TestClient(create_app(root))
        assert client.get('/').status_code==200
        health=client.get('/health').json()
        assert health['actionable'] is False
        assets=client.get('/api/assets').json()
        assert assets['claim_ceiling']=='DESCRIPTIVE_ONLY'
    finally: td.cleanup()


def test_manual_csv_import_bootstrap():
    td,root=temp_root()
    try:
        src=root/'input.csv'; now=datetime(2026,7,12,12,tzinfo=timezone.utc)
        rows=['asset,timeframe,observed_at,available_at,open,high,low,close,volume,source_record_id']
        for i in range(120):
            t=now-timedelta(hours=120-i)
            rows.append(f'AAPL,1h,{t.isoformat()},{t.isoformat()},{100+i/10},{101+i/10},{99+i/10},{100.5+i/10},10,a{i}')
        src.write_text('\n'.join(rows)+'\n')
        result=import_canonical_csv(root,csv_path=src,tier='bootstrap',now=now)
        assert result['status']=='IMPORTED' and result['rows']==120
    finally: td.cleanup()
