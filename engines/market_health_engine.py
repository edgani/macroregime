"""engines/market_health_engine.py
Merged: CrashMeterEngine + VIXBucketEngine + USDCorrelationEngine + ChecklistEngine
All "health/risk" signals in one place. Ported from v9_fixed.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

def clamp01(x): return float(max(0.0, min(1.0, x)))

def _ret(s, n):
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n+1: return None
    try:
        r = float(s.iloc[-1]/s.iloc[-n-1]-1)
        return r if math.isfinite(r) else None
    except: return None

def _corr_15d(s1: pd.Series, s2: pd.Series) -> Optional[float]:
    """15-day rolling correlation for USD Mythic Variable."""
    try:
        s1 = pd.to_numeric(s1, errors="coerce").dropna()
        s2 = pd.to_numeric(s2, errors="coerce").dropna()
        n = min(len(s1),len(s2),20)
        if n < 8: return None
        r1 = s1.pct_change().dropna().tail(n)
        r2 = s2.pct_change().dropna().tail(n)
        # Align
        min_n = min(len(r1),len(r2))
        if min_n < 6: return None
        c = float(np.corrcoef(r1.values[-min_n:], r2.values[-min_n:])[0,1])
        return c if math.isfinite(c) else None
    except: return None


class MarketHealthEngine:
    """
    Single engine covering:
    - VIX bucket (Investable/Chop/Defensive)
    - Crash meter score
    - USD Mythic Variable correlations
    - Per-market entry checklists
    """

    def run(self, prices: Dict[str, pd.Series], gip_features: Dict[str,float], quad: str) -> Dict[str,object]:
        # ── VIX Bucket ──────────────────────────────────────────────────
        vix_s = prices.get("^VIX")
        vix_last = 18.0
        if vix_s is not None:
            s = pd.to_numeric(vix_s, errors="coerce").dropna()
            if not s.empty: vix_last = float(s.iloc[-1])

        if vix_last < 19:   bucket = "Investable"; risk_mode = "Normal"
        elif vix_last < 29: bucket = "Chop";        risk_mode = "Reduced"
        else:               bucket = "Defensive";   risk_mode = "Defensive"

        vix_notes = {
            "Investable": "VIX tenang (<19) — pullback lebih layak dibeli bila signal searah.",
            "Chop":       "VIX sedang (19-29) — buy low/sell high; kurangi kejar breakout lemah.",
            "Defensive":  "VIX tinggi (>29) — capital preservation dulu. Sizing lebih kecil.",
        }[bucket]

        # ── Crash Meter ─────────────────────────────────────────────────
        def _r(t,n): return _ret(prices.get(t),n) or 0.0

        tlt_1m   = _r("TLT",21)
        hyg_1m   = _r("HYG",21)
        spy_1m   = _r("SPY",21)
        iwm_1m   = _r("IWM",21)
        dxy_1m   = _r("DX-Y.NYB",21) or _r("UUP",21)
        oil_1m   = _r("CL=F",21)

        # Credit stress: HYG underperforming SPY
        credit_stress = clamp01(0.5 + 5.0*(spy_1m - hyg_1m))
        # Breadth stress: IWM lagging SPY
        breadth_stress = clamp01(0.5 + 5.0*(spy_1m - iwm_1m))
        # Dollar pressure
        dollar_press = clamp01(0.5 + dxy_1m/0.04)
        # Vol stress
        vol_stress = clamp01((vix_last-15)/25)
        # Flight to quality: TLT rising
        quality_bid = clamp01(0.5 + tlt_1m/0.04)

        crash_score = clamp01(
            0.30*vol_stress + 0.25*credit_stress + 0.20*breadth_stress +
            0.15*dollar_press + 0.10*quality_bid
        )
        risk_off_score = clamp01(0.35*credit_stress + 0.30*breadth_stress + 0.20*dollar_press + 0.15*vol_stress)

        crash_state = "elevated" if crash_score>=0.65 else "watch" if crash_score>=0.45 else "calm"
        risk_off_state = "risk_off" if risk_off_score>=0.60 else "caution" if risk_off_score>=0.40 else "risk_on"

        crash_reasons = []
        if vol_stress >= 0.55: crash_reasons.append(f"VIX elevated ({vix_last:.0f})")
        if credit_stress >= 0.60: crash_reasons.append("HYG underperforming SPY — credit stress")
        if breadth_stress >= 0.60: crash_reasons.append("IWM lagging SPY — breadth narrowing")
        if dollar_press >= 0.65: crash_reasons.append("USD strengthening = EM/risk pressure")
        if quality_bid >= 0.60: crash_reasons.append("TLT bid = flight to quality")

        # ── USD Mythic Variable (McCullough April 2026) ────────────────────
        uup_raw = prices.get("UUP")
        if uup_raw is None or (isinstance(uup_raw, pd.Series) and uup_raw.empty):
            uup_raw = prices.get("DX-Y.NYB")
        uup = uup_raw if (uup_raw is not None and isinstance(uup_raw, pd.Series) and not uup_raw.empty) else None
        corr_pairs = [("SPX","SPY"),("NASDAQ","QQQ"),("BTC","BTC-USD"),("GOLD","GC=F"),
                      ("OIL","CL=F"),("SILVER","SLV"),("EEM","EEM"),("BRENT","BZ=F"),
                      ("TLT","TLT"),("COPPER","HG=F")]
        usd_corrs: Dict[str,float] = {}
        mythic_active = False
        mythic_assets: List[str] = []

        if uup is not None:
            for name, ticker in corr_pairs:
                s = prices.get(ticker)
                if s is None: continue
                c = _corr_15d(uup, s)
                if c is not None:
                    usd_corrs[name] = round(c, 3)
                    # Mythic variable: correlation below -0.85 = dollar drives everything
                    if name in ("SPX","BTC","GOLD") and c < -0.85:
                        mythic_assets.append(name)

        mythic_active = len(mythic_assets) >= 2
        mythic_note = ""
        if mythic_active:
            mythic_note = f"⚡ USD MYTHIC VARIABLE ACTIVE ({', '.join(mythic_assets)}). USD direction = portfolio direction. USD bearish TREND → add SPX, BTC, Gold, EM."

        # ── Per-Market Entry Checklists ────────────────────────────────────
        g = gip_features.get("growth_momentum",0); i = gip_features.get("inflation_momentum",0)
        p = gip_features.get("policy_score",0); cov = gip_features.get("data_coverage",0.5)
        q3_mod = gip_features.get("q3_modifier",0)
        
        def _score(items): 
            out=[]
            for label,score in items:
                sc=clamp01(float(score))
                state = "Improving" if sc>=0.67 else "Mixed" if sc>=0.45 else "Fragile"
                tone  = "good"      if sc>=0.67 else "warn"  if sc>=0.45 else "bad"
                out.append({"label":label,"score":round(sc,2),"state":state,"tone":tone})
            return out

        checklist_global = _score([
            ("Growth",      0.5 + 0.5*g),
            ("Inflation",   0.5 - 0.35*max(0,i)),
            ("DXY",         0.5 - 0.5*max(0,dxy_1m)),
            ("Bonds/TLT",   0.5 + 0.5*tlt_1m),
            ("Credit",      0.5 - 0.5*max(0,credit_stress-0.5)),
            ("Vol/VIX",     0.6 if bucket=="Investable" else 0.35 if bucket=="Defensive" else 0.50),
            ("Breadth",     0.5 - 0.4*max(0,breadth_stress-0.5)),
            ("Policy",      0.5 + 0.4*p),
            ("USD",         0.5 - 0.5*max(0,dollar_press-0.5)),
        ])

        spy_3m = _r("SPY",63); hyg_3m = _r("HYG",63); xlp_3m = _r("XLP",63)
        xly_3m = _r("XLY",63); xli_3m = _r("XLI",63)
        checklist_us = _score([
            ("Breadth melebar",   0.5 - 0.4*max(0,breadth_stress-0.5)),
            ("Equal-weight lead", 0.5 + 3.0*(_r("RSP",63) or spy_3m - 0.0)),
            ("Small caps lead",   0.5 + 3.0*((_r("IWM",63) or 0) - (spy_3m or 0))),
            ("Credit aman",       0.5 - 0.5*max(0,credit_stress-0.5)),
            ("Vol mendukung",     0.6 if bucket!="Defensive" else 0.30),
            ("Sector breadth",    0.5 + 2.0*(xli_3m or 0)),
        ])

        usdidr = _r("USDIDR=X",21) or 0.0
        eido_3m = _r("EIDO",63) or 0.0
        bbca_3m = _r("BBCA.JK",63) or 0.0
        checklist_ihsg = _score([
            ("USD/IDR aman",        0.5 - max(0,usdidr)*3),
            ("Foreign flow",        0.5 + eido_3m*3),
            ("Heavyweights sehat",  0.5 + bbca_3m*3),
            ("Breadth IHSG",        0.5 - max(0,q3_mod)*2),
            ("BI rate support",     0.5 + 0.5*p),
            ("Commodity spillover", 0.5 + (_r("GC=F",63) or 0)*1.5),
        ])

        usd_jpy = _r("USDJPY=X",21) or 0.0
        checklist_fx = _score([
            ("Rate diff bersih",     0.5 + 0.3*p),
            ("Macro surprise",       0.5 + 0.3*g),
            ("Positioning dingin",   0.5 - vol_stress*0.5),
            ("Liquidity oke",        0.6 if bucket!="Defensive" else 0.30),
            ("Intervention risk",    0.5 - dollar_press*0.4),
            ("Options nggak ekstrem",0.5 - vol_stress*0.4),
        ])

        oil_3m = _r("CL=F",63) or 0.0
        gld_3m = _r("GLD",63) or _r("GC=F",63) or 0.0
        checklist_commodities = _score([
            ("Physical balance tight",0.5 + oil_3m*1.5),
            ("Curve confirm",         0.5 + oil_3m*1.0),
            ("USD/rates support",     0.5 - dollar_press*0.5),
            ("Gold bid",              0.5 + gld_3m*2.0),
            ("Positioning ok",        0.5 - vol_stress*0.3),
            ("Supply shock",          0.5 + max(0,i)*0.6),
        ])

        btc_3m = _r("BTC-USD",63) or 0.0
        checklist_crypto = _score([
            ("Flow masuk",           0.5 + btc_3m*1.5),
            ("Funding/OI sehat",     0.5 - vol_stress*0.5),
            ("Unlock risk ok",       0.5 - max(0,vol_stress-0.3)),
            ("Liquidity cukup",      0.5 - credit_stress*0.3),
            ("Narrative hidup",      0.5 + btc_3m*1.0),
            ("USD bearish confirm",  0.5 - dollar_press*0.6),
        ])

        return dict(
            vix_bucket=dict(bucket=bucket, risk_mode=risk_mode, vix_last=vix_last, note=vix_notes),
            crash=dict(score=round(crash_score,3), state=crash_state, reasons=crash_reasons),
            risk_off=dict(score=round(risk_off_score,3), state=risk_off_state),
            usd_corr=dict(correlations=usd_corrs, mythic_active=mythic_active, mythic_assets=mythic_assets, note=mythic_note),
            checklists=dict(global_=checklist_global, us=checklist_us, ihsg=checklist_ihsg,
                            fx=checklist_fx, commodities=checklist_commodities, crypto=checklist_crypto),
            signals=dict(credit_stress=round(credit_stress,3), breadth_stress=round(breadth_stress,3),
                         dollar_press=round(dollar_press,3), vol_stress=round(vol_stress,3),
                         quality_bid=round(quality_bid,3)),
        )
