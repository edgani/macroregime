"""narrative_news_loader.py

Fetches themed news per narrative category from multiple RSS sources.
More targeted than the generic news_loader — each query is built around
specific narrative activation keywords to maximize signal-to-noise.

Sources: Google News RSS, Reuters RSS, FT (free), Yahoo Finance RSS
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus
import re
import requests

from config.settings import LIVE_FETCH_ENABLED, NEWS_CACHE_TTL_SECONDS
from config.narrative_universe import _NARRATIVE_LIBRARY, NarrativeTemplate
from utils.streamlit_compat import st


def _fetch_rss(session: requests.Session, url: str, limit: int = 8) -> List[Dict[str, str]]:
    try:
        resp = session.get(url, timeout=6)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        out = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            desc = re.sub(r"<[^>]+>", "", (item.findtext("description") or "")).strip()[:200]
            if title:
                out.append({"title": title, "link": link, "published": pub, "summary": desc})
        return out
    except Exception:
        return []


def _build_google_rss_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"


def _keyword_score(text: str, keywords: List[str]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw.lower() in t)


@st.cache_data(ttl=NEWS_CACHE_TTL_SECONDS * 2, show_spinner=False)
def load_narrative_signals(*, force_refresh: bool = False) -> Dict[str, object]:
    """
    For each narrative in the library, fetch targeted news and score relevance.

    Returns:
        {
            "narratives": {
                narrative_name: {
                    "activation_score": 0-10 (keyword hits),
                    "invalidation_score": 0-10,
                    "net_score": activation - invalidation,
                    "items": [headline dicts],
                    "is_live": bool,
                }
            },
            "top_narratives": [sorted by net_score desc],
            "generated_at": iso timestamp,
        }
    """
    if not LIVE_FETCH_ENABLED:
        return {
            "narratives": {},
            "top_narratives": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    results: Dict[str, Dict] = {}

    for narrative in _NARRATIVE_LIBRARY:
        # Build targeted query from top activation keywords (max 5 terms)
        top_keywords = narrative.activation_keywords[:5]
        query = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in top_keywords[:3])
        url = _build_google_rss_url(query)
        items = _fetch_rss(session, url, limit=8)

        # Score activation and invalidation
        all_text = " ".join(f"{i['title']} {i.get('summary', '')}" for i in items)
        act_score = _keyword_score(all_text, narrative.activation_keywords)
        inv_score = _keyword_score(all_text, narrative.invalidation_keywords)
        net_score = act_score - (inv_score * 1.5)  # invalidation has 1.5x weight

        results[narrative.name] = {
            "activation_score": act_score,
            "invalidation_score": inv_score,
            "net_score": net_score,
            "is_live": net_score >= 2 and act_score >= 2,
            "pump_risk": narrative.pump_risk,
            "category": narrative.category,
            "description": narrative.description,
            "beneficiaries": narrative.beneficiaries,
            "fades": narrative.fades,
            "confirmation_signals": narrative.confirmation_signals,
            "typical_duration_weeks": narrative.typical_duration_weeks,
            "conviction_ceiling": narrative.conviction_ceiling,
            "regime_alignment": narrative.regime_alignment,
            "items": items[:5],
        }

    # Sort by net_score desc, only include narratives with positive signal
    top = sorted(
        [(name, data) for name, data in results.items() if data["net_score"] > 0],
        key=lambda x: x[1]["net_score"],
        reverse=True,
    )

    return {
        "narratives": results,
        "top_narratives": [{"name": name, **data} for name, data in top[:8]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
