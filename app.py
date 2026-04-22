"""MacroRegime Pro v11.6b — Standard Ticker Format (XAUUSD, USDJPY, etc.)"""
import os
import sys
import glob
import time
import json
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

import streamlit as st

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

# Kill cache
for f in glob.glob("/tmp/fred_cache_*.pkl") + glob.glob("/tmp/price_cache_*.pkl"):
    try: os.remove(f)
    except: pass

if "FRED_API_KEY" in st.secrets:
    os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme

_inject_theme()

# =============================================================================
# ON-CHAIN ALPHA SCANNER — Multi-Chain (Free APIs Only)
# =============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ChainConfig:
    name: str
    chain_slug: str
    dune_chain_id: Optional[str] = None
    etherscan_subdomain: Optional[str] = None
    native_token: str = ""
    native_token_contract: Optional[str] = None

CHAIN_REGISTRY = {
    'ethereum': ChainConfig('Ethereum', 'Ethereum', 'ethereum', 'api.etherscan.io', 'ETH', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
    'base': ChainConfig('Base', 'Base', 'base', 'api.basescan.org', 'ETH', '0x4200000000000000000000000000000000000006'),
    'arbitrum': ChainConfig('Arbitrum', 'Arbitrum', 'arbitrum', 'api.arbiscan.io', 'ETH', '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'),
    'optimism': ChainConfig('Optimism', 'Optimism', 'optimism', 'api-optimistic.etherscan.io', 'ETH', '0x4200000000000000000000000000000000000006'),
    'solana': ChainConfig('Solana', 'Solana', 'solana', None, 'SOL', 'So11111111111111111111111111111111111111112'),
    'bittensor': ChainConfig('Bittensor', 'Bittensor', None, None, 'TAO', None),
    'avalanche': ChainConfig('Avalanche', 'Avalanche', 'avalanche', 'api.snowtrace.io', 'AVAX', '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'),
    'polygon': ChainConfig('Polygon', 'Polygon', 'polygon', 'api.polygonscan.com', 'MATIC', '0x7D1AfA7B718fb893dB30A3abc0Cfc608AaCfeBB0'),
    'bnb': ChainConfig('BNB Chain', 'BSC', 'bsc', 'api.bscscan.com', 'BNB', '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
}

class MultiChainAlphaScanner:
    def __init__(self, dune_key=None, etherscan_key=None, taostats_key=None):
        self.dune_sim_key = dune_key
        self.etherscan_key = etherscan_key
        self.taostats_key = taostats_key
        self._last_etherscan_call = 0
        self._last_dune_call = 0
        self._last_solscan_call = 0
        self.whale_threshold_usd = 50000
        self.bridge_spike_threshold = 1.15
        self.volume_spike_threshold = 3.0
        self.stablecoin_spike_threshold = 1.10

    def get_chain_macro_flow(self, chain_slug: str, lookback_days: int = 7) -> Dict:
        try:
            base = "https://api.llama.fi"
            results = {'chain': chain_slug, 'timestamp': datetime.utcnow().isoformat()}
            tvl_url = f"{base}/v2/historicalChainTvl/{chain_slug}"
            tvl_res = requests.get(tvl_url, timeout=15)
            if tvl_res.status_code == 200:
                tvl_data = tvl_res.json()
                if tvl_data:
                    latest = tvl_data[-1]
                    past = tvl_data[-min(lookback_days+1, len(tvl_data))]
                    results['tvl_now'] = latest[1]
                    results['tvl_7d_ago'] = past[1]
                    results['tvl_delta_pct'] = round((latest[1] - past[1]) / past[1] * 100, 2) if past[1] > 0 else 0
            stb_url = f"{base}/stablecoincharts/{chain_slug}"
            stb_res = requests.get(stb_url, timeout=15)
            if stb_res.status_code == 200:
                stb_data = stb_res.json()
                if stb_data:
                    latest_stb = stb_data[-1]['totalCirculatingUSD']['peggedUSD']
                    past_stb = stb_data[-min(lookback_days+1, len(stb_data))]['totalCirculatingUSD']['peggedUSD']
                    results['stablecoin_now'] = latest_stb
                    results['stablecoin_delta_pct'] = round((latest_stb - past_stb) / past_stb * 100, 2) if past_stb > 0 else 0
            vol_url = f"{base}/overview/dexs/{chain_slug}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
            vol_res = requests.get(vol_url, timeout=15)
            if vol_res.status_code == 200:
                vol_data = vol_res.json()
                if 'totalDataChart' in vol_data and vol_data['totalDataChart']:
                    vols = [x[1] for x in vol_data['totalDataChart'] if x[1]]
                    if len(vols) >= 2:
                        results['dex_volume_24h'] = vols[-1]
                        results['dex_volume_median_7d'] = np.median(vols[-7:]) if len(vols) >= 7 else np.median(vols)
                        results['dex_volume_spike'] = round(vols[-1] / results['dex_volume_median_7d'], 2) if results['dex_volume_median_7d'] > 0 else 0
            fees_url = f"{base}/overview/fees/{chain_slug}?excludeTotalDataChart=false&dataType=dailyFees"
            fees_res = requests.get(fees_url, timeout=15)
            if fees_res.status_code == 200:
                fees_data = fees_res.json()
                if 'totalDataChart' in fees_data and fees_data['totalDataChart']:
                    fees = [x[1] for x in fees_data['totalDataChart'] if x[1]]
                    if fees:
                        results['fees_24h'] = fees[-1]
                        results['fees_median_7d'] = np.median(fees[-7:]) if len(fees) >= 7 else np.median(fees)
            score = 0
            if results.get('stablecoin_delta_pct', 0) > 15: score += 40
            elif results.get('stablecoin_delta_pct', 0) > 10: score += 25
            elif results.get('stablecoin_delta_pct', 0) > 5: score += 10
            if results.get('tvl_delta_pct', 0) > 10: score += 30
            elif results.get('tvl_delta_pct', 0) > 5: score += 15
            if results.get('dex_volume_spike', 0) > 3: score += 20
            elif results.get('dex_volume_spike', 0) > 1.5: score += 10
            results['macro_score'] = min(score, 100)
            results['macro_signal'] = 'HOT' if score >= 60 else 'WARM' if score >= 35 else 'COLD'
            return results
        except Exception as e:
            logger.error(f"DeFiLlama error for {chain_slug}: {e}")
            return {'chain': chain_slug, 'error': str(e)}

    def _dune_sim_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        if not self.dune_sim_key: return None
        elapsed = time.time() - self._last_dune_call
        if elapsed < 0.21: time.sleep(0.21 - elapsed)
        try:
            base = "https://api.dune.com/api/sim"
            headers = {"X-Dune-API-Key": self.dune_sim_key}
            res = requests.get(f"{base}{endpoint}", headers=headers, params=params, timeout=15)
            self._last_dune_call = time.time()
            if res.status_code == 200: return res.json()
            else: logger.warning(f"Dune Sim error {res.status_code}: {res.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Dune Sim request failed: {e}")
            return None

    def get_token_holders_dune(self, chain: str, token_contract: str, top_n: int = 50) -> pd.DataFrame:
        data = self._dune_sim_request("/token-holders", {"chain": chain, "contract": token_contract, "limit": top_n})
        if not data or 'holders' not in data: return pd.DataFrame()
        df = pd.DataFrame(data['holders'])
        df['chain'] = chain; df['token'] = token_contract
        return df

    def _etherscan_request(self, subdomain: str, params: Dict) -> Optional[Dict]:
        if not self.etherscan_key: return None
        elapsed = time.time() - self._last_etherscan_call
        if elapsed < 0.21: time.sleep(0.21 - elapsed)
        try:
            url = f"https://{subdomain}/api"
            params['apikey'] = self.etherscan_key
            res = requests.get(url, params=params, timeout=15)
            self._last_etherscan_call = time.time()
            if res.status_code == 200:
                data = res.json()
                if data.get('status') == '1': return data
                else: logger.warning(f"Etherscan msg: {data.get('result', data.get('message'))}")
            return None
        except Exception as e:
            logger.error(f"Etherscan error: {e}")
            return None

    def get_token_balance_etherscan(self, subdomain: str, token_contract: str, wallet: str) -> float:
        data = self._etherscan_request(subdomain, {'module': 'account', 'action': 'tokenbalance', 'contractaddress': token_contract, 'address': wallet, 'tag': 'latest'})
        if data and 'result' in data: return int(data['result']) / 1e18
        return 0.0

    def get_token_transfers_etherscan(self, subdomain: str, token_contract: str, wallet: str) -> pd.DataFrame:
        data = self._etherscan_request(subdomain, {'module': 'account', 'action': 'tokentx', 'contractaddress': token_contract, 'address': wallet, 'sort': 'desc'})
        if data and isinstance(data.get('result'), list):
            df = pd.DataFrame(data['result'])
            if not df.empty and 'value' in df.columns: df['value_float'] = df['value'].astype(float) / 1e18
            return df
        return pd.DataFrame()

    def _solscan_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        elapsed = time.time() - self._last_solscan_call
        if elapsed < 0.5: time.sleep(0.5 - elapsed)
        try:
            base = "https://public-api.solscan.io"
            res = requests.get(f"{base}/{endpoint}", params=params, timeout=15)
            self._last_solscan_call = time.time()
            if res.status_code == 200: return res.json()
            return None
        except Exception as e:
            logger.error(f"Solscan error: {e}")
            return None

    def get_solana_portfolio(self, wallet: str) -> Dict:
        return self._solscan_request(f"account/portfolio", {'address': wallet}) or {}

    def _taostats_request(self, endpoint: str) -> Optional[Dict]:
        if not self.taostats_key: return None
        try:
            base = "https://api.taostats.io/api"
            headers = {"Authorization": f"Bearer {self.taostats_key}"}
            res = requests.get(f"{base}/{endpoint}", headers=headers, timeout=15)
            if res.status_code == 200: return res.json()
            return None
        except Exception as e:
            logger.error(f"TAOStats error: {e}")
            return None

    def get_bittensor_overview(self) -> Dict:
        data = self._taostats_request("network/overview")
        return data or {}

    def get_bittensor_subnet_flows(self) -> pd.DataFrame:
        data = self._taostats_request("subnets")
        if data and 'data' in data: return pd.DataFrame(data['data'])
        return pd.DataFrame()

    def scan_chain_alpha(self, chain_key: str, token_contract: Optional[str] = None, whale_wallets: Optional[List[str]] = None) -> Dict:
        config = CHAIN_REGISTRY.get(chain_key)
        if not config: return {'error': f'Chain {chain_key} not supported'}
        result = {'chain': chain_key, 'timestamp': datetime.utcnow().isoformat(), 'layers': {}}
        macro = self.get_chain_macro_flow(config.chain_slug)
        result['layers']['macro'] = macro
        whale_score = 0
        whale_data = []
        if whale_wallets and config.etherscan_subdomain and token_contract:
            for wallet in whale_wallets:
                balance = self.get_token_balance_etherscan(config.etherscan_subdomain, token_contract, wallet)
                tx_df = self.get_token_transfers_etherscan(config.etherscan_subdomain, token_contract, wallet)
                net_flow = 0
                if not tx_df.empty and 'value_float' in tx_df.columns:
                    cutoff = (datetime.utcnow() - timedelta(days=7)).timestamp()
                    recent = tx_df[tx_df['timeStamp'].astype(int) > cutoff]
                    if not recent.empty:
                        inflow = recent[recent['to'].str.lower() == wallet.lower()]['value_float'].sum()
                        outflow = recent[recent['from'].str.lower() == wallet.lower()]['value_float'].sum()
                        net_flow = inflow - outflow
                whale_data.append({'wallet': wallet, 'balance': balance, 'net_flow_7d': net_flow, 'accumulating': net_flow > 0})
            if whale_data:
                accum_count = sum(1 for w in whale_data if w['accumulating'])
                total_flow = sum(w['net_flow_7d'] for w in whale_data if w['accumulating'])
                whale_score = min((accum_count / len(whale_data) * 50) + (min(total_flow / 10000, 50)), 100)
        elif whale_wallets and chain_key == 'solana' and token_contract:
            for wallet in whale_wallets:
                portfolio = self.get_solana_portfolio(wallet)
                balance = 0
                if portfolio and 'data' in portfolio:
                    for item in portfolio['data']:
                        if item.get('tokenAddress') == token_contract:
                            balance = item.get('balance', 0) / (10 ** item.get('decimals', 9))
                whale_data.append({'wallet': wallet, 'balance': balance, 'net_flow_7d': 0, 'accumulating': False})
            whale_score = min(sum(w['balance'] for w in whale_data) / 100000 * 10, 100)
        result['layers']['whale'] = {'wallets_tracked': len(whale_wallets) if whale_wallets else 0, 'whale_data': whale_data, 'whale_score': round(whale_score, 2)}
        dune_score = 0
        if self.dune_sim_key and token_contract and config.dune_chain_id:
            try:
                holders = self.get_token_holders_dune(config.dune_chain_id, token_contract, top_n=20)
                if not holders.empty and 'balance' in holders.columns:
                    total_top20 = holders['balance'].sum()
                    dune_score = min(total_top20 / 1000000 * 5, 40)
            except Exception as e:
                logger.warning(f"Dune layer error: {e}")
        result['layers']['dune_realtime'] = {'dune_score': round(dune_score, 2)}
        tao_score = 0
        if chain_key == 'bittensor':
            overview = self.get_bittensor_overview()
            subnets = self.get_bittensor_subnet_flows()
            if overview:
                tao_score = min((overview.get('staking_ratio', 0) * 30) + (subnets.shape[0] if not subnets.empty else 0) * 2, 100)
            result['layers']['bittensor'] = {'overview': overview, 'subnet_count': subnets.shape[0] if not subnets.empty else 0, 'tao_score': round(tao_score, 2)}
        weights = {'macro': 0.35, 'whale': 0.35, 'dune': 0.20, 'tao': 0.10 if chain_key == 'bittensor' else 0}
        composite = (weights['macro'] * macro.get('macro_score', 0) + weights['whale'] * whale_score + weights['dune'] * dune_score + weights['tao'] * tao_score)
        result['composite_alpha_score'] = round(composite, 2)
        result['verdict'] = ('🔥 STRONG ACCUMULATION' if composite >= 70 else '⚡ MONITOR CLOSELY' if composite >= 45 else '❄️ PASS / WAIT')
        return result

    def scan_all_chains(self, targets: Dict[str, Dict]) -> pd.DataFrame:
        results = []
        for chain_key, config in targets.items():
            logger.info(f"Scanning {chain_key}...")
            res = self.scan_chain_alpha(chain_key, token_contract=config.get('token'), whale_wallets=config.get('wallets'))
            results.append({
                'chain': chain_key,
                'alpha_score': res.get('composite_alpha_score', 0),
                'verdict': res.get('verdict', 'N/A'),
                'macro_signal': res.get('layers', {}).get('macro', {}).get('macro_signal', 'N/A'),
                'tvl_delta': res.get('layers', {}).get('macro', {}).get('tvl_delta_pct', 0),
                'stable_delta': res.get('layers', {}).get('macro', {}).get('stablecoin_delta_pct', 0),
                'dex_spike': res.get('layers', {}).get('macro', {}).get('dex_volume_spike', 0),
                'whale_score': res.get('layers', {}).get('whale', {}).get('whale_score', 0),
                'detail': res
            })
            time.sleep(1)
        return pd.DataFrame(results)

# =============================================================================
# SNAPSHOT LOADER (Original)
# =============================================================================
@st.cache_data(ttl=300)
def _load_snapshot():
    try:
        snap = build_snapshot(force_refresh=True)
        q = snap.get("q", {})
        if q:
            q["structural_quad"] = "Q3"
            q["global_quad"] = "Q3"
            q["quad"] = "Q3"
            q["operating_regime"] = "Stagflation Persists"
            if q.get("confidence", 0) < 0.25: q["confidence"] = 0.35
            snap["q"] = q
        rt = snap.get("regime_tickers", {})
        rt["us_longs"] = ["XLU", "XLP", "XLV", "TLT", "GLD"]
        rt["us_shorts"] = ["XLK", "XLY", "IWM", "SMH"]
        rt["ihsg_buys"] = ["BBCA.JK", "BBRI.JK", "TLKM.JK"]
        rt["fx_longs"] = ["USDJPY", "UUP"]
        rt["fx_shorts"] = ["EURUSD", "AUDUSD"]
        rt["commodity_longs"] = ["XAUUSD", "XAGUSD"]
        rt["commodity_shorts"] = ["XTIUSD", "XCUUSD"]
        rt["crypto_longs"] = ["BTC-USD", "ETH-USD"]
        rt["crypto_shorts"] = ["SOL-USD"]
        snap["regime_tickers"] = rt
        return snap
    except Exception as e:
        st.error(f"Snapshot failed: {e}")
        return {
            "q": {"quad":"Q3","structural_quad":"Q3","monthly_quad":"Q2","global_quad":"Q3","confidence":0.35,"divergence":"divergent","operating_regime":"Stagflation Persists","vix_last":20.0,"structural_probs":{},"monthly_probs":{},"g_core":0,"i_core":0,"p_core":0},
            "f": {}, "fred_meta": {"loaded":0,"missing":24,"api_key_present":True},
            "regime_tickers": {"us_longs":["XLU","XLP","XLV","TLT","GLD"],"us_shorts":["XLK","XLY","IWM","SMH"],"ihsg_buys":["BBCA.JK","BBRI.JK","TLKM.JK"],"fx_longs":["USDJPY","UUP"],"fx_shorts":["EURUSD","AUDUSD"],"commodity_longs":["XAUUSD","XAGUSD"],"commodity_shorts":["XTIUSD","XCUUSD"],"crypto_longs":["BTC-USD","ETH-USD"],"crypto_shorts":["SOL-USD"]},
            "top_drivers": [], "narrative_discovery": {}, "bottleneck_discovery": {},
            "most_hated_rally": {}, "regime_transition": {}, "prices": {}
        }

snap = _load_snapshot()
q = snap.get("q", {})
f = snap.get("f", {})
quad = q.get("quad","Q3")
structural_quad = q.get("structural_quad", "Q3")
monthly_quad = q.get("monthly_quad", "Q2")
global_quad = q.get("global_quad", "Q3")
conf = q.get("confidence", 0.35)
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "Stagflation Persists")
tickers = snap.get("regime_tickers", {})
prices = snap.get("prices", {})
btl = snap.get("bottleneck_discovery", {})
narr = snap.get("narrative_discovery", {})

def _h(html): st.markdown(" ".join(html.split()), unsafe_allow_html=True)

QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qbg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[0]
def _qfg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[1]

s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
g_bg, g_fg = _qbg(global_quad), _qfg(global_quad)

# Header
_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;">v11.6b · Standard Tickers · On-Chain Alpha</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:#3fb950;">🟢 S:{structural_quad} · M:{monthly_quad} · G:{global_quad}</div>
  </div>
</div>
""")

# Regime Card
_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{structural_quad}</span>
    <span style="background:{m_bg};color:{m_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{monthly_quad}</span>
    <span style="background:{g_bg};color:{g_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{global_quad}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#f85149;font-weight:600;">{conf:.0%}</span></span>
    <span>Growth: <span style="color:#3fb950;">▲</span></span>
    <span>Inflasi: <span style="color:#f85149;">▼</span></span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">{tickers.get('us_longs',['—'])[0]}</span></span>
    <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">{tickers.get('us_shorts',['—'])[0]}</span></span>
  </div>
</div>
""")

# TABS
tabs = st.tabs(["⚡ Command Center", "🌍 Markets", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    btl = snap.get("bottleneck_discovery", {})
    narr = snap.get("narrative_discovery", {})

    def ret_n(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    def get_ret(s, n):
        r = ret_n(s, n)
        return f"{r:+.1%}" if r == r else "—"

    def ticker_card(tk, name, ret1m, ret3m, signal):
        color = "#3fb950" if signal == "long" else "#f85149" if signal == "short" else "#d29922"
        icon = "▲" if signal == "long" else "▼" if signal == "short" else "⚡"
        return f"""
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;">
          <div>
            <div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div>
            <div style="font-size:10px;color:#8b949e;">{name}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:{color};font-weight:700;">{icon} {ret1m}</div>
            <div style="font-size:9px;color:#8b949e;">3M: {ret3m}</div>
          </div>
        </div>
        """

    def render_cards(ticker_list, names_map, signal_type, per_row=2):
        if not ticker_list: return
        cards = []
        for t in ticker_list:
            s = prices.get(t)
            cards.append(ticker_card(t, names_map.get(t, t), get_ret(s, 21), get_ret(s, 63), signal_type))
        for i in range(0, len(cards), per_row):
            row = cards[i:i+per_row]
            _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    def render_heatmap(assets_list):
        if not prices: return
        heat_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for tk, name in assets_list:
            s = prices.get(tk)
            if s is not None:
                r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                c = "#1a4d2e" if r1 > 0.05 else "#2d5a3d" if r1 > 0 else "#5c1a1a" if r1 < -0.05 else "#3d1a1a" if r1 < 0 else "#2d3748"
                txt = "#4ade80" if r1 > 0 else "#f87171" if r1 < 0 else "#a0aec0"
                heat_html.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
        heat_html.append('</div>')
        _h("".join(heat_html))

    def render_market_leaders(asset_list, benchmark_tk=None, title="Market Leadership"):
        bench_ret = ret_n(prices.get(benchmark_tk), 63) if benchmark_tk else float("nan")
        rows = []
        for tk, name in asset_list:
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63)
                rel = (r3 - bench_ret) if bench_ret == bench_ret and r3 == r3 else r3
                rows.append({"name": name, "rel": rel, "tk": tk})
        if not rows:
            st.caption(f"No price data for {title}")
            return
        rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
        st.markdown(f"**📊 {title} (Top 5)**")
        for s in rows[:5]:
            rel = s["rel"]
            rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
            bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
            _h(f"""
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
              <div style="width:70px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
              <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
              </div>
              <div style="width:60px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
            </div>
            """)

    def render_sector_bars():
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 Sector Leadership (Top 5)**")
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

    def render_ihsg_sector_bars():
        SECTORS = {
            "Energy":   ["ADRO.JK", "ITMG.JK", "PTBA.JK"],
            "Finance":  ["BBCA.JK", "BBRI.JK", "BMRI.JK"],
            "Consumer": ["UNVR.JK", "INDF.JK", "ICBP.JK"],
            "Infra":    ["TLKM.JK", "PGAS.JK", "EXCL.JK"],
            "Property": ["CTRA.JK", "PWON.JK", "BSDE.JK"],
            "Mining":   ["ANTM.JK", "INCO.JK", "MDKA.JK"],
            "Health":   ["KLBF.JK", "SIDO.JK", "KAEF.JK"],
            "Agri":     ["AALI.JK", "LSIP.JK", "SGRO.JK"],
            "Industri": ["ASII.JK", "AUTO.JK", "MPMX.JK"],
        }
        jkse3 = ret_n(prices.get("^JKSE"), 63)
        sec_rows = []
        for name, proxies in SECTORS.items():
            rets = []
            for tk in proxies:
                s = prices.get(tk)
                if s is not None and len(s) > 63:
                    r = ret_n(s, 63)
                    if r == r: rets.append(r)
            if rets:
                avg = sum(rets) / len(rets)
                rel = (avg - jkse3) if jkse3 == jkse3 else avg
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 IDX Sector Leadership (Top 5)**")
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

    # ── Ticker Filter Sets ──
    FX_TICKERS = {"USDJPY", "EURUSD", "AUDUSD", "GBPUSD", "USDCAD", "USDIDR", "UUP", "DXY", "EURGBP", "EURJPY", "GBPJPY", "NZDUSD", "USDCNH", "USDCHF"}
    COMM_TICKERS = {"XAUUSD", "XAGUSD", "XTIUSD", "XBRUSD", "XCUUSD", "XNGUSD", "URA", "XPTUSD", "XPDUSD", "XALUSD", "XZNUSD", "USOIL", "UKOIL"}

    def is_us_ticker(tk):
        return not any(x in tk for x in [".JK", "-USD"]) and tk not in ["^JKSE"] and tk not in FX_TICKERS and tk not in COMM_TICKERS
    def is_ihsg_ticker(tk):
        return ".JK" in tk or tk == "^JKSE"
    def is_fx_ticker(tk):
        return tk in FX_TICKERS
    def is_comm_ticker(tk):
        return tk in COMM_TICKERS
    def is_crypto_ticker(tk):
        return "-USD" in tk

    def render_bottleneck_filtered(filter_fn, market_name):
        if not btl:
            st.caption("No bottleneck data")
            return
        if btl.get("summary"): st.caption(btl["summary"])
        basket = btl.get("front_run_basket", [])
        total = len(basket)
        filtered = [item for item in basket if filter_fn(item.get("ticker", ""))]
        if not filtered:
            st.caption(f"No {market_name} bottleneck detected — adaptive scan returned {total} candidate(s), none matched {market_name} ticker patterns.")
            return
        b_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for item in filtered[:8]:
            tk = item.get("ticker","—")
            sec = item.get("sector","—")[:10]
            score = item.get("bottleneck_score",0)
            stage = item.get("stage","—")
            stage_c = {"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stage, "#8b949e")
            b_html.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:9px;color:#8b949e;">{sec}</div><div style="font-size:10px;color:{stage_c};">{stage} · {score:.2f}</div></div>')
        b_html.append('</div>')
        _h("".join(b_html))

    def render_master_filtered(long_key, short_key, color_long, color_short, filter_fn, market_name):
        all_tickers = []
        for t in tickers.get(long_key, [])[:4]:
            all_tickers.append((t, "Long", color_long))
        if short_key:
            for t in tickers.get(short_key, [])[:4]:
                all_tickers.append((t, "Short", color_short))
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:6]:
                tk = item.get("ticker","—")
                if filter_fn(tk) and tk not in [x[0] for x in all_tickers]:
                    all_tickers.append((tk, "Adap", "#58a6ff"))
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:3]:
                for b in n.get("primary_beneficiaries", [])[:3]:
                    if filter_fn(b) and b not in [x[0] for x in all_tickers]:
                        all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))
        else:
            st.caption(f"No {market_name} tickers")

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(us_longs, names, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(us_shorts, names, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("XTIUSD","Oil"),("UUP","USD")])
        render_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_us_ticker, "US")
        st.markdown("**📋 Master Board**")
        render_master_filtered("us_longs", "us_shorts", "#3fb950", "#f85149", is_us_ticker, "US")

    # ══════ 🇮🇩 IHSG (Long Only) ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
        st.markdown("**📍 NOW — LONG**")
        render_cards(ihsg_longs, names_ihsg, "long", 3)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        render_ihsg_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_ihsg_ticker, "IHSG")
        st.markdown("**📋 Master Board**")
        render_master_filtered("ihsg_buys", None, "#fb923c", "#f85149", is_ihsg_ticker, "IHSG")

    # ══════ 💱 FX (Long + Short) ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fx_shorts = tickers.get("fx_shorts", [])
        names_fx = {"EURUSD":"EUR/USD","USDJPY":"USD/JPY","AUDUSD":"AUD/USD","USDIDR":"USD/IDR","UUP":"DXY","GBPUSD":"GBP/USD","USDCAD":"USD/CAD","NZDUSD":"NZD/USD","USDCHF":"USD/CHF"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(fx_longs, names_fx, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(fx_shorts, names_fx, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("EURUSD","EUR/USD"),("USDJPY","USD/JPY"),("AUDUSD","AUD/USD"),("USDIDR","USD/IDR"),("UUP","DXY")])
        render_market_leaders([("UUP","DXY"),("USDJPY","USD/JPY"),("EURUSD","EUR/USD"),("AUDUSD","AUD/USD"),("GBPUSD","GBP/USD"),("USDCAD","USD/CAD")], benchmark_tk="UUP", title="FX Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_fx_ticker, "FX")
        st.markdown("**📋 Master Board**")
        render_master_filtered("fx_longs", "fx_shorts", "#58a6ff", "#f85149", is_fx_ticker, "FX")

    # ══════ 🛢️ COMMODITIES (Long + Short) ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        comm_shorts = tickers.get("commodity_shorts", [])
        names_comm = {"XTIUSD":"WTI Oil","XAUUSD":"Gold","XCUUSD":"Copper","XAGUSD":"Silver","XNGUSD":"Nat Gas","XBRUSD":"Brent","URA":"Uranium"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(comm_longs, names_comm, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(comm_shorts, names_comm, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("XTIUSD","WTI Oil"),("XAUUSD","Gold"),("XCUUSD","Copper"),("XAGUSD","Silver"),("XNGUSD","Nat Gas")])
        render_market_leaders([("XAUUSD","Gold"),("XTIUSD","WTI Oil"),("XCUUSD","Copper"),("XAGUSD","Silver"),("XNGUSD","Nat Gas"),("XBRUSD","Brent"),("URA","Uranium")], benchmark_tk="XAUUSD", title="Commodity Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_comm_ticker, "Commodities")
        st.markdown("**📋 Master Board**")
        render_master_filtered("commodity_longs", "commodity_shorts", "#fb923c", "#f85149", is_comm_ticker, "Commodities")

    # ══════ 🔐 CRYPTO (Long + Short + On-Chain Alpha Auto-Scan) ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        cry_shorts = tickers.get("crypto_shorts", [])
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(cry_longs, names_cry, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(cry_shorts, names_cry, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        render_market_leaders([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot")], benchmark_tk="BTC-USD", title="Crypto Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_crypto_ticker, "Crypto")
        st.markdown("**📋 Master Board**")
        render_master_filtered("crypto_longs", "crypto_shorts", "#a371f7", "#f85149", is_crypto_ticker, "Crypto")

        # ═══════════════════════════════════════════════════════════════════════
        # ON-CHAIN ALPHA — AUTO SCAN (Integrated into Crypto Tab)
        # ═══════════════════════════════════════════════════════════════════════
        st.divider()
        st.markdown("**⛓️ On-Chain Alpha — Auto Scan**")
        st.caption("Multi-chain accumulation detection · Runs automatically when you open this tab")

        # API keys dari secrets atau kosong (DeFiLlama works tanpa key)
        dune_key = st.secrets.get("DUNE_SIM_KEY", "")
        etherscan_key = st.secrets.get("ETHERSCAN_KEY", "")
        taostats_key = st.secrets.get("TAOSTATS_KEY", "")

        with st.expander("🔑 API Keys (simpan di secrets.toml untuk auto-run)", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1: dune_input = st.text_input("Dune Sim", value=dune_key, type="password", key="dune_crypto")
            with c2: eth_input = st.text_input("Etherscan", value=etherscan_key, type="password", key="eth_crypto")
            with c3: tao_input = st.text_input("TAOStats", value=taostats_key, type="password", key="tao_crypto")

        # Override dengan input manual kalo user isi
        if dune_input: dune_key = dune_input
        if eth_input: etherscan_key = eth_input
        if tao_input: taostats_key = tao_input

        scanner = MultiChainAlphaScanner(dune_key=dune_key, etherscan_key=etherscan_key, taostats_key=taostats_key)

        # Auto-run targets: chains yang paling relevant untuk crypto narrative
        crypto_targets = {
            'base': {'token': '0x4200000000000000000000000000000000000006', 'wallets': []},
            'solana': {'token': 'So11111111111111111111111111111111111111112', 'wallets': []},
            'bittensor': {'token': None, 'wallets': []},
            'ethereum': {'token': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'wallets': []},
        }

        # Auto-run dengan spinner
        with st.spinner("⛓️ Scanning on-chain flows (Base, Solana, Bittensor, Ethereum)... ⏳ ~30s"):
            df_crypto = scanner.scan_all_chains(crypto_targets)

        if not df_crypto.empty:
            # Summary counters
            hot = df_crypto[df_crypto['alpha_score'] >= 60]
            warm = df_crypto[(df_crypto['alpha_score'] >= 40) & (df_crypto['alpha_score'] < 60)]
            cold = df_crypto[df_crypto['alpha_score'] < 40]

            cols = st.columns(3)
            with cols[0]:
                _h(f'<div style="background:#1a4d2e;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#4ade80;">{len(hot)}</div><div style="font-size:10px;color:#8b949e;">🔥 HOT</div></div>')
            with cols[1]:
                _h(f'<div style="background:#5c3d00;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#fbbf24;">{len(warm)}</div><div style="font-size:10px;color:#8b949e;">⚡ WARM</div></div>')
            with cols[2]:
                _h(f'<div style="background:#5c1a1a;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#f87171;">{len(cold)}</div><div style="font-size:10px;color:#8b949e;">❄️ COLD</div></div>')

            # Per-chain cards
            for _, row in df_crypto.iterrows():
                ch = row['chain']
                score = row['alpha_score']
                verdict = row['verdict']
                macro_sig = row['macro_signal']
                tvl_d = row['tvl_delta']
                stable_d = row['stable_delta']
                dex_spike = row['dex_spike']
                whale_s = row['whale_score']

                score_color = "#4ade80" if score >= 70 else "#fbbf24" if score >= 45 else "#f87171"
                score_bg = "#1a4d2e" if score >= 70 else "#5c3d00" if score >= 45 else "#5c1a1a"

                _h(f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:8px;">
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                      <div style="background:{score_bg};color:{score_color};padding:3px 10px;border-radius:16px;font-size:11px;font-weight:700;">{ch.upper()}</div>
                      <div style="font-size:13px;font-weight:700;color:#e6edf3;">{verdict}</div>
                    </div>
                    <div style="font-size:18px;font-weight:800;color:{score_color};">{score:.0f}<span style="font-size:10px;color:#8b949e;">/100</span></div>
                  </div>
                  <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:10px;color:#c9d1d9;">
                    <span>📊 Macro: <span style="color:#fb923c;font-weight:600;">{macro_sig}</span></span>
                    <span>📈 TVL: <span style="color:#3fb950;font-weight:600;">{tvl_d:+.1f}%</span></span>
                    <span>💰 Stable: <span style="color:#3fb950;font-weight:600;">{stable_d:+.1f}%</span></span>
                    <span>🌊 DEX: <span style="color:#58a6ff;font-weight:600;">{dex_spike:.1f}x</span></span>
                    <span>🐋 Whale: <span style="color:#a371f7;font-weight:600;">{whale_s:.0f}</span></span>
                  </div>
                </div>
                """)

            # Legend
            st.caption("📊 Stable Δ = dry powder · 📈 TVL Δ = smart money deposit · 🌊 DEX = momentum · 🐋 Whale = accumulation")
        else:
            st.info("On-chain scan returned no data — check API keys or network connectivity.")

with tabs[2]:
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw: st.markdown("**Regime State**"); st.json(q)
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {}); m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(k, 0.0); mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad; is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else: st.info("No probability data")

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0); missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else: st.error("FRED metadata unavailable")
    
    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()