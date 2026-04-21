"""orchestration/build_snapshot.py — Fixed for repo signature"""
from __future__ import annotations
from typing import Dict

from data.fred_loader import load_fred_bundle
from data.price_loader import load_price_bundle
from features.macro_features import build_macro_features
from engines.quad_state_engine import QuadStateEngine
from engines.narrative_discovery_engine import NarrativeDiscoveryEngine
from engines.adaptive_bottleneck_engine import AdaptiveBottleneckEngine
from data.narrative_news_loader import load_narrative_signals

# Ticker universe — synced with repo config
TICKERS = [
    # US Equities
    "SPY", "QQQ", "IWM", "TLT", "UUP", "EEM", "XLI", "XLY", "XHB", "XLU", "XLP", "XLK",
    "SMH", "XLE", "XLB", "XLV", "XLF", "XLRE", "SPLV", "OXY", "FCX", "LMT", "NOC", "RTX",
    "GD", "HII", "AVAV", "NVDA", "AMD", "AVGO", "TSM", "ASML", "MRVL", "LITE", "COHR",
    "CRDO", "ALAB", "NPTN", "AAOI", "POET", "MU", "WDC", "STX", "TER", "FORM", "AMKR",
    "MKSI", "ENTG", "CCMP", "AMAT", "LRCX", "KLAC", "CIEN", "ANET", "INFN", "COMM",
    "CEG", "NNE", "SMR", "OKLO", "VST", "NRG", "URA", "CCJ", "UUUU", "LEU", "TSLA",
    "ENPH", "SEDG", "FLNC", "QS", "SLDP", "ALB", "SQM", "LLY", "NVO", "VKTX", "MRNA",
    "ISRG", "IONQ", "RGTI", "QBTS", "QUBT", "IBM", "GOOGL", "MSFT", "AMZN", "META",
    "DELL", "HPQ", "INTC", "F", "GM", "TM", "MCD", "SBUX", "PEP", "KO", "YUM", "XOM",
    "CVX", "COP", "CL=F", "GC=F", "HG=F", "SI=F", "NG=F", "BZ=F",
    # FX
    "EURUSD=X", "USDJPY=X", "AUDUSD=X", "USDIDR=X",
    # Crypto
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD",
    # IHSG
    "ADRO.JK", "PTBA.JK", "ITMG.JK", "ANTM.JK", "INCO.JK", "BBCA.JK", "BBRI.JK",
    "ASII.JK", "TLKM.JK", "IPCM.JK", "TMAS.JK", "PTDI.JK", "MNCN.JK", "KLBF.JK",
]


def build_snapshot(force_refresh: bool = False, prefer_saved: bool = False, compact_mode: bool = False) -> Dict:
    # ── Load Data ──
    fred_bundle = load_fred_bundle(force_refresh=force_refresh)
    fred = fred_bundle.get("series", {})
    fred_meta = fred_bundle.get("meta", {})

    # Price bundle WITH tickers argument (repo signature)
    price_bundle = load_price_bundle(
        tickers=TICKERS,
        force_refresh=force_refresh,
        prefer_local_history=prefer_saved,
    )
    prices = price_bundle.get("series", {})
    price_meta = price_bundle.get("meta", {})
    volumes = price_bundle.get("volumes", {}) if isinstance(price_bundle, dict) else {}

    vix_series = fred.get("VIX")
    vix_last = float(vix_series.iloc[-1]) if vix_series is not None and not vix_series.empty else 20.0

    loader_meta = {"fred": fred_meta, "prices": price_meta}

    # ── Macro Features ──
    macro = build_macro_features(fred, prices, loader_meta=loader_meta)

    # ── Quad Engine ──
    quad_engine = QuadStateEngine()
    quad = quad_engine.run(macro)

    # ── Global Quad (inline fallback) ──
    s_quad = quad.structural_quad
    m_quad = quad.monthly_quad
    global_quad = s_quad if s_quad == m_quad else s_quad

    # ── Narrative Discovery ──
    narrative_signals = load_narrative_signals()
    narr_engine = NarrativeDiscoveryEngine()
    narr_output = narr_engine.run(
        narrative_signals=narrative_signals,
        current_quad=quad.current_quad,
        monthly_quad=quad.monthly_quad,
        scenario_features={},
        use_claude=False,
    )

    # ── Adaptive Bottleneck Engine ──
    try:
        ade = AdaptiveBottleneckEngine(prices, volumes=volumes, vix=vix_last)
        adaptive_output = ade.run(current_quad=quad.current_quad)
        bottleneck_dict = {
            "active_sectors": adaptive_output.active_sectors,
            "leader_tickers": adaptive_output.leader_tickers,
            "supply_chain_chains": adaptive_output.supply_chain_chains,
            "front_run_basket": adaptive_output.front_run_basket,
            "cross_market_opportunities": adaptive_output.cross_market_opportunities,
            "summary": adaptive_output.summary,
            "discovery_method": adaptive_output.discovery_method,
        }
    except Exception as e:
        bottleneck_dict = {
            "active_sectors": [], "leader_tickers": [], "supply_chain_chains": [],
            "front_run_basket": [], "cross_market_opportunities": [],
            "summary": f"Adaptive engine error: {str(e)}", "discovery_method": "error",
        }

    # ── Regime Tickers ──
    regime_tickers = _build_regime_tickers(quad.current_quad)

    # ── Top Drivers ──
    top_drivers = _build_top_drivers(macro, quad)

    # ── Assemble ──
    snapshot = {
        "q": {
            "quad": quad.current_quad,
            "structural_quad": quad.structural_quad,
            "monthly_quad": quad.monthly_quad,
            "global_quad": global_quad,
            "next_quad": quad.next_quad,
            "confidence": quad.confidence,
            "deepness": quad.deepness,
            "duration_maturity": quad.duration_maturity,
            "flip_hazard": quad.flip_hazard,
            "divergence": quad.divergence_state,
            "operating_regime": quad.operating_regime,
            "structural_probs": quad.structural_probs,
            "monthly_probs": quad.monthly_probs,
            "g_core": quad.g_core,
            "i_core": quad.i_core,
            "p_core": quad.p_core,
            "vix_last": vix_last,
        },
        "f": macro,
        "fred_meta": fred_meta,
        "price_meta": price_meta,
        "prices": prices,
        "volumes": volumes,
        "regime_tickers": regime_tickers,
        "top_drivers": top_drivers,
        "narrative_discovery": {
            "active_narratives": [vars(n) for n in narr_output.active_narratives],
            "summary": narr_output.summary,
        },
        "bottleneck_discovery": bottleneck_dict,
        "most_hated_rally": _check_most_hated_rally(prices, macro),
        "regime_transition": _check_transition(quad, macro),
        "meta": {
            "generated_at": str(pd.Timestamp.now()),
            "schema": "v12_adaptive",
            "runtime_mode": "live",
            "loader_meta": loader_meta,
        },
    }
    return snapshot


def _build_regime_tickers(quad: str) -> Dict:
    tickers = {
        "Q1": {
            "us_longs": ["XLK", "XLY", "IWM", "QQQ", "SMH"],
            "us_shorts": ["XLU", "XLP", "TLT"],
            "ihsg_buys": ["BBCA.JK", "BBRI.JK", "ASII.JK"],
            "fx_longs": ["AUDUSD=X", "EURUSD=X"],
            "commodity_longs": ["CL=F", "HG=F"],
            "crypto_longs": ["BTC-USD", "ETH-USD"],
        },
        "Q2": {
            "us_longs": ["XLE", "XLI", "XLB", "OXY", "FCX"],
            "us_shorts": ["XLK", "XLY", "QQQ"],
            "ihsg_buys": ["ADRO.JK", "ANTM.JK", "PTBA.JK"],
            "fx_longs": ["USDJPY=X", "UUP"],
            "commodity_longs": ["CL=F", "GC=F", "URA"],
            "crypto_longs": [],
        },
        "Q3": {
            "us_longs": ["XLU", "XLP", "XLV", "TLT", "GLD"],
            "us_shorts": ["XLK", "XLY", "IWM", "SMH"],
            "ihsg_buys": ["BBCA.JK", "BBRI.JK", "TLKM.JK"],
            "fx_longs": ["USDJPY=X", "UUP"],
            "commodity_longs": ["GC=F", "SI=F"],
            "crypto_longs": [],
        },
        "Q4": {
            "us_longs": ["XLU", "XLP", "TLT", "GLD", "SPLV"],
            "us_shorts": ["XLK", "XLY", "XLI", "IWM"],
            "ihsg_buys": ["BBCA.JK", "BBRI.JK"],
            "fx_longs": ["UUP", "USDJPY=X"],
            "commodity_longs": ["GC=F", "TLT"],
            "crypto_longs": [],
        },
    }
    return tickers.get(quad, tickers["Q1"])


def _build_top_drivers(macro: Dict, quad) -> list:
    drivers = []
    if macro.get("oil_1m", 0) > 0.03:
        drivers.append({"name": "Oil Bid", "score": min(macro["oil_1m"] / 0.10, 1.0)})
    if macro.get("gold_1m", 0) > 0.02:
        drivers.append({"name": "Gold Bid", "score": min(macro["gold_1m"] / 0.08, 1.0)})
    if macro.get("dxy_1m", 0) < -0.01:
        drivers.append({"name": "Dollar Weak", "score": abs(macro["dxy_1m"]) / 0.05})
    if macro.get("slowdown_flags", 0) > 0.5:
        drivers.append({"name": "Slowdown", "score": macro["slowdown_flags"]})
    if macro.get("inflation_shock", 0) > 0.2:
        drivers.append({"name": "Inflation Shock", "score": macro["inflation_shock"]})
    return sorted(drivers, key=lambda x: x["score"], reverse=True)[:4]


def _check_most_hated_rally(prices, macro):
    spy_1m = macro.get("spy_1m", 0)
    iwm_1m = macro.get("iwm_1m", 0)
    xly_1m = macro.get("xly_1m", 0)
    clear = sum([
        1 if spy_1m > 0.02 else 0,
        1 if iwm_1m > spy_1m else 0,
        1 if xly_1m > 0.01 else 0,
        1 if macro.get("claims_13w_delta", 0) < 0 else 0,
    ])
    return {
        "clear_count": clear,
        "stage": "rally" if clear >= 3 else "monitor",
        "action": "Aggressive" if clear >= 3 else "Selective",
    }


def _check_transition(quad, macro):
    flip = quad.flip_hazard
    if flip > 0.5:
        return {
            "front_run_window": "1-2 weeks",
            "front_run_rationale": f"High flip hazard ({flip:.0%}) — regime transition likely",
            "early_warning_signals": [
                f"ISM delta: {macro.get('ism_3m_delta', 0):.2f}",
                f"Claims delta: {macro.get('claims_13w_delta', 0):.1f}",
                f"Breakeven 1m: {macro.get('breakeven_1m_delta', 0):.3f}",
            ],
        }
    return {
        "front_run_window": "—",
        "front_run_rationale": "Regime stable — no transition imminent",
        "early_warning_signals": [],
    }


import pandas as pd
