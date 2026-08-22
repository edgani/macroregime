"""warroom/early_warning.py — panic-bottom & euphoria-top early warning (TERUJI di data real).

Jawaban Edward: "kasih early warning saat orang panic sell padahal udah mau bottom, & saat euforia
padahal mau crash." Diuji di S&P 500 + VIX real 2013-2018 (lihat research/RESEARCH_FINDINGS.md §7):

  ✅ PANIC = BOTTOM: SIGNIFIKAN. VIX spike + breadth capitulation → fwd 63d +5-8% vs +3% baseline,
     p<0.001. Composite fear-greed: EXTREME FEAR → +5.3%, corr(greed,fwd)=-0.21 p<0.0001. TERUJI.
  ⚠️ EUPHORIA = TOP: LEMAH di sample ini (p=0.34) — bias bull-market 2013-18. Butuh data 2008/2020/2022
     buat uji proper. Di-FLAG, ga di-overclaim. Jujur > ngarang.

Composite Fear-Greed (0=extreme fear/BUY, 100=extreme greed/CAUTION):
  fg = 40%·(1−VIX_pct) + 30%·(1−breadth_below_50ma) + 30%·momentum_z
Semua dari harga + VIX. Tiap output punya basis + tingkat kepercayaan (fear signal kuat, greed lemah).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def fear_greed(close, vix=None):
    """Composite fear-greed index 0-100 (0=max fear, 100=max greed) + contrarian signal.
    close: DataFrame [dates × tickers] or Series (index). vix: Series aligned, optional."""
    if isinstance(close, pd.DataFrame):
        spx = close.mean(axis=1)
        below50 = (close < close.rolling(50).mean()).mean(axis=1)
    else:
        spx = close
        below50 = pd.Series(0.5, index=spx.index)  # no breadth without cross-section
    z20 = (spx - spx.rolling(20).mean()) / spx.rolling(20).std()
    if vix is not None:
        vix = vix.reindex(spx.index).ffill()
        vix_pct = vix.rank(pct=True)
    else:
        # proxy fear from realized vol if no VIX
        rv = spx.pct_change().rolling(20).std()
        vix_pct = rv.rank(pct=True)
    fg = ((1 - vix_pct) * 0.4 + (1 - below50) * 0.3 + ((z20.clip(-3, 3) + 3) / 6) * 0.3) * 100
    cur = float(fg.iloc[-1]) if len(fg.dropna()) else None
    if cur is None:
        return {"value": None, "state": "no data"}
    if cur < 25:
        state, signal, col = "EXTREME FEAR", "contrarian BUY (validated: fwd63 +5% edge, p<0.001)", "grn"
    elif cur < 40:
        state, signal, col = "Fear", "lean long — fear historically precedes gains", "grn"
    elif cur < 60:
        state, signal, col = "Neutral", "no contrarian edge", "gry"
    elif cur < 75:
        state, signal, col = "Greed", "caution (weak signal — euphoria unproven in bull data)", "amb"
    else:
        state, signal, col = "EXTREME GREED", "reduce risk / hedge (greed signal weak, treat as risk context)", "amb"
    return {"value": round(cur, 0), "state": state, "signal": signal, "color": col,
            "vix_pct": round(float(vix_pct.iloc[-1]) * 100, 0) if vix is not None else None,
            "breadth_below_50ma": round(float(below50.iloc[-1]) * 100, 0) if isinstance(close, pd.DataFrame) else None,
            "confidence": "fear side validated (p<0.001); greed side weak/unproven"}


def panic_signal(close, vix):
    """Boolean: is a PANIC BOTTOM setup active now? VIX spike (>80pct) + oversold (z<-1).
    Validated: forward 63d +6.2% vs +3.3% baseline, p<0.001."""
    spx = close.mean(axis=1) if isinstance(close, pd.DataFrame) else close
    vix = vix.reindex(spx.index).ffill()
    vix_pct = vix.rank(pct=True)
    z20 = (spx - spx.rolling(20).mean()) / spx.rolling(20).std()
    active = bool((vix_pct.iloc[-1] > 0.80) and (z20.iloc[-1] < -1.0))
    breadth = None
    if isinstance(close, pd.DataFrame):
        breadth = float((close < close.rolling(50).mean()).mean(axis=1).iloc[-1])
    return {"active": active, "vix_pct": round(float(vix_pct.iloc[-1]) * 100, 0),
            "oversold_z": round(float(z20.iloc[-1]), 2), "breadth_below_50ma": round(breadth * 100, 0) if breadth else None,
            "expected_fwd63": "+6% (vs +3% base, p<0.001)" if active else None,
            "message": "PANIC BOTTOM setup — capitulation historically precedes bounce" if active else "no panic setup"}


def build(close, vix=None):
    """Dashboard-ready early-warning package."""
    fg = fear_greed(close, vix)
    out = {"fear_greed": fg}
    if vix is not None and isinstance(close, pd.DataFrame):
        out["panic"] = panic_signal(close, vix)
    return out
