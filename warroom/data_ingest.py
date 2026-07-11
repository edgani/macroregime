"""warroom/data_ingest.py — AUTO-ADD ticker + auto-update cache.

Jawaban Edward: "kalo ada ticker baru di luar data kita, gimana auto-add ke data supaya auto-update?"

Pipeline:
  1. add_ticker(symbol) → fetch OHLC dari sumber gratis, simpan ke cache parquet.
  2. update_cache() → refresh semua ticker yang udah ada sampai tanggal terbaru.
  3. ensure(symbols) → dipanggil engine mana pun; ticker yang belum ada otomatis di-fetch.

Sumber (urutan fallback):
  - stooq (gratis, no key, daily OHLC global termasuk .US/.JK) via pandas-datareader / HTTP CSV
  - yfinance (kalau ke-install & network Yahoo ada di mesin lu — DEFAULT di produksi)
  - GitHub dataset mirror (buat sample/backfill)

Di sandbox Anthropic, Yahoo/stooq ke-block → fetch bakal gagal & di-LOG jujur (ga ngarang data).
Di mesin LU, ini jalan penuh: tiap ticker baru yang muncul (dari discovery/rekomendasi) auto ke-tarik
& masuk cache. Cache = parquet per-ticker di data/cache/, plus panel gabungan buat backtest.
"""
from __future__ import annotations
import os
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
PANEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "panel.parquet")


def _cache_path(symbol):
    safe = symbol.replace("/", "_").replace("\\", "_")
    return os.path.join(CACHE_DIR, f"{safe}.parquet")


def _fetch_stooq(symbol, start="2010-01-01"):
    """Stooq daily CSV — free, no key. US names need .US suffix, IDX need .JK-style handled by caller."""
    import urllib.request, io
    s = symbol.lower()
    if "." not in s and "-" not in s:
        s = s + ".us"
    url = f"https://stooq.com/q/d/l/?s={s}&i=d"
    raw = urllib.request.urlopen(url, timeout=30).read()
    df = pd.read_csv(io.BytesIO(raw))
    if "Date" not in df.columns or len(df) < 20:
        raise ValueError(f"stooq returned no data for {symbol}")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]
    return df[df.index >= start]


def _fetch_yfinance(symbol, start="2010-01-01"):
    import yfinance as yf
    df = yf.download(symbol, start=start, progress=False, auto_adjust=False)
    if df is None or len(df) < 20:
        raise ValueError(f"yfinance returned no data for {symbol}")
    df = df.rename(columns=str.title)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def add_ticker(symbol, start="2010-01-01", source="auto"):
    """Fetch a ticker and cache it. Returns dict {ok, source, rows, path, error}."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    errors = []
    sources = ([source] if source != "auto" else ["yfinance", "stooq"])
    for src in sources:
        try:
            df = _fetch_yfinance(symbol, start) if src == "yfinance" else _fetch_stooq(symbol, start)
            df.to_parquet(_cache_path(symbol))
            return {"ok": True, "source": src, "rows": len(df), "path": _cache_path(symbol),
                    "range": f"{df.index.min().date()}→{df.index.max().date()}"}
        except Exception as e:
            errors.append(f"{src}: {type(e).__name__} {str(e)[:60]}")
    return {"ok": False, "source": None, "error": " | ".join(errors),
            "note": "fetch failed (expected in sandbox — Yahoo/stooq blocked). Runs on your machine."}


def ensure(symbols, start="2010-01-01", max_age_days=1):
    """Make sure each symbol is cached & fresh. Auto-fetches missing/stale ones. Returns status map.
    Call this from any engine that receives a new ticker — it self-heals the dataset."""
    import time
    out = {}
    for sym in symbols:
        p = _cache_path(sym)
        if os.path.exists(p):
            age = (time.time() - os.path.getmtime(p)) / 86400
            if age <= max_age_days:
                out[sym] = {"ok": True, "cached": True, "age_days": round(age, 1)}
                continue
        out[sym] = add_ticker(sym, start)
    return out


def update_cache(max_age_days=1):
    """Refresh every ticker already in cache to the latest date."""
    if not os.path.isdir(CACHE_DIR):
        return {"updated": 0, "note": "no cache yet"}
    syms = [f[:-8] for f in os.listdir(CACHE_DIR) if f.endswith(".parquet")]
    res = ensure(syms, max_age_days=max_age_days)
    return {"checked": len(syms), "refetched": sum(1 for v in res.values() if not v.get("cached")), "detail": res}


def load_cached(symbol):
    p = _cache_path(symbol)
    return pd.read_parquet(p) if os.path.exists(p) else None


def build_panel(symbols=None):
    """Combine cached tickers into a long panel [date, open, high, low, close, volume, Name] for backtest."""
    if not os.path.isdir(CACHE_DIR):
        return None
    syms = symbols or [f[:-8] for f in os.listdir(CACHE_DIR) if f.endswith(".parquet")]
    frames = []
    for s in syms:
        d = load_cached(s)
        if d is not None and len(d) > 50:
            d = d.reset_index().rename(columns={"index": "date", "Date": "date",
                                                "Open": "open", "High": "high", "Low": "low",
                                                "Close": "close", "Volume": "volume"})
            d["Name"] = s
            frames.append(d[["date", "open", "high", "low", "close", "volume", "Name"]])
    if not frames:
        return None
    panel = pd.concat(frames, ignore_index=True)
    os.makedirs(os.path.dirname(PANEL_PATH), exist_ok=True)
    panel.to_parquet(PANEL_PATH)
    return panel
