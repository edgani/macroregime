"""engines/market_health_engine.py
Merged: VIX Bucket + Crash Meter + USD Mythic Variable + Breadth/Health + Checklists
+ IWM ATH-to-ATH drawdown spread
+ CNN Fear & Greed (fetched or proxied)

HEDGEYE HEALTHY MARKET CONCEPT (McCullough):
"Multiple sectors must participate simultaneously — not just NVDA/AAPL/MSFT pulling everything."

4 signals that must ALL confirm:
1. sector_support_ratio >= 0.55  → 6+ of 11 sectors positive 1M
2. eqw_health > 0.50             → RSP (equal-weight) outperforming cap-weight SPY
3. smallcap_health > 0.50        → IWM leading or matching SPY
4. narrow_leadership LOW         → MAG7 concentration NOT dominating

IWM ATH-to-ATH spread: IWM drawdown from ATH MINUS SPY drawdown from ATH.
  - If IWM drawdown >> SPY drawdown → small caps left behind → Narrow/Fragile
  - If IWM near ATH alongside SPY → Healthy participation

CNN Fear & Greed (7 components): momentum, price strength, breadth,
put/call ratio, VIX, junk bond demand, safe-haven demand. 
0=max fear, 100=max greed. Extreme fear (<20) → contrarian buy; extreme greed (>80) → caution.
"""
from __future__ import annotations
import math, json, urllib.request
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

def _drawdown_from_ath(s) -> Optional[float]:
    """Return drawdown from all-time high (negative number)."""
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 5: return None
    try:
        ath = float(s.max())
        last = float(s.iloc[-1])
        dd = (last / ath - 1)
        return dd if math.isfinite(dd) else None
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

def _fetch_fear_greed() -> Optional[Dict]:
    """Fetch CNN Fear & Greed score. Returns dict with score(0-100) and label."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        req = urllib.request.Request(url, headers={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer":"https://www.cnn.com/markets/fear-and-greed"
        })
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read())
        fg = d.get("fear_and_greed", {})
        score = float(fg.get("score", 50))
        rating = str(fg.get("rating", "Neutral"))
        return {"score": score, "label": rating, "source": "cnn_live"}
    except:
        pass
    return None


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
        vix_note = {
            "Investable":"VIX tenang (<19) — pullback lebih layak dibeli bila signal searah.",
            "Chop":"VIX sedang (19-29) — buy low/sell high; kurangi kejar breakout lemah.",
            "Defensive":"VIX tinggi (>29) — capital preservation. Sizing jauh lebih kecil."
        }[bucket]

        def r(t,n): return _ret(prices.get(t),n) or 0.0

        # ── Breadth + Sector Health (CORE HEDGEYE CONCEPT) ─────────────
        sector_scores = {}
        positive_1m = 0; positive_3m = 0
        for bucket_name, syms in US_BUCKETS.items():
            rv_1m = [_ret(prices.get(t), 21) for t in syms if prices.get(t) is not None]
            rv_3m = [_ret(prices.get(t), 63) for t in syms if prices.get(t) is not None]
            v1 = [x for x in rv_1m if x is not None]
            v3 = [x for x in rv_3m if x is not None]
            avg_1m = float(np.mean(v1)) if v1 else 0.0
            avg_3m = float(np.mean(v3)) if v3 else 0.0
            sector_scores[bucket_name] = {"1m": avg_1m, "3m": avg_3m}
            if avg_1m > 0.001: positive_1m += 1
            if avg_3m > 0.01:  positive_3m += 1

        total_buckets = max(len(US_BUCKETS), 1)
        sector_support_ratio_1m = positive_1m / total_buckets
        sector_support_ratio_3m = positive_3m / total_buckets

        spy_1m = r("SPY",21); rsp_1m = r("RSP",21)
        spy_3m = r("SPY",63); rsp_3m = r("RSP",63)
        eqw_rel_1m = rsp_1m - spy_1m
        eqw_health = clamp01(0.5 + eqw_rel_1m/0.04)

        iwm_1m = r("IWM",21); iwm_rel_1m = iwm_1m - spy_1m
        smallcap_health = clamp01(0.5 + iwm_rel_1m/0.05)

        # ── IWM ATH-to-ATH drawdown spread (Ricky2212 ATH-10/20/30 concept) ──
        iwm_ath_dd  = _drawdown_from_ath(prices.get("IWM"))
        spy_ath_dd  = _drawdown_from_ath(prices.get("SPY"))
        iwm_ath_spread = None  # IWM drawdown minus SPY drawdown
        iwm_ath_health = 0.5   # neutral default
        if iwm_ath_dd is not None and spy_ath_dd is not None:
            iwm_ath_spread = iwm_ath_dd - spy_ath_dd  # negative = IWM weaker
            # -10% spread = very unhealthy, 0% = healthy parity, +5% = IWM leading
            iwm_ath_health = clamp01(0.5 + iwm_ath_spread / 0.15)

        ath_label = "—"
        if iwm_ath_dd is not None:
            ath_label = f"IWM {iwm_ath_dd:.1%} from ATH | SPY {spy_ath_dd:.1%} from ATH"
            if iwm_ath_spread is not None:
                ath_label += f" | Spread: {iwm_ath_spread:.1%}"

        # Ricky2212 correction zones: ATH-10% = healthy correction, ATH-20% = bear market, ATH-30% = big crisis
        market_correction_level = "normal"
        if spy_ath_dd is not None:
            if spy_ath_dd <= -0.30:   market_correction_level = "big_crisis"
            elif spy_ath_dd <= -0.20: market_correction_level = "bear_market"
            elif spy_ath_dd <= -0.10: market_correction_level = "healthy_correction"

        # ── MAG7 Concentration ──
        mag7_returns = [_ret(prices.get(t),21) for t in MAG7 if prices.get(t) is not None]
        mag7_avg = float(np.mean([x for x in mag7_returns if x is not None])) if mag7_returns else 0.0
        mag7_concentration = clamp01(0.5 + (mag7_avg - spy_1m)/0.06)
        narrow_leadership = mag7_concentration

        breadth_health = clamp01(
            0.30 * sector_support_ratio_1m + 0.20 * eqw_health +
            0.20 * smallcap_health + 0.15 * iwm_ath_health +
            0.15 * (1.0 - narrow_leadership)
        )

        raw = (
            0.35 * sector_support_ratio_1m + 0.25 * eqw_health +
            0.20 * smallcap_health + 0.10 * iwm_ath_health -
            0.20 * narrow_leadership + 0.10
        )
        score = clamp01(raw)
        verdict = "Healthy" if score>=0.68 else "Improving" if score>=0.52 else "Narrow" if score>=0.42 else "Fragile"

        notes = []
        if sector_support_ratio_1m < 0.45: notes.append(f"Hanya {positive_1m}/{total_buckets} sektor positif — leadership sempit")
        if eqw_health < 0.45: notes.append("Equal-weight (RSP) belum konfirmasi — mega cap yang naik, bukan pasar luas")
        if smallcap_health < 0.45: notes.append("Small caps (IWM) belum ikut — breadth masih lemah")
        if iwm_ath_health < 0.40 and iwm_ath_spread is not None: notes.append(f"IWM jauh di bawah ATH-nya vs SPY ({iwm_ath_spread:.1%} spread)")
        if narrow_leadership > 0.65: notes.append("MAG7 concentration tinggi — naik tapi ditopang sedikit nama")
        if market_correction_level != "normal": notes.append(f"Market dalam {market_correction_level.replace('_',' ')} territory (Ricky2212 ATH rule)")
        if not notes: notes.append("Breadth sehat: banyak sektor, equal-weight, dan small cap ikut konfirmasi")

        # ── Crash Meter ─────────────────────────────────────────────────
        tlt_1m=r("TLT",21); hyg_1m=r("HYG",21); dxy_1m=r("DX-Y.NYB",21)
        credit_stress = clamp01(0.5 + 5.0*(spy_1m - hyg_1m))
        breadth_stress= clamp01(0.5 + 5.0*(spy_1m - iwm_1m))
        dollar_press  = clamp01(0.5 + dxy_1m/0.04)
        vol_stress    = clamp01((vix_last-15)/25)
        quality_bid   = clamp01(0.5 + tlt_1m/0.04)
        ath_stress    = clamp01(max(0, -iwm_ath_spread/0.15)) if iwm_ath_spread is not None else 0.5

        crash_score = clamp01(
            0.25*vol_stress + 0.20*credit_stress + 0.15*breadth_stress +
            0.15*dollar_press + 0.10*quality_bid + 0.15*ath_stress
        )
        risk_off_score = clamp01(0.30*credit_stress + 0.25*breadth_stress + 0.20*dollar_press + 0.15*vol_stress + 0.10*ath_stress)
        crash_state = "elevated" if crash_score>=0.65 else "watch" if crash_score>=0.45 else "calm"
        risk_off_state = "risk_off" if risk_off_score>=0.60 else "caution" if risk_off_score>=0.40 else "risk_on"
        crash_reasons = []
        if vol_stress>=0.55: crash_reasons.append(f"VIX elevated ({vix_last:.0f})")
        if credit_stress>=0.60: crash_reasons.append("HYG << SPY (credit stress)")
        if breadth_stress>=0.60: crash_reasons.append("IWM << SPY (breadth stress)")
        if dollar_press>=0.65: crash_reasons.append("USD strengthening")
        if quality_bid>=0.60: crash_reasons.append("TLT bid = flight to quality")
        if ath_stress>=0.60 and iwm_ath_spread: crash_reasons.append(f"IWM ATH spread: {iwm_ath_spread:.1%}")
        if market_correction_level == "big_crisis": crash_reasons.append("⚠️ SPY ≥30% below ATH = BIG CRISIS zone")
        elif market_correction_level == "bear_market": crash_reasons.append("SPY ≥20% below ATH = Bear market territory")

        # ── CNN Fear & Greed (live fetch with proxy fallback) ───────────
        fg_data = _fetch_fear_greed()
        # Proxy from market signals if live fetch fails
        if fg_data is None:
            # Construct proxy: combine VIX, credit, breadth, momentum
            proxy_score = clamp01(
                0.25*(1-vol_stress) + 0.20*(1-credit_stress) + 0.20*(1-breadth_stress) +
                0.20*clamp01(0.5+spy_1m/0.04) + 0.15*(1-dollar_press)
            ) * 100
            labels = {(0,25):"Extreme Fear",(25,45):"Fear",(45,55):"Neutral",(55,75):"Greed",(75,100):"Extreme Greed"}
            l = next((v for (lo,hi),v in labels.items() if lo<=proxy_score<hi), "Neutral")
            fg_data = {"score": round(proxy_score,1), "label": l, "source": "proxy"}
        fg_score  = fg_data.get("score", 50)
        fg_label  = fg_data.get("label", "Neutral")
        fg_source = fg_data.get("source", "proxy")
        # Crash meter boost from extreme fear
        if fg_score < 20:
            crash_reasons.append(f"CNN F&G Extreme Fear ({fg_score:.0f}) — contrarian potential")
        elif fg_score > 80:
            crash_reasons.append(f"CNN F&G Extreme Greed ({fg_score:.0f}) — caution warranted")

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
        mythic_note = f"⚡ USD MYTHIC VARIABLE ACTIVE ({', '.join(mythic_assets)}). USD bearish TREND → add SPX, BTC, Gold, EM." if mythic_active else ""

        # ── Per-Market Entry Checklists ────────────────────────────────
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
            ("Growth momentum",        0.5+0.5*g),
            ("Inflation controlled",   0.5-0.35*max(0,i)),
            ("USD direction ok",       0.5-0.5*max(0,dxy_1m)),
            ("Bonds/TLT signal",       0.5+0.5*tlt_1m),
            ("Credit healthy (HYG)",   0.5-0.5*max(0,credit_stress-0.5)),
            ("VIX regime",             0.6 if bucket=="Investable" else 0.35 if bucket=="Defensive" else 0.50),
            ("Breadth (sectors)",      breadth_health),
            ("Policy supportive",      0.5+0.4*p),
            ("Small cap leading",      smallcap_health),
            ("Equal-weight confirm",   eqw_health),
            ("CNN F&G ok (not extreme greed)", clamp01(1 - max(0, fg_score-75)/25)),
        ])
        checklist_us = _score([
            (f"Sector breadth ({positive_1m}/{total_buckets}+)", sector_support_ratio_1m),
            ("Equal-weight (RSP) confirm",  eqw_health),
            ("Small caps (IWM) leading",    smallcap_health),
            ("IWM near ATH vs SPY",         iwm_ath_health),
            ("MAG7 not too dominant",        1.0-narrow_leadership),
            ("Credit aman (HYG)",           0.5-0.5*max(0,credit_stress-0.5)),
            ("Vol mendukung (VIX)",         0.6 if bucket!="Defensive" else 0.30),
            ("F&G not extreme",             clamp01(1 - max(0, fg_score-75)/25)),
        ])
        usdidr=r("USDIDR=X",21) or 0.0
        eido_3m=r("EIDO",63) or 0.0
        bbca_3m=r("BBCA.JK",63) or 0.0
        checklist_ihsg = _score([
            ("USD/IDR aman",         0.5-max(0,usdidr)*3),
            ("Foreign flow confirm", 0.5+eido_3m*3),
            ("Heavyweights sehat",   0.5+bbca_3m*3),
            ("BI rate support",      0.5+0.5*p),
            ("Commodity floor",      0.5+(r("GC=F",63) or 0)*1.5),
            ("Breadth IHSG",         0.5-max(0,q3m)*2),
        ])
        checklist_fx = _score([
            ("Rate diff bersih",   0.5+0.3*p),
            ("Macro surprise",     0.5+0.3*g),
            ("Positioning cool",   0.5-vol_stress*0.5),
            ("Liquidity ok",       0.6 if bucket!="Defensive" else 0.30),
            ("Intervention risk",  0.5-dollar_press*0.4),
            ("Options ok",         0.5-vol_stress*0.4),
        ])
        oil_3m=r("CL=F",63) or 0.0; gld_3m=r("GLD",63) or r("GC=F",63) or 0.0
        checklist_commodities = _score([
            ("Physical balance",   0.5+oil_3m*1.5),
            ("Curve confirm",      0.5+oil_3m*1.0),
            ("USD/rates support",  0.5-dollar_press*0.5),
            ("Gold bid",           0.5+gld_3m*2.0),
            ("Positioning ok",     0.5-vol_stress*0.3),
            ("Supply shock proxy", 0.5+max(0,i)*0.6),
        ])
        btc_3m=r("BTC-USD",63) or 0.0
        checklist_crypto = _score([
            ("Flow masuk",        0.5+btc_3m*1.5),
            ("Funding/OI sehat",  0.5-vol_stress*0.5),
            ("Unlock risk ok",    0.5-max(0,vol_stress-0.3)),
            ("Liquidity cukup",   0.5-credit_stress*0.3),
            ("Narrative hidup",   0.5+btc_3m*1.0),
            ("USD bearish",       0.5-dollar_press*0.6),
            ("F&G not extreme",   clamp01(1 - max(0, fg_score-75)/25)),
        ])

        return dict(
            market_health=dict(
                score=round(score,3), verdict=verdict,
                sector_support_ratio=round(sector_support_ratio_1m,2),
                sector_support_ratio_3m=round(sector_support_ratio_3m,2),
                positive_sectors_1m=positive_1m, total_buckets=total_buckets,
                eqw_health=round(eqw_health,2), eqw_rel_1m=round(eqw_rel_1m,4),
                smallcap_health=round(smallcap_health,2), iwm_rel_1m=round(iwm_rel_1m,4),
                narrow_leadership=round(narrow_leadership,2), breadth_health=round(breadth_health,2),
                mag7_concentration=round(mag7_concentration,2),
                iwm_ath_dd=iwm_ath_dd, spy_ath_dd=spy_ath_dd,
                iwm_ath_spread=iwm_ath_spread, iwm_ath_health=round(iwm_ath_health,2),
                ath_label=ath_label, market_correction_level=market_correction_level,
                sector_scores=sector_scores, notes=notes,
                what_confirms="RSP, IWM, dan 6+ sektor ikut positif bersama. IWM dekat ATH-nya.",
                what_invalidates="Index naik tapi RSP flat, IWM tertinggal, atau hanya 3-4 sektor.",
            ),
            vix_bucket=dict(bucket=bucket, risk_mode=risk_mode, vix_last=vix_last, note=vix_note),
            fear_greed=dict(score=fg_score, label=fg_label, source=fg_source),
            crash=dict(score=round(crash_score,3), state=crash_state, reasons=crash_reasons),
            risk_off=dict(score=round(risk_off_score,3), state=risk_off_state),
            usd_corr=dict(correlations=usd_corrs, mythic_active=mythic_active, mythic_assets=mythic_assets, note=mythic_note),
            checklists=dict(global_=checklist_global, us=checklist_us, ihsg=checklist_ihsg,
                            fx=checklist_fx, commodities=checklist_commodities, crypto=checklist_crypto),
            signals=dict(credit_stress=round(credit_stress,3), breadth_stress=round(breadth_stress,3),
                         dollar_press=round(dollar_press,3), vol_stress=round(vol_stress,3),
                         quality_bid=round(quality_bid,3), eqw_rel=round(eqw_rel_1m,4),
                         iwm_rel=round(iwm_rel_1m,4), fg_score=fg_score, ath_stress=round(ath_stress,3)),
        )
