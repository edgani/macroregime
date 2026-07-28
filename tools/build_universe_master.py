"""tools/build_universe_master.py — canonical point-in-time universe masters (R5).

Builds data/universe/{us,ihsg,crypto,commodities,fx}.json + coverage report +
coverage-gap registry. Sources:

  US:   data/reference/current_us_universe_2026-07-17.csv (Nasdaq listed/otherlisted,
        13k instruments, exchange + security class), sp500_ticker_start_end.csv
        (membership history incl. delisted, research grade)
  IHSG: warroom/data.py IDX_UNIVERSE (price-fed) + honest license gap for full IDX
  Crypto: warroom/data.py CRYPTO_UNIVERSE (venue-exact) + optional CoinGecko live list
  Commodities: exact CME/NYMEX/COMEX contract specs (static reference)
  FX:   pair master with conventions (static reference)

Tiers: TIER_A_FULL_DECISION (price-fed + cache), TIER_B_RESEARCH_DISCOVERY,
TIER_C_REFERENCE_ONLY, UNSUPPORTED_LICENSE_REQUIRED, UNAVAILABLE.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "universe"
OUT.mkdir(parents=True, exist_ok=True)
COV = ROOT / "data" / "coverage"
COV.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

from warroom import data as D  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inst(market, instrument, venue, tier, **kw):
    rec = {
        "instrument": instrument,
        "market": market,
        "venue": venue,
        "tier": tier,
        "as_of": NOW,
        "source": kw.pop("source", None),
        "data_state": kw.pop("data_state", "CURRENT"),
    }
    rec.update(kw)
    return rec


# ---------------- US ----------------

def build_us():
    ref = ROOT / "data" / "reference" / "current_us_universe_2026-07-17.csv"
    fed = set(D.US_UNIVERSE)
    master, gaps = [], []
    counts = {"TIER_A_FULL_DECISION": 0, "TIER_B_RESEARCH_DISCOVERY": 0,
              "TIER_C_REFERENCE_ONLY": 0, "UNSUPPORTED_LICENSE_REQUIRED": 0}
    with ref.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = row["symbol"].strip()
            cls = row.get("security_class", "")
            etf = row.get("etf", "N") == "Y"
            test = row.get("test_issue", "N") == "Y"
            if test:
                continue
            if sym in fed:
                tier = "TIER_A_FULL_DECISION"
            elif etf:
                tier = "TIER_C_REFERENCE_ONLY"   # ETFs = execution/hedge instruments, labelled
            elif cls in ("COMMON", "REIT") or row.get("eligible_us_v1") == "YES":
                tier = "TIER_B_RESEARCH_DISCOVERY"
            else:
                tier = "TIER_C_REFERENCE_ONLY"
            counts[tier] = counts.get(tier, 0) + 1
            master.append(_inst("us", sym, row.get("exchange", "?"), tier,
                                security_class=cls, etf=etf,
                                security_name=row.get("security_name", "").strip(),
                                source="nasdaq listed/otherlisted snapshot 2026-07-17"))
    # delisted membership history (S&P 500 sleeve, research grade)
    sp = ROOT / "data" / "reference" / "sp500_ticker_start_end.csv"
    n_delisted = 0
    with sp.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("end_date"):
                n_delisted += 1
    gaps.append({
        "domain": "us.delisted_history_full_market",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "full-market delisted history + survivorship-free fundamentals require licensed data (CRSP/Sharadar/Compustat); repo holds S&P 500 membership history only (research grade)",
        "present": f"S&P 500 membership history with {n_delisted} delisted entries (third-party, research ceiling)",
        "provider_required": "CRSP or Sharadar or Compustat",
        "recall_impact": "HIGH for extreme-winner cohort construction outside S&P 500; failed-lookalike and delisted cohorts incomplete",
    })
    gaps.append({
        "domain": "us.pit_fundamentals",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "point-in-time SEC fundamentals (backlog/guidance/revisions) need licensed PIT store; EDGAR scraping admitted but not yet wired",
        "provider_required": "SEC EDGAR full-text + PIT fundamentals vendor",
        "recall_impact": "HIGH for bottleneck activation inputs (orders/backlog/ASP evidence)",
    })
    meta = {"market": "us", "built_at": NOW, "instrument_count": len(master),
            "tiers": counts, "source_files": {ref.name: _sha(ref), sp.name: _sha(sp)},
            "schema": "warroom.universe_master.v1"}
    return master, meta, gaps


# ---------------- IHSG ----------------

def build_ihsg():
    fed = sorted(set(D.IDX_UNIVERSE))
    master = [_inst("ihsg", t, "IDX", "TIER_A_FULL_DECISION",
                    security_class="COMMON" if not t.startswith("^") else "INDEX",
                    source="warroom/data.py IDX_UNIVERSE (price-fed via yfinance .JK)")
              for t in fed]
    gaps = [{
        "domain": "ihsg.full_universe_master",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "complete IDX listed universe (~900 issuers) with listing/delisting history, boards, free float, and controller data requires IDX/RTI/KESEI licensed feed; current master covers price-fed sleeve only",
        "present": f"{len(fed)} instruments price-fed",
        "provider_required": "IDX data feed or licensed aggregator",
        "recall_impact": "HIGH: most IDX multibaggers historically came from small/mid caps outside the current sleeve",
    }, {
        "domain": "ihsg.broker_summary_done_detail",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "broker inventory, done-detail, crossing-adjusted accumulation require licensed IDX broker-summary data",
        "provider_required": "IDX broker summary / RTI",
        "recall_impact": "MEDIUM-HIGH for flow-based activation on IDX",
    }]
    meta = {"market": "ihsg", "built_at": NOW, "instrument_count": len(master),
            "tiers": {"TIER_A_FULL_DECISION": len(fed)}, "schema": "warroom.universe_master.v1"}
    return master, meta, gaps


# ---------------- Crypto ----------------

def build_crypto(fetch_live: bool):
    fed = sorted(set(D.CRYPTO_UNIVERSE))
    master = [_inst("crypto", t, "yahoo/coinbase-spot", "TIER_A_FULL_DECISION",
                    instrument_kind="spot" if t.endswith("-USD") else "equity_proxy",
                    source="warroom/data.py CRYPTO_UNIVERSE")
              for t in fed]
    live_n = 0
    if fetch_live:
        try:
            import urllib.request
            url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
                   "&order=market_cap_desc&per_page=100&page=1")
            req = urllib.request.Request(url, headers={"User-Agent": "warroom-r5/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                coins = json.loads(r.read().decode())
            for c in coins:
                sym = (c.get("symbol", "") or "").upper() + "-USD"
                if sym in fed:
                    continue
                master.append(_inst("crypto", sym, "coingecko-aggregate", "TIER_B_RESEARCH_DISCOVERY",
                                    instrument_kind="spot", coingecko_id=c.get("id"),
                                    market_cap=c.get("market_cap"),
                                    source="coingecko markets top-100"))
                live_n += 1
        except Exception as e:
            master.append(_inst("crypto", "__COINGECKO_FEED__", "coingecko", "UNAVAILABLE",
                                data_state="ERROR", source=f"coingecko fetch failed: {type(e).__name__}"))
    gaps = [{
        "domain": "crypto.venue_exact_derivatives",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "perp/futures/options with funding, basis, OI, liquidations require venue-exact feeds (Binance/Bybit/Deribit APIs admitted but not wired)",
        "provider_required": "venue APIs (Binance/Deribit) or CCXT integration",
        "recall_impact": "MEDIUM: positioning-based timing signals unavailable",
    }, {
        "domain": "crypto.onchain_fees_usage",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "protocol usage/fees/value-capture require on-chain analytics (Artemis/TokenTerminal/DeFiLlama admitted not wired)",
        "provider_required": "DeFiLlama/Artemis API",
        "recall_impact": "MEDIUM-HIGH for crypto bottleneck/value-capture theses",
    }]
    meta = {"market": "crypto", "built_at": NOW,
            "instrument_count": len(master),
            "tiers": {"TIER_A_FULL_DECISION": len(fed), "TIER_B_RESEARCH_DISCOVERY": live_n},
            "schema": "warroom.universe_master.v1"}
    return master, meta, gaps


# ---------------- Commodities ----------------

COMMODITY_CONTRACTS = [
    {"instrument": "CL", "name": "WTI Crude Oil", "venue": "NYMEX", "multiplier": 1000,
     "unit": "USD/bbl", "delivery": "physical (Cushing)", "proxy_etf": "USO"},
    {"instrument": "GC", "name": "Gold", "venue": "COMEX", "multiplier": 100,
     "unit": "USD/troy oz", "delivery": "physical", "proxy_etf": "GLD"},
    {"instrument": "HG", "name": "Copper", "venue": "COMEX", "multiplier": 25000,
     "unit": "USD/lb", "delivery": "physical", "proxy_etf": "CPER"},
]


def build_commodities():
    fed = sorted(set(D.COMMO_UNIVERSE))
    master = []
    for c in COMMODITY_CONTRACTS:
        master.append(_inst("commodities", c["instrument"], c["venue"], "TIER_B_RESEARCH_DISCOVERY",
                            instrument_kind="future", name=c["name"], multiplier=c["multiplier"],
                            unit=c["unit"], delivery=c["delivery"],
                            note="exact contract spec registered; continuous price history via proxy",
                            source="CME contract specs (static reference)"))
    for t in fed:
        master.append(_inst("commodities", t, "yahoo-etf", "TIER_A_FULL_DECISION",
                            instrument_kind="etf_proxy",
                            note="labelled proxy — NOT the exact deliverable contract",
                            source="warroom/data.py COMMO_UNIVERSE"))
    gaps = [{
        "domain": "commodities.exact_futures_history",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "continuous exact-contract series (CL/GC/HG individual months, roll rules, curve) require CME/Datastream/Quandl licensed feed; ETF proxies currently carry price discovery",
        "provider_required": "CME Datamine or Nasdaq Data Link (CHRIS)",
        "recall_impact": "MEDIUM: curve/roll and physical-basis signals unavailable",
    }, {
        "domain": "commodities.physical_inventories",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "EIA/USDA/LME inventory series admitted but not wired as PIT feeds",
        "provider_required": "EIA API (free, key required), USDA, LME licensed",
        "recall_impact": "HIGH for physical-shock subcomponent of crash meter and commodity theses",
    }]
    meta = {"market": "commodities", "built_at": NOW, "instrument_count": len(master),
            "tiers": {"TIER_A_FULL_DECISION": len(fed),
                      "TIER_B_RESEARCH_DISCOVERY": len(COMMODITY_CONTRACTS)},
            "schema": "warroom.universe_master.v1"}
    return master, meta, gaps


# ---------------- FX ----------------

FX_PAIRS = [
    {"instrument": "EURUSD", "base": "EUR", "quote": "USD", "kind": "spot_major", "convention": "USD per EUR"},
    {"instrument": "USDJPY", "base": "USD", "quote": "JPY", "kind": "spot_major", "convention": "JPY per USD"},
    {"instrument": "GBPUSD", "base": "GBP", "quote": "USD", "kind": "spot_major", "convention": "USD per GBP"},
    {"instrument": "AUDUSD", "base": "AUD", "quote": "USD", "kind": "spot_major", "convention": "USD per AUD"},
    {"instrument": "USDIDR", "base": "USD", "quote": "IDR", "kind": "spot_em_ndf_region", "convention": "IDR per USD"},
    {"instrument": "DXY", "base": "USD", "quote": "basket", "kind": "index", "convention": "index points"},
]


def build_fx():
    fed = set(D.FX_UNIVERSE)
    master = []
    for p in FX_PAIRS:
        yt = p["instrument"] + "=X"
        tier = "TIER_A_FULL_DECISION" if (yt in fed or p["instrument"] == "DXY") else "TIER_B_RESEARCH_DISCOVERY"
        master.append(_inst("fx", p["instrument"], "yahoo/ecn-composite", tier,
                            instrument_kind=p["kind"], convention=p["convention"],
                            source="warroom/data.py FX_UNIVERSE / static pair master"))
    gaps = [{
        "domain": "fx.forwards_options_tff",
        "status": "UNSUPPORTED_LICENSE_REQUIRED",
        "reason": "deliverable/NDF forwards, FX options, and CFTC TFF positioning require licensed feeds; COT (futures) admitted via build_feeds but not wired live",
        "provider_required": "CFTC TFF public reports + Bloomberg/Refinitiv for forwards/options",
        "recall_impact": "MEDIUM for carry crowding and intervention-risk signals",
    }]
    meta = {"market": "fx", "built_at": NOW, "instrument_count": len(master),
            "tiers": {"TIER_A_FULL_DECISION": sum(1 for m in master if m["tier"] == "TIER_A_FULL_DECISION")},
            "schema": "warroom.universe_master.v1"}
    return master, meta, gaps


def main():
    fetch_live = os.getenv("UNIVERSE_FETCH_LIVE", "1") == "1"
    all_gaps, report = [], {}
    for name, fn in (("us", build_us), ("ihsg", build_ihsg),
                     ("crypto", lambda: build_crypto(fetch_live)),
                     ("commodities", build_commodities), ("fx", build_fx)):
        master, meta, gaps = fn()
        (OUT / f"{name}.json").write_text(json.dumps(
            {"meta": meta, "instruments": master}, indent=1), encoding="utf-8")
        all_gaps.extend(gaps)
        report[name] = {
            "instrument_count": meta["instrument_count"],
            "tiers": meta["tiers"],
            "gaps": len(gaps),
        }
        print(f"{name}: {meta['instrument_count']} instruments, tiers={meta['tiers']}, gaps={len(gaps)}")

    gap_reg = {"schema": "warroom.coverage_gap_registry.v1", "built_at": NOW, "gaps": all_gaps}
    (COV / "gap_registry.json").write_text(json.dumps(gap_reg, indent=1), encoding="utf-8")

    # recall-loss quantification per market (explicit, honest)
    recall = {
        "us": "S&P 500 sleeve has delisted history; outside it, delisted/failed-lookalike recall unquantified until licensed PIT source (likely material for small-cap surges)",
        "ihsg": "HIGH recall loss: full IDX ~900 issuers vs price-fed sleeve; small/mid-cap multibaggers systematically missed",
        "crypto": "top-100 discovery via CoinGecko live; long-tail venue listings missed without venue APIs",
        "commodities": "3 exact contracts registered (WTI/Gold/Copper scope); other commodities reference-only",
        "fx": "6 majors/EM pairs; exotics reference-only",
    }
    cov = {"schema": "warroom.coverage_report.v1", "built_at": NOW,
           "markets": report, "recall_risk": recall}
    (COV / "coverage_report.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    print(f"gaps: {len(all_gaps)} -> data/coverage/gap_registry.json")
    print("coverage report -> data/coverage/coverage_report.json")


if __name__ == "__main__":
    main()
