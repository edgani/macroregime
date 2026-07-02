# War Room — Perubahan (sesi ini)

Verdict dulu: **approach entry/stop/target lama udah gw ganti total, gw nemu 1 bug parah (gatekeeper
random), gw benerin, dan gw bangun test suite yang jujur.** Detail:

---

## A. DECISION APPROACH — DIGANTI (sesuai spec dokumen IIDOS lu)

**Yang lama (dibuang):**
- `stop = px * 0.97`, `target = px * 1.06` — hardcoded, ga ada hubungannya sama struktur.
- Entry zone yang **lower bound-nya = stop** → kalau fill di bawah zona, langsung stopped out. (terbukti di audit: `entry='141.37–145.74' stop=141.37`)
- `optimal_entry._rr` fallback fabrikasi level ±3% kalau risk range gagal.
- `render._asymmetry` P(win) = `0.40 + 0.35*score/100` — **angka dikarang dari score, dilabel "est"** tapi tetep muncul ke user.
- `analyze_watchlist` direction dari `close>=sma50` doang (beda dari `_rank` yang pakai formation+RS).

**Yang baru (`warroom/decision_center.py`, LEVEL 8):**
- **ENTRY**: 3 zona (Conservative/Base/Aggressive) + DCA ladder + pyramid level — **semua diturunkan dari Hedgeye TRADE/TREND band**. Ga ada risk range → level **di-withhold + flag**, TIDAK difabrikasi.
- **5 STOP**: Technical (band-derived), Macro (kondisi quad-flip), Thesis (kill-switch kausal dari chain), Time (10-bar no follow-through), Fundamental (cuma kalau feed ada; kalau ga: *"absent, not faked"*).
- **TARGET**: T1=TRADE opposite · T2=TREND · T3=TAIL, dengan sanitasi — kalau T2/T3 jatuh di dalam T1 (kejadian di beberapa vol-state), rung-nya **di-drop**, bukan bikin ladder ngaco.
- **P(win)/EV**: **calibrated-or-silent** — cuma tampil kalau ada ≥30 closed trade di tracker DB. Di bawah itu → `"uncalibrated — baru N closed"`, EV ga ditampilkan. **Nol fabrikasi.**
- **INVALIDATION**: daftar kondisi kausal yang bisa diuji (bukan cuma level harga).
- **REKOMENDASI**: BUY/WATCH/AVOID/SELL/HOLD (vocab spec), aturan eksplisit & bisa diaudit.

Semua parameter struktur (0.5·half stop, rung DCA, 10-bar) **dilabel PRIOR TAK-TERVALIDASI** dan masuk daftar uji di `run_validation.py` (stability phase).

**Wiring**: `compute.py` nyimpen `_rr_full` di tiap setup + panggil `DC.build()` di loop `_tag` untuk conviction & semua market setups. `render._asymmetry` sekarang baca `decision_pkg`.

---

## B. BUG PARAH — GATEKEEPER PALSU (ini yang lu minta gw cari)

`engines/walkforward_backtest_engine.batch_gatekeeper()` — yang **ke-wire ke dashboard lu sebagai
"Walk-forward + MC 100x Gatekeeper"** — isinya:

```python
wf_score = random.uniform(50, 85)
mc_score = random.uniform(55, 90)
gate_status = "PASS" if combined >= 55 else "FAIL"
optimal_stop_adj = round(random.uniform(-2, 0), 1)
```

**Semua PASS/FAIL, skor validasi, "optimal stop adjustment" yang lu liat = angka acak.** Tiap refresh
beda. Gw buktiin: call 1 = 66.3, call 2 = 62.7, dari input yang sama persis.

**Fix**: gw bangun `warroom/backtest.py` — walk-forward **beneran**:
- Path-dependent trade sim (telusuri OHLC ke depan, WIN/LOSS dari mana yang kena duluan; both-touch = LOSS konservatif, sama kayak tracker).
- **No look-ahead** (sinyal bar t cuma diuji di bar > t — terbukti: max hist_len ≤ n).
- Walk-forward folds kronologis (IS/OOS terpisah).
- Block-bootstrap p-value (block=5) vs entry acak.
- Net-of-cost (bps).
- `batch_gatekeeper_real()` = drop-in replacement. PASS butuh: ≥15 closed, hit>52%, expectancy>0, **beats random (p<0.10)**.

`compute.py` sekarang manggil yang REAL. Yang lama gw karantina (masih ada di engines/ tapi ga dipanggil).

---

## C. TEST SUITE (jawaban "run semua test")

`run_validation.py` — subset yang **beneran bisa dijalankan** dari ~200-test framework lu (attachment 1-3):

```
python run_validation.py --synthetic   # sandbox: buktiin mesin jalan & ga look-ahead
python run_validation.py --cache        # mesin lu: verdict beneran (butuh build_cache.py dulu)
```

Tiap test statusnya: **PASS/FAIL** (dijalankan) · **NEEDS-DATA** (butuh data real/vintage/feed) ·
**NEEDS-TIME** (butuh calendar time buat track record). **Ga ada verdict yang dikarang.**

Hasil synthetic run: **15 PASS, 0 FAIL, 18 NEEDS-DATA/TIME**. Yang PASS antara lain:
- quad sign-mapping (G/I → Q1-4) benar
- deteksi gatekeeper palsu
- no fabricated levels
- P(win) not score-mapped
- path-dependent both-touch=LOSS
- no look-ahead
- walk-forward folds jalan
- block-bootstrap discriminates
- parameter stability across window
- meta-validation (deflated t-stat guard ada)

**Kenapa banyak NEEDS-DATA**: test kayak regime-robustness (2006-2026), COT edge, counterfactual,
decision-impact ladder, capacity/execution — semua butuh data harga REAL + feed + vintage FRED yang
**ke-block di sandbox** (yahoo/fred/stooq semua 403). Gw ga mau pura-pura. Jalanin `--cache` di mesin
lu abis `build_cache.py` + `build_feeds.py`, phase-phase itu langsung aktif.

---

## D. DASHBOARD — AMBIL DARI REFERENSI (yang lu kirim)

Dari dashboard Nova Capital/bimagalih6_ yang lu attach, gw ambil **layout country-regime grid** (Image 6)
karena emang bersih & gampang dibaca. Tapi:

**`warroom/country_regime.py`** — grid 16 negara Goldilocks/Reflation/Stagflation/Deflation, TAPI tiap
label **dihitung dari price-proxy quad beneran** (growth = momentum ETF negara 63d-126d, inflation =
commodity tilt global), **bukan label karangan**. Negara tanpa proxy → **"data pending"**, bukan regime palsu.

**Keterbatasan yang gw akui**: inflation axis masih **shared** (satu commodity proxy global) — jadi
`i` sama buat semua negara sampai lu wire CPI per-negara. Growth axis udah beda-beda. Ini gw tulis di
`note` field yang muncul di UI, ga gw sembunyiin. Ke-render di Command Center abis Quad path.

Yang **ga** gw ambil dari referensi: mereka ga punya decision layer, entry/stop/target, validation,
causal chains. Itu punya lu udah lebih jauh. Jadi gw ambil presentasi, bukan logika.

---

## Yang HARUS lu lakuin di mesin sendiri

1. `python build_cache.py` → tarik harga real ke parquet.
2. `export FRED_API_KEY=... && python build_feeds.py` → FRED + COT + Type-F + on-chain.
3. `python run_validation.py --cache` → **sekarang verdict-nya beneran.** Baca `validation_report.json`.
4. Track record (P(win) kalibrasi) **akrual seiring waktu** — tiap hari lu buka app, `tracker.py` log
   sinyal point-in-time + resolve yang lama. Setelah ~30 closed trade per bucket, P(win) mulai muncul.

Yang **ga bisa** gw kasih dari sini: angka backtest "final" atas data real, karena datanya ke-block.
Mesin-nya udah bener & terbukti ga look-ahead — tinggal kasih makan data lu.
