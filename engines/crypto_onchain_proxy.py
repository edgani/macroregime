"""engines/crypto_onchain_proxy.py — v38

On-chain activity PROXY via price/volume patterns. No real Glassnode/Nansen feed.

Edward's ask: "Crypto on-chain activity yang bisa kasih clue kalo sebuah token mau di naikin"

What we CAN proxy from price/volume:
  - Whale accumulation (large block detection from price action + volume spikes)
  - BTC dominance shift (alt season signal)
  - Halving cycle position (for PoW: BTC, LTC, BCH)
  - Funding rate proxy (extreme momentum + reversal pattern)
  - Listing momentum (new highs + volume = exchange listing effect)

What we CANNOT do (need paid feed):
  - Real wallet activity (Glassnode $50-300/mo)
  - Smart money flow tracking (Nansen $150-2000/mo)
  - DEX volume + TVL (DeFiLlama free / Dune)
  - Stablecoin issuance (Glassnode)
  - Miner reserves + exchange flow (Glassnode)

Output: CryptoSignal per ticker with proxy confidence + caveats.
"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# DATACLASS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class CryptoSignal:
    """On-chain proxy signal for a crypto ticker."""
    ticker: str
    proxy_score: float                # 0-100 composite
    direction_bias: str               # ACCUMULATION / DISTRIBUTION / NEUTRAL
    
    # Component scores
    whale_activity_score: float       # large block accumulation pattern
    cycle_position_score: float       # halving cycle (PoW) or year-cycle
    funding_extreme_score: float      # momentum / mean reversion proxy
    relative_strength_score: float    # vs BTC dominance
    listing_momentum_score: float     # new high break + volume
    
    detected_patterns: List[str]
    caveats: List[str]
    
    # Recommended action
    action: str                       # ACCUMULATE / RIDE / FADE / AVOID / MONITOR
    horizon: str


# ═══════════════════════════════════════════════════════════════════════
# CYCLE DATA — HALVING DATES + CYCLE ANCHORS
# ═══════════════════════════════════════════════════════════════════════

BTC_HALVINGS = ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-19", "2028-04-15"]

PROOF_OF_WORK_TICKERS = {
    "BTC-USD": "BTC",
    "BTCUSDT": "BTC",
    "LTC-USD": "LTC",
    "LTCUSDT": "LTC",
    "BCH-USD": "BCH",
    "BCHUSDT": "BCH",
    "DOGE-USD": "DOGE",
    "DOGEUSDT": "DOGE",
}


# ═══════════════════════════════════════════════════════════════════════
# CRYPTO ON-CHAIN PROXY ENGINE
# ═══════════════════════════════════════════════════════════════════════

class CryptoOnChainProxy:
    """Detect on-chain-like signals from price/volume patterns."""

    def detect(self, ticker: str, prices: pd.Series,
               btc_prices: Optional[pd.Series] = None,
               snap: Optional[Dict] = None) -> Optional[CryptoSignal]:
        """Run all proxy detectors. Return CryptoSignal."""
        s = pd.to_numeric(prices, errors="coerce").dropna()
        if len(s) < 60:
            return None

        try:
            metrics = self._compute_metrics(s)

            whale_score, whale_patterns = self._detect_whale_activity(s, metrics)
            cycle_score, cycle_patterns = self._detect_cycle_position(ticker, s)
            funding_score, funding_patterns = self._detect_funding_extreme(s, metrics)
            rs_score, rs_patterns = self._detect_relative_strength(
                ticker, s, btc_prices
            )
            listing_score, listing_patterns = self._detect_listing_momentum(s, metrics)

            # Composite
            proxy_score = (
                whale_score * 0.30 + cycle_score * 0.20 +
                funding_score * 0.20 + rs_score * 0.15 + listing_score * 0.15
            )

            patterns = (
                whale_patterns + cycle_patterns + funding_patterns +
                rs_patterns + listing_patterns
            )

            # Direction bias
            if whale_score > 60 and proxy_score > 55:
                direction_bias = "ACCUMULATION"
            elif funding_score < 30 and metrics["ret_20d"] > 0.30:
                direction_bias = "DISTRIBUTION"
            else:
                direction_bias = "NEUTRAL"

            # Action mapping
            if direction_bias == "ACCUMULATION" and proxy_score >= 65:
                action = "ACCUMULATE"
                horizon = "2-12 weeks"
            elif direction_bias == "ACCUMULATION" and proxy_score >= 50:
                action = "RIDE"
                horizon = "1-4 weeks"
            elif direction_bias == "DISTRIBUTION":
                action = "FADE"
                horizon = "1-2 weeks"
            elif proxy_score < 35:
                action = "AVOID"
                horizon = "N/A"
            else:
                action = "MONITOR"
                horizon = "1-2 weeks"

            caveats = [
                "Proxy only — no real on-chain feed (Glassnode/Nansen unavailable)",
                "Whale activity inferred from price/volume, not wallet data",
                "Cycle timing approximate (halving-anchored for PoW only)",
            ]

            return CryptoSignal(
                ticker=ticker,
                proxy_score=round(proxy_score, 1),
                direction_bias=direction_bias,
                whale_activity_score=round(whale_score, 1),
                cycle_position_score=round(cycle_score, 1),
                funding_extreme_score=round(funding_score, 1),
                relative_strength_score=round(rs_score, 1),
                listing_momentum_score=round(listing_score, 1),
                detected_patterns=patterns,
                caveats=caveats,
                action=action,
                horizon=horizon,
            )
        except Exception as e:
            logger.debug(f"Crypto proxy detect failed for {ticker}: {e}")
            return None

    # ── Metrics ───────────────────────────────────────────────────────

    def _compute_metrics(self, s: pd.Series) -> Dict:
        returns = s.pct_change().dropna()
        return {
            "current": float(s.iloc[-1]),
            "ret_5d": float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0,
            "ret_20d": float(s.iloc[-1] / s.iloc[-21] - 1) if len(s) >= 21 else 0,
            "ret_60d": float(s.iloc[-1] / s.iloc[-61] - 1) if len(s) >= 61 else 0,
            "vol_20": float(returns.tail(20).std()) if len(returns) >= 20 else 0,
            "vol_60": float(returns.tail(60).std()) if len(returns) >= 60 else 0,
            "high_60": float(s.tail(60).max()),
            "low_60": float(s.tail(60).min()),
            "sma_50": float(s.tail(50).mean()) if len(s) >= 50 else float(s.mean()),
            "green_days_20": int((returns.tail(20) > 0).sum()),
        }

    # ── Detector 1: Whale Activity Proxy ──────────────────────────────

    def _detect_whale_activity(self, s: pd.Series, m: Dict) -> tuple[float, List[str]]:
        """Large block accumulation proxy via price/volume."""
        patterns = []
        score = 30

        # Pattern 1: Vol compression + green days (silent accumulation)
        vol_ratio = m["vol_20"] / max(m["vol_60"], 0.001)
        if vol_ratio < 0.70 and m["green_days_20"] >= 12:
            patterns.append(f"🐋 Silent accumulation: vol {vol_ratio:.2f}x + {m['green_days_20']}/20 green days")
            score += 30

        # Pattern 2: Higher lows + range compression
        returns = s.pct_change().dropna()
        recent_lows = []
        for i in range(0, min(20, len(s)), 5):
            chunk = s.iloc[-i-5:-i] if i > 0 else s.tail(5)
            if len(chunk) >= 5:
                recent_lows.append(float(chunk.min()))
        if len(recent_lows) >= 3 and all(recent_lows[i] >= recent_lows[i+1] * 0.99 
                                          for i in range(len(recent_lows)-1)):
            patterns.append("📈 Higher lows pattern (4-week)")
            score += 20

        # Pattern 3: OBV-like proxy (volume-weighted returns positive)
        # Without real volume, use abs return as proxy
        weighted = (returns.tail(20) * returns.tail(20).abs()).sum()
        if weighted > 0.01:
            patterns.append("💰 Up-day strength > down-day weakness")
            score += 15

        return min(100, score), patterns

    # ── Detector 2: Cycle Position ────────────────────────────────────

    def _detect_cycle_position(self, ticker: str, s: pd.Series) -> tuple[float, List[str]]:
        """For PoW coins: how far into halving cycle?"""
        patterns = []
        score = 50

        coin = PROOF_OF_WORK_TICKERS.get(ticker.upper())
        if not coin:
            patterns.append("⚪ Non-PoW asset (no halving cycle)")
            return score, patterns

        # Find most recent halving date
        now = datetime.now()
        recent_halving = None
        next_halving = None
        for h in BTC_HALVINGS:
            h_dt = datetime.strptime(h, "%Y-%m-%d")
            if h_dt < now:
                recent_halving = h_dt
            elif h_dt > now and not next_halving:
                next_halving = h_dt

        if recent_halving:
            days_since = (now - recent_halving).days
            months_since = days_since / 30
            
            # Historical pattern: peak ~12-18 months post-halving for BTC
            if 8 <= months_since <= 18:
                patterns.append(f"🌕 {coin}: {months_since:.0f} months post-halving (bull phase window)")
                score += 30
            elif 0 <= months_since < 8:
                patterns.append(f"🌒 {coin}: {months_since:.0f} months post-halving (early phase)")
                score += 15
            elif months_since > 24:
                patterns.append(f"🌑 {coin}: {months_since:.0f} months post-halving (bear/accumulation)")
                score -= 10

        if next_halving:
            days_to_next = (next_halving - now).days
            if 0 < days_to_next < 365:
                patterns.append(f"⏰ Halving in {days_to_next} days (pre-halving rally setup)")
                score += 20

        return max(0, min(100, score)), patterns

    # ── Detector 3: Funding Rate Proxy ────────────────────────────────

    def _detect_funding_extreme(self, s: pd.Series, m: Dict) -> tuple[float, List[str]]:
        """Extreme momentum = funding extreme = mean reversion risk."""
        patterns = []
        score = 50

        # Extreme positive momentum = high funding = top risk
        if m["ret_20d"] > 0.50:
            patterns.append(f"⚠️ Extreme momentum: +{m['ret_20d']:.0%} in 20d (funding likely high)")
            score -= 20
        elif m["ret_20d"] > 0.25:
            patterns.append(f"📊 Strong momentum: +{m['ret_20d']:.0%} (watch funding)")
            score -= 5

        # Extreme negative momentum = washout = potential entry
        if m["ret_20d"] < -0.30:
            patterns.append(f"💀 Washout: {m['ret_20d']:.0%} in 20d (capitulation potential)")
            score += 25

        # Stable upward = healthy
        if 0.05 < m["ret_20d"] < 0.20 and 0.05 < m["ret_60d"] < 0.50:
            patterns.append(f"✅ Healthy uptrend: 20d {m['ret_20d']:+.0%}, 60d {m['ret_60d']:+.0%}")
            score += 20

        return max(0, min(100, score)), patterns

    # ── Detector 4: Relative Strength vs BTC ──────────────────────────

    def _detect_relative_strength(self, ticker: str, s: pd.Series,
                                    btc_prices: Optional[pd.Series]) -> tuple[float, List[str]]:
        """For alts: outperforming BTC = alt season indicator."""
        patterns = []
        score = 50

        if ticker.upper() in ("BTC-USD", "BTCUSDT"):
            patterns.append("⚪ BTC itself — RS check N/A")
            return score, patterns

        if btc_prices is None:
            patterns.append("⚠️ BTC reference price not available — RS not computed")
            return score, patterns

        try:
            btc_s = pd.to_numeric(pd.Series(btc_prices), errors="coerce").dropna()
            if len(btc_s) < 20 or len(s) < 20:
                return score, patterns
            
            alt_20d = float(s.iloc[-1] / s.iloc[-21] - 1)
            btc_20d = float(btc_s.iloc[-1] / btc_s.iloc[-21] - 1)
            rs = alt_20d - btc_20d

            if rs > 0.15:
                patterns.append(f"🚀 Outperforming BTC by {rs*100:+.1f}% (20d)")
                score += 25
            elif rs > 0.05:
                patterns.append(f"💪 Edge vs BTC: +{rs*100:.1f}% (20d)")
                score += 10
            elif rs < -0.15:
                patterns.append(f"📉 Underperforming BTC by {abs(rs)*100:.1f}%")
                score -= 15
        except Exception:
            pass

        return max(0, min(100, score)), patterns

    # ── Detector 5: Listing Momentum ──────────────────────────────────

    def _detect_listing_momentum(self, s: pd.Series, m: Dict) -> tuple[float, List[str]]:
        """New highs + sustained = exchange listing momentum proxy."""
        patterns = []
        score = 50

        # New 60-day high in last 5 days?
        last_5_max = float(s.tail(5).max())
        if last_5_max >= m["high_60"] * 0.99:
            patterns.append("🎯 New 60-day high (listing momentum / breakout)")
            score += 25

        # Sustained gains (60d+ uptrend with multiple legs)
        if m["ret_60d"] > 0.30 and m["green_days_20"] >= 13:
            patterns.append(f"📊 Sustained uptrend: 60d {m['ret_60d']:+.0%}, persistent green")
            score += 20

        # At 60-day low (reverse — distribution)
        if m["current"] <= m["low_60"] * 1.02:
            patterns.append("⚠️ Near 60-day low — distribution risk")
            score -= 20

        return max(0, min(100, score)), patterns


# ═══════════════════════════════════════════════════════════════════════
# Formatting helper
# ═══════════════════════════════════════════════════════════════════════

def format_crypto_signal_markdown(sig: CryptoSignal) -> str:
    if not sig:
        return ""
    lines = []
    lines.append(f"### 🪙 {sig.ticker} On-Chain Proxy")
    lines.append(f"**Proxy Score**: {sig.proxy_score:.0f}/100 · **Bias**: {sig.direction_bias}")
    lines.append(f"**Action**: `{sig.action}` · **Horizon**: {sig.horizon}")
    lines.append("")
    lines.append("**Component Scores**:")
    lines.append(f"- 🐋 Whale activity: {sig.whale_activity_score:.0f}")
    lines.append(f"- 🔄 Cycle position: {sig.cycle_position_score:.0f}")
    lines.append(f"- ⚡ Funding extreme: {sig.funding_extreme_score:.0f}")
    lines.append(f"- 💪 Relative strength (vs BTC): {sig.relative_strength_score:.0f}")
    lines.append(f"- 🎯 Listing momentum: {sig.listing_momentum_score:.0f}")
    lines.append("")
    if sig.detected_patterns:
        lines.append("**Patterns detected**:")
        for p in sig.detected_patterns:
            lines.append(f"- {p}")
        lines.append("")
    lines.append("**Honest caveats**:")
    for c in sig.caveats:
        lines.append(f"- {c}")
    return "\n".join(lines)


__all__ = [
    "CryptoOnChainProxy",
    "CryptoSignal",
    "format_crypto_signal_markdown",
    "PROOF_OF_WORK_TICKERS",
    "BTC_HALVINGS",
]
