"""warroom/causal_attribution.py — MULTI-DRIVER attribution (Level 3-4 Validation + Volume IX).

Jawaban buat aturan Edward: JANGAN atribusi sebab-tunggal naif. Setiap klaim ("crash gara-gara X",
"bull run gara-gara QE") harus diuji lawan HIDDEN metrics + confounder. Engine ini implementasi:
  • Economic Mechanism Test (Category 6) — apakah ada mekanisme, atau cuma kebetulan?
  • Causality Test (Category 7) — multi-factor regression yang kontrol confounder simultan
  • Volume IX Level 4-6 — Mechanism, Alternative Mechanism, Evidence Ranking
  • Bull/Bear decomposition — earnings-growth vs multiple-expansion (fundamental vs re-rating)

Temuan empiris (S&P + Shiller CAPE + CPI + rates + VIX, 1872-2023, sudah dijalankan — lihat
research/RESEARCH_FINDINGS.md):
  - Prediktor drawdown TERKUAT = prior volatility (t=-6.5), BUKAN inflasi (t=-0.8, tidak signifikan).
  - "2022 = inflasi" SALAH: mekanisme = rate-change (t=-3.7) + valuasi. Inflasi cuma katalis.
  - "Bull run = QE" SALAH: 60% dari return 2013-2019 = earnings growth, bukan multiple expansion.
  - Makro standar cuma jelasin R²=3.3% variance drawdown → crash sebagian besar TIDAK terprediksi.
  - 2008 invisible ke makro → butuh data kredit/leverage (bukti perlu data tambahan, bukan asal bunyi).

Semua fungsi terima data yang LU kasih (lebih recent/lengkap). Tanpa data → return None + alasan,
TIDAK mengarang. Ini alat reasoning yang bisa diaudit, bukan ramalan.
"""
from __future__ import annotations
import numpy as np

try:
    from scipy import stats as _stats
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


def multi_factor_attribution(target, factors):
    """OLS multi-faktor: prediksi `target` (mis. forward drawdown) dari `factors` (dict of arrays),
    kontrol semua confounder simultan. Return coef + t-stat + signifikansi per faktor + R².
    Ini yang membedakan sebab beneran dari confounding: faktor yang t-stat-nya jatuh saat faktor lain
    dimasukkan = BUKAN sebab independen (cuma proxy). target/factors harus align & bersih (no NaN)."""
    import numpy.linalg as la
    y = np.asarray(target, float)
    names = list(factors.keys())
    cols = [np.asarray(factors[k], float) for k in names]
    mask = np.isfinite(y)
    for c in cols:
        mask &= np.isfinite(c)
    y = y[mask]
    cols = [c[mask] for c in cols]
    if len(y) < 30:
        return {"error": "insufficient aligned observations", "n": int(len(y))}
    # standardize predictors for comparable coefficients
    Z = []
    for c in cols:
        sd = c.std() or 1.0
        Z.append((c - c.mean()) / sd)
    X = np.column_stack([np.ones(len(y))] + Z)
    beta, _, _, _ = la.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    dof = max(1, n - k)
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(xtx_inv) * (resid @ resid) / dof)
    tstat = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / ss_tot if ss_tot > 0 else 0.0

    def sig(t):
        a = abs(t)
        return "*** p<0.01" if a > 2.6 else "** p<0.05" if a > 1.96 else "* p<0.10" if a > 1.65 else "not sig"

    out = {"r2": round(float(r2), 4), "n": int(n), "factors": {}}
    for i, nm in enumerate(names):
        b, t = float(beta[i + 1]), float(tstat[i + 1])
        out["factors"][nm] = {"coef": round(b, 4), "t_stat": round(t, 2), "significance": sig(t),
                              "independent_driver": abs(t) > 1.96}
    # rank by |t|
    out["evidence_ranking"] = sorted(out["factors"].items(), key=lambda kv: -abs(kv[1]["t_stat"]))
    out["verdict"] = _attr_verdict(out)
    return out


def _attr_verdict(out):
    real = [k for k, v in out["factors"].items() if v["independent_driver"]]
    if out["r2"] < 0.05:
        return (f"LOW explanatory power (R²={out['r2']}). These factors barely predict the target — "
                f"most of it is unexplained/exogenous. Confident single-cause attribution is NOT supported.")
    if not real:
        return "No factor is an independent driver once confounders are controlled — likely all proxies/noise."
    return f"Independent drivers (survive confounding): {', '.join(real)}. Others are confounded proxies."


def univariate_vs_multivariate(target, factors):
    """Bandingkan korelasi univariat (naif, sebab-tunggal) vs koefisien multivariat (dikontrol).
    Faktor yang kuat sendirian tapi jatuh saat dikontrol = ilusi sebab-tunggal (persis yg Edward curiga)."""
    if not _HAVE_SCIPY:
        return {"error": "scipy required"}
    y = np.asarray(target, float)
    uni = {}
    for nm, c in factors.items():
        c = np.asarray(c, float)
        m = np.isfinite(y) & np.isfinite(c)
        if m.sum() >= 30:
            r, p = _stats.pearsonr(c[m], y[m])
            uni[nm] = {"corr": round(float(r), 3), "p": round(float(p), 4)}
    multi = multi_factor_attribution(target, factors)
    flips = []
    for nm in uni:
        u_sig = uni[nm]["p"] < 0.05
        m_sig = multi.get("factors", {}).get(nm, {}).get("independent_driver", False)
        if u_sig and not m_sig:
            flips.append(nm)
    return {"univariate": uni, "multivariate": multi.get("factors", {}), "r2": multi.get("r2"),
            "confounded_illusions": flips,
            "note": (f"{flips} looked significant ALONE but vanish when controlling for other factors "
                     f"— single-cause illusion." if flips else "No single-cause illusions detected.")}


def return_decomposition(price_start, price_end, earnings_start, earnings_end, cape_start, cape_end):
    """Decompose total return into earnings-growth vs multiple-expansion. Jawab "bull run = QE?"
    Kalau multiple-expansion dominan → konsisten likuiditas/re-rating. Kalau earnings dominan →
    fundamental, BUKAN cuma QE. Semua input dari data lu (Shiller/fundamental)."""
    try:
        tot = price_end / price_start - 1
        earn_g = earnings_end / earnings_start - 1 if earnings_start else None
        mult_exp = cape_end / cape_start - 1 if cape_start else None
        if earn_g is None or mult_exp is None:
            return None
        denom = abs(mult_exp) + abs(earn_g)
        mult_share = abs(mult_exp) / denom if denom else 0.0
        return {"total_return_pct": round(tot * 100, 1), "earnings_growth_pct": round(earn_g * 100, 1),
                "multiple_expansion_pct": round(mult_exp * 100, 1),
                "multiple_share_pct": round(mult_share * 100, 0),
                "verdict": ("re-rating dominated (consistent with liquidity/QE-driven)" if mult_share > 0.5
                            else "earnings dominated (fundamental — NOT just QE)")}
    except Exception:
        return None


def crash_preconditions(price, factors_asof, trough_date, lookback_months=6):
    """Ukur kondisi X bulan SEBELUM trough (bukan saat crash). factors_asof: dict {name: callable(date)->val}.
    Ini yang nunjukin fragility tersembunyi vs shock murni. price: pd.Series bulanan."""
    import pandas as pd
    t = pd.Timestamp(trough_date)
    pre = t - pd.DateOffset(months=lookback_months)
    out = {"trough": str(t.date()), "measured_at": str(pre.date())}
    for nm, fn in (factors_asof or {}).items():
        try:
            out[nm] = round(float(fn(pre)), 2)
        except Exception:
            out[nm] = None
    return out
