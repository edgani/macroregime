"""engines/bottleneck_discovery_v3.py — Multi-Market Adaptive · Reactive · Proactive Discovery

Covers: US Equities, Forex, Commodities, Crypto, IHSG (Indonesia), Bonds, Global/Country ETFs.
Integrates as PRE-FILTER before bottleneck_engine.py.

Modes:
  • REACTIVE  : Detect brewing bottlenecks from price/volume anomalies across FULL universe
  • ADAPTIVE  : Constraint scores auto-calibrate to macro regime, sector momentum, flow
  • PROACTIVE : Predict NEXT bottleneck layer from supply-chain chain logic + lead-lag
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# SUPPLY-CHAIN BOTTLENECK CHAIN — Cross-market, cross-asset
# ═══════════════════════════════════════════════════════════════════════════════
BOTTLENECK_CHAIN: Dict[str, Dict] = {
    # US / Global Tech
    "ai_compute": {
        "next": ["ai_memory", "ai_packaging", "ai_optics", "semis_taiwan", "semis_korea"],
        "lag_weeks": 8,
        "drivers": ["NVDA", "AMD", "AVGO", "TSM"],
        "narrative": "AI training chip demand overflow → memory + packaging + interconnect + foundry shortage",
    },
    "ai_memory": {
        "next": ["ai_packaging", "ai_power", "transformer_infra", "semis_korea"],
        "lag_weeks": 12,
        "drivers": ["MU", "SNDK"],
        "narrative": "HBM/flash shortage → advanced packaging + power density + thermal infra + Korea memory",
    },
    "ai_optics": {
        "next": ["ai_power_infra", "transformer_infra", "ai_packaging"],
        "lag_weeks": 16,
        "drivers": ["LITE", "COHR", "POET"],
        "narrative": "Photonics deployment → power draw per rack explodes → transformer/thermal bottleneck",
    },
    "ai_power": {
        "next": ["ai_power_infra", "transformer_infra", "uranium", "commodity_copper"],
        "lag_weeks": 20,
        "drivers": ["ON", "WOLF", "MPWR"],
        "narrative": "SiC/GaN power device shortage → data center power infra + grid upgrade + nuclear baseload + copper",
    },
    "ai_power_infra": {
        "next": ["transformer_infra", "uranium", "energy_infra", "commodity_copper", "commodity_aluminum"],
        "lag_weeks": 24,
        "drivers": ["VST", "ETN", "VRT", "GEV"],
        "narrative": "Data center power contracts → transformer lead times + baseload power + gas turbines + raw materials",
    },
    "transformer_infra": {
        "next": ["energy_infra", "commodity_copper", "commodity_aluminum", "indonesia_mining"],
        "lag_weeks": 28,
        "drivers": ["ETN", "VRT", "HUBB", "GEV"],
        "narrative": "Transformer/switchgear sold out → copper/aluminum wire + grid hardware + Indonesia mineral demand",
    },
    "semis_taiwan": {
        "next": ["ai_packaging", "ai_optics", "commodity_copper"],
        "lag_weeks": 10,
        "drivers": ["EWT", "TSM"],
        "narrative": "Taiwan foundry capacity maxed → packaging + interconnect + copper demand",
    },
    "semis_korea": {
        "next": ["ai_power", "transformer_infra", "commodity_nickel"],
        "lag_weeks": 14,
        "drivers": ["EWY", "MU"],
        "narrative": "Korea memory/HBM surge → power devices + thermal + nickel for batteries",
    },
    # Commodity → Indonesia chain
    "commodity_copper": {
        "next": ["transformer_infra", "indonesia_mining", "energy_infra"],
        "lag_weeks": 18,
        "drivers": ["HG=F", "CPER", "FCX"],
        "narrative": "Copper shortage → wiring demand + Indonesia copper/gold miners (MDKA, ANTM) + grid hardware",
    },
    "commodity_nickel": {
        "next": ["indonesia_mining", "semis_korea", "energy_infra"],
        "lag_weeks": 12,
        "drivers": ["INCO.JK", "NCKL.JK"],
        "narrative": "Nickel EV/battery demand → Indonesia nickel miners + Korea battery supply chain",
    },
    "oil_energy": {
        "next": ["shipping_supply_crisis", "indonesia_shipping", "indonesia_energy", "commodity_copper"],
        "lag_weeks": 10,
        "drivers": ["CL=F", "XLE", "USO"],
        "narrative": "Oil surge → tanker/OSV day rates spike → Indonesia shipping (SOCI, BULL, WINS) + energy infra",
    },
    "shipping_supply_crisis": {
        "next": ["indonesia_shipping", "indonesia_osv", "commodity_copper"],
        "lag_weeks": 8,
        "drivers": ["SOCI.JK", "BULL.JK", "SMDR.JK", "TMAS.JK", "PSSI.JK"],
        "narrative": "Global vessel shortage → Indonesia tanker/OSV day rates explode + dry bulk",
    },
    # Macro → EM → IHSG
    "dxy_bearish": {
        "next": ["em_fx", "ihsg_banks", "ihsg_consumer", "commodity_gold"],
        "lag_weeks": 6,
        "drivers": ["DX-Y.NYB", "USDIDR=X"],
        "narrative": "USD bearish TREND → EM FX relief → IHSG foreign flow → banking + consumer + gold bid",
    },
    "em_fx": {
        "next": ["ihsg_banks", "ihsg_property", "indonesia_commodity_supercycle"],
        "lag_weeks": 4,
        "drivers": ["EIDO", "USDIDR=X", "BBCA.JK"],
        "narrative": "EM FX rally → Indonesia foreign net buy → banks lead + property follow + commodity exporters",
    },
    # Defense
    "defense": {
        "next": ["commodity_nickel", "commodity_copper", "energy_infra", "aerospace"],
        "lag_weeks": 32,
        "drivers": ["LMT", "NOC", "RTX"],
        "narrative": "Munitions/missile production ramp → raw materials + energy for manufacturing",
    },
    # Healthcare
    "healthcare_eq": {
        "next": ["pharma", "commodity_copper"],
        "lag_weeks": 20,
        "drivers": ["ISRG", "ABT"],
        "narrative": "Robotic surgery install base → consumables + precision manufacturing metals",
    },
    # Indonesia-specific
    "indonesia_commodity_supercycle": {
        "next": ["indonesia_shipping", "indonesia_osv", "indonesia_energy", "indonesia_mining"],
        "lag_weeks": 6,
        "drivers": ["ITMG.JK", "ADRO.JK", "INCO.JK", "MDKA.JK"],
        "narrative": "Indonesia coal/nickel/CPO global bid → shipping demand + offshore drilling + mining expansion",
    },
    "indonesia_osv": {
        "next": ["indonesia_shipping", "indonesia_energy"],
        "lag_weeks": 4,
        "drivers": ["WINS.JK", "LEAD.JK", "SHIP.JK"],
        "narrative": "OSV day rates spike → tanker overflow + offshore energy service demand",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# NARRATIVE → CROSS-ASSET SPILLOVER MAP (all markets)
# ═══════════════════════════════════════════════════════════════════════════════
NARRATIVE_SPILLOVER: Dict[str, List[Tuple[str, float]]] = {
    "ai_compute": [
        ("TAO22974-USD", 0.85), ("RNDR-USD", 0.80), ("FET-USD", 0.75),
        ("EWT", 0.70), ("EWY", 0.65),
    ],
    "ai_memory": [
        ("TAO22974-USD", 0.70), ("RNDR-USD", 0.75), ("INJ-USD", 0.60),
        ("EWY", 0.75), ("MU", 0.80),
    ],
    "ai_optics": [
        ("TAO22974-USD", 0.90), ("RNDR-USD", 0.85), ("OCEAN-USD", 0.65),
    ],
    "ai_power": [
        ("BTC-USD", 0.55), ("ETH-USD", 0.50), ("VST", 0.85), ("ETN", 0.82),
    ],
    "ai_power_infra": [
        ("BTC-USD", 0.60), ("ETH-USD", 0.55), ("GEV", 0.85), ("VRT", 0.88),
    ],
    "transformer_infra": [
        ("HG=F", 0.70), ("CPER", 0.65), ("FCX", 0.60), ("ETN", 0.90),
    ],
    "commodity_copper": [
        ("HG=F", 0.95), ("CPER", 0.90), ("FCX", 0.85),
        ("MDKA.JK", 0.60), ("ANTM.JK", 0.55), ("INCO.JK", 0.50),
    ],
    "commodity_nickel": [
        ("INCO.JK", 0.90), ("NCKL.JK", 0.85), ("ANTM.JK", 0.60),
        ("EWY", 0.55),
    ],
    "oil_energy": [
        ("CL=F", 0.95), ("USO", 0.90), ("XLE", 0.85),
        ("SOCI.JK", 0.70), ("BULL.JK", 0.65), ("WINS.JK", 0.55),
        ("AKRA.JK", 0.50), ("ADRO.JK", 0.55),
    ],
    "shipping_supply_crisis": [
        ("SOCI.JK", 0.85), ("BULL.JK", 0.80), ("SMDR.JK", 0.75),
        ("TMAS.JK", 0.70), ("PSSI.JK", 0.65), ("WINS.JK", 0.75), ("LEAD.JK", 0.70),
    ],
    "dxy_bearish": [
        ("GLD", 0.80), ("GC=F", 0.75), ("BTC-USD", 0.60),
        ("EIDO", 0.75), ("BBCA.JK", 0.70), ("BBRI.JK", 0.60),
        ("USDIDR=X", 0.90), ("USDZAR=X", 0.70), ("USDBRL=X", 0.65),
    ],
    "em_fx": [
        ("EIDO", 0.85), ("BBCA.JK", 0.80), ("BBRI.JK", 0.70),
        ("USDIDR=X", 0.90), ("USDMXN=X", 0.75), ("USDBRL=X", 0.70),
    ],
    "defense": [
        ("LINK-USD", 0.45), ("AAVE-USD", 0.40), ("LMT", 0.95), ("NOC", 0.90),
        ("RTX", 0.85), ("KTOS", 0.70),
    ],
    "precious_metals": [
        ("BTC-USD", 0.70), ("GLD", 0.95), ("GC=F", 0.90),
        ("ANTM.JK", 0.55), ("MDKA.JK", 0.50),
    ],
    "uranium": [
        ("BTC-USD", 0.55), ("URA", 0.95), ("CCJ", 0.90), ("NXE", 0.80),
    ],
    "indonesia_commodity_supercycle": [
        ("ITMG.JK", 0.90), ("ADRO.JK", 0.85), ("PTBA.JK", 0.80),
        ("INCO.JK", 0.85), ("MDKA.JK", 0.80), ("ANTM.JK", 0.75),
        ("WINS.JK", 0.70), ("LEAD.JK", 0.65), ("SOCI.JK", 0.60),
        ("EIDO", 0.80),
    ],
    "indonesia_osv": [
        ("WINS.JK", 0.90), ("LEAD.JK", 0.85), ("SHIP.JK", 0.75), ("ELSA.JK", 0.70),
    ],
    "depin_ai": [
        ("TAO22974-USD", 1.00), ("RNDR-USD", 0.90), ("HNT-USD", 0.70),
        ("FET-USD", 0.75), ("OCEAN-USD", 0.65),
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# MARKET-SPECIFIC BREWING SIGNATURES
# ═══════════════════════════════════════════════════════════════════════════════
MARKET_BREWING_CONFIG: Dict[str, Dict] = {
    "us_equity": {
        "min_days": 30,
        "acc_threshold": 0.55,
        "range_threshold": 0.70,
        "rs_boost": True,
        "volatility_filter": False,
    },
    "forex": {
        "min_days": 30,
        "acc_threshold": 0.50,
        "range_threshold": 0.65,
        "rs_boost": True,
        "volatility_filter": True,
    },
    "commodity": {
        "min_days": 30,
        "acc_threshold": 0.50,
        "range_threshold": 0.60,
        "rs_boost": True,
        "volatility_filter": True,
    },
    "crypto": {
        "min_days": 30,
        "acc_threshold": 0.50,
        "range_threshold": 0.65,
        "rs_boost": True,
        "volatility_filter": True,
    },
    "ihsg": {
        "min_days": 30,
        "acc_threshold": 0.50,
        "range_threshold": 0.65,
        "rs_boost": True,
        "volatility_filter": False,
        "foreign_flow_proxy": True,
    },
    "bonds": {
        "min_days": 30,
        "acc_threshold": 0.45,
        "range_threshold": 0.60,
        "rs_boost": True,
        "volatility_filter": False,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class DiscoveredCandidate:
    ticker: str
    sector: str
    market: str
    discovery_mode: str
    constraint: float
    base_constraint: float
    regime_adjustment: float
    flow_adjustment: float
    trend_score: float
    rs_3m: Optional[float]
    rs_1m: Optional[float]
    acc: float
    range_pos: float
    range_label: str
    pct_from_hi: float
    pct_from_lo: float
    ev: float
    level: str
    brewing_score: float
    narrative: str
    spillover_targets: List[Tuple[str, float]] = field(default_factory=list)
    proactive_eta_weeks: Optional[int] = None
    proactive_probability: Optional[float] = None
    catalyst_proxy: str = ""
    risk_proxy: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
class BottleneckDiscoveryV3:
    def __init__(self, settings_module):
        self.cfg = settings_module
        self.profiles = getattr(settings_module, "BOTTLENECK_PROFILES", {})
        self.sector_map = getattr(settings_module, "TICKER_SECTOR", {})
        self.market_map = getattr(settings_module, "MARKET_CLASSIFICATION", {})
        self.quad_direction = getattr(settings_module, "QUAD_MARKET_DIRECTION", {})
        self.quad_playbook = getattr(settings_module, "QUAD_ASSET_PERFORMANCE", {})
        self.us_buckets = getattr(settings_module, "US_BUCKETS", {})
        self.ihsg_buckets = getattr(settings_module, "IHSG_BUCKETS", {})
        self.fx_buckets = getattr(settings_module, "FX_BUCKETS", {})
        self.comm_buckets = getattr(settings_module, "COMMODITY_BUCKETS", {})
        self.crypto_buckets = getattr(settings_module, "CRYPTO_BUCKETS", {})

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _ret(s: pd.Series, n: int) -> Optional[float]:
        if s is None or len(s) < n + 1:
            return None
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 1:
            return None
        try:
            return float(s.iloc[-1] / s.iloc[-n - 1] - 1)
        except Exception:
            return None

    @staticmethod
    def _rs(close: pd.Series, bench: Optional[pd.Series], n: int = 63) -> Optional[float]:
        if bench is None:
            return None
        try:
            c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
            b = pd.to_numeric(bench, errors="coerce").dropna().tail(n)
            if len(c) < 20 or len(b) < 20:
                return None
            cr = c.pct_change().dropna().values
            br = b.pct_change().dropna().values
            min_len = min(len(cr), len(br))
            cr, br = cr[-min_len:], br[-min_len:]
            if len(cr) < 5:
                return None
            return float(np.mean(cr) - np.mean(br))
        except Exception:
            return None

    @staticmethod
    def _vol_acc(close: pd.Series, n: int = 63) -> float:
        try:
            c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
            if len(c) < 30:
                return 0.0
            v = c.pct_change().dropna().values
            up = v > 0
            uv = float(np.mean(v[up])) if up.any() else float(np.mean(v))
            dv = float(np.mean(v[~up])) if (~up).any() else float(np.mean(v))
            return float(np.clip(0.5 * (uv / (abs(dv) + 1e-10)), 0.0, 1.0))
        except Exception:
            return 0.5

    @staticmethod
    def _trend(close: pd.Series, n: int = 63) -> Tuple[bool, bool, str]:
        c = pd.to_numeric(close, errors="coerce").dropna().tail(n).values
        if len(c) < 20:
            return False, False, "insufficient"
        half = max(len(c) // 3, 5)
        hh = float(np.max(c[-half:])) > float(np.max(c[:half])) * 1.003
        hl = float(np.min(c[-half:])) > float(np.min(c[:half])) * 1.003
        lh = float(np.max(c[-half:])) < float(np.max(c[:half])) * 0.997
        ll = float(np.min(c[-half:])) < float(np.min(c[:half])) * 0.997
        if hh and hl:
            return True, True, "uptrend"
        if lh and ll:
            return False, False, "downtrend"
        return hh, hl, "range"

    @staticmethod
    def _range_pos(close: pd.Series, n: int = 63) -> Tuple[float, str]:
        c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
        if len(c) < 20:
            return 0.5, "mid_range"
        lo, hi = float(c.min()), float(c.max())
        px = float(c.iloc[-1])
        span = hi - lo
        if span < 1e-9:
            return 0.5, "mid_range"
        rp = (px - lo) / span
        if rp >= 0.90:
            label = "at_resistance"
        elif rp >= 0.75:
            label = "approaching_breakout"
        elif rp <= 0.10:
            label = "at_support"
        else:
            label = "mid_range"
        return rp, label

    @staticmethod
    def _volatility_regime(close: pd.Series, n: int = 63) -> str:
        try:
            c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
            if len(c) < 30:
                return "normal"
            rv = float(c.pct_change().dropna().tail(21).std() * math.sqrt(252))
            if rv > 0.80:
                return "extreme"
            if rv > 0.50:
                return "high"
            if rv < 0.20:
                return "low"
            return "normal"
        except Exception:
            return "normal"

    # ── ADAPTIVE: Dynamic constraint per market & regime ──────────────────────
    def adaptive_constraint(
        self, ticker: str, sector: str, market: str, quad_str: str,
        sector_momentum: Optional[float] = None,
        flow_score: Optional[float] = None,
        fundamental_proxy: Optional[Dict] = None,
    ) -> Tuple[float, float, float, float]:
        prof = self.profiles.get(sector, self.profiles.get("generic", {"constraint": 0.20}))
        base = float(prof.get("constraint", 0.20))

        # Regime adjustment
        regime_adj = 0.0
        qk = quad_str.upper()
        structural_sectors = {
            "ai_optics", "ai_power", "ai_power_infra", "transformer_infra",
            "healthcare_eq", "defense", "utilities", "precious_metals",
            "uranium", "water", "staples", "depin_ai",
        }
        if qk in ("Q3", "Q4") and sector in structural_sectors:
            regime_adj += 0.08
        if qk in ("Q1", "Q2") and sector in {"ai_compute", "ai_networking", "energy_infra", "coal", "nickel", "cpo_palm"}:
            regime_adj += 0.06

        # Market-specific regime boost
        if market == "ihsg" and qk in ("Q2", "Q1"):
            regime_adj += 0.05
        if market == "commodity" and qk in ("Q2", "Q3"):
            regime_adj += 0.06
        if market == "crypto" and qk == "Q1":
            regime_adj += 0.10
        if market == "bonds" and qk in ("Q3", "Q4"):
            regime_adj += 0.08

        # Flow adjustment
        flow_adj = 0.0
        if sector_momentum is not None and math.isfinite(sector_momentum):
            flow_adj += np.clip(sector_momentum * 2.0, -0.05, 0.10)
        if flow_score is not None and math.isfinite(flow_score):
            flow_adj += np.clip(flow_score * 0.10, -0.05, 0.08)

        # Fundamental proxy
        fund_adj = 0.0
        if fundamental_proxy:
            if fundamental_proxy.get("supply_squeeze_detected"):
                fund_adj += 0.12
            if fundamental_proxy.get("capex_surge_detected"):
                fund_adj += 0.06
            if fundamental_proxy.get("lead_time_weeks", 0) > 26:
                fund_adj += 0.08

        final = float(np.clip(base + regime_adj + flow_adj + fund_adj, 0.0, 1.0))
        return final, base, regime_adj, flow_adj

    # ── BENCHMARK SELECTOR per market ─────────────────────────────────────────
    def _select_benchmark(self, market: str, prices: Dict) -> Optional[pd.Series]:
        bench_map = {
            "us_equity": "SPY",
            "forex": "DX-Y.NYB",
            "commodity": "GC=F",
            "crypto": "BTC-USD",
            "ihsg": "EIDO",
            "bonds": "TLT",
        }
        b = bench_map.get(market, "SPY")
        return prices.get(b)

    # ── REACTIVE: Multi-market scan ───────────────────────────────────────────
    def reactive_scan(
        self,
        prices: Dict[str, pd.Series],
        volumes: Optional[Dict[str, pd.Series]] = None,
        quad_str: str = "Q3",
        sector_momentum: Optional[Dict[str, float]] = None,
        flow_scores: Optional[Dict[str, float]] = None,
        top_n: int = 50,
    ) -> List[DiscoveredCandidate]:
        candidates: List[DiscoveredCandidate] = []

        for ticker, close in prices.items():
            close = pd.to_numeric(close, errors="coerce").dropna()
            if len(close) < 30:
                continue

            sector = self.sector_map.get(ticker, "generic")
            market = self.market_map.get(ticker, "us_equity")
            cfg = MARKET_BREWING_CONFIG.get(market, MARKET_BREWING_CONFIG["us_equity"])

            # Benchmark
            bench = self._select_benchmark(market, prices)
            if market == "ihsg":
                eido = prices.get("EIDO")
                if eido is not None:
                    bench = eido

            # Trend
            hh, hl, trd = self._trend(close, 63)
            trend_score = 1.0 if trd == "uptrend" else 0.5 if trd == "range" else 0.0

            # RS
            rs3 = self._rs(close, bench, 63)
            rs21 = self._rs(close, bench, 21)

            # Volume accumulation
            acc = self._vol_acc(close, 63)

            # Range position
            rp, rp_label = self._range_pos(close, 63)

            # 52w
            hi52 = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
            lo52 = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
            px = float(close.iloc[-1])
            pct_from_hi = (px - hi52) / max(hi52, 1e-9)
            pct_from_lo = (px - lo52) / max(lo52, 1e-9)

            # Volatility regime filter (for FX, commodity, crypto)
            vol_reg = self._volatility_regime(close, 63)
            if cfg.get("volatility_filter") and vol_reg == "extreme":
                continue

            # Adaptive constraint
            sm = sector_momentum.get(sector) if sector_momentum else None
            fs = flow_scores.get(ticker) if flow_scores else None
            constraint, base_c, reg_adj, flow_adj = self.adaptive_constraint(
                ticker, sector, market, quad_str, sm, fs
            )

            # Brewing signature (market-tuned)
            brewing_sig = 0.0
            if constraint >= 0.60:
                brewing_sig += 0.20
            if acc >= cfg["acc_threshold"]:
                brewing_sig += 0.15
            if rp >= cfg["range_threshold"] and rp < 0.95:
                brewing_sig += 0.20
            if rs3 is not None and rs3 > 0.02:
                brewing_sig += 0.15
            if pct_from_hi < -0.05 and pct_from_lo > 0.15:
                brewing_sig += 0.15
            if trd in ("uptrend", "range"):
                brewing_sig += 0.15

            # Market-specific bonuses
            if market == "forex" and abs(rs3 or 0) > 0.03 and vol_reg in ("low", "normal"):
                brewing_sig += 0.10
            if market == "commodity" and pct_from_lo > 0.30 and acc >= 0.55:
                brewing_sig += 0.10
            if market == "ihsg" and pct_from_hi < -0.15 and acc >= 0.50:
                brewing_sig += 0.10
            if market == "bonds" and trd == "uptrend" and (rs3 or 0) > 0.01:
                brewing_sig += 0.10

            # Level
            if brewing_sig >= 0.70 and rp >= 0.75 and trd in ("uptrend", "range"):
                level = "level_1"
            elif brewing_sig >= 0.55 and constraint >= 0.55:
                level = "watch"
            else:
                level = "avoid"

            # EV
            regime_fit = float(self.profiles.get(sector, {}).get(quad_str, 0.5))
            ev = regime_fit * trend_score * constraint * (1.0 + (rs3 or 0.0))
            ev = float(np.clip(ev, -2.0, 2.0))

            # Narrative
            narrative = BOTTLENECK_CHAIN.get(sector, {}).get("narrative", f"{sector} supply/demand imbalance")

            if brewing_sig >= 0.50:
                candidates.append(DiscoveredCandidate(
                    ticker=ticker, sector=sector, market=market,
                    discovery_mode="reactive", constraint=round(constraint, 2),
                    base_constraint=round(base_c, 2), regime_adjustment=round(reg_adj, 3),
                    flow_adjustment=round(flow_adj, 3), trend_score=round(trend_score, 2),
                    rs_3m=round(rs3, 4) if rs3 is not None else None,
                    rs_1m=round(rs21, 4) if rs21 is not None else None,
                    acc=round(acc, 2), range_pos=round(rp, 2), range_label=rp_label,
                    pct_from_hi=round(pct_from_hi, 3), pct_from_lo=round(pct_from_lo, 3),
                    ev=round(ev, 3), level=level, brewing_score=round(brewing_sig, 3),
                    narrative=narrative,
                ))

        candidates.sort(key=lambda x: x.brewing_score * x.ev, reverse=True)
        return candidates[:top_n]

    # ── PROACTIVE: Predict next layer ─────────────────────────────────────────
    def proactive_chain(
        self,
        surging_sectors: List[str],
        prices: Dict[str, pd.Series],
        quad_str: str = "Q3",
        top_n: int = 20,
    ) -> List[DiscoveredCandidate]:
        predictions: List[DiscoveredCandidate] = []
        for surging_sector in surging_sectors:
            chain = BOTTLENECK_CHAIN.get(surging_sector)
            if not chain:
                continue
            for next_sector in chain["next"]:
                prof = self.profiles.get(next_sector, self.profiles.get("generic"))
                base_c = float(prof.get("constraint", 0.20))
                regime_fit = float(prof.get(quad_str, 0.5))
                tickers = [t for t, s in self.sector_map.items() if s == next_sector]
                for ticker in tickers:
                    close = prices.get(ticker)
                    if close is None or len(pd.to_numeric(close, errors="coerce").dropna()) < 30:
                        continue
                    close = pd.to_numeric(close, errors="coerce").dropna()
                    hh, hl, trd = self._trend(close, 63)
                    trend_score = 1.0 if trd == "uptrend" else 0.5 if trd == "range" else 0.0
                    rp, rp_label = self._range_pos(close, 63)
                    acc = self._vol_acc(close, 63)
                    ev = regime_fit * max(trend_score, 0.3) * base_c * 1.0
                    ev = float(np.clip(ev, -2.0, 2.0))
                    spill = NARRATIVE_SPILLOVER.get(next_sector, [])
                    predictions.append(DiscoveredCandidate(
                        ticker=ticker, sector=next_sector,
                        market=self.market_map.get(ticker, "us_equity"),
                        discovery_mode="proactive", constraint=round(base_c, 2),
                        base_constraint=round(base_c, 2), regime_adjustment=0.0,
                        flow_adjustment=0.0, trend_score=round(trend_score, 2),
                        rs_3m=None, rs_1m=None, acc=round(acc, 2),
                        range_pos=round(rp, 2), range_label=rp_label,
                        pct_from_hi=0.0, pct_from_lo=0.0, ev=round(ev, 3),
                        level="watch", brewing_score=0.0, narrative=chain["narrative"],
                        spillover_targets=spill,
                        proactive_eta_weeks=chain["lag_weeks"],
                        proactive_probability=round(base_c * regime_fit, 2),
                        catalyst_proxy=f"{surging_sector} bottleneck overflow → {next_sector} in ~{chain['lag_weeks']}w",
                        risk_proxy="Pre-breakout; may never materialize if upstream demand stalls",
                    ))
        predictions.sort(key=lambda x: x.proactive_probability or 0.0, reverse=True)
        return predictions[:top_n]

    # ── SPILLOVER: Cross-market lead-lag ──────────────────────────────────────
    def spillover_detect(
        self,
        surging_ticker: str,
        surging_prices: pd.Series,
        target_universe: List[str],
        prices: Dict[str, pd.Series],
        lookback: int = 63,
        min_correlation: float = 0.25,
    ) -> List[Dict]:
        s = pd.to_numeric(surging_prices, errors="coerce").dropna().tail(lookback)
        if len(s) < 30:
            return []
        sr = s.pct_change().dropna().values
        results = []
        for target in target_universe:
            t = prices.get(target)
            if t is None:
                continue
            t = pd.to_numeric(t, errors="coerce").dropna().tail(lookback)
            if len(t) < 30:
                continue
            tr = t.pct_change().dropna().values
            min_len = min(len(sr), len(tr))
            if min_len < 20:
                continue
            sr_, tr_ = sr[-min_len:], tr[-min_len:]
            corr = float(np.corrcoef(sr_, tr_)[0, 1]) if len(sr_) > 1 else 0.0
            if math.isnan(corr) or abs(corr) < min_correlation:
                continue
            best_lag = 0
            best_lag_corr = abs(corr)
            for lag in range(1, 6):
                if len(sr_) <= lag or len(tr_) <= lag:
                    break
                c = float(np.corrcoef(sr_[:-lag], tr_[lag:])[0, 1])
                if not math.isnan(c) and abs(c) > best_lag_corr:
                    best_lag_corr = abs(c)
                    best_lag = lag
            surging_ret = float(s.iloc[-1] / s.iloc[0] - 1)
            target_ret = float(t.iloc[-1] / t.iloc[0] - 1)
            perf_gap = target_ret - surging_ret
            surging_sector = self.sector_map.get(surging_ticker, "generic")
            target_sector = self.sector_map.get(target, "generic")
            narr_match = 0.0
            if surging_sector in NARRATIVE_SPILLOVER:
                for tok, score in NARRATIVE_SPILLOVER[surging_sector]:
                    if tok == target:
                        narr_match = score
                        break
            results.append({
                "surging": surging_ticker, "target": target,
                "correlation": round(corr, 3), "lead_lag_days": best_lag,
                "lead_lag_corr": round(best_lag_corr, 3),
                "surging_ret_63d": round(surging_ret, 3),
                "target_ret_63d": round(target_ret, 3),
                "performance_gap": round(perf_gap, 3),
                "narrative_match": round(narr_match, 2),
                "spillover_score": round(
                    (abs(corr) * 0.3) + (max(0, -perf_gap) * 2.0) + (narr_match * 0.4) + (best_lag_corr * 0.3),
                    3
                ),
                "verdict": "lagging_narrative" if perf_gap < -0.05 and narr_match > 0.5 else
                           "lagging_correlation" if perf_gap < -0.05 else
                           "synced" if abs(perf_gap) < 0.03 else "leading",
            })
        results.sort(key=lambda x: x["spillover_score"], reverse=True)
        return results

    # ── MAIN RUN ──────────────────────────────────────────────────────────────
    def run(
        self,
        prices: Dict[str, pd.Series],
        volumes: Optional[Dict[str, pd.Series]] = None,
        quad_str: str = "Q3",
        quad_mon: str = "Q2",
        asset_ranges: Optional[Dict] = None,
        sector_momentum: Optional[Dict[str, float]] = None,
        flow_scores: Optional[Dict[str, float]] = None,
        proactive_surging_sectors: Optional[List[str]] = None,
        top_n: int = 50,
    ) -> Dict:
        reactive = self.reactive_scan(prices, volumes, quad_str, sector_momentum, flow_scores, top_n)
        surging = proactive_surging_sectors or []
        if not surging and reactive:
            surging = list({c.sector for c in reactive if c.brewing_score >= 0.70})
        proactive = self.proactive_chain(surging, prices, quad_str, top_n)

        # Multi-market spillover
        spillover = []
        market_buckets = {"crypto": [], "ihsg": [], "forex": [], "commodity": [], "bonds": []}
        for mkt, tickers in [("crypto", [t for t in prices if self.market_map.get(t) == "crypto"]),
                              ("ihsg", [t for t in prices if t.endswith(".JK")]),
                              ("forex", [t for t in prices if self.market_map.get(t) == "forex"]),
                              ("commodity", [t for t in prices if self.market_map.get(t) == "commodity"]),
                              ("bonds", [t for t in prices if self.market_map.get(t) == "bonds"])]:
            market_buckets[mkt] = tickers

        for c in reactive[:5]:
            for mkt, univ in market_buckets.items():
                if not univ:
                    continue
                sp = self.spillover_detect(c.ticker, prices[c.ticker], univ, prices, 63, 0.20)
                for row in sp:
                    if row["verdict"] in ("lagging_narrative", "lagging_correlation"):
                        row["source_narrative"] = c.narrative
                        row["source_market"] = c.market
                        spillover.append(row)

        spillover.sort(key=lambda x: x["spillover_score"], reverse=True)

        all_tickers = {c.ticker for c in reactive} | {c.ticker for c in proactive}
        return {
            "reactive": [self._to_dict(c) for c in reactive],
            "proactive": [self._to_dict(c) for c in proactive],
            "spillover": spillover[:top_n],
            "meta": {
                "universe_scanned": len(prices),
                "reactive_found": len(reactive),
                "proactive_predicted": len(proactive),
                "spillover_links": len(spillover),
                "unique_candidates": len(all_tickers),
                "quad": quad_str, "monthly_quad": quad_mon,
            },
        }

    @staticmethod
    def _to_dict(c: DiscoveredCandidate) -> Dict:
        return {
            "ticker": c.ticker, "sector": c.sector, "market": c.market,
            "discovery_mode": c.discovery_mode, "constraint": c.constraint,
            "base_constraint": c.base_constraint, "regime_adjustment": c.regime_adjustment,
            "flow_adjustment": c.flow_adjustment, "trend_score": c.trend_score,
            "rs_3m": c.rs_3m, "rs_1m": c.rs_1m, "acc": c.acc,
            "range_pos": c.range_pos, "range_label": c.range_label,
            "pct_from_hi": c.pct_from_hi, "pct_from_lo": c.pct_from_lo,
            "ev": c.ev, "level": c.level, "brewing_score": c.brewing_score,
            "narrative": c.narrative, "spillover_targets": c.spillover_targets,
            "proactive_eta_weeks": c.proactive_eta_weeks,
            "proactive_probability": c.proactive_probability,
            "catalyst_proxy": c.catalyst_proxy, "risk_proxy": c.risk_proxy,
        }