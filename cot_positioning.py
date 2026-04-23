"""
cot_positioning.py — CFTC Commitments of Traders Engine
Hedgeye-style: 52-week COT Index, Extreme Alerts, FLIP Indicator, Consensus Overlay
Data: CFTC Public Reporting Environment (PRE) — Legacy All dataset
"""
import os, json, math, logging, requests, pandas as pd, numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

CFTC_API_BASE = "https://publicreporting.cftc.gov/resource"
LEGACY_DATASET = "srt6-5q2f"

MARKET_MAP = {
    "S&P 500": {"search": "E-MINI S&P 500", "category": "Equity"},
    "Nasdaq": {"search": "E-MINI NASDAQ", "category": "Equity"},
    "Russell": {"search": "E-MINI RUSSELL", "category": "Equity"},
    "10Y Treasury": {"search": "10-YEAR TREASURY NOTES", "category": "Rates"},
    "2Y Treasury": {"search": "2-YEAR TREASURY NOTES", "category": "Rates"},
    "Gold": {"search": "GOLD", "category": "Commodity"},
    "Silver": {"search": "SILVER", "category": "Commodity"},
    "Copper": {"search": "COPPER", "category": "Commodity"},
    "WTI Oil": {"search": "CRUDE OIL, LIGHT SWEET", "category": "Commodity"},
    "Natural Gas": {"search": "NATURAL GAS", "category": "Commodity"},
    "VIX": {"search": "VIX FUTURES", "category": "Volatility"},
    "USD Index": {"search": "U.S. DOLLAR INDEX", "category": "FX"},
    "Euro": {"search": "EURO FX", "category": "FX"},
    "Yen": {"search": "JAPANESE YEN", "category": "FX"},
    "Bitcoin": {"search": "BITCOIN", "category": "Crypto"},
}

@dataclass
class CoTReading:
    date: str
    market: str
    oi: int
    noncomm_net: int
    noncomm_long: int
    noncomm_short: int
    comm_net: int
    comm_long: int
    comm_short: int
    nonrep_net: int
    cot_index: float = 0.0
    extreme: str = "—"
    flip_signal: bool = False


class CFTCPositioningEngine:
    def __init__(self, weeks=60):
        self.weeks = weeks
        self.raw_df: Optional[pd.DataFrame] = None
        self.readings: Dict[str, List[CoTReading]] = {}

    def _fetch_legacy(self) -> Optional[pd.DataFrame]:
        cutoff = (datetime.now() - timedelta(weeks=self.weeks + 4)).strftime("%Y-%m-%d")
        url = f"{CFTC_API_BASE}/{LEGACY_DATASET}.json"
        params = {
            "$limit": 50000,
            "$where": f"report_date_as_yyyy_mm_dd > '{cutoff}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
        }
        try:
            r = requests.get(url, params=params, timeout=45)
            if r.status_code != 200:
                logger.warning(f"CFTC API status {r.status_code}")
                return None
            data = r.json()
            if not data:
                return None
            df = pd.DataFrame(data)
            df.columns = [c.lower().strip() for c in df.columns]
            keep = [
                "report_date_as_yyyy_mm_dd",
                "market_and_exchange_names",
                "open_interest_all",
                "noncomm_positions_long_all",
                "noncomm_positions_short_all",
                "noncomm_postions_spread_all",
                "comm_positions_long_all",
                "comm_positions_short_all",
            ]
            df = df[[c for c in keep if c in df.columns]]
            df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
            for c in df.columns:
                if c not in ("report_date_as_yyyy_mm_dd", "market_and_exchange_names"):
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            logger.info(f"CFTC fetch: {len(df)} rows, {df['report_date_as_yyyy_mm_dd'].nunique()} weeks")
            return df
        except Exception as e:
            logger.error(f"CFTC fetch error: {e}")
            return None

    def _match_market(self, name: str) -> Optional[str]:
        name_upper = name.upper()
        for label, meta in MARKET_MAP.items():
            if meta["search"].upper() in name_upper:
                return label
        return None

    def _compute_cot_index(self, series: pd.Series) -> float:
        if len(series) < 10:
            return 50.0
        min_v = series.min()
        max_v = series.max()
        if max_v == min_v:
            return 50.0
        latest = series.iloc[-1]
        idx = 100.0 * (latest - min_v) / (max_v - min_v)
        return float(np.clip(idx, 0.0, 100.0))

    def _extreme_flag(self, idx: float) -> str:
        if idx >= 90:
            return "🔴 EXTREME LONG"
        if idx <= 10:
            return "🟢 EXTREME SHORT"
        return "—"

    def build(self) -> Dict:
        df = self._fetch_legacy()
        if df is None:
            return {"error": "CFTC API unavailable", "markets": {}}

        self.raw_df = df
        df["noncomm_net"] = df.get("noncomm_positions_long_all", 0) - df.get("noncomm_positions_short_all", 0)
        df["comm_net"] = df.get("comm_positions_long_all", 0) - df.get("comm_positions_short_all", 0)
        df["market_label"] = df["market_and_exchange_names"].apply(self._match_market)
        df = df.dropna(subset=["market_label"])

        markets: Dict[str, List[CoTReading]] = {}
        for label in df["market_label"].unique():
            sub = df[df["market_label"] == label].sort_values("report_date_as_yyyy_mm_dd")
            if len(sub) < 4:
                continue
            readings = []
            for i in range(len(sub)):
                row = sub.iloc[i]
                window = sub["noncomm_net"].iloc[max(0, i - 52):i + 1]
                idx = self._compute_cot_index(window)
                extreme = self._extreme_flag(idx)
                flip = False
                if i > 0:
                    prev = sub.iloc[i - 1]
                    curr = row
                    flip = ((curr["noncomm_net"] - prev["noncomm_net"]) > 0 and
                            (curr["comm_net"] - prev["comm_net"]) > 0) or \
                           ((curr["noncomm_net"] - prev["noncomm_net"]) < 0 and
                            (curr["comm_net"] - prev["comm_net"]) < 0)
                r = CoTReading(
                    date=str(row["report_date_as_yyyy_mm_dd"].date()),
                    market=label,
                    oi=int(row.get("open_interest_all", 0)),
                    noncomm_net=int(row["noncomm_net"]),
                    noncomm_long=int(row.get("noncomm_positions_long_all", 0)),
                    noncomm_short=int(row.get("noncomm_positions_short_all", 0)),
                    comm_net=int(row["comm_net"]),
                    comm_long=int(row.get("comm_positions_long_all", 0)),
                    comm_short=int(row.get("comm_positions_short_all", 0)),
                    nonrep_net=0,
                    cot_index=round(idx, 1),
                    extreme=extreme,
                    flip_signal=flip,
                )
                readings.append(r)
            markets[label] = readings

        self.readings = markets
        return self._summarize()

    def _consensus_score(self, readings: List[CoTReading]) -> Dict:
        if not readings:
            return {}
        latest = readings[-1]
        consensus_long_pct = latest.noncomm_long / max(latest.oi, 1)
        consensus_short_pct = latest.noncomm_short / max(latest.oi, 1)
        smart_long_pct = latest.comm_long / max(latest.oi, 1)
        smart_short_pct = latest.comm_short / max(latest.oi, 1)
        crowded = latest.cot_index
        contrarian_bias = "NEUTRAL"
        if crowded >= 85:
            contrarian_bias = "🟡 CONTRARIAN SHORT"
        elif crowded <= 15:
            contrarian_bias = "🟡 CONTRARIAN LONG"
        return {
            "latest_date": latest.date,
            "noncomm_net": latest.noncomm_net,
            "comm_net": latest.comm_net,
            "cot_index": latest.cot_index,
            "extreme": latest.extreme,
            "flip": latest.flip_signal,
            "consensus_long_pct": round(consensus_long_pct, 2),
            "consensus_short_pct": round(consensus_short_pct, 2),
            "smart_long_pct": round(smart_long_pct, 2),
            "smart_short_pct": round(smart_short_pct, 2),
            "contrarian_bias": contrarian_bias,
            "crowded_score": round(crowded, 1),
        }

    def _summarize(self) -> Dict:
        out = {}
        for label, readings in self.readings.items():
            out[label] = self._consensus_score(readings)
        extremes = [m for m, d in out.items() if "EXTREME" in d.get("extreme", "")]
        flips = [m for m, d in out.items() if d.get("flip", False)]
        return {
            "markets": out,
            "extreme_count": len(extremes),
            "extreme_names": extremes,
            "flip_count": len(flips),
            "flip_names": flips,
            "timestamp": datetime.now().isoformat(),
            "source": "CFTC PRE Legacy All",
        }


def get_cot_snapshot() -> Dict:
    engine = CFTCPositioningEngine(weeks=60)
    return engine.build()


if __name__ == "__main__":
    snap = get_cot_snapshot()
    print(json.dumps(snap, indent=2, default=str))