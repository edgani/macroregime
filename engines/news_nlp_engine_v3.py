"""engines/news_nlp_engine_v3.py — LIGHTWEIGHT VERSION (NO torch/transformers)

Uses Yahoo Finance RSS + Google News RSS + regex-based NLP.
Zero ML models. Zero downloads. Builds in <30 seconds.
"""
from __future__ import annotations
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import feedparser
import requests

logger = logging.getLogger(__name__)

class LightweightNLP:
    """Pure regex/knowledge-based NLP. No ML."""

    NARRATIVE_KEYWORDS = {
        "ai_infrastructure": ["AI data center", "GPU shortage", "HBM", "CoWoS", "photonics", "CPO", "SiC", "Blackwell", "NVIDIA", "NVDA"],
        "energy_transition": ["nuclear renaissance", "AI power", "grid upgrade", "baseload", "gas turbine", "transformer", "power plant"],
        "hard_assets_scarcity": ["copper shortage", "de-dollarization", "central bank buying", "supply deficit", "gold", "silver", "commodity"],
        "defense_reshoring": ["NATO spending", "munitions shortage", "hypersonic", "missile defense", "defense", "military"],
        "healthcare_scarcity": ["GLP-1 shortage", "robotic surgery", "aging population", "drug pricing", "healthcare", "pharma"],
        "shipping_supply_crisis": ["Red Sea disruption", "fleet renewal", "IMO 2023", "day rates", "vessel shortage", "shipping", "freight"],
        "fed_pivot_liquidity": ["Fed cut", "liquidity injection", "QT end", "yield curve steepening", "rate cut", "pivot"],
        "dxy_bearish_em_recovery": ["USD bearish", "EM FX relief", "DXY breakdown", "Fed pivot", "capital flows", "emerging market"],
        "china_reopening_commodity": ["China stimulus", "property rescue", "infrastructure", "commodity demand", "China", "Beijing"],
        "bond_duration_bull": ["TLT", "yield collapse", "deflation", "recession pricing", "flight to quality", "treasury"],
        "indonesia_commodity_supercycle": ["IHSG", "foreign flow", "CKPN cascade", "offshore drilling", "JIIPE", "Indonesia"],
    }

    SUPPLY_CHAIN_KEYWORDS = [
        "shortage", "constrained supply", "sole source", "only supplier", "limited suppliers",
        "capacity constrained", "lead time extended", "bottleneck", "tight supply", "supply crunch",
        "backlog", "order backlog", "demand exceeds supply", "unable to meet demand",
        "capacity expansion", "ramping production", "supply chain disruption",
    ]

    BULLISH = ["surge", "rally", "breakout", "soar", "jump", "boom", "strong", "beat", "outperform", "upgrade", "bull", "gain"]
    BEARISH = ["crash", "plunge", "drop", "fall", "weak", "miss", "underperform", "downgrade", "cut", "layoff", "bear", "loss"]

    def classify(self, headline: str) -> Tuple[str, float]:
        h = headline.lower()
        best_narr, best_score = "general", 0.0
        for narr, kws in self.NARRATIVE_KEYWORDS.items():
            score = sum(1 for kw in kws if kw.lower() in h) / max(len(kws), 1)
            if score > best_score:
                best_score = score
                best_narr = narr
        # Boost for supply chain keywords
        supply_boost = sum(0.05 for kw in self.SUPPLY_CHAIN_KEYWORDS if kw in h)
        return best_narr, min(best_score * 2.5 + supply_boost, 1.0)

    def sentiment(self, headline: str) -> Tuple[str, float]:
        h = headline.lower()
        bull = sum(1 for w in self.BULLISH if w in h)
        bear = sum(1 for w in self.BEARISH if w in h)
        if bull > bear:
            return "positive", min(0.5 + (bull - bear) * 0.12, 1.0)
        elif bear > bull:
            return "negative", min(0.5 + (bear - bull) * 0.12, 1.0)
        return "neutral", 0.5

    def extract_tickers(self, text: str, known: List[str]) -> List[str]:
        found = []
        text_upper = text.upper()
        for t in known:
            if f"${t}" in text_upper or re.search(r'' + re.escape(t) + r'', text):
                found.append(t)

@dataclass
class NewsItem:
    ticker: str
    headline: str
    source: str
    published: str
    narrative: str = ""
    narrative_score: float = 0.0
    sentiment: str = "neutral"
    sentiment_score: float = 0.5
    supply_chain_mentions: List[str] = field(default_factory=list)
    is_new_theme: bool = False
    linked_tickers: List[str] = field(default_factory=list)

class NewsNLPEngineV3:
    def __init__(self, use_transformers: bool = False, known_tickers: Optional[List[str]] = None):
        self.use_transformers = False  # FORCE lightweight
        self.known_tickers = known_tickers or []
        self.light = LightweightNLP()

    def fetch_yahoo_rss(self, tickers: List[str], max_per_ticker: int = 10) -> Dict[str, List[dict]]:
        results = {}
        for i in range(0, len(tickers), 20):
            batch = tickers[i:i+20]
            sym_str = ",".join(batch)
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym_str}"
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_ticker * len(batch)]:
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    pub = entry.get("published", "")
                    m = re.search(r'/quote/([A-Z0-9\.\-]+)/', link)
                    guessed = m.group(1) if m else None
                    if guessed and guessed in batch:
                        results.setdefault(guessed, []).append({
                            "headline": title, "link": link, "published": pub, "source": "Yahoo Finance"
                        })
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Yahoo RSS error: {e}")
        return results

    def fetch_google_news(self, query: str, max_items: int = 15) -> List[dict]:
        q = requests.utils.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(url)
            return [{"headline": e.get("title", ""), "link": e.get("link", ""),
                     "published": e.get("published", ""), "source": "Google News"}
                    for e in feed.entries[:max_items]]
        except Exception as e:
            logger.warning(f"Google News error: {e}")
            return []

    def analyze(self, headline: str, ticker: str = "") -> NewsItem:
        headline = headline.strip()
        if not headline:
            return NewsItem(ticker=ticker, headline="", source="", published="")
        narrative, narr_score = self.light.classify(headline)
        is_new_theme = narrative == "general" and narr_score < 0.15
        sentiment, sent_score = self.light.sentiment(headline)
        hlower = headline.lower()
        supply_mentions = [kw for kw in self.light.SUPPLY_CHAIN_KEYWORDS if kw in hlower]
        linked = self.light.extract_tickers(headline, self.known_tickers)
        return NewsItem(
            ticker=ticker, headline=headline, source="", published="",
            narrative=narrative, narrative_score=round(narr_score, 3),
            sentiment=sentiment, sentiment_score=round(sent_score, 3),
            supply_chain_mentions=supply_mentions,
            is_new_theme=is_new_theme,
            linked_tickers=linked,
        )

    def run(self, tickers: List[str], theme_queries: Optional[List[str]] = None, max_per_ticker: int = 8) -> Dict[str, object]:
        ticker_news = self.fetch_yahoo_rss(tickers, max_per_ticker)
        theme_results = {}
        if theme_queries:
            for q in theme_queries:
                theme_results[q] = self.fetch_google_news(q, max_items=12)

        analyzed = []
        for t, items in ticker_news.items():
            for item in items:
                ni = self.analyze(item["headline"], ticker=t)
                ni.source = item["source"]
                ni.published = item["published"]
                analyzed.append(ni)
        for q, items in theme_results.items():
            for item in items:
                ni = self.analyze(item["headline"], ticker="")
                ni.source = item["source"]
                ni.published = item["published"]
                analyzed.append(ni)

        from collections import defaultdict
        narrative_scores = defaultdict(lambda: {"count": 0, "avg_sentiment": 0.0, "supply_hits": 0, "tickers": set()})
        for ni in analyzed:
            narrative_scores[ni.narrative]["count"] += 1
            narrative_scores[ni.narrative]["avg_sentiment"] += ni.sentiment_score
            narrative_scores[ni.narrative]["supply_hits"] += len(ni.supply_chain_mentions)
            if ni.ticker:
                narrative_scores[ni.narrative]["tickers"].add(ni.ticker)

        for narr, data in narrative_scores.items():
            if data["count"] > 0:
                data["avg_sentiment"] = round(data["avg_sentiment"] / data["count"], 3)
            data["tickers"] = list(data["tickers"])

        emergent = []
        for narr, data in narrative_scores.items():
            if data["count"] >= 3 and data["supply_hits"] >= 2:
                emergent.append({
                    "narrative": narr, "mention_count": data["count"],
                    "avg_sentiment": data["avg_sentiment"], "supply_chain_hits": data["supply_hits"],
                    "linked_tickers": data["tickers"],
                    "is_new": narr not in self.light.NARRATIVE_KEYWORDS,
                })

        new_theme_headlines = [ni for ni in analyzed if ni.is_new_theme and ni.narrative_score < 0.3]
        new_themes = self._cluster_new_themes(new_theme_headlines)

        return {
            "analyzed_count": len(analyzed),
            "narrative_scores": dict(narrative_scores),
            "emergent_narratives": sorted(emergent, key=lambda x: x["supply_chain_hits"], reverse=True),
            "new_theme_candidates": new_themes,
            "supply_chain_alerts": [ni for ni in analyzed if len(ni.supply_chain_mentions) > 0],
            "ticker_specific": {t: [ni for ni in analyzed if ni.ticker == t] for t in tickers},
            "meta": {
                "tickers_queried": len(tickers), "theme_queries": theme_queries or [],
                "nlp_mode": "lightweight",
            }
        }

    def _cluster_new_themes(self, headlines: List[NewsItem]) -> List[dict]:
        if len(headlines) < 2:
            return []
        def extract_kw(text):
            words = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', text)
            stop = {"The","And","For","Are","But","Not","You","All","Can","Had","Her","Was","One","Our","Out","Day","Get","Has","Him","His","How","Its","May","New","Now","Old","See","Two","Who","Boy","Did","She","Use","Her","Way","Many","Oil","Sit","Set","Run","Eat","Far","Sea","Eye","Ago","Off","Too","Any","Say","Man","Try","Ask","End","Why","Let","Put","She","Try","Way","Own","Say"}
            return set(w.lower() for w in words if w not in stop)
        groups = []
        used = set()
        for i, hi in enumerate(headlines):
            if i in used:
                continue
            kws_i = extract_kw(hi.headline)
            group = [hi]
            used.add(i)
            for j, hj in enumerate(headlines[i+1:], start=i+1):
                if j in used:
                    continue
                kws_j = extract_kw(hj.headline)
                if len(kws_i & kws_j) >= 2:
                    group.append(hj)
                    used.add(j)
            if len(group) >= 2:
                all_kws = set()
                for g in group:
                    all_kws |= extract_kw(g.headline)
                # Generate readable theme description from keywords
                top_kws = sorted(list(all_kws), key=lambda w: sum(1 for g in group if w in g.headline.lower()), reverse=True)[:5]
                theme_desc = " / ".join(top_kws) if top_kws else "emerging_theme"
                groups.append({
                    "headline_count": len(group),
                    "shared_keywords": list(all_kws)[:10],
                    "sample_headlines": [g.headline for g in group[:3]],
                    "suggested_theme_name": f"Theme: {theme_desc}",
                    "keyword_strength": len(all_kws),
                })
        return groups
