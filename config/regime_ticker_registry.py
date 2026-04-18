"""regime_ticker_registry.py

Explicit ticker maps for each regime × asset class.
Organized by quad (structural) and route overlay (tactical).

Each entry has:
  - long:  best instruments to own in this regime
  - short: best instruments to fade in this regime  
  - front_run: highest-conviction front-run instruments (enter BEFORE regime is confirmed)
  - watch: instruments that CONFIRM the regime is real (don't own, just observe)
  - rationale: why

For IHSG: buy_only (no short in Indonesian retail context).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# US EQUITIES — Long + Short per Quad
# ---------------------------------------------------------------------------

US_TICKERS: dict[str, dict] = {

    "Q1": {  # Growth ↑, Inflation ↓ — BEST risk-on environment
        "long": {
            "etfs": ["QQQ", "IWM", "RSP", "XLK", "XLY", "XLC", "VUG", "SPHB"],
            "stocks": [
                "NVDA", "MSFT", "META", "GOOGL", "AMZN",  # mega-cap growth
                "AVGO", "AMD", "AMAT", "KLAC", "LRCX",    # semis (growth proxy)
                "NOW", "CRM", "ADBE", "INTU", "PANW",      # software
                "JPM", "GS", "MS", "BX", "KKR",            # financials (credit expanding)
                "UBER", "BKNG", "CMG",                     # consumer discretionary
                "PLTR", "RDDT", "ARM",                     # momentum/growth
            ],
            "rationale": "Risk-on broadening. Small caps, equal weight, growth stocks all bid. Financials benefit from steepening yield curve.",
        },
        "short": {
            "etfs": ["UUP", "GLD", "XLU", "SPLV"],        # dollar, gold, defensives underperform
            "stocks": [
                "KO", "PG", "JNJ", "PEP",                 # staples — drag in risk-on
                "NEE", "DUK", "SO",                        # utilities — rate-sensitive, underperform
            ],
            "rationale": "Safe havens and defensives lag badly in Q1. Dollar weakens as risk appetite opens.",
        },
        "front_run": {
            "etfs": ["IWM", "RSP", "SPHB"],               # small caps front-run Q1 by 2-4 weeks
            "stocks": ["JPM", "GS", "IWM"],                # financials confirm credit expansion early
            "signal": "Buy IWM/RSP when growth_momentum turns positive + claims trend down + ISM > 49",
        },
        "watch": ["TLT", "HYG", "XBI"],                   # TLT falling = growth confirmed; HYG tightening = credit ok
    },

    "Q2": {  # Growth ↑, Inflation ↑ — COMMODITY BULL, equity rotation into cyclicals
        "long": {
            "etfs": ["XLE", "XLB", "XLI", "GLD", "DBC", "DBA", "OIH", "PDBC", "DBB"],
            "stocks": [
                "XOM", "CVX", "COP", "OXY", "EOG", "SLB",  # energy — core Q2 trade
                "DVN", "MPC", "PSX", "VLO", "HES",          # energy midstream/refining
                "FCX", "CLF", "NEM", "GOLD", "AA",          # materials — copper, gold miners
                "CAT", "DE", "EMR", "GE", "HON",            # industrials
                "BA", "RTX", "LMT", "NOC",                  # defense — geopolitical + inflation
                "MS", "GS", "JPM",                          # financials — spreads widen
            ],
            "rationale": "Commodities, energy, materials are the regime. Cyclicals outperform. Gold bid as inflation hedge. Financials benefit from wider spreads.",
        },
        "short": {
            "etfs": ["TLT", "IEF", "QUAL", "USMV"],       # duration DESTROYED in Q2
            "stocks": [
                "MSFT", "AAPL", "GOOGL",                   # big tech — multiple compression as rates rise
                "TSLA", "ARKK",                            # high-duration growth — worst performers
                "KO", "PG", "JNJ",                         # staples — underperform vs cyclicals
            ],
            "rationale": "Rates rising = duration compression. Tech/growth multiples contract. Staples lose relative.",
        },
        "front_run": {
            "etfs": ["XLE", "OIH", "DBB"],                 # energy and base metals lead by 3-6 weeks
            "stocks": ["XOM", "CVX", "FCX", "CAT"],        # early movers in commodity cycle
            "signal": "Long XLE when oil_3m > 5% + breakevens rising + ISM still above 52",
        },
        "watch": ["UUP", "TLT", "HYG"],                   # dollar bid = Q2 confirmed; TLT breaking = bonds pricing inflation
    },

    "Q3": {  # Growth ↓, Inflation ↑ — STAGFLATION — worst for most assets
        "long": {
            "etfs": ["GLD", "SLV", "USO", "XLE", "BIL", "PDBC"],   # gold, energy, cash
            "stocks": [
                "XOM", "CVX", "COP",                       # energy still works if supply shock persists
                "NEM", "GOLD", "WPM",                      # gold miners
                "LMT", "RTX", "NOC",                       # defense (geopolitical = Q3 trigger)
                "WMT", "COST",                             # consumer staples that can pass through inflation
            ],
            "rationale": "Only hard assets, energy, and cash work in stagflation. Defensive positioning. Minimize equity exposure overall.",
        },
        "short": {
            "etfs": ["QQQ", "IWM", "XLY", "SPY", "TLT", "HYG"],   # everything except commodities
            "stocks": [
                "TSLA", "ARKK", "AMD", "META",             # high-beta growth — crushed
                "AMZN", "HD", "TGT",                       # consumer discretionary — demand destruction
                "HOOD", "COIN", "MSTR",                    # speculative — massive downside
                "BA", "UBER",                              # capex-heavy cyclicals
            ],
            "rationale": "Stagflation destroys equity valuations. Growth stocks hurt by rates. Consumer hurt by inflation. Small caps especially vulnerable.",
        },
        "front_run": {
            "etfs": ["GLD", "BIL", "SLV"],                # gold front-runs Q3 by 4-8 weeks
            "stocks": ["NEM", "WPM", "LMT"],              # gold miners and defense early movers
            "signal": "Long GLD when ISM < 50 + oil still >5% + breakevens above 2.8% + growth_momentum negative",
        },
        "watch": ["HYG", "JNK", "IWM"],                   # credit spreading = Q3 confirmed; IWM breaking = economy rolling over
    },

    "Q4": {  # Growth ↓, Inflation ↓ — DEFLATION RISK, duration works, defensives hold
        "long": {
            "etfs": ["TLT", "IEF", "GLD", "XLP", "XLV", "XLU", "QUAL"],
            "stocks": [
                "JNJ", "ABT", "UNH", "LLY",               # healthcare — defensive with pricing power
                "KO", "PG", "WMT", "COST",                # consumer staples — recession resistant
                "NEE", "DUK", "SO",                        # utilities — rate-sensitive (rates falling in Q4)
                "MSFT", "AAPL",                            # mega-cap quality holds better than small caps
                "BRK-B",                                   # Berkshire — quality + cash buffer
            ],
            "rationale": "Deflation risk = buy duration. Defensive sectors hold. Quality outperforms. Safe haven bid. Avoid cyclicals and growth until Q4 transitions to Q1.",
        },
        "short": {
            "etfs": ["XLE", "XLB", "XLI", "IWM", "DBC", "HYG"],
            "stocks": [
                "XOM", "CVX",                              # energy — demand destruction in Q4
                "FCX", "CLF", "AA",                        # base metals — recessionary demand destruction
                "CAT", "DE",                               # industrials — capex cycle rolls over
                "COIN", "MSTR", "HOOD",                    # speculative — risk off
            ],
            "rationale": "Commodities, cyclicals, and credit-sensitive instruments all underperform in Q4 deflationary episode.",
        },
        "front_run": {
            "etfs": ["TLT", "XLP", "GLD"],                # bonds and defensives lead by 4-8 weeks
            "stocks": ["JNJ", "KO", "LLY", "MSFT"],       # quality defensives rotate in early
            "signal": "Long TLT when growth_momentum negative + ISM < 50 + oil rolling over + breakevens falling",
        },
        "watch": ["HYG", "JNK", "SPY"],                   # HYG spread tightening = Q4 might transition to Q1; SPY finding floor = pivot approaching
    },
}


# ---------------------------------------------------------------------------
# IHSG — Buy Only, per Quad
# ---------------------------------------------------------------------------

IHSG_TICKERS: dict[str, dict] = {

    "Q1": {  # Global risk-on, IDR appreciates, EM inflows
        "buy": {
            "core": ["BBCA.JK", "BMRI.JK", "BBRI.JK", "TLKM.JK", "ASII.JK"],
            "tactical": [
                "BRIS.JK", "BBNI.JK", "NISP.JK",          # banking — EM inflows boost IHSG banks
                "EXCL.JK", "ISAT.JK",                      # telco — domestic consumption recovery
                "JSMR.JK", "BSDE.JK", "CTRA.JK",          # infrastructure/property — rates ease signal
                "AMRT.JK", "ACES.JK", "MAPI.JK",          # consumer cyclical — spending recovers
            ],
            "rationale": "Q1 = EM inflows into IHSG. Banks, telco, and consumer cyclicals lead. IDR appreciating helps domestic demand. Avoid commodities — global inflation not the story here.",
        },
        "reduce": ["ADRO.JK", "PTBA.JK", "INCO.JK"],     # coal/metals lag in Q1 global disinflation
        "front_run": {
            "tickers": ["BBCA.JK", "BMRI.JK", "ASII.JK"],
            "signal": "Buy IHSG banks when IDR stabilizes + foreign net buy turns positive + VIX < 20",
        },
    },

    "Q2": {  # Global commodity bull — IHSG coal/metal exporters WIN
        "buy": {
            "core": [
                "ADRO.JK", "PTBA.JK", "ITMG.JK",          # coal — primary Q2 beneficiary
                "HRUM.JK", "INDY.JK", "AADI.JK",          # coal mid/small
                "INCO.JK", "ANTM.JK", "MDKA.JK",          # nickel/gold/copper
                "TINS.JK", "BUMI.JK",                     # tin/diversified mining
                "MEDC.JK", "AKRA.JK",                     # energy
            ],
            "tactical": [
                "BBCA.JK", "BMRI.JK", "BBRI.JK",          # banks still OK — growth strong
                "UNTR.JK",                                 # heavy equipment (coal fleet expansion)
            ],
            "rationale": "Q2 = commodity supercycle plays dominate IHSG. Coal exporters (ADRO, PTBA, ITMG) are the highest-conviction longs. Indonesia is a net commodity exporter. IDR benefits from terms-of-trade improvement.",
        },
        "reduce": ["ICBP.JK", "INDF.JK", "KLBF.JK"],     # consumer defensives — relative underperformers
        "front_run": {
            "tickers": ["ADRO.JK", "PTBA.JK", "INCO.JK"],
            "signal": "Buy coal names when oil_3m > 8% + Newcastle coal price bid + USDIDR below 16,000 (IDR strong)",
        },
    },

    "Q3": {  # Stagflation — IHSG split: exporters up, importers crushed
        "buy": {
            "core": [
                "ADRO.JK", "PTBA.JK", "ITMG.JK",          # coal still works (energy price shock)
                "ANTM.JK", "MDKA.JK",                     # gold — safe haven
                "ICBP.JK", "INDF.JK",                     # consumer defensive — food/staples
                "KLBF.JK", "SIDO.JK",                     # pharma/consumer staples
            ],
            "tactical": [
                "BBCA.JK",                                 # highest quality bank — hold selectively
            ],
            "rationale": "Q3 = maximum split in IHSG. Commodity exporters still work while importers and banks suffer from IDR weakness and rising inflation. Reduce broad IHSG exposure significantly.",
        },
        "reduce": [
            "BMRI.JK", "BBRI.JK", "BBNI.JK",             # banks — NIM pressure, NPL risk if IDR weakens sharply
            "ASII.JK",                                    # auto — consumer squeeze
            "BSDE.JK", "CTRA.JK",                        # property — rate sensitive
            "AMRT.JK", "MAPI.JK",                        # consumer cyclical — spending collapses
        ],
        "front_run": {
            "tickers": ["ANTM.JK", "MDKA.JK", "ADRO.JK"],
            "signal": "Rotate from banks to coal/gold when IDR > 16,200 + BI hiking cycle + oil still bid",
        },
    },

    "Q4": {  # Global growth scare — reduce IHSG broadly
        "buy": {
            "core": [
                "BBCA.JK",                                 # highest quality bank — hold small
                "ICBP.JK", "INDF.JK", "KLBF.JK",         # consumer defensive
                "TLKM.JK",                                # defensive telco
            ],
            "tactical": [],
            "rationale": "Q4 = reduce IHSG overall. Foreign outflows hurt. IDR under pressure. Only highest quality names hold value. Wait for Q4 → Q1 transition signal before adding.",
        },
        "reduce": [
            "ADRO.JK", "PTBA.JK",                        # coal — demand destruction
            "ANTM.JK", "INCO.JK",                        # metals — global recession kills demand
            "AMRT.JK", "ACES.JK",                        # consumer cyclical
            "BSDE.JK", "CTRA.JK",                        # property — credit tightening
        ],
        "front_run": {
            "tickers": ["BBCA.JK", "BMRI.JK"],           # high-quality banks front-run Q4→Q1 recovery
            "signal": "Buy BBCA/BMRI when Fed signals pivot + VIX rolls over + foreign net buy turns positive",
        },
    },
}


# ---------------------------------------------------------------------------
# FOREX — Long/Short per Quad
# ---------------------------------------------------------------------------

FX_TICKERS: dict[str, dict] = {

    "Q1": {  # Dollar weakens, EM FX rallies, risk-on pairs
        "long": {
            "pairs": ["EURUSD=X", "AUDUSD=X", "GBPUSD=X", "IDR=X"],  # dollar weakens
            "expression": "Short UUP (dollar ETF); Long EM FX basket",
            "rationale": "Q1 = dollar bear. Risk-on capital flows to EM. IDR, BRL, ZAR, INR all appreciate.",
        },
        "short": {
            "pairs": ["JPY=X", "CHF=X"],                 # carry currencies — funded in JPY, CHF
            "expression": "Long USDJPY, Long USDCHF (but these are indirect shorts)",
            "rationale": "Low-vol currencies lose as carry trades open. JPY/CHF weaken in risk-on.",
        },
        "front_run": {
            "tickers": ["EURUSD=X", "AUDUSD=X"],
            "signal": "Long AUD/EUR vs USD when growth_momentum turns positive + VIX drops below 18",
        },
    },

    "Q2": {  # Commodity FX dominates, dollar pressured but not collapsing
        "long": {
            "pairs": ["AUDUSD=X", "CAD=X", "NOK - proxy via ETF"],
            "expression": "Long AUD, CAD (oil proxy); Long BRL, NOK. Commodity FX basket.",
            "rationale": "Q2 = commodity currency supercycle. AUD (copper/iron ore), CAD (oil/gas), NOK (oil), BRL (iron ore, soybeans) all rip.",
        },
        "short": {
            "pairs": ["JPY=X", "CHF=X"],
            "expression": "Short JPY (carry funded), CHF (risk-on outflows from safe havens)",
            "rationale": "Low-yielding safe havens weaken as inflation erodes real returns and risk appetite stays open.",
        },
        "front_run": {
            "tickers": ["AUDUSD=X", "CAD=X"],
            "signal": "Long AUD/CAD when oil_3m > 8% + global PMI still > 52 + copper bid",
        },
    },

    "Q3": {  # Dollar bid, EM FX crushed — IDR most vulnerable as oil importer
        "long": {
            "pairs": ["JPY=X"],                           # safe haven
            "expression": "Long UUP (dollar), Long JPY (yen repatriation safe haven). Short USDIDR not applicable (long USDIDR = long USD vs IDR)",
            "rationale": "Q3 = dollar wrecking ball. EM current account deficit currencies get demolished (IDR, INR, TRY, ZAR). JPY safe haven bid despite inflation.",
        },
        "short": {
            "pairs": ["IDR=X", "AUDUSD=X", "EURUSD=X"],
            "expression": "Long USDIDR (IDR weakens), Short AUD (commodity demand destruction begins), Short EM FX basket",
            "rationale": "Oil importing EMs get hit by petrodollar squeeze. IDR especially vulnerable — Indonesia imports oil net.",
        },
        "front_run": {
            "tickers": ["IDR=X", "JPY=X"],
            "signal": "Hedge IDR exposure when USDIDR breaks 16,200 + oil > +12% 3m + BI behind the curve",
        },
    },

    "Q4": {  # Dollar peaks and rolls over — EM FX starts recovering
        "long": {
            "pairs": ["JPY=X", "CHF=X"],                 # early Q4 = still defensive
            "expression": "Long JPY (yen safe haven), gradually rotate to selective EM as dollar peaks",
            "rationale": "Q4 = dollar peaks as Fed pivots. JPY/CHF still hold early. Late Q4 = start buying EM FX.",
        },
        "short": {
            "pairs": ["AUDUSD=X", "CAD=X"],             # commodity FX still weak in early Q4
            "expression": "Short AUD, CAD as commodity demand destruction hits. Reverse in late Q4.",
            "rationale": "Commodity currencies lag until demand recovers. Early Q4 is still bearish for AUD/CAD.",
        },
        "front_run": {
            "tickers": ["EURUSD=X", "AUDUSD=X"],
            "signal": "Start buying EUR/AUD vs USD when Fed signals pivot + dollar index peaks + breakevens fall below 2.3%",
        },
    },
}


# ---------------------------------------------------------------------------
# COMMODITIES — Long/Short per Quad
# ---------------------------------------------------------------------------

COMMODITY_TICKERS: dict[str, dict] = {

    "Q1": {  # Growth up, inflation down — selective commodity exposure
        "long": {
            "tickers": ["HG=F", "SI=F", "PL=F"],          # copper (growth proxy), silver, platinum
            "etfs": ["DBB", "PDBC"],
            "rationale": "Q1 = base metals bid on growth narrative. Copper is the 'Dr. Copper' growth signal. Not a commodity supercycle — selective.",
        },
        "short": {
            "tickers": ["GC=F"],                          # gold underperforms in risk-on Q1
            "etfs": ["GLD", "USO"],
            "rationale": "Gold loses its bid when risk appetite is healthy. Oil only works if supply constrained.",
        },
        "front_run": {
            "tickers": ["HG=F", "DBB"],
            "signal": "Long copper when ISM new orders > 53 + China PMI > 50 + dollar weakening",
        },
    },

    "Q2": {  # ALL commodities bullish — this is the pure commodity regime
        "long": {
            "tickers": [
                "CL=F", "BZ=F",   # crude oil (WTI, Brent) — #1 Q2 commodity
                "NG=F",            # natural gas
                "HG=F",            # copper
                "GC=F", "SI=F",   # gold, silver — inflation hedge
                "ZC=F", "ZW=F", "ZS=F",  # grains (corn, wheat, soybeans) — food inflation
                "HG=F",            # copper — industrial demand
            ],
            "etfs": ["XLE", "DBC", "DBA", "DBB", "PDBC", "GLD", "SLV", "OIH"],
            "rationale": "Q2 is THE commodity regime. Energy leads. Then base metals. Then ags. Then precious. All bid — pick your expression.",
        },
        "short": {
            "tickers": [],                                # no commodity shorts in pure Q2
            "rationale": "Don't fight a commodity supercycle. In Q2, all commodities participate.",
        },
        "front_run": {
            "tickers": ["CL=F", "GC=F", "HG=F"],
            "signal": "Long crude + gold + copper when ISM > 53 + breakevens > 2.5% + supply concerns visible in headlines",
        },
    },

    "Q3": {  # Stagflation — commodity complex DIVERGES (energy/gold up, base metals down)
        "long": {
            "tickers": ["CL=F", "BZ=F", "GC=F", "SI=F"],  # energy + precious metals only
            "etfs": ["GLD", "USO", "XLE", "PDBC"],
            "rationale": "Q3 = only energy (supply shock) and gold (safe haven) work. Base metals get hit by demand destruction narrative.",
        },
        "short": {
            "tickers": ["HG=F", "ZC=F", "ZW=F"],         # copper and ags — demand destruction
            "etfs": ["DBB"],
            "rationale": "Copper is a growth proxy — if growth is falling, copper falls. This is the core Q3 trade: long oil/gold, short copper.",
        },
        "front_run": {
            "tickers": ["GC=F", "XLE"],
            "signal": "Long gold + short copper when ISM < 50 + oil still bid + yields rising = classic stagflation divergence",
        },
    },

    "Q4": {  # Deflation fear — commodities broadly bearish
        "long": {
            "tickers": ["GC=F"],                         # gold as deflation/uncertainty hedge only
            "etfs": ["GLD"],
            "rationale": "Only gold holds in Q4 as a monetary safe haven. Everything else deflationary.",
        },
        "short": {
            "tickers": ["CL=F", "HG=F", "ZC=F", "NG=F"],  # energy + base metals + ags all down
            "etfs": ["DBC", "USO", "DBB", "DBA"],
            "rationale": "Demand destruction = commodities sold. Oil is the biggest loser in Q4.",
        },
        "front_run": {
            "tickers": ["GC=F", "CL=F (short)"],
            "signal": "Short oil + long gold when ISM < 50 + claims rising + oil_1m < 0 = deflationary demand destruction confirmed",
        },
    },
}


# ---------------------------------------------------------------------------
# CRYPTO — Long/Short per Quad
# ---------------------------------------------------------------------------

CRYPTO_TICKERS: dict[str, dict] = {

    "Q1": {  # BEST crypto environment — liquidity + risk-on + growth
        "long": {
            "tier1": ["BTC-USD", "ETH-USD"],               # always core in Q1
            "tier2": ["SOL-USD", "AVAX-USD", "BNB-USD"],  # L1 performers
            "tier3": ["LINK-USD", "DOT-USD", "ATOM-USD"],  # infrastructure
            "speculative": ["ARB-USD", "OP-USD", "NEAR-USD", "APT-USD"],  # L2 beta
            "rationale": "Q1 = full risk-on. BTC leads, then ETH, then L1s, then DeFi, then alt season. Liquidity and growth narrative = perfect crypto backdrop.",
        },
        "short": {
            "tickers": [],
            "rationale": "Don't short crypto in Q1. If you must, only fade meme coins that ran 10x+ without fundamentals.",
        },
        "front_run": {
            "tickers": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "signal": "Buy BTC when Fed signals pause/cut + dollar weakens + VIX drops below 18 + growth_momentum turns positive",
        },
    },

    "Q2": {  # BTC as inflation hedge — altcoins mixed
        "long": {
            "tier1": ["BTC-USD"],                          # BTC as digital gold / inflation hedge
            "tier2": ["ETH-USD", "SOL-USD"],               # selective — not full alt season
            "avoid": ["DOGE-USD", "WIF-USD", "PEPE24478-USD"],  # meme coins — inflation kills them
            "rationale": "Q2 = BTC wins on inflation narrative. ETH/SOL hold. But alts struggle as rates rise and multiple compression hits growth assets.",
        },
        "short": {
            "tickers": ["WIF-USD", "PEPE24478-USD", "BONK-USD", "FLOKI-USD"],
            "rationale": "Meme coins and high-beta speculative altcoins are first to die when rates bite.",
        },
        "front_run": {
            "tickers": ["BTC-USD"],
            "signal": "Accumulate BTC when inflation_momentum rising + oil bid + breakevens > 2.5% = BTC inflation hedge narrative activates",
        },
    },

    "Q3": {  # WORST crypto regime — risk-off + rates rising + liquidity removed
        "long": {
            "tier1": ["BTC-USD"],                          # if anything, only BTC
            "note": "Reduce crypto exposure to minimum. Only BTC as speculative store of value.",
            "rationale": "Q3 destroys crypto. No liquidity, no growth, no risk appetite. BTC might hold some value but alts get decimated.",
        },
        "short": {
            "tier1": ["ETH-USD", "SOL-USD"],               # even ETH/SOL fall in Q3
            "tier2": ["AVAX-USD", "LINK-USD", "DOT-USD"],
            "speculative": [
                "WIF-USD", "PEPE24478-USD", "BONK-USD",  # meme coins -70% to -95%
                "ARB-USD", "OP-USD",                      # L2 beta — no bid
                "AAVE-USD", "UNI7083-USD",               # DeFi TVL collapses
                "TAO22974-USD", "FET-USD",               # AI crypto — narrative fades fast
            ],
            "rationale": "Everything except BTC gets destroyed in Q3. Short the speculative tail hard.",
        },
        "front_run": {
            "tickers": ["BTC-USD (partial short hedge)"],
            "signal": "Reduce all crypto when growth_momentum negative + VIX > 25 + ISM < 49 + tightening cycle active",
        },
    },

    "Q4": {  # Deflation fear — crypto risk-off, but BEST ENTRY POINT
        "long": {
            "note": "BEST LONG-TERM ENTRY in Q4 late stage — accumulate BTC for Q1 rally",
            "tier1": ["BTC-USD"],                          # accumulate on dips in late Q4
            "signal_to_enter": "Buy BTC when Fed pivots (signals rate cuts) + dollar peaks + Q4→Q1 transition signals fire",
            "rationale": "Q4 creates the setup for the next Q1 crypto bull. Dollar peaks, liquidity bottoms, BTC finds its floor. Accumulate in stages.",
        },
        "short": {
            "tier1": ["ETH-USD", "SOL-USD"],               # lag BTC to the bottom
            "speculative": ["WIF-USD", "PEPE24478-USD", "AVAX-USD", "ARB-USD"],
            "rationale": "Q4 = full deleveraging. Altcoins overshoot to the downside. Short early Q4, close when VIX peaks.",
        },
        "front_run": {
            "tickers": ["BTC-USD"],
            "signal": "Flip from short to long on BTC when: Fed pivot confirmed + VIX peaks + dollar index 3m return < -3% + regime_transition front_run_window = '1-2w'",
        },
    },
}


# ---------------------------------------------------------------------------
# TRANSITION-SPECIFIC FRONT-RUN TICKER LISTS
# What to buy/sell when transitioning BETWEEN quads (before confirmation)
# ---------------------------------------------------------------------------

TRANSITION_FRONT_RUN: dict[str, dict] = {

    "Q1→Q2": {
        "description": "Growth still solid, inflation starting to re-accelerate. Buy commodities BEFORE the market prices it.",
        "us_long":  ["XLE", "XLB", "FCX", "OXY", "NEM"],
        "us_short": ["TLT", "QQQ"],
        "ihsg_buy": ["ADRO.JK", "PTBA.JK", "INCO.JK"],
        "fx_long":  ["AUDUSD=X", "CAD=X"],
        "commodity_long": ["CL=F", "HG=F", "GC=F"],
        "crypto":   "Trim ETH/alts, hold BTC only",
        "signal":   "inflation_momentum turning up + oil_1m > 3% + breakeven_1m_delta > 0.05",
    },

    "Q2→Q3": {
        "description": "Growth starting to roll over while inflation stays hot. Rotate out of cyclicals into hard assets and cash.",
        "us_long":  ["GLD", "XLE", "BIL", "LMT"],
        "us_short": ["QQQ", "IWM", "XLY", "XLB"],
        "ihsg_buy": ["ANTM.JK", "KLBF.JK", "ICBP.JK"],
        "ihsg_reduce": ["AMRT.JK", "ASII.JK", "BSDE.JK"],
        "fx_long":  ["JPY=X"],
        "commodity_long": ["GC=F"],
        "commodity_short": ["HG=F"],
        "crypto":   "Exit all altcoins. Hold BTC with tight stop.",
        "signal":   "growth_momentum negative + ISM 3m_delta < -2 + inflation_level > 0.20",
    },

    "Q3→Q4": {
        "description": "Supply shock fading, inflation decelerating. Rotate from energy/gold toward duration.",
        "us_long":  ["TLT", "IEF", "XLP", "XLV", "QUAL"],
        "us_short": ["XLE", "USO"],
        "ihsg_buy": ["BBCA.JK", "ICBP.JK", "KLBF.JK"],
        "ihsg_reduce": ["ADRO.JK", "PTBA.JK"],
        "fx_long":  ["JPY=X", "CHF=X"],
        "commodity_long": ["GC=F"],
        "commodity_short": ["CL=F", "HG=F"],
        "crypto":   "Stay out or very small BTC only.",
        "signal":   "inflation_momentum < 0 + oil_1m < 0 + breakeven_1m_delta < -0.05",
    },

    "Q4→Q1": {
        "description": "THE INFLECTION — best risk-on entry in the entire cycle. Buy everything early.",
        "us_long":  ["IWM", "RSP", "QQQ", "XLK", "JPM", "GS"],
        "us_short": ["TLT (flatten duration)"],
        "ihsg_buy": ["BBCA.JK", "BMRI.JK", "BBRI.JK", "ASII.JK"],
        "fx_long":  ["EURUSD=X", "AUDUSD=X", "IDR=X"],
        "commodity_long": ["HG=F", "SI=F"],
        "crypto":   "AGGRESSIVE BUY — BTC, ETH, SOL. Largest position of the cycle.",
        "signal":   "leading_indicator_composite > 0 + ISM_3m_delta > 0 + claims falling + Fed paused/cutting + front_run_window = 'now'",
    },
}
