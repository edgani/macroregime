"""engines/market_health_engine.py
Merged: VIX Bucket + Crash Meter + USD Mythic Variable + Breadth/Health + Checklists

HEDGEYE HEALTHY MARKET CONCEPT (from McCullough):
"A healthy market is when MULTIPLE SECTORS are participating simultaneously."
NOT: Index up because NVDA/AAPL/MSFT pulling everything.
YES: Equal-weight (RSP) confirming SPY, small caps (IWM) leading, 7+ of 11 sectors positive.

Four signals that confirm Healthy market (Hedgeye definition):
1. sector_support_ratio >= 0.55 → 6+ of 11 sectors positive on 1M basis
2. eqw_health > 0.50          → RSP (equal-weight SPY) outperforming cap-weight SPY
3. smallcap_health > 0.50     → IWM outperforming or close to SPY
4. narrow_leadership LOW       → MAG7 concentration NOT dominating = broad participation

Verdicts: Healthy → Improving → Narrow → Fragile
- Healthy: 3+ of 4 signals green. Full conviction to deploy.
- Improving: 2 of 4. Selective adds.
- Narrow: 1-2 of 4. Index up but dangerous — leadership shrinking.
- Fragile: 0-1. Capital preservation mode.
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

def _corr_15d(s1, s2):
    try:
        s1 = pd.to_numeric(s1, errors="coerce").dropna()
        s2 = pd.to_numeric(s2, errors="coerce").dropna()
        n = min(len(s1),len(s2),20)
        if n < 8: return None
        r1 = s1.pct_change().dropna().tail(n)
        r2 = s2.pct_change().dropna().tail(n)
        mn = min(len(r1),len(r2))
        if mn < 6: return None
        c = float(np.corrcoef(r1.values[-mn:], r2.values[-mn:])[0,1])
        return c if math.isfinite(c) else None
    except: return None


class MarketHealthEngine:
    def run(self, prices: Dict[str, pd.Series], gip_features: Dict[str,float], quad: str) -> Dict[str,object]:
        from config.settings import US_BUCKETS, MAG7

        # ── VIX Bucket ──────────────────────────────────────────────────
        vix_s = prices.get("^VIX")
        vix_last = 18.0
        if vix_s is not None:
            s = pd.to_numeric(vix_s, errors="coerce").dropna()
            if not s.empty: vix_last = float(s.iloc[-1])
        bucket   = "Investable" if vix_last<19 else "Chop" if vix_last<29 else "Defensive"
        risk_mode= "Normal"     if vix_last<19 else "Reduced" if vix_last<29 else "Defensive"
        vix_note = {"Investable":"VIX tenang (<19) — pullback lebih layak dibeli bila signal searah.",
                    "Chop":"VIX sedang (19-29) — buy low/sell high; kurangi kejar breakout lemah.",
                    "Defensive":"VIX tinggi (>29) — capital preservation. Sizing jauh lebih kecil."}[bucket]

        def r(t,n): return _ret(prices.get(t),n) or 0.0

        # ── Breadth / Sector Health (CORE HEDGEYE CONCEPT) ─────────────
        # Sector support ratio: how many sectors are positive on 1M?
        sector_scores = {}
        positive_1m = 0
        positive_3m = 0
        for bucket_name, syms in US_BUCKETS.items():
            returns_1m = [_ret(prices.get(t), 21) for t in syms if prices.get(t) is not None]
            returns_3m = [_ret(prices.get(t), 63) for t in syms if prices.get(t) is not None]
            valid_1m = [rv for rv in returns_1m if rv is not None]
            valid_3m = [rv for rv in returns_3m if rv is not None]
            avg_1m = float(np.mean(valid_1m)) if valid_1m else 0.0
            avg_3m = float(np.mean(valid_3m)) if valid_3m else 0.0
            sector_scores[bucket_name] = {"1m": avg_1m, "3m": avg_3m}
            if avg_1m > 0.001: positive_1m += 1  # 0.1% threshold to count as "participating"
            if avg_3m > 0.01:  positive_3m += 1

        total_buckets = max(len(US_BUCKETS), 1)
        sector_support_ratio_1m = positive_1m / total_buckets
        sector_support_ratio_3m = positive_3m / total_buckets

        # Equal-weight vs cap-weight
        spy_1m = r("SPY",21); rsp_1m = r("RSP",21)
        spy_3m = r("SPY",63); rsp_3m = r("RSP",63)
        eqw_rel_1m = rsp_1m - spy_1m   # positive = broad market, not just mega cap
        eqw_rel_3m = rsp_3m - spy_3m
        eqw_health = clamp01(0.5 + eqw_rel_1m/0.04)

        # Small cap health
        iwm_1m = r("IWM",21); iwm_rel_1m = iwm_1m - spy_1m
        iwm_3m = r("IWM",63); iwm_rel_3m = iwm_3m - spy_3m
        smallcap_health = clamp01(0.5 + iwm_rel_1m/0.05)

        # MAG7 concentration (narrow leadership risk)
        mag7_returns = [_ret(prices.get(t),21) for t in MAG7 if prices.get(t) is not None]
        mag7_avg = float(np.mean([x for x in mag7_returns if x is not None])) if mag7_returns else 0.0
        broad_avg = spy_1m
        mag7_concentration = clamp01(0.5 + (mag7_avg - broad_avg)/0.06)  # high = narrow, bad
        narrow_leadership = mag7_concentration  # high = narrow = bad

        # Breadth composite (primary health signal)
        breadth_health = clamp01(
            0.35 * sector_support_ratio_1m +
            0.25 * eqw_health +
            0.25 * smallcap_health +
            0.15 * (1.0 - narrow_leadership)  # less concentration = more breadth
        )

        # Market health score
        raw = (
            0.40 * sector_support_ratio_1m +
            0.25 * eqw_health +
            0.20 * smallcap_health +
            0.05 * breadth_health -
            0.25 * narrow_leadership +
            0.10
        )
        score = clamp01(raw)

        if score >= 0.68:   verdict = "Healthy"
        elif score >= 0.52: verdict = "Improving"
        elif score >= 0.42: verdict = "Narrow"
        else:               verdict = "Fragile"

        notes = []
        if sector_support_ratio_1m < 0.45: notes.append(f"Hanya {positive_1m}/{total_buckets} sektor positif — leadership sempit")
        if eqw_health < 0.45: notes.append("Equal-weight (RSP) belum konfirmasi — mega cap yang naik, bukan pasar luas")
        if smallcap_health < 0.45: notes.append("Small caps (IWM) belum ikut — breadth masih lemah")
        if narrow_leadership > 0.65: notes.append(f"MAG7 concentration tinggi — naik tapi ditopang sedikit nama")
        if not notes: notes.append("Breadth sehat: banyak sektor, equal-weight, dan small cap ikut konfirmasi")

        # ── Crash Meter ─────────────────────────────────────────────────
        tlt_1m=r("TLT",21); hyg_1m=r("HYG",21); dxy_1m=r("DX-Y.NYB",21)
        credit_stress = clamp01(0.5 + 5.0*(spy_1m - hyg_1m))
        breadth_stress= clamp01(0.5 + 5.0*(spy_1m - iwm_1m))
        dollar_press  = clamp01(0.5 + dxy_1m/0.04)
        vol_stress    = clamp01((vix_last-15)/25)
        quality_bid   = clamp01(0.5 + tlt_1m/0.04)

        crash_score = clamp01(0.30*vol_stress + 0.25*credit_stress + 0.20*breadth_stress + 0.15*dollar_press + 0.10*quality_bid)
        risk_off_score = clamp01(0.35*credit_stress + 0.30*breadth_stress + 0.20*dollar_press + 0.15*vol_stress)
        crash_state = "elevated" if crash_score>=0.65 else "watch" if crash_score>=0.45 else "calm"
        risk_off_state = "risk_off" if risk_off_score>=0.60 else "caution" if risk_off_score>=0.40 else "risk_on"
        crash_reasons = []
        if vol_stress>=0.55: crash_reasons.append(f"VIX elevated ({vix_last:.0f})")
        if credit_stress>=0.60: crash_reasons.append("Credit stress: HYG << SPY")
        if breadth_stress>=0.60: crash_reasons.append("Breadth stress: IWM << SPY")
        if dollar_press>=0.65: crash_reasons.append("USD strengthening = EM/risk pressure")
        if quality_bid>=0.60: crash_reasons.append("TLT bid = flight to quality")

        # ── USD Mythic Variable ─────────────────────────────────────────
        uup_s = prices.get("UUP")
        if uup_s is None or (isinstance(uup_s, pd.Series) and uup_s.empty):
            uup_s = prices.get("DX-Y.NYB")
        uup = uup_s if (uup_s is not None and isinstance(uup_s, pd.Series) and not uup_s.empty) else None

        corr_pairs = [("SPX","SPY"),("NASDAQ","QQQ"),("BTC","BTC-USD"),("GOLD","GC=F"),
                      ("OIL","CL=F"),("SILVER","SLV"),("EEM","EEM"),("BRENT","BZ=F"),
                      ("TLT","TLT"),("COPPER","HG=F")]
        usd_corrs: Dict[str,float] = {}
        mythic_assets: List[str] = []
        if uup is not None:
            for name, ticker in corr_pairs:
                s = prices.get(ticker)
                if s is None: continue
                c = _corr_15d(uup, s)
                if c is not None:
                    usd_corrs[name] = round(c, 3)
                    if name in ("SPX","BTC","GOLD") and c < -0.85:
                        mythic_assets.append(name)
        mythic_active = len(mythic_assets) >= 2
        mythic_note = f"⚡ USD MYTHIC VARIABLE ACTIVE ({', '.join(mythic_assets)}). USD direction = portfolio direction. USD bearish TREND → add SPX, BTC, Gold, EM." if mythic_active else ""

        # ── Per-Market Entry Checklists ────────────────────────────────────
        g=gip_features.get("growth_momentum",0); i=gip_features.get("inflation_momentum",0)
        p=gip_features.get("policy_score",0); q3m=gip_features.get("q3_modifier",0)

        def _score(items):
            out=[]
            for label,sc in items:
                sc=clamp01(float(sc))
                state="Improving" if sc>=0.67 else "Mixed" if sc>=0.45 else "Fragile"
                tone="good" if sc>=0.67 else "warn" if sc>=0.45 else "bad"
                out.append({"label":label,"score":round(sc,2),"state":state,"tone":tone})
            return out

        checklist_global = _score([
            ("Growth momentum",       0.5+0.5*g),
            ("Inflation controlled",  0.5-0.35*max(0,i)),
            ("USD direction ok",      0.5-0.5*max(0,dxy_1m)),
            ("Bonds/TLT signal",      0.5+0.5*tlt_1m),
            ("Credit healthy",        0.5-0.5*max(0,credit_stress-0.5)),
            ("VIX regime",            0.6 if bucket=="Investable" else 0.35 if bucket=="Defensive" else 0.50),
            ("Breadth (sectors)",     breadth_health),
            ("Policy supportive",     0.5+0.4*p),
            ("Small cap leading",     smallcap_health),
            ("Equal-weight confirm",  eqw_health),
        ])
        checklist_us = _score([
            (f"Sector breadth ({positive_1m}/{total_buckets}+)", sector_support_ratio_1m),
            ("Equal-weight confirm",  eqw_health),
            ("Small caps leading",    smallcap_health),
            ("MAG7 not too dominant", 1.0-narrow_leadership),
            ("Credit aman",           0.5-0.5*max(0,credit_stress-0.5)),
            ("Vol mendukung",         0.6 if bucket!="Defensive" else 0.30),
        ])
        usdidr=r("USDIDR=X",21) or 0.0
        eido_3m=r("EIDO",63) or 0.0
        bbca_3m=r("BBCA.JK",63) or 0.0
        checklist_ihsg = _score([
            ("USD/IDR aman",      0.5-max(0,usdidr)*3),
            ("Foreign flow",      0.5+eido_3m*3),
            ("Heavyweights",      0.5+bbca_3m*3),
            ("BI rate support",   0.5+0.5*p),
            ("Commodity floor",   0.5+(r("GC=F",63) or 0)*1.5),
            ("Breadth IHSG",      0.5-max(0,q3m)*2),
        ])
        checklist_fx = _score([
            ("Rate diff bersih",  0.5+0.3*p),
            ("Macro surprise",    0.5+0.3*g),
            ("Positioning cool",  0.5-vol_stress*0.5),
            ("Liquidity ok",      0.6 if bucket!="Defensive" else 0.30),
            ("Intervention risk", 0.5-dollar_press*0.4),
            ("Options ok",        0.5-vol_stress*0.4),
        ])
        oil_3m=r("CL=F",63) or 0.0; gld_3m=r("GLD",63) or r("GC=F",63) or 0.0
        checklist_commodities = _score([
            ("Physical balance",  0.5+oil_3m*1.5),
            ("Curve confirm",     0.5+oil_3m*1.0),
            ("USD/rates support", 0.5-dollar_press*0.5),
            ("Gold bid",          0.5+gld_3m*2.0),
            ("Positioning ok",    0.5-vol_stress*0.3),
            ("Supply shock",      0.5+max(0,i)*0.6),
        ])
        btc_3m=r("BTC-USD",63) or 0.0
        checklist_crypto = _score([
            ("Flow masuk",       0.5+btc_3m*1.5),
            ("Funding/OI sehat", 0.5-vol_stress*0.5),
            ("Unlock risk ok",   0.5-max(0,vol_stress-0.3)),
            ("Liquidity cukup",  0.5-credit_stress*0.3),
            ("Narrative hidup",  0.5+btc_3m*1.0),
            ("USD bearish",      0.5-dollar_press*0.6),
        ])

        return dict(
            # Breadth / Market Health (CORE HEDGEYE)
            market_health=dict(
                score=round(score,3), verdict=verdict,
                sector_support_ratio=round(sector_support_ratio_1m,2),
                sector_support_ratio_3m=round(sector_support_ratio_3m,2),
                positive_sectors_1m=positive_1m,
                total_buckets=total_buckets,
                eqw_health=round(eqw_health,2),
                eqw_rel_1m=round(eqw_rel_1m,4),
                smallcap_health=round(smallcap_health,2),
                iwm_rel_1m=round(iwm_rel_1m,4),
                narrow_leadership=round(narrow_leadership,2),
                breadth_health=round(breadth_health,2),
                mag7_concentration=round(mag7_concentration,2),
                sector_scores=sector_scores,
                notes=notes,
                what_confirms="Equal-weight (RSP), small caps (IWM), dan 6+ sektor ikut positif bersama.",
                what_invalidates="Index naik tapi RSP flat, IWM tertinggal, dan hanya 3-4 sektor yang menopang.",
            ),
            vix_bucket=dict(bucket=bucket, risk_mode=risk_mode, vix_last=vix_last, note=vix_note),
            crash=dict(score=round(crash_score,3), state=crash_state, reasons=crash_reasons),
            risk_off=dict(score=round(risk_off_score,3), state=risk_off_state),
            usd_corr=dict(correlations=usd_corrs, mythic_active=mythic_active, mythic_assets=mythic_assets, note=mythic_note),
            checklists=dict(global_=checklist_global, us=checklist_us, ihsg=checklist_ihsg,
                            fx=checklist_fx, commodities=checklist_commodities, crypto=checklist_crypto),
            signals=dict(credit_stress=round(credit_stress,3), breadth_stress=round(breadth_stress,3),
                         dollar_press=round(dollar_press,3), vol_stress=round(vol_stress,3),
                         quality_bid=round(quality_bid,3), eqw_rel=round(eqw_rel_1m,4),
                         iwm_rel=round(iwm_rel_1m,4)),
        )
