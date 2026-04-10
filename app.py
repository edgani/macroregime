from __future__ import annotations

import streamlit as st
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.build_snapshot import build_snapshot
from orchestration.page_router import render_selected_page
from config.settings import APP_NAME, APP_VERSION, LIVE_RUNTIME_MODE
from data.snapshot_store import snapshot_path, load_snapshot, load_snapshot_manifest
from ui.theme import inject_theme


def _safe_build_snapshot(refresh: bool, open_mode: str, compact_mode: bool) -> dict:
    attempts = [
        lambda: build_snapshot(force_refresh=refresh, compact_mode=compact_mode, open_mode=open_mode),
        lambda: build_snapshot(force_refresh=refresh, prefer_saved=(open_mode == 'snapshot_only'), compact_mode=compact_mode),
        lambda: build_snapshot(force_refresh=refresh, prefer_saved=(open_mode == 'snapshot_only')),
        lambda: build_snapshot(force_refresh=refresh),
        lambda: build_snapshot(),
    ]
    last_exc: Exception | None = None
    for fn in attempts:
        try:
            return fn()
        except TypeError as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    return build_snapshot()


def _render_sidebar_meta(snapshot: dict) -> None:
    meta = snapshot.get('meta', {}) or {}
    loader_meta = meta.get('loader_meta', {}) or {}
    hist = meta.get('history_meta', {}) or {}
    prices_meta = loader_meta.get('prices', {}) or {}
    st.sidebar.caption(f"v{APP_VERSION} · runtime: {meta.get('runtime_mode', LIVE_RUNTIME_MODE)}")
    st.sidebar.caption(f"Snapshot as of: {meta.get('generated_at', '-')}")
    st.sidebar.caption(
        f"History store: {hist.get('present', 0)}/{hist.get('requested', 0)} symbols | price loaded: {prices_meta.get('loaded', 0)}"
    )
    st.sidebar.caption(
        f"Price refresh: {prices_meta.get('refresh_mode', '-')} | provider fetch: {prices_meta.get('fetched_from_provider', 0)} | last bar max: {prices_meta.get('max_last_bar_date', '-')}"
    )
    if int(hist.get('present', 0) or 0) == 0:
        st.sidebar.warning('Local history belum kebangun. Jalankan updater script atau klik refresh backend snapshot saat online.')


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon='📊', layout='wide', initial_sidebar_state='expanded')
    inject_theme()

    st.sidebar.title(APP_NAME)
    st.sidebar.caption('Fresh-first mode tries live/local merge first, then falls back to snapshot only if needed.')

    open_mode = st.sidebar.radio('Open mode', ['Smart fresh', 'Force rebuild', 'Snapshot only'], index=0)
    refresh = open_mode == 'Force rebuild' or st.sidebar.button('Refresh backend snapshot now')
    clear_snap = st.sidebar.button('Clear saved snapshot')
    compact_mode = st.sidebar.toggle('Compact mode', value=True)

    manifest = load_snapshot_manifest()
    if isinstance(manifest, dict):
        st.sidebar.caption(f"Last saved snapshot: {manifest.get('generated_at', '-')}")

    if clear_snap:
        try:
            snapshot_path().unlink(missing_ok=True)
            st.sidebar.success('Saved snapshot dibersihin.')
        except Exception as exc:
            st.sidebar.warning(f'Gagal clear snapshot: {exc}')

    try:
        normalized_open_mode = {'Smart fresh': 'smart_fresh', 'Force rebuild': 'force_rebuild', 'Snapshot only': 'snapshot_only'}[open_mode]
        snapshot = _safe_build_snapshot(refresh=refresh, open_mode=normalized_open_mode, compact_mode=compact_mode)
    except Exception as exc:
        cached = load_snapshot()
        detail = traceback.format_exc()
        if isinstance(cached, dict):
            st.sidebar.warning(f'Live rebuild gagal, pakai snapshot tersimpan: {exc}')
            with st.expander('Lihat detail error rebuild', expanded=False):
                st.exception(exc)
                st.code(detail, language='python')
            snapshot = cached
        else:
            st.error('Snapshot gagal dibangun dan tidak ada cache yang bisa dipakai.')
            st.exception(exc)
            st.code(detail, language='python')
            return

    _render_sidebar_meta(snapshot)

    nav_mode = st.sidebar.radio(
        'Pilih group',
        ['Command Center', 'Markets', 'Scenario Lab', 'Diagnostics'],
    )

    if nav_mode == 'Command Center':
        page = st.sidebar.radio('Pilih halaman', ['Home', 'Active Route', 'Opportunity Board'])
    elif nav_mode == 'Markets':
        page = st.sidebar.radio('Pilih market', ['US', 'IHSG', 'FX', 'Commodities', 'Crypto'])
    elif nav_mode == 'Scenario Lab':
        page = 'Scenario Lab'
    else:
        page = 'Diagnostics'

    render_selected_page(page=page, snapshot=snapshot)


if __name__ == '__main__':
    main()
