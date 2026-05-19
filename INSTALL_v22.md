# 🚀 MacroRegime Pro v2.2 — Sprint 6 Deep Audit Fixes

**Date:** May 16, 2026

## 🩺 Audit Findings (Yang Bikin Lu Khawatir)

Edward, gw deep-audit semua kode. Ini 6 bugs critical yang ketemu:

| # | Issue | Severity | Impact |
|---|---|---|---|
| **1** | `_build_consolidated_row` direction NEVER FLIPS dari composite even if 4 signals contradict | 🔴 **CRITICAL** | "LONG padahal harusnya SHORT" — exactly yang lu khawatirkan |
| **2** | v2 RiskRangeEngine entry/target/stop **diabaikan** oleh `_rr_levels` proxy | 🔴 CRITICAL | Pakai dumb proxy bukan v2 engine |
| **3** | 14 engine outputs computed tapi **never displayed** (charm/vanna/gex/structure/volga/odte/etc.) | 🟡 MEDIUM | Buang build time tanpa ROI |
| **4** | Dashboard punya 27x "Quad", 30x "Regime" duplicate mentions | 🟡 MEDIUM | Visual clutter |
| **5** | Bonds-XAU correlation **belum ada engine** — missing edge | 🟢 LOW | Opportunity cost |
| **6** | Filter ticker per tab via bucket lookup → **bisa leakage** (ETF di wrong tab) | 🟢 LOW | Wrong categorization possible |

## ✅ Yang Sudah Fixed di v2.2

### 1. Composite Signal Engine (P0 — fixes direction bug)
File: `engines/composite_signal_engine.py` (350 lines, 8 signal sources weighted)

**Sebelum (BUG):**
```
Price < trade_lrr → composite "bullish" → direction "LONG"
Even if: COT bearish + OI distribution + Greeks bearish + Q4 regime
Result: STILL LONG. Just labeled "CONFLICTED" but direction unchanged.
```

**Sekarang (FIXED):**
```
8 signal scores → weighted aggregate → final direction
If ≥3 signals contradict → direction can FLIP
Output: "⚠️ FLIPPED SHORT from naive bullish — COT bearish, Greeks bearish, Q4 misaligned"
```

Test verified: Naive bullish flipped to SHORT when Q4 + COT + OI + Greeks all bearish.

### 2. Risk Setup Engine (P0 — integrates everything)
File: `engines/risk_setup_engine.py` (250 lines)

**Methodology upgrades vs old `_rr_levels`:**
- Entry: considers price location (Buy Now if already below trade_l)
- Target 1: closer of (Trade upper / Max Pain / Call Wall)
- Target 2: Trend upper if high conviction, else 80% to Trend
- Stop: ATR-based with validity check (always below entry for LONG, above for SHORT)
- Stops filtered: NO stop above entry untuk LONG (was a bug)
- Confidence: combined composite + RR quality

### 3. Bonds-XAU Regime Engine (P0 — new edge)
File: `engines/bonds_xau_regime.py` (300 lines)

**Edge added:**
- Real Yield (DGS10 - T10YIE) → gold inverse correlation regime
- Yield Curve 2s10s → recession signal → bonds bid
- Gold/Silver ratio → risk regime (>80 risk off, <60 risk on)
- DXY-Gold rolling correlation → classic inverse vs rare decorrelation
- TLT/GLD ratio → flight vs inflation hedge
- HYG-LQD credit spread → stress indicator

**Outputs ticker biases for:**
GLD, SLV, GDX, GDXJ, NEM, AEM, SIL, SILJ, TLT, IEF, TIP, UUP

### 4. Market Classifier (P1 — prevents tab leakage)
File: `engines/market_classifier.py` (150 lines)

Canonical mapping ticker → market category:
- US Equity: NVDA, AAPL, MSFT, etc.
- Forex: =X suffix, DX-Y.NYB, UUP/FXE/FXY
- Commodity: =F suffix, GLD/SLV/USO/UNG (ETF proxies)
- Crypto: -USD suffix
- IHSG: .JK suffix
- Japan/Korea/China/etc: .T/.KS/.SS/.HK/.L/.PA

Validates against config buckets, catches cross-listings.

## 📊 How Tickers Now Filter Per Tab

| Tab | Source Universe | Filter Logic |
|---|---|---|
| **🇺🇸 US Stocks** | `US_SECTORS ∪ US_BUCKETS` | Composite signal NOT NEUTRAL/AVOID + market_classifier == "us_equity" |
| **💱 Forex** | `FOREX_PAIRS` | Composite signal NOT NEUTRAL/AVOID + market_classifier == "forex" |
| **🛢️ Commodities** | `COMMODITIES` | Same + classifier == "commodity" |
| **₿ Crypto** | `CRYPTO` + crypto_center engine | Composite + 21d return override for crypto-specific momentum |
| **🌍 IHSG** | `IHSG_UNIVERSE` | Composite + classifier == "ihsg" |
| **⚡ Alpha Center** | Top by priority_score across ALL tabs | Cross-market alpha ranking |

**Direction now properly determined by:**
1. Mean reversion (price vs Trade range) — weight 0.20
2. Trend (price vs SMA50/200) — weight 0.20
3. COT bias — weight 0.15
4. OI position — weight 0.10
5. Greeks composite — weight 0.10
6. Gamma regime — weight 0.10
7. News sentiment — weight 0.10
8. Quad alignment — weight 0.10 (FLIPS sign if fighting regime)

If ≥3 signals contradict naive composite → direction can FLIP to opposite.
If too many contradictions → marked AVOID (don't trade).

## 📊 Entry/Target/Stop Now Determined By

**For LONG:**
```
Entry:
  IF price < trade_lrr → Buy Now at current price (don't chase up)
  ELSE → wait for dip to trade_lrr
  
Target 1: MIN of [trade_trr, max_pain, call_wall] above entry
  → uses options magnet (Max Pain) if closer than Trade upper

Target 2:
  IF composite is_strong → Trend upper (ambitious)
  ELSE → 80% of way to Trend upper (modest)
  
Stop: MAX of [
  Entry - 1.5×ATR_14,           # ATR-based (capture jump risk)
  Trade_lrr - 20% × spread,      # Range-based  
  put_wall × 0.998 (if exists)   # Options-based
] — filtered to ensure stop < entry
```

**SHORT mirror:** Min of stops, all > entry.

## 🎯 Sample Outputs (verified smoke test)

**Test 1: BULLISH→SHORT flip when signals contradict**
```
Input: QQQ price=445, trade_l=450 (naive bullish), but...
  COT bearish, OI High at highs, Greeks BEARISH, Gamma DEEP_NEGATIVE, Q4 regime
Output: 
  Direction: SHORT (FLIPPED from bullish)
  Score: -0.20 | Confidence: 44%
  Rationale: "⚠️ FLIPPED from bullish: Top: greeks=-0.80, mean_reversion=+0.75, cot=-0.70"
```

**Test 2: All aligned bullish**
```
Input: NVDA, all signals + Q1 = bullish
Output:
  Direction: LONG | Score: +0.56 | Confidence: 100%
```

**Test 3: Risk Setup LONG NVDA @ 120**
```
Trade range: 125-145, ATR 3.5
Entry: 120 (Buy Now — already below trade_l)
Target1: 140 (Max Pain — closer than trade_r 145)
Target2: 155 (Trend upper — high conviction)
Stop: 117.76 (ATR-1.5x = 114.75 OR RR-20% = 121; 117.76 = valid tightest)
RR: 8.94x
```

**Test 4: Bonds-XAU Regime**
```
Real yield 1.9%, Yield curve INVERTED -0.2 → "CURVE_INVERTED" flag
Gold/Silver ratio 7.3 (low risk-on)
Regime: RISK_OFF_BONDS_BID
Gold bias: +0.40 (LONG), Bonds: +0.60 (STRONG_LONG)
```

## 🚀 Install

```bash
cd /path/to/edgani/tes
git add . && git commit -m "Pre-v2.2 backup"
unzip ~/Downloads/macroregime_v2_2.zip
cp -r macroregime_FULL_v22/* .
git add . && git commit -m "v2.2: Sprint 6 — composite signal + risk setup + bonds-XAU" && git push
```

## 📊 What You'll See

### Dashboard (5 tabs sekarang — added Bonds-XAU)
```
🧠 Yves Behavioral | 📊 GIP v10 Bayesian | 🔍 Discovery Summary | ⚡ Cascade Summary | 🪙 Bonds-XAU Regime
```

### Footer
```
Built 85s · 250 assets · 28 indicators · 1340 headlines · ⚠️ 8 dir flipped · v28-Sprint6
                                                              ↑ THIS is new
```

### Ticker Detail Cards (US Stocks/Forex/Commodities/Crypto)
Setiap card sekarang punya:
- **Direction** ← dari composite signal (bisa LONG/SHORT/FLIPPED)
- **Entry/Target1/Target2/Stop** ← dari risk_setup_engine
- **Composite Score** & **Confidence**
- **Rationale** (penjelasan kenapa direction itu, termasuk kalau di-flip)

## 📋 Verification Checklist Setelah Deploy

1. Cek log untuk: `Composite signals: N tickers, M direction flipped from naive composite`
   - Jika M > 0 → direction flip BERFUNGSI. Lu liat di Dashboard footer "⚠️ M dir flipped".
2. Cek Dashboard Bonds-XAU tab — regime label muncul (RISK_OFF/STAGFLATION/etc.)
3. Buka US Stocks tab — beberapa ticker harusnya punya `⚠️ FLIPPED` di recommendation
4. Buka ticker detail card — entry/target/stop sekarang make sense (stop selalu di sisi yang benar)

## 🚨 Troubleshooting

| Symptom | Fix |
|---|---|
| Composite signal not working | Check `_V2_COMPOSITE=True` in log; if False, import failed |
| Stop above entry for LONG | Should be impossible now — report screenshot if happens |
| Bonds-XAU regime "UNKNOWN" | Some FRED series missing — check `DGS10`, `DGS2`, `T10YIE` loaded |
| Direction never flips | Test data may not have enough contradicting signals — that's correct behavior |

## #process — Manage risk accordingly. Deploy + lapor.
