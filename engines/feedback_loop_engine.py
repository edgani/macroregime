"""engines/feedback_loop_engine.py v1 — Reinforcement Learning for Autonomy

Tracks every auto-discovery for 6 months.
Auto-promotes high-performers to permanent lists.
Auto-demotes false positives.
"""
from __future__ import annotations
import json
import os
import time
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

DB_PATH = ".cache/autonomy_feedback_db.json"

@dataclass
class TrackedDiscovery:
    discovery_id: str
    name: str
    category: str
    beneficiary_tickers: List[str]
    discovered_at: float  # timestamp
    confidence_at_discovery: float
    regime_at_discovery: str
    promoted: bool = False
    demoted: bool = False
    six_month_return: Optional[float] = None
    vs_benchmark_return: Optional[float] = None
    validation_status: str = "pending"  # pending | validated | false_positive

class FeedbackLoopEngine:
    """
    The memory of the autonomy system.
    Without this, discoveries are just suggestions.
    With this, the system learns what works.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.db = self._load_db()

    def _load_db(self) -> Dict[str, dict]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    return json.load(f)
            except:
                return {"discoveries": [], "promotions": [], "demotions": []}
        return {"discoveries": [], "promotions": [], "demotions": []}

    def _save_db(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self.db, f, indent=2, default=str)

    def track(self, candidates: List[dict], regime: str):
        """Call this every time AutoDiscoveryEngine produces candidates."""
        for c in candidates:
            did = f"{c['name']}_{c['discovered_at']}".replace(" ", "_")
            if did not in [d["discovery_id"] for d in self.db["discoveries"]]:
                self.db["discoveries"].append({
                    "discovery_id": did,
                    "name": c["name"],
                    "category": c["category"],
                    "beneficiary_tickers": c.get("beneficiary_tickers", []),
                    "discovered_at": c.get("discovered_at", ""),
                    "discovered_ts": time.time(),
                    "confidence_at_discovery": c.get("confidence", 0.5),
                    "regime_at_discovery": regime,
                    "promoted": False,
                    "demoted": False,
                    "six_month_return": None,
                    "vs_benchmark_return": None,
                    "validation_status": "pending",
                })
        self._save_db()

    def evaluate(self, prices: Dict[str, pd.Series], benchmark: str = "SPY"):
        """
        Call this periodically (e.g., monthly) to evaluate pending discoveries.
        Promote if 6M return > benchmark + 10%.
        Demote if 6M return < -10%.
        """
        bench = prices.get(benchmark)
        if bench is None or len(bench) < 130:  # ~6 months
            return {"evaluated": 0, "promoted": 0, "demoted": 0}

        bench_ret = self._ret(bench, 126) or 0.0  # 6M ~ 126 trading days
        now = time.time()
        six_month_sec = 180 * 24 * 3600

        promoted = []
        demoted = []

        for d in self.db["discoveries"]:
            if d["validation_status"] != "pending":
                continue
            
            # Need at least 6 months since discovery
            disc_ts = d.get("discovered_ts", 0)
            if now - disc_ts < six_month_sec:
                continue

            tickers = d.get("beneficiary_tickers", [])
            if not tickers:
                continue

            # Compute average 6M return of beneficiaries
            rets = []
            for t in tickers:
                s = prices.get(t)
                if s is None or len(s) < 130:
                    continue
                r = self._ret(s, 126)
                if r is not None:
                    rets.append(r)

            if not rets:
                continue

            avg_ret = float(np.mean(rets))
            vs_bench = avg_ret - bench_ret

            d["six_month_return"] = round(avg_ret, 4)
            d["vs_benchmark_return"] = round(vs_bench, 4)

            if vs_bench > 0.10:  # Outperformed benchmark by 10%+
                d["validation_status"] = "validated"
                d["promoted"] = True
                promoted.append(d)
            elif avg_ret < -0.10:  # Lost 10%+
                d["validation_status"] = "false_positive"
                d["demoted"] = True
                demoted.append(d)
            else:
                d["validation_status"] = "inconclusive"

        self.db["promotions"].extend([p["discovery_id"] for p in promoted])
        self.db["demotions"].extend([d["discovery_id"] for d in demoted])
        self._save_db()

        return {
            "evaluated": len([d for d in self.db["discoveries"] if d["six_month_return"] is not None]),
            "promoted": len(promoted),
            "demoted": len(demoted),
            "promotion_list": promoted,
            "demotion_list": demoted,
        }

    def get_permanent_additions(self) -> Dict[str, List[dict]]:
        """Return discoveries that should be permanently added to system lists."""
        validated = [d for d in self.db["discoveries"] if d.get("validation_status") == "validated" and d.get("promoted")]
        return {
            "bottlenecks": [d for d in validated if d["category"] == "bottleneck"],
            "narratives": [d for d in validated if d["category"] == "narrative"],
            "transitions": [d for d in validated if d["category"] == "transition"],
        }

    def apply_to_settings(self, bottleneck_dict, narrative_dict, transition_dict):
        """
        Mutates the dicts in-place by adding validated discoveries.
        Call this before engines use the dicts.
        """
        adds = self.get_permanent_additions()
        for b in adds["bottlenecks"]:
            # Convert to KNOWN_BOTTLENECKS format
            for t in b.get("beneficiary_tickers", []):
                if t not in bottleneck_dict:
                    bottleneck_dict[t] = {
                        "type": "structural",
                        "sub": "auto_discovered",
                        "constraint": b.get("confidence_at_discovery", 0.7),
                        "phase": "level_1",
                        "thesis": b.get("name", "") + ": " + b.get("thesis", ""),
                        "catalyst": b.get("confirmation_signal", ""),
                        "tp_type": "structural",
                        "risk": "Auto-discovered; validate before sizing",
                        "auto": True,
                    }
        # Similar for narratives and transitions...
        return bottleneck_dict, narrative_dict, transition_dict

    def _ret(self, s, n):
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 1:
            return None
        try:
            r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
            return r if math.isfinite(r) else None
        except:
            return None