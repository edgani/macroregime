"""engines/news_nlp_engine.py v1 — Ticker-Specific News Scraping + Local NLP

Uses Yahoo Finance RSS (FREE, ticker-specific) + HuggingFace local models.
No API key. No Claude. No OpenAI.
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
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Local NLP (lazy load to avoid import overhead) ──────────────────────────
_nlp_cache = {}

def _get_zero_shot():
    if "zero_shot" not in _nlp_cache:
        from transformers import pipeline
        # Use smaller model for CPU efficiency; upgrade to bart-large if GPU available
        _nlp_cache["zero_shot"] = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",  # ~490MB download once
            device=-1,  # CPU
        )
    return _nlp_cache["zero_shot"]

def _get_ner():
    if "ner" not in _nlp_cache:
        from transformers import pipeline
        _nlp_cache["ner"] = pipeline(
            "ner",
            model="dslim/bert-base-NER",
            grouped_entities=True,
            device=-1,
        )
    return _nlp_cache["ner"]

def _get_sentiment():
    if "sentiment" not in _nlp_cache:
        from transformers import pipeline
        _nlp_cache["sentiment"] = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            device=-1,
        )
    return _nlp_cache["sentiment"]

# ── Fallback: lightweight keyword NLP without transformers ──────────────────
class LightweightNLP:
    """If transformers not available / too heavy, use this."""
    
    NARRATIVE_KEYWORDS = {
        "ai_infrastructure": ["AI data center", "GPU shortage", "HBM", "CoWoS", "photonics", "CPO", "SiC", "power density", "Blackwell"],
        "energy_transition": ["nuclear renaissance", "AI power", "grid upgrade", "baseload", "gas turbine", "transformer"],
        "hard_assets_scarcity": ["copper shortage", "de-dollarization", "central bank buying", "supply deficit", "resource nationalism"],
        "defense_reshoring": ["NATO spending", "munitions shortage", "hypersonic", "missile defense", "industrial base"],
        "healthcare_scarcity": ["GLP-1 shortage", "robotic surgery", "aging population", "drug pricing"],
        "shipping_supply_crisis": ["Red Sea disruption", "fleet renewal", "IMO 2023", "day rates", "vessel shortage"],
        "fed_pivot_liquidity": ["Fed cut", "liquidity injection", "QT end", "yield curve steepening", "credit easing"],
        "dxy_bearish_em_recovery": ["USD bearish", "EM FX relief", "DXY breakdown", "Fed pivot", "capital flows"],
        "china_reopening_commodity": ["China stimulus", "property rescue", "infrastructure", "commodity demand"],
        "bond_duration_bull": ["TLT", "yield collapse", "deflation", "recession pricing", "flight to quality"],
        "indonesia_commodity_supercycle": ["IHSG", "foreign flow", "CKPN cascade", "offshore drilling", "JIIPE"],
    }
    
    SUPPLY_CHAIN_KEYWORDS = ["shortage", "constrained supply", "sole source", "only supplier", "limited suppliers", 
                             "capacity constrained", "lead time extended", "bottleneck", "tight supply", "supply crunch"]
    
    BULLISH_WORDS = ["surge", "rally", "breakout", "soar", "jump", "boom", "strong", "beat", "outperform", "upgrade"]
    BEARISH_WORDS = ["crash", "plunge", "drop", "fall", "weak", "miss", "underperform", "downgrade", "cut", "layoff"]
    
    def classify(self, headline: str) -> Tuple[str, float]:
        headline_lower = headline.lower()
        best_narr = "general"
        best_score = 0.0
        for narr, kws in self.NARRATIVE_KEYWORDS.items():
            score = sum(1 for kw in kws if kw.lower() in headline_lower) / max(len(kws), 1)
            if score > best_score:
                best_score = score
                best_narr = narr
        return best_narr, min(best_score * 3, 1.0)  # boost to 0-1
    
    def sentiment(self, headline: str) -> Tuple[str, float]:
        h = headline.lower()
        bull = sum(1 for w in self.BULLISH_WORDS if w in h)
        bear = sum(1 for w in self.BEARISH_WORDS if w in h)
        if bull > bear:
            return "positive", min(0.5 + (bull - bear) * 0.15, 1.0)
        elif bear > bull:
            return "negative", min(0.5 + (bear - bull) * 0.15, 1.0)
        return "neutral", 0.5
    
    def extract_tickers(self, text: str, known_tickers: List[str]) -> List[str]:
        found = []
        for t in known_tickers:
            # Match whole word or $TICKER
            if re.search(r'\b' + re.escape(t) + r'\b', text) or re.search(r'\$' + re.escape(t), text):
                found.append(t)
        return found

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

class NewsNLPEngine:
    """
    Scrape ticker-specific news via Yahoo Finance RSS (FREE).
    Classify narratives using local zero-shot NLP or lightweight fallback.
    """

    def __init__(self, use_transformers: bool = True, known_tickers: Optional[List[str]] = None):
        self.use_transformers = use_transformers
        self.known_tickers = known_tickers or []
        self.lightweight = LightweightNLP()
        self._nlp_ok = None

    def _check_nlp(self) -> bool:
        if self._nlp_ok is not None:
            return self._nlp_ok
        try:
            if self.use_transformers:
                _ = _get_zero_shot()
                _ = _get_ner()
                _ = _get_sentiment()
            self._nlp_ok = True
        except Exception as e:
            logger.warning(f"Transformers NLP unavailable ({e}), using lightweight fallback.")
            self._nlp_ok = False
        return self._nlp_ok

    def fetch_yahoo_rss(self, tickers: List[str], max_items_per_ticker: int = 10) -> Dict[str, List[dict]]:
        """Fetch Yahoo Finance RSS for specific tickers. FREE. No API key."""
        results = {}
        # Yahoo allows batch: s=AAPL,NVDA,LITE
        batch_size = 20
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            sym_str = ",".join(batch)
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym_str}"
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_items_per_ticker * len(batch)]:
                    # Extract ticker from link or title if possible
                    # Yahoo RSS link format often contains ticker
                    link = entry.get("link", "")
                    title = entry.get("title", "")
                    pub = entry.get("published", "")
                    
                    # Guess ticker from link: /quote/AAPL/news/...
                    m = re.search(r'/quote/([A-Z\.-]+)/', link)
                    guessed = m.group(1) if m else None
                    
                    if guessed and guessed in batch:
                        results.setdefault(guessed, []).append({
                            "headline": title,
                            "link": link,
                            "published": pub,
                            "source": "Yahoo Finance",
                        })
                time.sleep(0.5)  # be polite
            except Exception as e:
                logger.warning(f"Yahoo RSS error for {sym_str}: {e}")
        return results

    def fetch_google_news(self, query: str, max_items: int = 15) -> List[dict]:
        """Google News RSS for theme queries. FREE."""
        # Format: https://news.google.com/rss/search?q=NVDA+shortage+supply
        q = requests.utils.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(url)
            return [{
                "headline": e.get("title", ""),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
                "source": e.get("source", {}).get("title", "Google News"),
            } for e in feed.entries[:max_items]]
        except Exception as e:
            logger.warning(f"Google News error: {e}")
            return []

    def analyze_headline(self, headline: str, ticker: str = "") -> NewsItem:
        """Run NLP on a single headline."""
        headline = headline.strip()
        if not headline:
            return NewsItem(ticker=ticker, headline="", source="", published="")

        nlp_available = self._check_nlp()

        # ── Narrative Classification ─────────────────────────────────
        candidate_labels = list(self.lightweight.NARRATIVE_KEYWORDS.keys()) + ["new_theme"]
        if nlp_available and len(headline) > 20:
            try:
                zs = _get_zero_shot()(headline, candidate_labels, multi_label=False)
                narrative = zs["labels"][0]
                narr_score = zs["scores"][0]
            except Exception:
                narrative, narr_score = self.lightweight.classify(headline)
        else:
            narrative, narr_score = self.lightweight.classify(headline)

        is_new_theme = narrative == "new_theme" or narr_score < 0.25

        # ── Sentiment ────────────────────────────────────────────────
        if nlp_available:
            try:
                sent = _get_sentiment()(headline[:512])[0]  # finbert max len
                sentiment = sent["label"].lower()
                sent_score = sent["score"]
            except Exception:
                sentiment, sent_score = self.lightweight.sentiment(headline)
        else:
            sentiment, sent_score = self.lightweight.sentiment(headline)

        # ── Supply Chain Keyword Mining ─────────────────────────────
        hlower = headline.lower()
        supply_mentions = [kw for kw in self.lightweight.SUPPLY_CHAIN_KEYWORDS if kw in hlower]

        # ── Ticker Extraction ─────────────────────────────────────────
        linked_tickers = self.lightweight.extract_tickers(headline, self.known_tickers)

        return NewsItem(
            ticker=ticker,
            headline=headline,
            source="",
            published="",
            narrative=narrative,
            narrative_score=round(narr_score, 3),
            sentiment=sentiment,
            sentiment_score=round(sent_score, 3),
            supply_chain_mentions=supply_mentions,
            is_new_theme=is_new_theme,
        )

    def run(
        self,
        tickers: List[str],
        theme_queries: Optional[List[str]] = None,
        max_per_ticker: int = 8,
    ) -> Dict[str, object]:
        """
        Main entry: fetch news for tickers + theme queries, analyze all.
        """
        # 1. Fetch ticker-specific news
        ticker_news = self.fetch_yahoo_rss(tickers, max_items_per_ticker=max_per_ticker)

        # 2. Fetch theme news
        theme_results = {}
        if theme_queries:
            for q in theme_queries:
                theme_results[q] = self.fetch_google_news(q, max_items=12)

        # 3. Analyze all headlines
        analyzed = []
        for t, items in ticker_news.items():
            for item in items:
                news_item = self.analyze_headline(item["headline"], ticker=t)
                news_item.source = item["source"]
                news_item.published = item["published"]
                analyzed.append(news_item)

        for q, items in theme_results.items():
            for item in items:
                news_item = self.analyze_headline(item["headline"], ticker="")
                news_item.source = item["source"]
                news_item.published = item["published"]
                analyzed.append(news_item)

        # 4. Aggregate narrative scores
        narrative_scores = defaultdict(lambda: {"count": 0, "avg_sentiment": 0.0, "supply_hits": 0, "tickers": set()})
        for ni in analyzed:
            narrative_scores[ni.narrative]["count"] += 1
            narrative_scores[ni.narrative]["avg_sentiment"] += ni.sentiment_score
            narrative_scores[ni.narrative]["supply_hits"] += len(ni.supply_chain_mentions)
            if ni.ticker:
                narrative_scores[ni.narrative]["tickers"].add(ni.ticker)

        # Normalize
        for narr, data in narrative_scores.items():
            if data["count"] > 0:
                data["avg_sentiment"] = round(data["avg_sentiment"] / data["count"], 3)
            data["tickers"] = list(data["tickers"])

        # 5. Detect emergent narratives (high count + supply chain mentions)
        emergent = []
        for narr, data in narrative_scores.items():
            if data["count"] >= 3 and data["supply_hits"] >= 2:
                emergent.append({
                    "narrative": narr,
                    "mention_count": data["count"],
                    "avg_sentiment": data["avg_sentiment"],
                    "supply_chain_hits": data["supply_hits"],
                    "linked_tickers": data["tickers"],
                    "is_new": narr not in self.lightweight.NARRATIVE_KEYWORDS,
                })

        # 6. Detect new themes from is_new_theme flag
        new_theme_headlines = [ni for ni in analyzed if ni.is_new_theme and ni.narrative_score < 0.3]
        # Cluster new theme headlines by shared keywords
        new_themes = self._cluster_new_themes(new_theme_headlines)

        return {
            "analyzed_count": len(analyzed),
            "narrative_scores": dict(narrative_scores),
            "emergent_narratives": sorted(emergent, key=lambda x: x["supply_chain_hits"], reverse=True),
            "new_theme_candidates": new_themes,
            "supply_chain_alerts": [ni for ni in analyzed if len(ni.supply_chain_mentions) > 0],
            "ticker_specific": {t: [ni for ni in analyzed if ni.ticker == t] for t in tickers},
            "meta": {
                "tickers_queried": len(tickers),
                "theme_queries": theme_queries or [],
                "nlp_mode": "transformers" if self._check_nlp() else "lightweight",
            }
        }

    def _cluster_new_themes(self, headlines: List[NewsItem]) -> List[dict]:
        """Simple keyword overlap clustering for 'new theme' headlines."""
        if len(headlines) < 2:
            return []
        
        # Extract keywords (nouns/adjectives) — simplified: words > 4 chars, capitalized or technical
        def extract_kw(text):
            words = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', text)
            return set(w.lower() for w in words if w.lower() not in {
                "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "she", "use", "her", "way", "many", "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago", "off", "too", "any", "say", "man", "try", "ask", "end", "why", "let", "put", "say", "she", "try", "way", "own", "say"
            })
        
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
                if len(kws_i & kws_j) >= 2:  # at least 2 shared keywords
                    group.append(hj)
                    used.add(j)
            if len(group) >= 2:
                all_kws = set()
                for g in group:
                    all_kws |= extract_kw(g.headline)
                groups.append({
                    "headline_count": len(group),
                    "shared_keywords": list(all_kws)[:10],
                    "sample_headlines": [g.headline for g in group[:3]],
                    "suggested_theme_name": "_".join(sorted(list(all_kws))[:3]),
                })
        return groups