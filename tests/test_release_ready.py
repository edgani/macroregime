from pathlib import Path
import json,sys,tomllib
import yaml
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash
from warroom_v3.providers import ProviderRegistry


def test_pyproject_is_valid_and_exposes_cli():
    data=tomllib.loads((ROOT/'pyproject.toml').read_text())
    assert data['project']['scripts']['warroom']=='warroom_v3.cli:main'
    deps=' '.join(data['project']['dependencies']).lower()
    assert 'streamlit' in deps


def test_compose_is_valid_and_localhost_only():
    data=yaml.safe_load((ROOT/'docker-compose.yml').read_text())
    assert data['services']['streamlit']['ports']==['127.0.0.1:8501:8501']
    assert 'collector' in data['services']


def test_systemd_streamlit_binds_localhost():
    text=(ROOT/'ops/systemd/warroom-streamlit.service').read_text()
    assert '--server.address=127.0.0.1' in text
    assert 'NoNewPrivileges=true' in text
    assert 'enable --now warroom-streamlit.service' in (ROOT/'ops/install_oracle_ubuntu.sh').read_text()


def test_seal_binds_current_provider_and_collection_plan():
    seal=json.loads((ROOT/'prospective/SEAL.json').read_text())
    body={k:v for k,v in seal.items() if k!='seal_hash'}
    assert seal['seal_hash']==canonical_hash(body)
    assert seal['provider_registry_hash']==ProviderRegistry.load(ROOT/'config/providers.json').snapshot_hash
    plan=json.loads((ROOT/'config/collection_plan.json').read_text())
    assert seal['collection_plan_hash']==plan['plan_hash']
    assert seal['paper_live_eligible'] is False


def test_release_manifest_binds_operational_core():
    release=json.loads((ROOT/'artifacts/release_manifest_ready.json').read_text())
    paths={x['path'] for x in release['files']}
    for required in ('src/warroom_v3/runtime.py','src/warroom_v3/trading.py','streamlit_app.py','config/providers.json'):
        assert required in paths
