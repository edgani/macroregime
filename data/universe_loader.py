from __future__ import annotations

from config.universe_registry import (
    US_BACKEND_UNIVERSE,
    IHSG_BACKEND_UNIVERSE,
    FX_BACKEND_UNIVERSE,
    COMMODITIES_BACKEND_UNIVERSE,
    CRYPTO_BACKEND_UNIVERSE,
    US_CURATED_BACKEND_UNIVERSE,
    IHSG_CURATED_BACKEND_UNIVERSE,
    FX_CURATED_BACKEND_UNIVERSE,
    COMMODITIES_CURATED_BACKEND_UNIVERSE,
    CRYPTO_CURATED_BACKEND_UNIVERSE,
    build_manifest_repo,
)
from utils.regime_router import select_runtime_universe as select_runtime_universe_regime, derive_route_state


def flatten_universe(obj) -> list[str]:
    if isinstance(obj, dict):
        out = []
        for v in obj.values():
            out.extend(flatten_universe(v))
        return out
    if isinstance(obj, (list, tuple, set)):
        out = []
        for v in obj:
            out.extend(flatten_universe(v))
        return out
    return [str(obj)]


def get_backend_universe() -> dict[str, list[str]]:
    return {
        'us': flatten_universe(US_BACKEND_UNIVERSE),
        'ihsg': flatten_universe(IHSG_BACKEND_UNIVERSE),
        'fx': flatten_universe(FX_BACKEND_UNIVERSE),
        'commodities': flatten_universe(COMMODITIES_BACKEND_UNIVERSE),
        'crypto': flatten_universe(CRYPTO_BACKEND_UNIVERSE),
    }


def get_manifest_repo() -> dict[str, dict]:
    return build_manifest_repo()


_DEFAULT_COMPACT_LIMITS = {
    'us': 250,
    'ihsg': 150,
    'fx': 16,
    'commodities': 24,
    'crypto': 200,
}


def _prioritized_market_symbols(market: str) -> list[str]:
    m = str(market).lower().strip()
    backend = get_backend_universe().get(m, [])
    if m == 'us':
        front = flatten_universe(US_CURATED_BACKEND_UNIVERSE)
    elif m == 'ihsg':
        front = flatten_universe(IHSG_CURATED_BACKEND_UNIVERSE)
    elif m == 'fx':
        front = flatten_universe(FX_CURATED_BACKEND_UNIVERSE)
    elif m == 'commodities':
        front = flatten_universe(COMMODITIES_CURATED_BACKEND_UNIVERSE)
    elif m == 'crypto':
        front = flatten_universe(CRYPTO_CURATED_BACKEND_UNIVERSE)
    else:
        front = []
    out = []
    for sym in front + backend:
        sx = str(sym).strip()
        if sx and sx not in out:
            out.append(sx)
    return out


def get_runtime_universe(compact_mode: bool = True, limits: dict[str, int] | None = None, shared_core: dict | None = None) -> dict[str, list[str]]:
    runtime, _meta = build_runtime_plan(compact_mode=compact_mode, limits=limits, shared_core=shared_core)
    return runtime


def build_runtime_meta(compact_mode: bool = True, limits: dict[str, int] | None = None, shared_core: dict | None = None) -> dict[str, dict]:
    _runtime, meta = build_runtime_plan(compact_mode=compact_mode, limits=limits, shared_core=shared_core)
    return meta


def build_runtime_plan(compact_mode: bool = True, limits: dict[str, int] | None = None, shared_core: dict | None = None) -> tuple[dict[str, list[str]], dict[str, dict]]:
    backend = get_backend_universe()
    limits = dict(_DEFAULT_COMPACT_LIMITS | (limits or {}))
    if compact_mode and shared_core:
        route_state = derive_route_state(shared_core)
        runtime, router_meta = select_runtime_universe_regime(True, route_state, limits=limits)
        meta = {
            market: {
                'backend_count': len(backend.get(market, [])),
                'runtime_count': len(runtime.get(market, [])),
                'compact_mode': bool(compact_mode),
            }
            for market in ('us', 'ihsg', 'fx', 'commodities', 'crypto')
        }
        for market, info in (router_meta.get('markets', {}) or {}).items():
            if market in meta:
                meta[market]['selector_method'] = info.get('method')
                meta[market]['label_counts'] = info.get('label_counts', {})
                meta[market]['family_counts'] = info.get('family_counts', {})
        meta['_route_state'] = router_meta.get('route_state', {})
        meta['_selector_method'] = router_meta.get('method')
        return runtime, meta

    runtime: dict[str, list[str]] = {}
    for market in ('us', 'ihsg', 'fx', 'commodities', 'crypto'):
        symbols = _prioritized_market_symbols(market)
        if compact_mode:
            limit = int(limits.get(market, len(symbols)) or len(symbols))
            runtime[market] = symbols[:max(1, min(limit, len(symbols)))]
        else:
            runtime[market] = symbols
    meta = {
        market: {
            'backend_count': len(backend.get(market, [])),
            'runtime_count': len(runtime.get(market, [])),
            'compact_mode': bool(compact_mode),
        }
        for market in ('us', 'ihsg', 'fx', 'commodities', 'crypto')
    }
    return runtime, meta
