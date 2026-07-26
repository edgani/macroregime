# War Room OS P6.86–P6.93 — US Alpha Foundry Operational

Freeze date: **17 July 2026**

Paket ini mengubah US Stocks branch dari blueprint menjadi **runner operasional** yang dapat:

1. mengunduh data gratis yang terdaftar;
2. membuat historical S&P 500 membership filter;
3. membangun mapping filing-time SEC CIK/ticker dengan quarantine;
4. mengekstrak komponen fundamental as-filed;
5. membangun monthly point-in-time-approximate research panel;
6. menjalankan purged expanding walk-forward component/selector tournament;
7. menghasilkan US Top-20 **shadow shortlist**;
8. menyegel shortlist ke prospective receipt yang tidak boleh ditimpa;
9. membuka historical lockbox hanya sekali;
10. menyimpan seluruh trial, termasuk yang gagal.

## Cara paling mudah di Windows

Double-click:

```text
RUN_QUICK.bat
```

Masukkan email ketika diminta untuk SEC fair-access user agent. Runner akan membuat virtual environment,
memasang dependencies, mengunduh data, menjalankan pipeline, dan menghasilkan:

```text
outputs/current/US_TOP20_SHADOW_SHORTLIST.csv
outputs/current/US_TOP20_SHADOW_RECEIPT.json
outputs/prospective/YYYY-MM-DD/
outputs/discovery/COMPONENT_SELECTOR_TOURNAMENT__VALIDATION.csv
outputs/discovery/TRIAL_GRAVEYARD.csv
```

`RUN_FULL_HISTORY.bat` memakai SEC history lebih panjang. Download gratisnya besar; quick mode dipakai untuk
membuktikan operasi terlebih dahulu.

## Status penggunaan

**Layak dipakai sekarang untuk:**

- component discovery yang terdaftar;
- historical WFA candidate screening;
- shortlist research/shadow;
- prospective signal logging;
- mengidentifikasi data berbayar yang benar-benar punya incremental hypothesis.

**Belum boleh dipakai untuk:**

- klaim proven alpha;
- automatic order;
- PAPER/LIVE;
- menghapus trial gagal;
- mengubah formula setelah lockbox dibuka;
- menyebut third-party price data sebagai exchange-grade execution data.

## Kenapa belum disebut proven

Historical WFA dapat mengontrol ordinary look-ahead, tetapi tidak menghapus seluruh researcher/LLM
contamination. Paket ini karena itu membatasi historical result maksimal menjadi `HISTORICAL_CANDIDATE`.
Status proven baru boleh setelah frozen formula menghasilkan future prospective receipts yang cukup.

## Data identity rule

Tidak ada fuzzy company join otomatis. Mapping filing ke ticker memakai:

1. ticker prefix pada SEC XBRL instance file yang cocok dengan membership saat filing;
2. current SEC CIK/ticker mapping hanya jika ticker tersebut aktif pada membership interval;
3. sisanya masuk `entity_mapping_quarantine.csv`.

Unmatched data tetap missing. Ia tidak diisi nol atau dipaksakan ke ticker terdekat.

## Dashboard Streamlit

Double-click:

```text
RUN_APP.bat
```

Dashboard membaca seluruh output pipeline dan menyediakan:

- Mission Control dan readiness state;
- US Top-20 shadow shortlist;
- component/selector tournament results;
- prospective receipts dan outcome unlocks;
- data-health dan entity-quarantine audit;
- Quick/Full/Build-only/Test runner;
- shortlist generator dan immutable prospective seal;
- one-shot lockbox dengan confirmation phrase;
- claim ladder dan frozen governance.

Dashboard sengaja tidak menyediakan order execution, position sizing, leverage, atau label `PROVEN`.
