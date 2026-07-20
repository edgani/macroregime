# THE REAL CRASH — found and fixed (round 2)

## Why nothing changed last round
Last round I fixed `union.update(prices[m])` — but that was NOT where it crashed. Proof from your
screenshot: the Regional Regime panel showed "◆ regional_regime.py ○ mock", so my new code DID
deploy — yet "Run failed: 'idx'" persisted. The crash was somewhere I hadn't looked.

## The actual crash (now fixed)
`run.py`, the per-market loop:  `univ = list(prices[m].keys())`  — bracket-indexed.

It only crashes under ONE condition: **at least one market fetched successfully (v40_ok=True) AND a
different market is missing from `prices`**. That's your exact live situation: yfinance gets
us/crypto/commodity/fx, but idx.co.id fails → `prices["idx"]` never set → `prices["idx"].keys()` →
`KeyError: 'idx'` → Streamlit falls back to the raw MOCK.

My offline sandbox could NEVER reproduce it, because offline `v40_ok=False`, so the synthetic
fallback fills EVERY market including idx — so `prices["idx"]` always existed here. That blind spot
is why I missed it twice. I've now simulated your exact condition (some markets present, idx absent)
and confirmed the fix.

Fixed: every market access in that loop is now `.get(m)`-guarded (`pm = prices.get(m) or {}`), plus
`MARKETS[m]` guarded. Tested 3 ways — idx missing, all present, and an unknown market name — no crash.

## Bonus regression fixed: IHSG had no fallback
I'd made the yfinance loop SKIP idx (relying only on idx.co.id). Since idx.co.id blocks bare
requests, that left IHSG with zero data. Now yfinance (BBCA.JK, BMRI.JK, …) is the reliable BASE for
IHSG, and typef_idx only OVERWRITES it (adding foreign-flow/bandarmologi) when idx.co.id actually
responds. So IHSG loads live either way.

## You'll now be able to SEE it worked
The header badge was hardcoded "v0.2 · MOCK" and never flipped. Now when live data loads it turns
green: **"v0.3 · LIVE · N names"**. If after redeploy it still says MOCK, the run still failed —
open F12 console and send me the error; it won't be 'idx' anymore.

## Redeploy
Extract this zip → push to your `edgani/tes` repo → Streamlit redeploys. Or run locally:
`streamlit run app.py`. Expected: header flips to LIVE green; us/crypto/commodity/fx populate;
IHSG populates via yfinance; Mission Control shows the 4-timeframe quad + real regional regime.
