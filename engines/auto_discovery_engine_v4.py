"""engines/auto_discovery_engine_v4.py — ROBUSTNESS FIX

FIXES:
1. All .iloc accesses guarded with isinstance(pd.Series) checks
2. Empty prices handled gracefully (returns empty but valid result)
3. _detect_volume_spike safe for non-pandas input
4. run() signature unchanged: run(prices, gip_result=None, risk_ranges=None)
"""
from __future__ import annotations
import re, math, json, os, time, logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Bottleneck Keyword Lexicon ──────────────────────────────────────────────
BOTTLENECK_KEYWORDS = {
    "capacity_constraint": [
        "at capacity", "sold out", "booked solid", "backlog", "waitlist",
        "lead time extended", "delivery delay", "supply constrained",
        "can't keep up with demand", "production maxed", "running flat out",
    ],
    "pricing_power": [
        "raised prices", "price increase", "pass through costs", "pricing power",
        "margin expansion", "higher realization", "price hike accepted",
    ],
    "scarcity": [
        "shortage", "tight supply", "limited availability", "allocation",
        "rationing", "inventory draw", "stockout", "depleted",
    ],
    "investment_cycle": [
        "capex expansion", "building new facility", "greenfield", "brownfield",
        "capacity addition", "ramping production", "debottlenecking",
        "expansion project", "new line", "doubling capacity",
    ],
    "regulatory_moat": [
        "licensing bottleneck", "permit delayed", "regulatory approval",
        "EPA review", "FDA backlog", "ITC ruling", "tariff protection",
        "import quota", "export license",
    ],
    "labor_bottleneck": [
        "labor shortage", "skilled worker gap", "hiring challenge",
        "wage pressure", "union negotiation", "strike risk",
    ],
}

EMERGING_THEMES = {
    "ai_power": {
        "triggers": ["data center power", "AI energy consumption", "gigawatt", "nuclear for AI", "SMR data center"],
        "commodity_link": ["uranium", "natural gas", "copper"],
        "downstream_sectors": ["utilities", "power_infra", "nuclear"],
    },
    "quantum_readiness": {
        "triggers": ["quantum advantage", "post-quantum cryptography", "NIST quantum", "QKD"],
        "commodity_link": ["helium", "cryogenics"],
        "downstream_sectors": ["cybersecurity", "semiconductors"],
    },
    "space_debris": {
        "triggers": ["orbital debris", "satellite collision", "Kessler syndrome", "active debris removal"],
        "commodity_link": [],
        "downstream_sectors": ["space", "defense"],
    },
    "carbon_border_tax": {
        "triggers": ["CBAM", "carbon border adjustment", "EU carbon tax", " Scope 3"],
        "commodity_link": ["steel", "aluminum", "cement"],
        "downstream_sectors": ["steel", "materials", "industrials"],
    },
    "biomanufacturing": {
        "triggers": ["bioreactor capacity", "CDMO bottleneck", "cell therapy manufacturing", "viral vector shortage"],
        "commodity_link": [],
        "downstream_sectors": ["pharma", "biotech"],
    },
    "critical_minerals": {
        "triggers": ["rare earth processing", "downstream refining", "China export ban", "Inoact"],
        "commodity_link": ["rare earths", "lithium", "graphite", "cobalt"],
        "downstream_sectors": ["materials", "batteries", "EV"],
    },
    "water_scarcity": {
        "triggers": ["aquifer depletion", "desalination", "water rights", "Colorado River"],
        "commodity_link": ["water"],
        "downstream_sectors": ["water", "agriculture", "utilities"],
    },
    "aging_infrastructure": {
        "triggers": ["bridge collapse", "grid modernization", "transformer shortage", "transmission bottleneck"],
        "commodity_link": ["copper", "steel", "aluminum"],
        "downstream_sectors": ["industrials", "utilities", "materials"],
    },
}

@dataclass
class DiscoveryCandidate:
    name: str
    category: str
    stage: str
    confidence: float
    signals: Dict[str, float] = field(default_factory=dict)
    tickers: List[str] = field(default_factory=list)
    thesis: str = ""
    invalidators: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    first_detected: str = ""
    last_updated: str = ""


class AutoDiscoveryEngineV4:
    def __init__(self, data_dir: str = "data/discovery_cache"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.candidates: List[DiscoveryCandidate] = []
        self.known_tickers: Set[str] = set()
        self.theme_history: Dict[str, List[float]] = defaultdict(list)

    def run(self, prices: Dict, gip_result=None, risk_ranges=None) -> Dict:
        """Main entry point - called by orchestrator."""
        logger.info("AutoDiscoveryEngineV4: Starting discovery cycle...")

        # Guard: empty or malformed prices
        if not prices:
            logger.warning("V4 received empty prices — returning empty result")
            return self._empty_result()

        # Validate that price values are pandas-like
        valid_prices = {}
        for k, v in prices.items():
            if isinstance(v, pd.Series) and len(v) >= 5:
                valid_prices[k] = v
            elif isinstance(v, (list, tuple)) and len(v) >= 5:
                valid_prices[k] = pd.Series(v)
            # else skip
        if not valid_prices:
            logger.warning("V4: no valid price series found (need pd.Series or list with len>=5)")
            return self._empty_result()

        prices = valid_prices

        # 1. Load existing candidates
        self._load_cache()

        # 2. Multi-source signal detection
        signals = []
        signals.extend(self._scan_earnings_keywords(prices))
        signals.extend(self._scan_news_headlines())
        signals.extend(self._scan_commodity_spikes(prices))
        signals.extend(self._scan_supply_chain_disruptions(prices))
        signals.extend(self._detect_emerging_themes(prices))
        signals.extend(self._scan_patent_filings())
        signals.extend(self._scan_job_postings())

        # 3. Score and deduplicate
        new_candidates = self._score_signals(signals)
        self._merge_candidates(new_candidates)

        # 4. Promote stages based on corroboration
        self._promote_stages()

        # 5. Map to tickers
        self._map_to_tickers(prices)

        # 6. Save cache
        self._save_cache()

        # 7. Build output
        active = [c for c in self.candidates if c.stage == "active"]
        building = [c for c in self.candidates if c.stage == "building"]
        brewing = [c for c in self.candidates if c.stage in ("pre_consensus", "early")]

        return {
            "ok": True,
            "candidates": [self._candidate_to_dict(c) for c in self.candidates],
            "active": [self._candidate_to_dict(c) for c in active],
            "building": [self._candidate_to_dict(c) for c in building],
            "brewing": [self._candidate_to_dict(c) for c in brewing],
            "total": len(self.candidates),
            "new_this_run": len(new_candidates),
            "signals_harvested": len(signals),
        }

    def _empty_result(self):
        return {
            "ok": True,
            "candidates": [],
            "active": [],
            "building": [],
            "brewing": [],
            "total": 0,
            "new_this_run": 0,
            "signals_harvested": 0,
            "note": "No valid price data for discovery",
        }

    def _load_cache(self):
        cache_file = os.path.join(self.data_dir, "candidates.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                self.candidates = [self._dict_to_candidate(d) for d in data.get("candidates", [])]
                logger.info(f"Loaded {len(self.candidates)} cached candidates")
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")

    def _save_cache(self):
        cache_file = os.path.join(self.data_dir, "candidates.json")
        try:
            with open(cache_file, "w") as f:
                json.dump({
                    "candidates": [self._candidate_to_dict(c) for c in self.candidates],
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    # ── SIGNAL HARVESTERS ──────────────────────────────────────────────────────

    def _scan_earnings_keywords(self, prices: Dict) -> List[Dict]:
        signals = []
        for ticker, series in prices.items():
            if len(series) < 20:
                continue
            try:
                ret_5d = float(series.iloc[-1] / series.iloc[-6] - 1) if len(series) >= 6 else 0
                vol_spike = self._detect_volume_spike(series)
                if ret_5d > 0.15 and vol_spike > 2.0:
                    signals.append({
                        "type": "earnings_proxy",
                        "ticker": ticker,
                        "strength": min(ret_5d * 3, 1.0),
                        "note": f"{ticker} +{ret_5d:.1%} in 5D with {vol_spike:.1f}x volume — possible bottleneck revelation",
                    })
            except Exception as e:
                logger.debug(f"Earnings scan error for {ticker}: {e}")
        return signals

    def _scan_news_headlines(self) -> List[Dict]:
        return []  # Placeholder — integrate your preferred news API

    def _scan_commodity_spikes(self, prices: Dict) -> List[Dict]:
        signals = []
        commodity_tickers = {
            "CL=F": "oil", "BZ=F": "brent", "NG=F": "natural_gas",
            "GC=F": "gold", "SI=F": "silver", "HG=F": "copper",
            "ZW=F": "wheat", "ZC=F": "corn", "ZS=F": "soybeans",
            "ALI=F": "aluminum", "PL=F": "platinum",
        }
        for ticker, commodity in commodity_tickers.items():
            s = prices.get(ticker)
            if s is None or len(s) < 20:
                continue
            try:
                ret_1m = float(s.iloc[-1] / s.iloc[-21] - 1) if len(s) >= 21 else 0
                ret_3m = float(s.iloc[-1] / s.iloc[-63] - 1) if len(s) >= 63 else 0
                if ret_1m > 0.15 or ret_3m > 0.30:
                    strength = min(abs(ret_3m) * 2, 1.0)
                    signals.append({
                        "type": "commodity_spike",
                        "commodity": commodity,
                        "ticker": ticker,
                        "strength": strength,
                        "note": f"{commodity.upper()} spike: 1M {ret_1m:+.1%}, 3M {ret_3m:+.1%} — downstream bottlenecks likely",
                    })
            except Exception as e:
                logger.debug(f"Commodity scan error for {ticker}: {e}")
        return signals

    def _scan_supply_chain_disruptions(self, prices: Dict) -> List[Dict]:
        signals = []
        freight_tickers = {
            "BDRY": "Baltic Dry Index",
            "WMT": "Walmart (inventory proxy)",
            "AMZN": "Amazon (logistics proxy)",
        }
        for ticker, desc in freight_tickers.items():
            s = prices.get(ticker)
            if s is None or len(s) < 63:
                continue
            try:
                ret_3m = float(s.iloc[-1] / s.iloc[-63] - 1)
                if abs(ret_3m) > 0.20:
                    signals.append({
                        "type": "freight_proxy",
                        "ticker": ticker,
                        "strength": min(abs(ret_3m), 1.0),
                        "note": f"{desc} moving {ret_3m:+.1%} in 3M — supply chain stress signal",
                    })
            except Exception as e:
                logger.debug(f"Freight scan error for {ticker}: {e}")
        return signals

    def _detect_emerging_themes(self, prices: Dict) -> List[Dict]:
        signals = []
        theme_groups = {
            "nuclear_renaissance": ["URA", "CCJ", "SMR", "OKLO", "NNE", "LEU"],
            "ai_power": ["VST", "CEG", "GEV", "VRT", "ETN", "NEE"],
            "quantum": ["IONQ", "RGTI", "QBTS", "IBM"],
            "space": ["RKLB", "ASTS", "SPIR", "PL"],
            "carbon_capture": ["PLUG", "BE", "FCEL", "CMI"],
        }
        for theme, tickers in theme_groups.items():
            bullish_count = 0
            total = 0
            avg_ret = 0.0
            for t in tickers:
                s = prices.get(t)
                if s is None or len(s) < 21:
                    continue
                total += 1
                try:
                    ret_1m = float(s.iloc[-1] / s.iloc[-21] - 1)
                except Exception:
                    continue
                avg_ret += ret_1m
                if ret_1m > 0.05:
                    bullish_count += 1
            if total >= 3:
                breadth = bullish_count / total
                avg_ret /= total
                if breadth > 0.5 and avg_ret > 0.05:
                    signals.append({
                        "type": "theme_cluster",
                        "theme": theme,
                        "strength": min(breadth * avg_ret * 10, 1.0),
                        "note": f"{theme}: {breadth:.0%} of components bullish, avg +{avg_ret:.1%}",
                    })
        return signals

    def _scan_patent_filings(self) -> List[Dict]:
        return []

    def _scan_job_postings(self) -> List[Dict]:
        return []

    # ── SCORING & DEDUPLICATION ──────────────────────────────────────────────

    def _score_signals(self, signals: List[Dict]) -> List[DiscoveryCandidate]:
        candidates = []
        by_theme = defaultdict(list)
        for sig in signals:
            key = sig.get("theme", sig.get("commodity", sig.get("ticker", "unknown")))
            by_theme[key].append(sig)

        for key, sigs in by_theme.items():
            total_strength = sum(s.get("strength", 0) for s in sigs)
            corroboration = len(sigs)
            confidence = min(total_strength * (1 + 0.2 * corroboration), 1.0)
            if confidence > 0.25:
                stage = "pre_consensus" if confidence < 0.45 else "early" if confidence < 0.60 else "building"
                candidate = DiscoveryCandidate(
                    name=key.replace("_", " ").title(),
                    category="bottleneck" if "commodity" in str(sigs[0].get("type")) else "theme",
                    stage=stage,
                    confidence=round(confidence, 3),
                    signals={s["type"]: s.get("strength", 0) for s in sigs},
                    thesis=" | ".join(s.get("note", "") for s in sigs[:3]),
                    first_detected=time.strftime("%Y-%m-%d"),
                    last_updated=time.strftime("%Y-%m-%d"),
                )
                candidates.append(candidate)
        return candidates

    def _merge_candidates(self, new_candidates: List[DiscoveryCandidate]):
        for new in new_candidates:
            existing = None
            for c in self.candidates:
                if c.name.lower() == new.name.lower() or self._similar_names(c.name, new.name):
                    existing = c
                    break
            if existing:
                existing.confidence = max(existing.confidence, new.confidence)
                existing.signals.update(new.signals)
                existing.last_updated = time.strftime("%Y-%m-%d")
                if new.thesis and new.thesis not in existing.thesis:
                    existing.thesis += " | " + new.thesis
            else:
                self.candidates.append(new)
                logger.info(f"New candidate discovered: {new.name} ({new.stage}, conf={new.confidence:.0%})")

    def _promote_stages(self):
        for c in self.candidates:
            signal_count = len(c.signals)
            days_active = self._days_since(c.first_detected)
            if c.stage == "pre_consensus":
                if signal_count >= 2 or days_active >= 14:
                    c.stage = "early"
            elif c.stage == "early":
                if signal_count >= 3 or (c.confidence > 0.55 and days_active >= 7):
                    c.stage = "building"
            elif c.stage == "building":
                if signal_count >= 4 or (c.confidence > 0.75 and days_active >= 21):
                    c.stage = "active"

    def _map_to_tickers(self, prices: Dict):
        theme_ticker_map = {
            "oil": ["XLE", "OIH", "XOM", "CVX", "COP", "SLB"],
            "copper": ["FCX", "SCCO", "BHP", "HG=F", "CPER"],
            "natural_gas": ["KMI", "WMB", "ET", "EPD", "SRE"],
            "uranium": ["URA", "CCJ", "SMR", "OKLO", "LEU"],
            "nuclear_renaissance": ["URA", "CCJ", "SMR", "OKLO", "NNE", "LEU", "VST", "CEG"],
            "ai_power": ["VST", "CEG", "GEV", "VRT", "ETN", "NEE", "DUK"],
            "quantum": ["IONQ", "RGTI", "QBTS"],
            "space": ["RKLB", "ASTS", "SPIR", "PL"],
            "carbon_capture": ["PLUG", "BE", "FCEL", "CMI"],
            "gold": ["GLD", "GDX", "NEM", "AEM"],
            "silver": ["SLV", "SIL", "SILJ"],
        }
        for c in self.candidates:
            name_key = c.name.lower().replace(" ", "_")
            tickers = theme_ticker_map.get(name_key, [])
            if not tickers:
                for theme_key, theme_tickers in theme_ticker_map.items():
                    if theme_key in name_key or name_key in theme_key:
                        tickers = theme_tickers
                        break
            # Only include tickers that exist in prices
            c.tickers = [t for t in tickers[:8] if t in prices]

    # ── UTILITIES ──────────────────────────────────────────────────────────────

    def _detect_volume_spike(self, series, window: int = 20) -> float:
        """Detect if volume is spiking (proxy for news/earnings)."""
        if not isinstance(series, pd.Series) or len(series) < window + 1:
            return 1.0
        try:
            recent_vol = float(np.std(series.iloc[-window:].pct_change().dropna()))
            baseline_vol = float(np.std(series.iloc[-2*window:-window].pct_change().dropna())) if len(series) >= 2*window else recent_vol
            if baseline_vol < 1e-9:
                return 1.0
            return recent_vol / baseline_vol
        except Exception:
            return 1.0

    def _days_since(self, date_str: str) -> int:
        try:
            from datetime import datetime
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return (datetime.now() - d).days
        except Exception:
            return 0

    def _similar_names(self, a: str, b: str) -> bool:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        overlap = len(a_words & b_words)
        return overlap >= 2 or (overlap == 1 and len(a_words) == 1 and len(b_words) == 1)

    def _candidate_to_dict(self, c: DiscoveryCandidate) -> Dict:
        return {
            "name": c.name, "category": c.category, "stage": c.stage,
            "confidence": c.confidence, "signals": c.signals,
            "tickers": c.tickers, "thesis": c.thesis,
            "invalidators": c.invalidators, "source_urls": c.source_urls,
            "first_detected": c.first_detected, "last_updated": c.last_updated,
        }

    def _dict_to_candidate(self, d: Dict) -> DiscoveryCandidate:
        return DiscoveryCandidate(
            name=d.get("name", "Unknown"),
            category=d.get("category", "theme"),
            stage=d.get("stage", "pre_consensus"),
            confidence=d.get("confidence", 0.0),
            signals=d.get("signals", {}),
            tickers=d.get("tickers", []),
            thesis=d.get("thesis", ""),
            invalidators=d.get("invalidators", []),
            source_urls=d.get("source_urls", []),
            first_detected=d.get("first_detected", ""),
            last_updated=d.get("last_updated", ""),
        )
