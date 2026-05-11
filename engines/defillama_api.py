"""engines/defillama_api.py — DeFiLlama REST API Client
Real TVL, stablecoin market cap, DEX volume, chain-specific data.
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE_URL = "https://api.llama.fi"


class DeFiLlamaAPI:
    """Production DeFiLlama API client with caching."""

    def __init__(self, cache_minutes: int = 30):
        self.cache_minutes = cache_minutes
        self._cache: Dict[str, tuple] = {}  # key -> (timestamp, data)

    def _get(self, endpoint: str) -> Optional[Dict]:
        """GET with caching and error handling."""
        cache_key = endpoint
        now = datetime.now()
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if (now - ts) < timedelta(minutes=self.cache_minutes):
                return data

        url = f"{BASE_URL}{endpoint}"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = (now, data)
            return data
        except Exception as e:
            logger.warning(f"DeFiLlama API error for {endpoint}: {e}")
            return None

    def get_tvl(self) -> Optional[float]:
        """Total DeFi TVL in billions."""
        data = self._get("/tvl")
        if data and isinstance(data, (int, float)):
            return round(data / 1e9, 2)
        return None

    def get_stablecoin_mcap(self) -> Optional[float]:
        """Total stablecoin market cap in billions."""
        data = self._get("/stablecoins")
        if data and isinstance(data, dict):
            # Try multiple possible key names
            for key in ["totalCirculatingUSD", "totalCirculating", "totalUSD", "total"]:
                val = data.get(key)
                if val:
                    return round(float(val) / 1e9, 2)
        return None

    def get_dex_volume_24h(self) -> Optional[float]:
        """24h DEX volume in billions."""
        data = self._get("/overview/dexs")
        if data and isinstance(data, dict):
            total = data.get("total24h")
            if total:
                return round(float(total) / 1e9, 2)
            # Try sum of protocols
            protos = data.get("protocols", [])
            if protos:
                return round(sum(float(p.get("total24h", 0)) for p in protos) / 1e9, 2)
        return None

    def get_chain_tvl(self, chain: str = "Ethereum") -> Optional[float]:
        """TVL for a specific chain."""
        data = self._get(f"/v2/chains")
        if data and isinstance(data, list):
            for c in data:
                if c.get("name", "").lower() == chain.lower():
                    tvl = c.get("tvl") or c.get("total") or c.get("totalValueLocked")
                    if tvl:
                        return round(float(tvl) / 1e9, 2)
        return None

    def get_protocol_tvl(self, protocol: str) -> Optional[float]:
        """TVL for a specific protocol (e.g., 'aave', 'uniswap')."""
        data = self._get(f"/tvl/{protocol}")
        if data and isinstance(data, (int, float)):
            return round(float(data) / 1e9, 2)
        return None

    def get_token_mcap(self, token: str) -> Optional[float]:
        """Market cap for a token from /coins endpoints."""
        # DeFiLlama coins API: /coins/prices/current/{coin}
        data = self._get(f"/coins/prices/current/coingecko:{token}")
        if data and isinstance(data, dict):
            price = data.get("price")
            # We don't have supply from this endpoint easily
            return None  # Requires additional calls
        return None

    def get_crypto_tokens_summary(self, tokens: List[str]) -> Dict[str, Dict]:
        """Get on-chain summary for a list of crypto tickers."""
        results = {}
        # Map common tickers to DeFiLlama protocol slugs
        PROTO_MAP = {
            "BTC-USD": "bitcoin",
            "ETH-USD": "ethereum",
            "SOL-USD": "solana",
            "AVAX-USD": "avalanche",
            "ADA-USD": "cardano",
            "DOT-USD": "polkadot",
            "LINK-USD": "chainlink",
            "MATIC-USD": "polygon",
            "ARB-USD": "arbitrum",
            "OP-USD": "optimism",
            "UNI-USD": "uniswap",
            "AAVE-USD": "aave",
            "LDO-USD": "lido",
            "MKR-USD": "makerdao",
            "CRV-USD": "curve-finance",
        }
        for t in tokens:
            slug = PROTO_MAP.get(t)
            if slug:
                tvl = self.get_protocol_tvl(slug)
                results[t] = {
                    "tvl_b": tvl,
                    "source": "DeFiLlama",
                }
        return results

    def get_full_snapshot(self) -> Dict:
        """Complete DeFiLlama snapshot for orchestrator."""
        return {
            "ok": True,
            "tvl_b": self.get_tvl(),
            "stable_mcap_b": self.get_stablecoin_mcap(),
            "dex_vol_24h_b": self.get_dex_volume_24h(),
            "eth_tvl_b": self.get_chain_tvl("Ethereum"),
            "sol_tvl_b": self.get_chain_tvl("Solana"),
            "source": "DeFiLlama API (LIVE)",
        }


# Singleton
llama_api = DeFiLlamaAPI()


def get_tvl() -> Optional[float]:
    return llama_api.get_tvl()


def get_stablecoin_mcap() -> Optional[float]:
    return llama_api.get_stablecoin_mcap()


def get_dex_volume_24h() -> Optional[float]:
    return llama_api.get_dex_volume_24h()


def get_full_snapshot() -> Dict:
    return llama_api.get_full_snapshot()
