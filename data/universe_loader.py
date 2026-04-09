from __future__ import annotations

from config.universe_registry import (
    US_BACKEND_UNIVERSE,
    IHSG_BACKEND_UNIVERSE,
    FX_BACKEND_UNIVERSE,
    COMMODITIES_BACKEND_UNIVERSE,
    CRYPTO_BACKEND_UNIVERSE,
    build_manifest_repo,
)


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
