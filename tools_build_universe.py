"""Build universe_full.json — the expanded per-ticker universe for the desk.

Sources (all live, no key):
  US        : S&P 500 + NASDAQ-100 constituents (Wikipedia tables)
  IDX       : IDX listed-company API (all ~963 emiten)
  Crypto    : Binance 24h tickers, top 100 USDT pairs by quote volume
  FX        : curated 28 majors/crosses + USDIDR/USDSGD
  Commodity : curated liquid futures (Yahoo symbols)

Output rows: {instrument, provider_symbol, provider, asset_type, name?}
The desk merges this with the research universe (research context wins on
duplicates); tickers without research context get honest NO_DATA packets.
Re-run manually or from the daily cycle when constituents need refreshing.
"""
from __future__ import annotations

import io
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "universe_full.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MARKETS = ["us", "idx", "crypto", "commodity", "fx"]


def get(url: str, timeout: float = 30.0) -> bytes:
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={**UA, "Accept": "application/json, text/html, */*",
                                                       "X-Requested-With": "XMLHttpRequest"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def us_universe() -> list[dict]:
    import pandas as pd
    rows: dict[str, dict] = {}
    for url, col in [
        ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol"),
        ("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker"),
    ]:
        tables = pd.read_html(io.BytesIO(get(url)))
        frame = max(tables, key=lambda t: len(t))
        for _, r in frame.iterrows():
            sym = str(r.get(col) or "").strip().upper().replace(".", "-")
            name = str(r.get("Security") or r.get("Company") or "").strip()
            if sym and sym.isascii() and len(sym) <= 6:
                rows.setdefault(sym, {"instrument": sym, "provider_symbol": sym, "provider": "YAHOO", "asset_type": "EQUITY", "name": name})
    return sorted(rows.values(), key=lambda x: x["instrument"])


def idx_universe() -> list[dict]:
    # DataTables server-side params: start/length returns the full set in one call.
    url = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?kodeEmiten=&start=0&length=2000"
    data = json.loads(get(url, timeout=60.0))
    rows: dict[str, dict] = {}
    for row in data.get("data") or []:
        code = str(row.get("KodeEmiten") or "").strip().upper()
        if not code or len(code) > 6:
            continue
        rows.setdefault(code, {"instrument": code, "provider_symbol": code + ".JK", "provider": "YAHOO", "asset_type": "EQUITY",
                               "name": str(row.get("NamaEmiten") or "").strip(), "board": str(row.get("PapanPencatatan") or "")})
    return sorted(rows.values(), key=lambda x: x["instrument"])


def crypto_universe(top_n: int = 100) -> list[dict]:
    data = json.loads(get("https://api.binance.com/api/v3/ticker/24hr", timeout=30.0))
    blocked = ("UP", "DOWN", "BEAR", "BULL")
    stables = {"USDC", "FDUSD", "TUSD", "DAI", "USDP", "EUR", "GBP", "BIDR", "IDRT", "TRY", "BRL", "ARS", "NGN", "UAH", "VAI", "AEUR"}
    pairs = []
    for row in data:
        sym = str(row.get("symbol") or "")
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        if base.endswith(blocked) or base in stables:
            continue
        try:
            vol = float(row.get("quoteVolume") or 0)
        except (TypeError, ValueError):
            continue
        pairs.append((vol, sym))
    pairs.sort(reverse=True)
    return [{"instrument": sym, "provider_symbol": sym, "provider": "BINANCE", "asset_type": "CRYPTO"} for _, sym in pairs[:top_n]]


def fx_universe() -> list[dict]:
    pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
             "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CADJPY", "CHFJPY",
             "EURGBP", "EURAUD", "EURCAD", "EURNZD", "EURCHF",
             "GBPAUD", "GBPCAD", "GBPNZD", "GBPCHF",
             "AUDCAD", "AUDNZD", "AUDCHF", "CADCHF", "USDIDR", "USDSGD"]
    return [{"instrument": p, "provider_symbol": p + "=X", "provider": "YAHOO", "asset_type": "FX"} for p in pairs]


def commodity_universe() -> list[dict]:
    contracts = {
        "GC": "Gold", "SI": "Silver", "PL": "Platinum", "HG": "Copper",
        "CL": "WTI crude", "BZ": "Brent crude", "NG": "Natural gas", "HO": "Heating oil", "RB": "RBOB gasoline",
        "ZW": "Wheat", "ZC": "Corn", "ZS": "Soybeans", "ZL": "Soybean oil", "SB": "Sugar", "KC": "Coffee",
        "CT": "Cotton", "CC": "Cocoa", "LE": "Live cattle", "HE": "Lean hogs", "LBR": "Lumber",
    }
    return [{"instrument": k, "provider_symbol": k + "=F", "provider": "YAHOO", "asset_type": "COMMODITY", "name": v}
            for k, v in sorted(contracts.items())]


def main() -> None:
    universe = {"us": us_universe(), "idx": idx_universe(), "crypto": crypto_universe(),
                "commodity": commodity_universe(), "fx": fx_universe()}
    payload = {
        "schema": "warroom.expanded_universe.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": {"us": "wikipedia sp500+ndx100", "idx": "idx.co.id company profiles",
                    "crypto": "binance 24h quote volume top100", "fx": "curated", "commodity": "curated futures"},
        "counts": {m: len(universe[m]) for m in MARKETS},
        "markets": universe,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["counts"]))
    print("total:", sum(payload["counts"].values()))


if __name__ == "__main__":
    main()
