"""live_data_engine.py — Reliable server-side data fetchers v40.4

Problem solved: barchart/CME/laevitas are JS-heavy + bot-detected → fail on cloud servers.
This engine uses sources that ACTUALLY work server-side (Streamlit Cloud):
  • OPTIONS OI STRUCTURE → yfinance option_chain (OI/IV, walls/max-pain/PCR and an OI-implied gamma proxy)
  • ON-CHAIN          → DeFiLlama api.llama.fi (public REST, proper headers)
  • COT               → CFTC reports (keyed by TICKER, not product name — fixes "unavailable")

All outputs keyed by the EXACT ticker symbol the UI uses (BTC-USD, EURUSD=X, NVDA, etc.)
so rich_ticker_card lookups succeed.
"""
from __future__ import annotations
import logging, math
from typing import Dict, List, Optional
import datetime as dt

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# OPTIONS via yfinance — OI structure / walls / max-pain / PCR / expected move
# ═══════════════════════════════════════════════════════════════════════════

def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs_gamma(S, K, T, r, sigma):
    """Black-Scholes gamma."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        pdf = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
        return pdf / (S * sigma * math.sqrt(T))
    except (ValueError, ZeroDivisionError):
        return 0.0


def _fetch_one_option_yf(ticker: str):
    """Fetch + compute options intelligence for ONE ticker. Returns (ticker, dict|None)."""
    import yfinance as yf
    try:
        tk = yf.Ticker(ticker)
        exps = tk.options
        if not exps:
            return ticker, None
        hist = tk.history(period="1d")
        if hist.empty:
            return ticker, None
        spot = float(hist["Close"].iloc[-1])
        if spot <= 0:
            return ticker, None
        today = dt.date.today()
        near_exps = exps[:2]
        total_call_oi = {}; total_put_oi = {}; gex_by_strike = {}
        atm_iv = None; atm_call_price = atm_put_price = None; min_atm_dist = 1e9
        for exp_str in near_exps:
            try:
                exp_date = dt.datetime.strptime(exp_str, "%Y-%m-%d").date()
                T = max((exp_date - today).days, 1) / 365.0
                chain = tk.option_chain(exp_str)
                calls, puts = chain.calls, chain.puts
                for _, row in calls.iterrows():
                    K = float(row["strike"]); oi = float(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0) or 0)
                    total_call_oi[K] = total_call_oi.get(K, 0) + oi
                    gamma = _bs_gamma(spot, K, T, 0.05, iv if iv > 0 else 0.5)
                    gex_by_strike[K] = gex_by_strike.get(K, 0) + gamma * oi * 100 * spot * spot * 0.01
                    dist = abs(K - spot)
                    if dist < min_atm_dist:
                        min_atm_dist = dist; atm_iv = iv
                        atm_call_price = float(row.get("lastPrice", 0) or 0)
                for _, row in puts.iterrows():
                    K = float(row["strike"]); oi = float(row.get("openInterest", 0) or 0)
                    iv = float(row.get("impliedVolatility", 0) or 0)
                    total_put_oi[K] = total_put_oi.get(K, 0) + oi
                    gamma = _bs_gamma(spot, K, T, 0.05, iv if iv > 0 else 0.5)
                    gex_by_strike[K] = gex_by_strike.get(K, 0) - gamma * oi * 100 * spot * spot * 0.01
                    if abs(K - spot) < 0.01 * spot:
                        atm_put_price = float(row.get("lastPrice", 0) or 0)
            except Exception:
                continue
        if not total_call_oi and not total_put_oi:
            return ticker, None
        calls_above = {k: v for k, v in total_call_oi.items() if k >= spot}
        call_wall = max(calls_above, key=calls_above.get) if calls_above else None
        puts_below = {k: v for k, v in total_put_oi.items() if k <= spot}
        put_wall = max(puts_below, key=puts_below.get) if puts_below else None
        net_gex = sum(gex_by_strike.values())
        gamma_flip = None; cum = 0
        for k in sorted(gex_by_strike.keys()):
            prev_cum = cum; cum += gex_by_strike[k]
            if prev_cum < 0 <= cum and gamma_flip is None:
                gamma_flip = k; break
        all_strikes = sorted(set(list(total_call_oi.keys()) + list(total_put_oi.keys())))
        max_pain = None; min_pain = 1e18
        for K_test in all_strikes:
            pain = 0
            for K, oi in total_call_oi.items():
                if K_test > K: pain += (K_test - K) * oi
            for K, oi in total_put_oi.items():
                if K_test < K: pain += (K - K_test) * oi
            if pain < min_pain:
                min_pain = pain; max_pain = K_test
        tot_call = sum(total_call_oi.values()); tot_put = sum(total_put_oi.values())
        pcr = (tot_put / tot_call) if tot_call > 0 else None
        expected_move_pct = None
        if atm_call_price and atm_put_price:
            expected_move_pct = (atm_call_price + atm_put_price) / spot * 100
        elif atm_iv:
            expected_move_pct = atm_iv / math.sqrt(52) * 100
        return ticker, {
            "spot": round(spot, 2),
            "call_wall": round(call_wall, 2) if call_wall else None,
            "call_wall_strike": round(call_wall, 2) if call_wall else None,
            "put_wall": round(put_wall, 2) if put_wall else None,
            "put_wall_strike": round(put_wall, 2) if put_wall else None,
            "max_pain": round(max_pain, 2) if max_pain else None,
            "gamma_flip": round(gamma_flip, 2) if gamma_flip else None,
            "gex_proxy": net_gex, "net_gex_proxy": net_gex,
            # Backward-compatible aliases. These are explicitly OI-implied proxies, not observed dealer books.
            "gex": net_gex, "net_gex": net_gex,
            "put_call_ratio": round(pcr, 2) if pcr else None,
            "pc_ratio": round(pcr, 2) if pcr else None,
            "atm_iv": round(atm_iv, 4) if atm_iv else None,
            "iv_30d": round(atm_iv, 4) if atm_iv else None,
            "expected_move_pct": round(expected_move_pct, 2) if expected_move_pct else None,
            "total_call_oi": int(tot_call), "total_put_oi": int(tot_put),
            "gex_by_strike": {round(float(k), 2): round(float(v), 0) for k, v in gex_by_strike.items()},
            "call_oi_by_strike": {round(float(k), 2): int(v) for k, v in total_call_oi.items()},
            "put_oi_by_strike": {round(float(k), 2): int(v) for k, v in total_put_oi.items()},
            "source": "yfinance_option_chain",
            "data_semantics": "OI_IMPLIED_GAMMA_PROXY_NOT_DEALER_POSITION",
        }
    except Exception as e:
        logger.debug(f"options fetch {ticker}: {e}")
        return ticker, None


def fetch_options_yf(tickers: List[str], max_tickers: int = 30, max_workers: int = 12) -> Dict:
    """Fetch option-chain OI/IV via yfinance and calculate walls, max-pain and an OI-implied gamma proxy.

    The gamma proxy assumes calls positive and puts negative; it is *not* an observed dealer inventory
    or a substitute for trade-level options flow. Threading only reduces I/O latency.
    """
    try:
        import yfinance as yf  # noqa: F401
    except ImportError:
        logger.warning("yfinance not installed — options unavailable")
        return {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    targets = tickers[:max_tickers]
    out = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_fetch_one_option_yf, t) for t in targets]
        for fut in as_completed(futures):
            try:
                tkr, data = fut.result()
                if data:
                    out[tkr] = data
            except Exception:
                continue
    logger.info(f"live_data: yfinance options fetched for {len(out)}/{len(targets)} tickers (parallel)")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ON-CHAIN via DeFiLlama public API
# ═══════════════════════════════════════════════════════════════════════════

def fetch_onchain_defillama(ticker_chain_map: Dict[str, str]) -> Dict:
    """Fetch on-chain TVL + changes from DeFiLlama. Keyed by TICKER (BTC-USD etc.).

    ticker_chain_map: {"BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana"}
    """
    import urllib.request, json
    out = {}
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
               "Accept": "application/json"}

    # Fetch all chains once
    try:
        req = urllib.request.Request("https://api.llama.fi/v2/chains", headers=headers)
        all_chains = json.loads(urllib.request.urlopen(req, timeout=12).read())
        chain_by_name = {c.get("name", "").lower(): c for c in all_chains}
    except Exception as e:
        logger.warning(f"DeFiLlama chains fetch failed: {e}")
        chain_by_name = {}

    for ticker, chain_name in ticker_chain_map.items():
        c = chain_by_name.get(chain_name.lower())
        if not c:
            continue
        tvl = c.get("tvl", 0)

        # Try to get historical for change calc
        tvl_change_7d = None
        try:
            req = urllib.request.Request(
                f"https://api.llama.fi/v2/historicalChainTvl/{chain_name}", headers=headers)
            hist = json.loads(urllib.request.urlopen(req, timeout=12).read())
            if len(hist) >= 8:
                now_tvl = hist[-1]["tvl"]
                week_ago = hist[-8]["tvl"]
                if week_ago > 0:
                    tvl_change_7d = (now_tvl / week_ago - 1) * 100
        except Exception:
            pass

        # Protocol TVL direction is not a whale-position claim.
        signal = "TVL_STABLE"
        if tvl_change_7d is not None:
            if tvl_change_7d > 5:
                signal = "PROTOCOL_TVL_INFLOW"
            elif tvl_change_7d < -5:
                signal = "PROTOCOL_TVL_OUTFLOW"

        out[ticker] = {
            "tvl": tvl,
            "tvl_usd": tvl,
            "tvl_change_7d": round(tvl_change_7d, 2) if tvl_change_7d is not None else None,
            "protocol_tvl_change_7d": round(tvl_change_7d, 2) if tvl_change_7d is not None else None,
            "signal": signal,
            "source": "defillama",
        }

    logger.info(f"live_data: DeFiLlama on-chain fetched for {len(out)} tickers")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# COT — keyed by TICKER (fixes "unavailable" — was keyed by product name)
# ═══════════════════════════════════════════════════════════════════════════

# Map TICKER SYMBOL → CFTC product name (so UI lookup by ticker works)
COT_TICKER_MAP = {
    "EURUSD=X": "EUR", "EUR=X": "EUR",
    "GBPUSD=X": "GBP", "GBP=X": "GBP",
    "JPY=X": "JPY", "USDJPY=X": "JPY",
    "AUDUSD=X": "AUD", "AUD=X": "AUD",
    "USDCAD=X": "CAD", "CAD=X": "CAD",
    "USDCHF=X": "CHF", "CHF=X": "CHF",
    "NZDUSD=X": "NZD",
    "DX-Y.NYB": "USD", "UUP": "USD",
    "GC=F": "GOLD", "GLD": "GOLD",
    "SI=F": "SILVER", "SLV": "SILVER",
    "CL=F": "CRUDE", "USO": "CRUDE",
    "NG=F": "NATGAS", "UNG": "NATGAS",
    "HG=F": "COPPER", "CPER": "COPPER",
    "ZC=F": "CORN", "CORN": "CORN",
    "ZW=F": "WHEAT", "WEAT": "WHEAT",
    "ZS=F": "SOYBEAN", "SOYB": "SOYBEAN",
    "RB=F": "GASOLINE", "UGA": "GASOLINE",
    "HO=F": "HEATING_OIL",
    "ZL=F": "SOYBEAN_OIL", "ZM=F": "SOYBEAN_MEAL",
    "KC=F": "COFFEE", "SB=F": "SUGAR", "CC=F": "COCOA", "CT=F": "COTTON",
    "LE=F": "LIVE_CATTLE", "HE=F": "LEAN_HOGS",
}


def fetch_cot_by_ticker(tickers: List[str]) -> Dict:
    """Fetch COT data keyed by TICKER symbol (not product name)."""
    try:
        from engines.cftc_cot_scraper import get_cot
    except Exception as e:
        logger.warning(f"CFTC scraper import failed: {e}")
        return {}

    out = {}
    # Build reverse: which products do we need + which tickers map to them
    needed = {}  # product → [tickers]
    for t in tickers:
        prod = COT_TICKER_MAP.get(t) or COT_TICKER_MAP.get(t.upper())
        if prod:
            needed.setdefault(prod, []).append(t)

    for prod, ticker_list in needed.items():
        try:
            cot = get_cot(prod)
            if cot:
                # Normalize fields
                normalized = {
                    "noncomm_net": cot.get("noncomm_net") or cot.get("non_commercial_net") or cot.get("net_position"),
                    "noncomm_change_wow": cot.get("noncomm_change") or cot.get("change_net") or cot.get("week_change"),
                    "commercial_net": cot.get("comm_net") or cot.get("commercial_net"),
                    "extreme_position": cot.get("extreme") or cot.get("at_extreme", False),
                    "product": prod,
                    "source": "cftc",
                }
                # Key by EACH ticker that maps to this product
                for t in ticker_list:
                    out[t] = normalized
        except Exception as e:
            logger.debug(f"COT {prod}: {e}")
            continue

    logger.info(f"live_data: COT fetched for {len(out)} tickers")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# SCRAPED DATA CONNECTOR — reads JSON pushed by the Hermes agent (or local scraper)
# ═══════════════════════════════════════════════════════════════════════════

def load_scraped_data(github_raw_url: str = None, local_path: str = None) -> Dict:
    """Load market data scraped by the Hermes agent / local browser scraper.

    The agent writes scraped_market_data.json and pushes to GitHub. This reads it
    and returns {ticker: {gex, call_wall, put_wall, max_pain, oi_by_strike, ...}}.
    Merged into snap['options_data'] so the dashboard shows real barchart/CME/laevitas
    data for tickers that yfinance can't cover (futures OI, crypto Deribit GEX, etc).

    Priority: local_path (if exists) → github_raw_url → empty.
    """
    import json, os
    # Default GitHub raw URL — point this at YOUR repo's scraped_market_data.json
    if github_raw_url is None:
        github_raw_url = "https://raw.githubusercontent.com/edgani/tes/main/scraped_market_data.json"

    # 1) Local file (if scraper runs on same box as dashboard)
    if local_path and os.path.exists(local_path):
        try:
            with open(local_path) as f:
                payload = json.load(f)
            return payload.get("data", {})
        except Exception as e:
            logger.debug(f"scraped local read failed: {e}")

    # 2) GitHub raw (agent pushes here)
    try:
        import urllib.request
        req = urllib.request.Request(github_raw_url, headers={"User-Agent": "Mozilla/5.0"})
        payload = json.loads(urllib.request.urlopen(req, timeout=10).read())
        data = payload.get("data", {})
        logger.info(f"live_data: loaded scraped data for {len(data)} tickers from GitHub")
        return data
    except Exception as e:
        logger.debug(f"scraped GitHub read failed (file may not exist yet): {e}")
        return {}


def fetch_finra_short_volume(tickers: List[str], lookback_days: int = 5) -> Dict:
    """Fetch FINRA Daily Short Sale Volume.

    This is an aggregate short-volume dataset, not individual dark-pool prints, not short interest,
    and not sufficient to infer accumulation/distribution. It is retained only as a descriptive
    market-microstructure input and is never promoted as institutional intent.
    """
    import urllib.request
    want = {t.upper() for t in tickers if not any(s in t.upper() for s in [".JK", "=X", "=F", "-USD", "^"])}
    if not want:
        return {}
    out: Dict[str, Dict] = {}
    today = dt.date.today()
    for back in range(1, lookback_days + 2):  # files publish with a delay; skip weekends implicitly
        d = today - dt.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        url = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d.strftime('%Y%m%d')}.txt"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "ignore")
        except Exception:
            continue
        lines = raw.strip().split("\n")
        if len(lines) < 2:
            continue
        for ln in lines[1:]:
            parts = ln.split("|")
            if len(parts) < 5:
                continue
            sym = parts[1].strip().upper()
            if sym not in want:
                continue
            try:
                sv = float(parts[2]); tv = float(parts[4])
            except Exception:
                continue
            if tv <= 0:
                continue
            out[sym] = {
                "short_volume": sv, "total_volume": tv,
                "short_pct": round(sv / tv * 100, 1), "date": parts[0].strip(),
            }
        if out:
            logger.info(f"FINRA short-vol: {len(out)} tickers from {d.isoformat()}")
            break  # got a valid day
    return out


def attach_finra_signal(finra: Dict, prices: Dict) -> Dict:
    """Attach descriptive price context without inferring institutional intent."""
    for sym, d in finra.items():
        ser = prices.get(sym)
        chg = None
        try:
            if ser is not None and len(ser) > 6:
                chg = (float(ser.iloc[-1]) / float(ser.iloc[-6]) - 1) * 100
        except Exception:
            pass
        sp = d.get("short_pct")
        d["signal"] = "DESCRIPTIVE_ONLY"
        d["price_change_5d_pct"] = round(chg, 2) if chg is not None else None
        d["note"] = (
            f"FINRA short-volume ratio {sp:.1f}%" if sp is not None else "FINRA short-volume available"
        ) + "; not accumulation/distribution evidence."
        d["data_semantics"] = "AGGREGATE_SHORT_VOLUME_NOT_DARK_POOL_PRINT_OR_SHORT_INTEREST"
    return finra


def fetch_flashalpha_gex(tickers: List[str], api_key: str = None, max_calls: int = 5) -> Dict:
    """Optional third-party pre-computed gamma fields.

    Provider output is preserved but War Room does not claim it observes dealer inventory. Credentials,
    entitlements and provider methodology must be verified independently.
    """
    import os
    key = api_key or os.environ.get("FLASHALPHA_KEY") or os.environ.get("FLASHALPHA_API_KEY")
    if not key:
        return {}
    try:
        from flashalpha import FlashAlpha
    except Exception:
        logger.debug("flashalpha package not installed (pip install flashalpha)")
        return {}
    fa = FlashAlpha(key)
    out: Dict[str, Dict] = {}
    for t in [x for x in tickers if not any(s in x.upper() for s in [".JK", "=X", "=F", "-USD", "^"])][:max_calls]:
        try:
            g = fa.gex(t)
            out[t] = {
                "net_gex": g.get("net_gex") or g.get("total_gex"),
                "gamma_flip": g.get("gamma_flip"),
                "call_wall": g.get("call_wall"),
                "put_wall": g.get("put_wall"),
                "dealer_regime": g.get("dealer_regime") or g.get("regime"),
                "source": "flashalpha",
                "data_semantics": "THIRD_PARTY_MODEL_OUTPUT_NOT_OBSERVED_DEALER_BOOK",
            }
        except Exception as e:
            logger.debug(f"flashalpha {t}: {e}")
            continue
    if out:
        logger.info(f"FlashAlpha GEX: {len(out)} tickers (real, free tier)")
    return out
