"""warroom/discover.py — auto-discovery: ingest NEW tickers from a thesis/note into the universe.

The serenity-style edge is always surfacing new names before they are obvious. This lets the system
do the same: paste a thesis (or a list of tickers) and the new names are validated + appended to the
tier-3 user universe (data/extended_universe.json). data.py's _dynamic_us() pulls tier-3 into
US_UNIVERSE on the next run, so the existing beta-play / theme / rotation / conviction engines then
analyze the new names automatically — no engine changes needed.

Honesty: a ticker being added here does NOT mean it trades or that data exists. Pre-IPO names (e.g.
Agility = $AGLT, currently the $CCXI SPAC, IPO ~Sep 2026) are added as WATCH items; the data loader
resolves them on a live machine (or skips them gracefully if no data / not yet public).
"""
import json, os, re, datetime

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "extended_universe.json")
_CASHTAG = re.compile(r"\$([A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?)\b")
_VALID = re.compile(r"[A-Z]{1,5}(\.[A-Z]{1,3})?|\^[A-Z]+|[0-9]{4}\.[A-Z]+")


def extract_tickers(text):
    """Pull $CASHTAG symbols from a pasted thesis/note (e.g. serenity's posts)."""
    return sorted({m.group(1).upper() for m in _CASHTAG.finditer(text or "")})


def add_tickers(tickers, source="user_note", role="user-requested", chain="discovery", watch=False):
    """Append validated tickers to tier_3_user_requested. Idempotent. Returns the list actually added."""
    try:
        d = json.load(open(_PATH))
    except Exception:
        d = {"_schema_version": "v38", "tier_2_discovered": {}, "tier_3_user_requested": {}, "fetch_failed": {}}
    t2 = d.get("tier_2_discovered", {})
    t3 = d.setdefault("tier_3_user_requested", {})
    today = datetime.date.today().isoformat()
    added = []
    for t in tickers:
        t = (t or "").strip().upper()
        if not t or t in t2 or t in t3 or not _VALID.fullmatch(t):
            continue
        t3[t] = {"discovered_date": today, "source": source, "watch": bool(watch),
                 "alpha_context": {"chain_name": chain, "tier": 3, "role": role}}
        added.append(t)
    json.dump(d, open(_PATH, "w"), indent=2)
    return added


def ingest_note(text, source="thesis_note", chain="discovery"):
    """One-shot: extract cashtags from a note and add them. Returns (extracted, added)."""
    found = extract_tickers(text)
    return found, add_tickers(found, source=source, chain=chain)
