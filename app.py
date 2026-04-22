from regime_engine import get_regime_snapshot

@st.cache_data(ttl=300)
def _load_snapshot():
    try:
        snap = build_snapshot(force_refresh=True)
    except Exception:
        snap = {}
    
    # Auto-calculate regime (NO HARDCODE)
    regime = get_regime_snapshot()
    
    q = snap.get("q", {})
    q["quad"] = regime['quad']
    q["structural_quad"] = regime['structural_quad']
    q["monthly_quad"] = regime['monthly_quad']
    q["global_quad"] = regime['global_quad']
    q["confidence"] = regime['confidence']
    q["operating_regime"] = regime['operating_regime']
    q["growth_yoy"] = regime['growth_yoy']
    q["inflation_yoy"] = regime['inflation_yoy']
    q["policy_rate"] = regime['policy_rate']
    q["treasury_10y"] = regime['treasury_10y']
    snap["q"] = q
    
    # FRED meta update
    fred_meta = snap.get("fred_meta", {})
    fred_meta["loaded"] = regime['fred_loaded']
    fred_meta["missing"] = regime['fred_missing']
    fred_meta["api_key_present"] = bool(os.environ.get("FRED_API_KEY"))
    fred_meta["source"] = regime['source']
    snap["fred_meta"] = fred_meta
    
    # Tickers tetep dari Hedgeye attachment (ini watchlist, bukan regime)
    rt = snap.get("regime_tickers", {})
    # ... (ticker list tetep sama seperti sebelumnya)
    snap["regime_tickers"] = rt
    return snap