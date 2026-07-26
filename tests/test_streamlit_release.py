from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_streamlit_app_and_config_exist():
    assert (ROOT/'streamlit_app.py').exists()
    config=tomllib.loads((ROOT/'.streamlit/config.toml').read_text())
    assert config['server']['address']=='127.0.0.1'
    assert config['server']['port']==8501
    assert config['server']['enableXsrfProtection'] is True


def test_streamlit_is_release_dependency():
    req=(ROOT/'requirements.txt').read_text().lower()
    assert 'streamlit' in req
    assert 'plotly' in req
    assert 'pandas' in req


def test_streamlit_systemd_service_is_local_only():
    service=(ROOT/'ops/systemd/warroom-streamlit.service').read_text()
    assert '--server.address=127.0.0.1' in service
    assert 'WARROOM_ROOT=/opt/warroom' in service
    assert 'ReadWritePaths=/opt/warroom/runtime' in service


def test_app_compiles_without_importing_streamlit_runtime():
    source=(ROOT/'streamlit_app.py').read_text()
    compile(source,str(ROOT/'streamlit_app.py'),'exec')


def test_streamlit_app_boots_in_empty_state(monkeypatch):
    monkeypatch.setenv('WARROOM_ROOT', str(ROOT))
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT/'streamlit_app.py'), default_timeout=30).run()
    assert not app.exception
    assert any(title.value == 'War Room OS v3' for title in app.title)


def test_streamlit_market_and_planner_with_finalized_bars(tmp_path, monkeypatch):
    import shutil
    from datetime import datetime, timezone, timedelta
    from streamlit.testing.v1 import AppTest
    from warroom_v3.data import OHLCVBar
    from warroom_v3.storage import write_batch

    for rel in ('config','evidence','validation','prospective'):
        shutil.copytree(ROOT/rel, tmp_path/rel)
    (tmp_path/'runtime').mkdir()
    fetched=datetime(2026,7,13,12,tzinfo=timezone.utc)
    seconds={'15m':900,'1h':3600,'4h':14400,'1d':86400}
    for timeframe, step in seconds.items():
        start=fetched-timedelta(seconds=step*130)
        bars=[]
        for i in range(120):
            observed=start+timedelta(seconds=step*(i+1))
            close=100+i*0.4
            bars.append(OHLCVBar(
                asset='BTCUSDT',timeframe=timeframe,observed_at=observed,available_at=observed,ingested_at=fetched,
                open=close-0.2,high=close+0.8,low=close-0.8,close=close,volume=1000+i,
                source_record_id=f'BTCUSDT:{timeframe}:{i}',
            ))
        write_batch(root=tmp_path/'runtime',tier='bootstrap',provider_id='TEST',source_uri='file:///test',raw=timeframe.encode(),bars=bars,fetched_at=fetched)
    monkeypatch.setenv('WARROOM_ROOT',str(tmp_path))
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception
    assert len(app.metric) >= 8
    app.sidebar.radio[0].set_value('Execution Planner').run()
    assert not app.exception
    assert any(button.label == 'Generate structural template' for button in app.button)
