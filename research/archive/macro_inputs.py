"""macro_inputs.py — map FRED series (warroom.fred.fetch) + price series → the input dicts
run_gcfis expects, so liquidity / fragility / shock / forward_macro POPULATE instead of 'no data'.
On your machine warroom.fred.fetch() returns the real series and every field below fills in."""
import pandas as pd, numpy as np

def _s(x):
    if x is None: return None
    if isinstance(x, pd.DataFrame):
        for c in ("Close", "close"):
            if c in x.columns: x = x[c]; break
        else:
            x = x.iloc[:, 3] if x.shape[1] > 3 else x.iloc[:, 0]
    try:
        s = pd.Series(x).dropna()
    except Exception:
        return None
    return s if len(s) >= 10 else None

def _ratio(a, b):
    a, b = _s(a), _s(b)
    if a is None or b is None: return None
    return (a / b.reindex(a.index).ffill()).dropna()

def _spread(a, b):
    a, b = _s(a), _s(b)
    if a is None or b is None: return None
    return (a - b.reindex(a.index).ffill()).dropna()

def _first(*xs):
    for x in xs:
        if x is not None: return x
    return None

def assemble(fred, prices, bench=None, vix=None):
    f = fred or {}; p = prices or {}
    fs = lambda k: _s(f.get(k))
    ps = lambda t: _s(p.get(t))
    dxy = _first(ps("DX-Y.NYB"), ps("DXY"))
    dxy_inv = (-dxy) if dxy is not None else None

    liquidity_inputs = {"fed_bs": fs("WALCL"), "tga": fs("WTREGEN"), "rrp": fs("RRPONTSYD"),
                        "credit_creation": _first(fs("M2SL"), fs("TOTBKCR"))}
    growth_inputs = {"copper_gold": _ratio(ps("HG=F"), ps("GC=F")), "oil": _first(ps("CL=F"), ps("BZ=F")),
                     "sox": _first(ps("SMH"), ps("SOXX")), "hy_oas_inv": (-fs("BAMLH0A0HYM2")) if fs("BAMLH0A0HYM2") is not None else None,
                     "smallcap_ratio": _ratio(ps("IWM"), ps("SPY")), "dxy_inv": dxy_inv,
                     "y10": fs("DGS10"), "curve_10_2": _spread(fs("DGS10"), fs("DGS2"))}
    infl_inputs = {"breakeven": _first(fs("T5YIE"), fs("T10YIE")), "commodities": _first(ps("CL=F"), ps("GC=F")),
                   "dxy_inv": dxy_inv, "wage_proxy": _first(fs("AHETPI"), fs("PAYEMS"))}
    hy = fs("BAMLH0A0HYM2")
    systemic_inputs = {"credit": hy, "vol": _s(vix),
                       "funding": _spread(fs("SOFR"), fs("EFFR")), "leverage": fs("M2SL"),
                       # shock engine keys (hy_oas + vix term-structure proxy cover the main weights)
                       "hy_oas": hy, "vix_ts": _s(vix), "move": fs("DGS10")}

    clean = lambda d: {k: v for k, v in d.items() if v is not None}
    return dict(liquidity_inputs=clean(liquidity_inputs), growth_inputs=clean(growth_inputs),
                infl_inputs=clean(infl_inputs), systemic_inputs=clean(systemic_inputs))
