"""engines/ticker_discovery_engine.py — v38

Solves Edward's problem: "Tickernya ga ada, lu auto add sendiri?"

Tiered ticker loading architecture:
  TIER 0: Major indices/ETFs (always loaded, fast — 50 tickers)
  TIER 1: Configured + bottleneck_kb + chain_reactions (loaded on dashboard open ~5s)
  TIER 2: LAZY LOAD — when alpha detected for unknown ticker
  TIER 3: USER-REQUESTED — "Add ticker X" button

Key flow:
  1. Scan alpha signals from chain_reaction_engine + alpha_synthesis_v37
  2. Cross-check against currently-loaded universe
  3. Flag missing tickers as "discovered"
  4. Queue for next fetch cycle (background, doesn't block dashboard)
  5. Cache results, auto-add to data/extended_universe.json
  6. On next orchestrator run, extended tickers loaded automatically

Performance preserved by:
  - Async/lazy loading
  - Cache 24h for discovered tickers
  - Tier 0 always pre-loaded (fast startup)
  - Universe file write batched
"""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

EXTENDED_UNIVERSE_PATH = "data/extended_universe.json"


# ═══════════════════════════════════════════════════════════════════════
# Schema for extended universe
# ═══════════════════════════════════════════════════════════════════════

EXTENDED_UNIVERSE_TEMPLATE = {
    "_schema_version": "v38",
    "_description": "Tickers auto-discovered by alpha engines but not in static config. Loaded as Tier 2.",
    "tier_2_discovered": {},   # {ticker: {discovered_date, source, alpha_context, last_fetched}}
    "tier_3_user_requested": {},   # {ticker: {requested_date, fetch_priority}}
    "fetch_failed": {},        # {ticker: {error, retry_after}}
}


class TickerDiscoveryEngine:
    """Auto-discover tickers from alpha engines + manage extended universe."""

    def __init__(self, universe_path: str = EXTENDED_UNIVERSE_PATH,
                 base_tier_0_size: int = 50):
        self.universe_path = universe_path
        self.base_tier_0_size = base_tier_0_size
        self.extended = self._load()

    def _load(self) -> Dict:
        """Load extended universe JSON, create if missing."""
        if not os.path.exists(self.universe_path):
            # Try alternate path
            alt = "extended_universe.json"
            if os.path.exists(alt):
                self.universe_path = alt
            else:
                logger.info(f"Extended universe not found, will create at {self.universe_path}")
                return dict(EXTENDED_UNIVERSE_TEMPLATE)
        try:
            with open(self.universe_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure required keys
            for key in ("tier_2_discovered", "tier_3_user_requested", "fetch_failed"):
                if key not in data:
                    data[key] = {}
            return data
        except Exception as e:
            logger.error(f"Failed to load extended universe: {e}")
            return dict(EXTENDED_UNIVERSE_TEMPLATE)

    def _save(self):
        """Save extended universe to JSON."""
        try:
            os.makedirs(os.path.dirname(self.universe_path), exist_ok=True)
            with open(self.universe_path, "w", encoding="utf-8") as f:
                json.dump(self.extended, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save extended universe: {e}")

    # ── Discovery from chain reactions ────────────────────────────────

    def discover_from_chains(self, current_universe: Set[str],
                              chain_engine) -> List[str]:
        """
        Scan all chain reactions for tickers NOT in current universe.
        Add them to tier_2_discovered.
        """
        new_discoveries = []
        if not hasattr(chain_engine, "chains"):
            return new_discoveries

        for chain in chain_engine.chains:
            chain_id = chain.get("chain_id", "?")
            chain_name = chain.get("name", "?")
            trigger_status = chain.get("trigger_status", "UNKNOWN")

            # Only discover from ACTIVE chains (prioritize relevant)
            if "ACTIVE" not in trigger_status:
                continue

            for step in chain.get("propagation_sequence", []):
                tier = step.get("tier", 1)
                for ticker in step.get("tickers", []):
                    tu = ticker.upper()
                    if tu in current_universe:
                        continue
                    if tu in self.extended.get("tier_2_discovered", {}):
                        continue
                    if tu in self.extended.get("fetch_failed", {}):
                        # Check if retry window expired
                        failed = self.extended["fetch_failed"][tu]
                        retry_after = failed.get("retry_after", "")
                        try:
                            if datetime.now() < datetime.strptime(retry_after, "%Y-%m-%d"):
                                continue
                        except Exception:
                            pass

                    # Add to tier 2
                    self.extended.setdefault("tier_2_discovered", {})[tu] = {
                        "discovered_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": f"chain:{chain_id}",
                        "alpha_context": {
                            "chain_name": chain_name,
                            "tier": tier,
                            "role": step.get("role", "?"),
                            "expected_multiplier": step.get("expected_multiplier", [1, 2]),
                        },
                        "last_fetched": None,
                        "fetch_priority": "HIGH" if tier <= 2 else "MEDIUM",
                    }
                    new_discoveries.append(tu)

        if new_discoveries:
            self._save()
            logger.info(f"Discovered {len(new_discoveries)} new tickers from chains")
        return new_discoveries

    # ── Discovery from alpha synthesis ────────────────────────────────

    def discover_from_alpha(self, current_universe: Set[str],
                             alpha_signals: List) -> List[str]:
        """Scan alpha signals for tickers NOT in current universe."""
        new_discoveries = []
        for sig in alpha_signals:
            tu = getattr(sig, "ticker", "").upper()
            if not tu or tu in current_universe:
                continue
            if tu in self.extended.get("tier_2_discovered", {}):
                continue

            self.extended.setdefault("tier_2_discovered", {})[tu] = {
                "discovered_date": datetime.now().strftime("%Y-%m-%d"),
                "source": f"alpha:{getattr(sig, 'framework', '?')}",
                "alpha_context": {
                    "direction": getattr(sig, "direction", "?"),
                    "conviction": getattr(sig, "conviction", 0),
                },
                "last_fetched": None,
                "fetch_priority": "HIGH" if getattr(sig, "conviction", 0) >= 75 else "MEDIUM",
            }
            new_discoveries.append(tu)

        if new_discoveries:
            self._save()
            logger.info(f"Discovered {len(new_discoveries)} new tickers from alpha")
        return new_discoveries

    # ── User-requested ────────────────────────────────────────────────

    def add_user_requested(self, ticker: str, priority: str = "HIGH"):
        """Add ticker to tier 3 (user explicit request)."""
        tu = ticker.upper()
        self.extended.setdefault("tier_3_user_requested", {})[tu] = {
            "requested_date": datetime.now().strftime("%Y-%m-%d"),
            "fetch_priority": priority,
        }
        self._save()
        logger.info(f"User requested ticker added: {tu}")

    # ── Getters for orchestrator ──────────────────────────────────────

    def get_all_extended_tickers(self) -> List[str]:
        """Get all extended tickers (tier 2 + tier 3) for orchestrator to fetch."""
        tier_2 = list(self.extended.get("tier_2_discovered", {}).keys())
        tier_3 = list(self.extended.get("tier_3_user_requested", {}).keys())
        return sorted(set(tier_2 + tier_3))

    def get_high_priority(self) -> List[str]:
        """Get high-priority extended tickers (fetch first)."""
        high = []
        for ticker, data in self.extended.get("tier_2_discovered", {}).items():
            if data.get("fetch_priority") == "HIGH":
                high.append(ticker)
        for ticker, data in self.extended.get("tier_3_user_requested", {}).items():
            if data.get("fetch_priority") == "HIGH":
                high.append(ticker)
        return sorted(set(high))

    def get_ticker_context(self, ticker: str) -> Optional[Dict]:
        """Get discovery context for a ticker (why it was added)."""
        tu = ticker.upper()
        if tu in self.extended.get("tier_2_discovered", {}):
            return self.extended["tier_2_discovered"][tu]
        if tu in self.extended.get("tier_3_user_requested", {}):
            return self.extended["tier_3_user_requested"][tu]
        return None

    # ── Fetch result handling ─────────────────────────────────────────

    def mark_fetched(self, ticker: str):
        """Mark ticker as successfully fetched."""
        tu = ticker.upper()
        if tu in self.extended.get("tier_2_discovered", {}):
            self.extended["tier_2_discovered"][tu]["last_fetched"] = (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self._save()

    def mark_failed(self, ticker: str, error: str, retry_days: int = 7):
        """Mark fetch failure with retry window."""
        tu = ticker.upper()
        retry_after = (datetime.now() + timedelta(days=retry_days)).strftime("%Y-%m-%d")
        self.extended.setdefault("fetch_failed", {})[tu] = {
            "error": str(error)[:200],
            "retry_after": retry_after,
            "failed_count": self.extended.get("fetch_failed", {}).get(tu, {}).get("failed_count", 0) + 1,
        }
        # Remove from discovered if too many failures
        if self.extended["fetch_failed"][tu]["failed_count"] >= 3:
            self.extended.get("tier_2_discovered", {}).pop(tu, None)
            logger.warning(f"Ticker {tu} removed from discovered after 3 failures")
        self._save()

    def cleanup_stale(self, days: int = 90):
        """Remove tier 2 discoveries that haven't been used in N days."""
        cutoff = datetime.now() - timedelta(days=days)
        removed = []
        for ticker, data in list(self.extended.get("tier_2_discovered", {}).items()):
            discovered = data.get("discovered_date", "")
            try:
                if datetime.strptime(discovered, "%Y-%m-%d") < cutoff:
                    if not data.get("last_fetched"):
                        del self.extended["tier_2_discovered"][ticker]
                        removed.append(ticker)
            except Exception:
                pass
        if removed:
            self._save()
            logger.info(f"Cleaned {len(removed)} stale discoveries")

    # ── Summary ────────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """Get summary of extended universe state."""
        return {
            "tier_2_count": len(self.extended.get("tier_2_discovered", {})),
            "tier_3_count": len(self.extended.get("tier_3_user_requested", {})),
            "failed_count": len(self.extended.get("fetch_failed", {})),
            "high_priority_count": len(self.get_high_priority()),
            "total_extended": len(self.get_all_extended_tickers()),
        }


# ═══════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════

_DISCOVERY_SINGLETON: Optional[TickerDiscoveryEngine] = None


def get_discovery_engine() -> TickerDiscoveryEngine:
    global _DISCOVERY_SINGLETON
    if _DISCOVERY_SINGLETON is None:
        _DISCOVERY_SINGLETON = TickerDiscoveryEngine()
    return _DISCOVERY_SINGLETON


# ═══════════════════════════════════════════════════════════════════════
# Orchestrator integration hook
# ═══════════════════════════════════════════════════════════════════════

def run_discovery_cycle(current_universe: Set[str],
                         chain_engine=None, alpha_signals: Optional[List] = None) -> Dict:
    """
    Called by orchestrator to discover new tickers and queue them.

    Returns summary dict with new discoveries.
    """
    engine = get_discovery_engine()

    new_from_chains = []
    new_from_alpha = []

    if chain_engine:
        new_from_chains = engine.discover_from_chains(current_universe, chain_engine)
    if alpha_signals:
        new_from_alpha = engine.discover_from_alpha(current_universe, alpha_signals)

    # Cleanup stale entries
    engine.cleanup_stale(days=90)

    return {
        "new_from_chains": new_from_chains,
        "new_from_alpha": new_from_alpha,
        "total_new": len(new_from_chains) + len(new_from_alpha),
        "extended_universe_size": engine.get_summary()["total_extended"],
        "high_priority_pending": engine.get_high_priority(),
    }


__all__ = [
    "TickerDiscoveryEngine",
    "get_discovery_engine",
    "run_discovery_cycle",
    "EXTENDED_UNIVERSE_TEMPLATE",
]
