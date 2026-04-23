"""
bottleneck_engine.py — Optimized 7-Layer Scanner
Performance rules:
  - RSS: max 3 feeds, 3 stories each = 9 total
  - Options: only spot > $30, skip if priced_in
  - No redundant price fetches
  - Lightweight narrative classification
"""
import os, json, math, logging, time, requests, feedparser
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = os.environ.get("BOTTLENECK_CONFIG", "./config/supply_chain.json")

def load_config(path: str = CONFIG_PATH) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Config load fail {path}: {e}")
        return {}

@dataclass
class SupplyNode:
    ticker: str
    name: str
    sector: str
    layer: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    bottleneck_indicators: Dict = field(default_factory=dict)

class SupplyChainGraph:
    def __init__(self, config: Optional[Dict] = None):
        self.cfg = config or load_config()
        self.db: Dict[str, SupplyNode] = {}
        self._build_from_config()
        meta = self.cfg.get("_meta", {})
        self.thresh = meta.get("thresholds", {"capacity_util": 0.90, "demand_growth": 1.5, "lead_time_weeks": 20})
        self.cu_threshold = self.thresh["capacity_util"]
        self.dg_threshold = self.thresh["demand_growth"]
        self.lt_threshold = self.thresh["lead_time_weeks"]

    def _build_from_config(self):
        for tk, data in self.cfg.get("nodes", {}).items():
            self.db[tk] = SupplyNode(
                ticker=tk, name=data.get("name", tk), sector=data.get("sector", "Other"),
                layer=data.get("layer", "unknown"), inputs=data.get("inputs", []),
                outputs=data.get("outputs", []), bottleneck_indicators=data.get("bottleneck_indicators", {}),
            )

    def detect_bottlenecks(self) -> List[Dict]:
        bottlenecks = []
        for ticker, node in self.db.items():
            bi = node.bottleneck_indicators
            score = 0.0; reasons = []
            cu = bi.get("capacity_util", 0)
            if cu > self.cu_threshold:
                score += 0.40 * min(1.0, (cu - self.cu_threshold) / 0.10)
                reasons.append(f"CapUtil {cu:.0%}")
            dg = bi.get("demand_growth", 0)
            if dg > self.dg_threshold:
                score += 0.35 * min(1.0, (dg - self.dg_threshold) / 1.0)
                reasons.append(f"Demand {dg:.1f}x")
            lt = bi.get("lead_time_weeks", 0)
            if lt > self.lt_threshold:
                score += 0.15 * min(1.0, (lt - self.lt_threshold) / 20)
                reasons.append(f"Lead {lt}w")
            tags = bi.get("tags", [])
            if "hbm_exposure" in tags and dg > 1.5:
                score += 0.10; reasons.append("HBM")
            if "cowos_exposure" in tags and cu > 0.90:
                score += 0.10; reasons.append("CoWoS")
            if "data_center_power" in tags:
                score += 0.08; reasons.append("DC-Power")
            if "supply_deficit" in tags:
                score += 0.08; reasons.append("SupplyDeficit")
            if score >= 0.45:
                bottlenecks.append({
                    "ticker": ticker, "name": node.name, "sector": node.sector, "layer": node.layer,
                    "bottleneck_score": round(min(score, 1.0), 2), "reasons": " | ".join(reasons),
                    "capacity_util": round(cu, 2), "demand_growth": round(dg, 2), "lead_time": lt,
                    "allocation_tier": bi.get("allocation_tier", "standard"), "tags": tags,
                })
        return sorted(bottlenecks, key=lambda x: x["bottleneck_score"], reverse=True)

    def allocation_filter(self, bottlenecks: List[Dict]) -> List[Dict]:
        winners = []
        for b in bottlenecks:
            tier = b.get("allocation_tier", "standard")
            if tier == "priority":
                b.update({"allocation_verdict": "✅ PRIORITY", "allocation_score": 1.0,
                           "allocation_note": "Guaranteed supply allocation"})
            elif tier == "standard":
                b.update({"allocation_verdict": "⚠️ STANDARD", "allocation_score": 0.55,
                           "allocation_note": "May face rationing"})
            else:
                b.update({"allocation_verdict": "❌ CUT", "allocation_score": 0.15,
                           "allocation_note": "Supply constrained — avoid"})
            if b["allocation_score"] >= 0.5:
                winners.append(b)
        return winners

    def upstream_map(self, ticker: str) -> List[str]:
        return self.db.get(ticker, SupplyNode(ticker, ticker, "", "")).inputs

    def downstream_map(self, ticker: str) -> List[str]:
        return self.db.get(ticker, SupplyNode(ticker, ticker, "", "")).outputs


class NarrativeEngine:
    def __init__(self, config: Optional[Dict] = None):
        self.cfg = config or load_config()
        self.feeds = self.cfg.get("narrative_sources", {}).get("rss_feeds", [])[:3]  # MAX 3 feeds
        self.themes = {
            "AI": ["nvidia", "ai chip", "gpu", "blackwell", "hbm3e", "cowos", "tsmc", "data center", "training", "inference", "cluster"],
            "Energy": ["oil", "natural gas", "power", "vistra", "nuclear", "electricity", "grid", "data center power", "renewable", "lng"],
            "Crypto": ["bitcoin", "ethereum", "etf", "halving", "mining", "hashrate", "spot etf", "institutional", "btc", "eth"],
            "Semi": ["memory", "dram", "nand", "foundry", "process node", "yield", "advanced packaging", "substrate", "semi", "chip"],
        }

    def scrape_rss(self, max_per_feed: int = 3) -> List[Dict]:  # MAX 3 per feed
        stories = []
        for url in self.feeds:
            try:
                fp = feedparser.parse(url)
                for entry in fp.entries[:max_per_feed]:
                    stories.append({"title": entry.get("title", ""), "summary": entry.get("summary", "")[:200]})
            except Exception as e:
                logger.warning(f"RSS fail {url}: {e}")
        return stories

    def classify(self, text: str) -> Dict[str, float]:
        text_lower = text.lower()[:500]  # Limit text length
        scores = {}
        for theme, keywords in self.themes.items():
            hits = sum(2 if kw in text_lower else 0 for kw in keywords)
            scores[theme] = min(1.0, hits / 6.0)
        dom = max(scores, key=scores.get) if scores else "NONE"
        return {"dominant": dom, "scores": scores, "intensity": scores.get(dom, 0)}

    def demand_pulse(self, stories: List[Dict]) -> Dict:
        theme_scores = {t: [] for t in self.themes}
        for s in stories:
            c = self.classify(s["title"] + " " + s.get("summary", ""))
            for t, sc in c["scores"].items():
                if sc > 0:
                    theme_scores[t].append(sc)
        pulse = {}
        for t, vals in theme_scores.items():
            if vals:
                avg = float(np.mean(vals)); mx = float(np.max(vals))
                pulse[t] = {"narrative_score": round(avg, 2), "peak_intensity": round(mx, 2),
                            "mentions": len(vals), "state": "🔥 HOT" if avg > 0.35 else "⚡ WARM" if avg > 0.18 else "❄️ COLD"}
            else:
                pulse[t] = {"narrative_score": 0.0, "peak_intensity": 0.0, "mentions": 0, "state": "❄️ COLD"}
        return pulse


class TransmissionMapper:
    def map(self, winners: List[Dict], prices: Dict[str, pd.Series]) -> List[Dict]:
        mapped = []
        for w in winners:
            tk = w["ticker"]; px = prices.get(tk)
            if px is None or len(px) < 63:
                w.update({"r1m": 0, "r3m": 0, "vol": 0, "priced_in": False, "transmission_score": 0.3,
                          "transmission_note": "No price data"})
                mapped.append(w); continue
            r1m = (px.iloc[-1] / px.iloc[-22] - 1) if len(px) >= 22 else 0
            r3m = (px.iloc[-1] / px.iloc[-64] - 1) if len(px) >= 64 else 0
            vol = px.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) if len(px) >= 20 else 0
            priced = abs(r3m) > 0.25 or vol > 0.40
            ts = 0.25 if priced else 0.80
            w.update({"r1m": round(r1m, 3), "r3m": round(r3m, 3), "vol": round(vol, 2),
                      "priced_in": priced, "transmission_score": ts,
                      "transmission_note": "Priced-in — avoid chase" if priced else "Early / Undercovered — preferred"})
            mapped.append(w)
        return mapped


class OptionsAnalyzer:
    def convexity_scan(self, ticker: str, spot: float, transmission_score: float) -> Optional[Dict]:
        # Performance: skip if priced-in, spot too low, or transmission weak
        if transmission_score < 0.5 or spot <= 30:
            return None
        try:
            t = yf.Ticker(ticker)
            exps = t.options
            if not exps:
                return None
            chain1 = t.option_chain(exps[0])
            calls = chain1.calls
            if calls.empty:
                return None
            otm = calls[(calls["strike"] > spot * 1.03) & (calls["strike"] < spot * 1.20) &
                        (calls["volume"] > 5) & (calls["openInterest"] > 50)].copy()
            if otm.empty:
                return None
            otm["moneyness"] = otm["strike"] / spot
            otm["convexity"] = otm["gamma"] / (otm["impliedVolatility"] + 0.001)
            best = otm.loc[otm["convexity"].idxmax()]
            em = float(best["impliedVolatility"]) * np.sqrt(30 / 252) * 100 if best["impliedVolatility"] > 0 else 0
            return {
                "ticker": ticker, "exp": exps[0], "strike": round(float(best["strike"]), 2), "spot": round(spot, 2),
                "moneyness": round(float(best["moneyness"]), 2), "iv": round(float(best["impliedVolatility"]), 2),
                "delta": round(float(best["delta"]), 3), "gamma": round(float(best["gamma"]), 4),
                "volume": int(best["volume"]), "oi": int(best["openInterest"]),
                "convexity_score": round(float(best["convexity"]), 2), "expected_move_pct": round(em, 1),
                "verdict": "🎯 HIGH" if best["convexity"] > 3.0 else "⚡ MOD" if best["convexity"] > 1.5 else "📉 LOW",
            }
        except Exception as e:
            logger.debug(f"Options skip {ticker}: {e}")
            return None


class BasketConstructor:
    def __init__(self, max_corr=0.82, max_size=5):
        self.max_corr = max_corr
        self.max_size = max_size

    def build(self, signals: List[Dict], prices: Dict[str, pd.Series]) -> List[Dict]:
        if not signals:
            return []
        signals = sorted(signals, key=lambda x: x.get("fusion_score", 0), reverse=True)
        basket = []
        for sig in signals:
            if len(basket) >= self.max_size:
                break
            tk = sig["ticker"]; px = prices.get(tk)
            if px is None or len(px) < 20:
                continue
            too_corr = False
            for b in basket:
                bpx = prices.get(b["ticker"])
                if bpx is None:
                    continue
                m = pd.concat([px.pct_change(), bpx.pct_change()], axis=1).dropna()
                if len(m) > 20:
                    corr = float(m.iloc[:, 0].corr(m.iloc[:, 1]))
                    if abs(corr) > self.max_corr:
                        too_corr = True
                        break
            if not too_corr:
                basket.append(sig)
        return basket


class UnifiedBottleneckScanner:
    def __init__(self, regime: Dict, config: Optional[Dict] = None):
        self.regime = regime
        self.config = config or load_config()
        self.supply = SupplyChainGraph(self.config)
        self.narrative = NarrativeEngine(self.config)
        self.options = OptionsAnalyzer()
        self.transmission = TransmissionMapper()
        self.basket = BasketConstructor()

    def scan(self, prices: Dict[str, pd.Series], run_options: bool = True) -> Dict:
        sq = self.regime.get("structural_quad", "Q2")
        mq = self.regime.get("monthly_quad", "Q2")
        conf = self.regime.get("confidence", 0.5)

        stories = self.narrative.scrape_rss()
        demand = self.narrative.demand_pulse(stories)
        bottlenecks = self.supply.detect_bottlenecks()
        winners = self.supply.allocation_filter(bottlenecks)
        transmitted = self.transmission.map(winners, prices)

        regime_mult = {"Q1": 1.15, "Q2": 1.20, "Q3": 0.95, "Q4": 0.75}.get(sq, 1.0)
        if sq != mq:
            regime_mult *= 0.70

        enriched = []
        for t in transmitted:
            tk = t["ticker"]; px = prices.get(tk)
            spot = float(px.iloc[-1]) if px is not None else 0
            sector = t.get("sector", "Other")
            narr_key = "AI" if sector == "AI" else "Energy" if sector == "Energy" else "Semi" if sector == "Semi" else "Crypto" if sector == "Crypto" else "Other"
            narr_score = demand.get(narr_key, {}).get("narrative_score", 0)

            opt = None
            if run_options and not t.get("priced_in", True) and spot > 30:
                try:
                    opt = self.options.convexity_scan(tk, spot, t.get("transmission_score", 0))
                except Exception as e:
                    logger.debug(f"Options skip {tk}: {e}")

            b_score = t.get("bottleneck_score", 0)
            a_score = t.get("allocation_score", 0)
            tr_score = t.get("transmission_score", 0)
            opt_boost = 0.25 if opt and opt["convexity_score"] > 2.0 else 0.12 if opt else 0.0

            raw_fusion = (0.28 * b_score + 0.22 * a_score + 0.20 * tr_score + 0.15 * narr_score + 0.15 * opt_boost) * regime_mult
            t["fusion_score"] = round(min(raw_fusion, 1.0), 2)
            t["fusion_grade"] = "S" if t["fusion_score"] >= 0.80 else "A" if t["fusion_score"] >= 0.65 else "B" if t["fusion_score"] >= 0.50 else "C"
            t["options_signal"] = opt
            t["narrative_match"] = narr_key
            t["narrative_score"] = narr_score
            enriched.append(t)

        basket = self.basket.build(enriched, prices)
        sector_counts = {}
        for e in enriched:
            s = e.get("sector", "Other")
            sector_counts[s] = sector_counts.get(s, 0) + 1

        return {
            "regime": {"structural": sq, "monthly": mq, "aligned": sq == mq, "confidence": conf, "regime_mult": regime_mult},
            "demand_pulse": demand,
            "bottlenecks_raw": bottlenecks,
            "allocation_winners": winners,
            "transmitted": transmitted,
            "enriched_signals": enriched,
            "basket": basket,
            "sector_summary": sector_counts,
            "stories_sample": stories[:3],
            "timestamp": datetime.now().isoformat(),
        }