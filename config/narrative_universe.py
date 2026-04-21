"""narrative_universe.py

Maps NARRATIVE THEMES → specific tickers + activation conditions.

A narrative is a market-moving story that:
1. Has a legitimate underlying thesis (not pure pump)
2. Has an identifiable catalyst type that activates it
3. Maps to specific beneficiary tickers
4. Has a regime alignment (which quad amplifies or suppresses it)
5. Has a stage (early / building / mature / exhausted)

The XNDU pattern: Google admits superconducting limits → photonic quantum thesis
validated → Xanadu as beneficiary → buy BEFORE market prices it.

This file defines the universe of tradeable narratives the system can detect.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class NarrativeTemplate:
    name: str
    description: str
    category: str                    # technology | geopolitical | policy | commodity | cycle | disruption
    catalyst_types: List[str]        # what kind of event activates this narrative
    activation_keywords: List[str]   # keywords in news that signal this narrative is live
    invalidation_keywords: List[str] # keywords that kill or reverse this narrative
    beneficiaries: Dict[str, List[str]]  # {market: [tickers]}
    fades: Dict[str, List[str]]          # {market: [tickers that LOSE from this narrative]}
    regime_alignment: Dict[str, float]   # {quad: multiplier} — which quad amplifies this
    typical_duration_weeks: int
    conviction_ceiling: float        # max conviction this narrative can reach (0-1)
    # pump_risk: 0=pure fundamental thesis, 1=pure narrative/momentum with no earnings
    pump_risk: float
    confirmation_signals: List[str]  # what market data confirms narrative is real


_NARRATIVE_LIBRARY: List[NarrativeTemplate] = [

    # -----------------------------------------------------------------------
    # TECHNOLOGY DISRUPTION NARRATIVES
    # -----------------------------------------------------------------------
    NarrativeTemplate(
        name="Quantum Photonics Disruption",
        description="Superconducting quantum hits scaling wall → photonic quantum companies gain credibility and institutional interest. Pattern: dominant player admits limitation → challenger benefits.",
        category="technology",
        catalyst_types=["competitor_admission", "government_contract", "research_breakthrough", "partnership_announcement"],
        activation_keywords=["photonic", "quantum photon", "superconducting cannot scale", "room temperature quantum", "xanadu", "ionq photonic", "darpa quantum", "imec quantum"],
        invalidation_keywords=["superconducting milestone", "google quantum supremacy", "ibm quantum record", "photonic decoherence"],
        beneficiaries={
            "us": ["IONQ", "QUBT", "RGTI", "QBTS"],   # listed quantum plays
            "watchlist": ["XNDU"],                      # OTC / pre-listing
        },
        fades={"us": ["IBM", "GOOGL"]},               # superconducting incumbents relatively
        regime_alignment={"Q1": 1.30, "Q2": 1.10, "Q3": 0.60, "Q4": 0.50},
        typical_duration_weeks=8,
        conviction_ceiling=0.65,
        pump_risk=0.55,                                # thesis real but early stage → moderate pump risk
        confirmation_signals=["unusual_volume_ionq_qubt", "institutional_filing_increase", "additional_darpa_contracts"],
    ),

    NarrativeTemplate(
        name="AI Chip Supply Constraint",
        description="Demand for AI compute exceeds supply → pricing power and margin expansion for chip designers and equipment. NVDA-led but benefits entire stack.",
        category="technology",
        catalyst_types=["earnings_beat", "hyperscaler_capex_raise", "supply_bottleneck", "government_restriction"],
        activation_keywords=["ai chip demand", "gpu shortage", "h100", "blackwell", "cuda", "ai infrastructure", "hyperscaler capex", "data center build", "nvda earnings"],
        invalidation_keywords=["ai bubble", "capex slowdown", "nvidia competitor", "custom chip", "huawei chip"],
        beneficiaries={
            "us": ["NVDA", "AVGO", "AMD", "AMAT", "KLAC", "LRCX", "ASML", "TSM", "ARM", "SMCI"],
            "etfs": ["SOXX", "SMH"],
        },
        fades={"us": ["INTC", "QCOM"]},
        regime_alignment={"Q1": 1.40, "Q2": 1.20, "Q3": 0.75, "Q4": 0.60},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.25,                                # strong fundamental basis
        confirmation_signals=["nvda_revenue_beat", "hyperscaler_capex_guidance_up", "smh_relative_strength"],
    ),

    NarrativeTemplate(
        name="Nuclear Energy Renaissance",
        description="AI data center electricity demand + carbon goals → nuclear the only viable baseload. SMRs and existing plants get re-rated.",
        category="technology",
        catalyst_types=["government_contract", "tech_company_deal", "regulatory_approval", "plant_restart"],
        activation_keywords=["nuclear power", "smr", "small modular reactor", "data center nuclear", "microsoft nuclear", "amazon nuclear", "constellation energy", "oklo", "nuscale", "kairos"],
        invalidation_keywords=["nuclear accident", "reactor shutdown", "nuclear waste problem", "solar cheaper", "wind cheaper"],
        beneficiaries={
            "us": ["CEG", "NNE", "SMR", "OKLO", "UUUU", "UEC", "CCJ"],   # uranium too
            "etfs": ["URA", "NLR"],
        },
        fades={"us": ["FSLR", "ENPH"]},              # solar loses relative
        regime_alignment={"Q1": 1.20, "Q2": 1.30, "Q3": 1.10, "Q4": 0.90},
        typical_duration_weeks=24,
        conviction_ceiling=0.75,
        pump_risk=0.30,
        confirmation_signals=["ura_etf_inflow", "uranium_spot_price_bid", "microsoft_nuclear_deal_signed"],
    ),

    NarrativeTemplate(
        name="AI Agent / Agentic Computing Breakout",
        description="AI moves from chatbot to autonomous agent → massive software platform re-rating. Winners: agent infrastructure, orchestration layers, enterprise AI deployments.",
        category="technology",
        catalyst_types=["product_launch", "enterprise_adoption", "research_breakthrough", "earnings_beat"],
        activation_keywords=["ai agent", "agentic ai", "autonomous agent", "openai agent", "claude computer use", "multi-agent", "workflow automation ai", "enterprise ai deployment"],
        invalidation_keywords=["ai regulation", "agent safety failure", "hallucination problem", "ai liability"],
        beneficiaries={
            "us": ["MSFT", "NOW", "CRM", "PLTR", "ORCL", "SNOW", "TTD", "GTLB"],
            "etfs": ["BOTZ", "AIQ"],
        },
        fades={"us": ["ACN", "MAN"]},               # traditional IT services disrupted
        regime_alignment={"Q1": 1.50, "Q2": 1.10, "Q3": 0.55, "Q4": 0.65},
        typical_duration_weeks=20,
        conviction_ceiling=0.80,
        pump_risk=0.30,
        confirmation_signals=["now_crm_enterprise_wins", "pltr_margin_expansion", "enterprise_software_beat_cycle"],
    ),

    NarrativeTemplate(
        name="Defense Tech / Autonomous Warfare Ramp",
        description="Geopolitical conflict escalation → defense modernization → tech-enabled defense (drones, AI warfare, C2 systems) gets massive budgets.",
        category="geopolitical",
        catalyst_types=["conflict_escalation", "budget_increase", "government_contract", "alliance_formation"],
        activation_keywords=["defense budget", "ukraine war", "taiwan tensions", "drone warfare", "autonomous weapons", "pentagon ai", "nato spending", "lockheed contract", "rtx contract", "palantir defense"],
        invalidation_keywords=["peace deal", "defense cut", "budget sequester", "ceasefire permanent"],
        beneficiaries={
            "us": ["LMT", "RTX", "NOC", "GD", "BA", "PLTR", "CACI", "KTOS", "RCAT", "ACHR"],
            "etfs": ["ITA", "XAR", "DFEN"],
        },
        fades={"us": []},
        regime_alignment={"Q2": 1.30, "Q3": 1.50, "Q1": 1.00, "Q4": 0.90},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.20,                                # strongest fundamental basis
        confirmation_signals=["ita_inflow", "lmt_rtx_book_to_bill_up", "congress_defense_appropriation"],
    ),

    # -----------------------------------------------------------------------
    # GEOPOLITICAL / COMMODITY NARRATIVES
    # -----------------------------------------------------------------------
    NarrativeTemplate(
        name="Iran-Hormuz Oil Supply Shock",
        description="Iran conflict or Strait of Hormuz disruption → 20% of global oil supply at risk → energy stocks front-run the geopolitical premium.",
        category="geopolitical",
        catalyst_types=["conflict_escalation", "sanctions", "shipping_disruption", "military_action"],
        activation_keywords=["iran war", "hormuz strait", "oil tanker attack", "iran sanctions", "middle east war", "houthi attack shipping", "red sea closure", "opec spare capacity"],
        invalidation_keywords=["iran deal", "ceasefire hormuz", "saudi spare capacity released", "strategic reserve release"],
        beneficiaries={
            "us": ["XOM", "CVX", "COP", "OXY", "EOG", "SLB", "HAL", "VLO", "MPC"],
            "etfs": ["XLE", "OIH", "USO"],
            "ihsg": ["ADRO.JK", "MEDC.JK", "AKRA.JK"],    # IHSG energy/coal benefit
            "commodities": ["CL=F", "BZ=F", "GC=F"],
        },
        fades={
            "us": ["DAL", "UAL", "AAL", "FDX"],            # airlines, logistics crushed
            "fx": ["IDR=X"],                                # IDR weakens (net oil importer)
        },
        regime_alignment={"Q2": 1.50, "Q3": 1.80, "Q1": 0.80, "Q4": 0.60},
        typical_duration_weeks=6,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["cl_f_above_90", "xle_relative_strength_week", "shipping_rate_spike"],
    ),

    NarrativeTemplate(
        name="Indonesia Coal Super-Cycle",
        description="Global energy transition slower than expected + Asia coal demand + supply constraints → Indonesian coal exporters at record margins.",
        category="commodity",
        catalyst_types=["supply_disruption", "demand_surge", "policy_change", "export_ban_lifted"],
        activation_keywords=["coal demand asia", "indonesia coal", "adaro coal", "ptba", "newcastle coal price", "china coal import", "india power crisis", "coal shortage"],
        invalidation_keywords=["coal ban", "renewable surge", "china lockdown", "india coal domestic", "australia coal"],
        beneficiaries={
            "ihsg": ["ADRO.JK", "PTBA.JK", "ITMG.JK", "HRUM.JK", "INDY.JK", "AADI.JK", "BUMI.JK"],
        },
        fades={
            "ihsg": ["ICBP.JK", "INDF.JK"],               # consumer importers hurt by energy cost
        },
        regime_alignment={"Q2": 1.80, "Q3": 1.50, "Q1": 0.70, "Q4": 0.40},
        typical_duration_weeks=16,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["newcastle_coal_price_above_150", "adro_dividend_surprise", "foreign_net_buy_ihsg_energy"],
    ),

    NarrativeTemplate(
        name="Indonesia Nickel / EV Battery Supply Chain",
        description="Global EV battery supply chain anchors to Indonesia nickel → INCO, ANTM, MDKA as key beneficiaries of China+1 battery strategy.",
        category="commodity",
        catalyst_types=["partnership_announcement", "government_contract", "factory_groundbreaking", "ev_demand_surge"],
        activation_keywords=["indonesia nickel", "ev battery indonesia", "inco nickel", "antam", "vale indonesia", "battery factory", "hpal nickel", "tesla indonesia", "ford indonesia"],
        invalidation_keywords=["nickel price crash", "ev demand slow", "sodium battery", "chinese nickel supply", "lme nickel"],
        beneficiaries={
            "ihsg": ["INCO.JK", "ANTM.JK", "MDKA.JK", "TINS.JK", "BRMS.JK"],
            "us": ["VALE", "FCX"],
        },
        fades={"ihsg": []},
        regime_alignment={"Q1": 1.20, "Q2": 1.40, "Q3": 0.90, "Q4": 0.60},
        typical_duration_weeks=20,
        conviction_ceiling=0.75,
        pump_risk=0.25,
        confirmation_signals=["nickel_lme_above_18000", "foreign_inco_antm_buying", "new_hpal_offtake_agreement"],
    ),

    # -----------------------------------------------------------------------
    # POLICY / MACRO NARRATIVES
    # -----------------------------------------------------------------------
    NarrativeTemplate(
        name="Fed Pivot / Rate Cut Cycle",
        description="Fed signals end of hiking → duration assets, rate-sensitive sectors, and EM FX all re-rate. This is the Q4→Q1 transition playbook.",
        category="policy",
        catalyst_types=["central_bank_statement", "inflation_print_miss", "labor_market_softening", "fed_speech"],
        activation_keywords=["fed cut", "rate cut", "powell pivot", "fed pause", "inflation cooling", "pcf below target", "fed funds futures", "dot plot dovish", "softish landing"],
        invalidation_keywords=["fed hike", "inflation surprise", "hot cpi", "labor market tight", "powell hawkish"],
        beneficiaries={
            "us": ["TLT", "IWM", "XLP", "XLU", "IYR", "HOOD", "COIN"],
            "ihsg": ["BBCA.JK", "BMRI.JK", "BSDE.JK", "CTRA.JK"],   # property, banks benefit
            "fx": ["EURUSD=X", "AUDUSD=X", "IDR=X"],
            "crypto": ["BTC-USD", "ETH-USD"],
        },
        fades={"us": ["UUP", "BIL"]},
        regime_alignment={"Q4": 1.80, "Q1": 1.60, "Q2": 0.80, "Q3": 0.50},
        typical_duration_weeks=16,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["tlt_above_200ma", "gold_above_2200", "usdinr_declining", "hyg_tightening"],
    ),

    NarrativeTemplate(
        name="Tariff War / Trade Disruption",
        description="US-China or broader tariff escalation → supply chain reshoring, domestic producers win, global trade losers. Stagflation risk amplifier.",
        category="policy",
        catalyst_types=["policy_announcement", "executive_order", "retaliation_measure", "election_result"],
        activation_keywords=["tariff", "trade war", "china tariff", "trump tariff", "export control", "reshoring", "friend-shoring", "decoupling", "sanctions"],
        invalidation_keywords=["trade deal", "tariff rollback", "wto ruling", "trade truce", "exemption"],
        beneficiaries={
            "us": ["LMT", "RTX", "NUE", "STLD", "CLF", "MLM", "VMC", "AAPL (domestic)", "PLTR"],
            "etfs": ["ITA", "XME"],
            "ihsg": ["ADRO.JK", "ANTM.JK"],  # commodity exporters less affected
        },
        fades={
            "us": ["AAPL (supply chain)", "TSLA", "NVDA (export controls)", "AVGO"],
            "ihsg": ["ASII.JK"],  # auto affected by tariffs on components
        },
        regime_alignment={"Q3": 1.50, "Q2": 1.20, "Q4": 1.00, "Q1": 0.70},
        typical_duration_weeks=12,
        conviction_ceiling=0.75,
        pump_risk=0.20,
        confirmation_signals=["xme_steel_relative_strength", "freight_rate_spike", "ism_supplier_deliveries_slow"],
    ),

    NarrativeTemplate(
        name="BI Rate Cut / IDR Stability",
        description="Bank Indonesia cuts rates OR signals dovish → IHSG banks, property, and consumer cyclicals re-rate. Requires USD weakness for room to cut.",
        category="policy",
        catalyst_types=["central_bank_statement", "inflation_print_miss", "bi_meeting", "current_account_improvement"],
        activation_keywords=["bank indonesia", "bi rate", "bi cut", "rupiah stable", "idr strengthen", "indonesia inflation", "bi dovish"],
        invalidation_keywords=["bi hike", "rupiah weak", "idr pressure", "inflation indonesia", "bi intervene"],
        beneficiaries={
            "ihsg": ["BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK", "BSDE.JK", "CTRA.JK", "SMRA.JK", "AMRT.JK"],
        },
        fades={"ihsg": []},
        regime_alignment={"Q1": 1.50, "Q4": 1.40, "Q2": 0.90, "Q3": 0.50},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.10,
        confirmation_signals=["usdidr_below_15800", "bi_rate_cut_confirmed", "foreign_net_buy_ihsg"],
    ),

    # -----------------------------------------------------------------------
    # CRYPTO-SPECIFIC NARRATIVES
    # -----------------------------------------------------------------------
    NarrativeTemplate(
        name="BTC Halving Supply Shock",
        description="Bitcoin halving reduces new supply by 50% → historically triggers 12-18 month bull cycle if demand holds. Q1 macro regime amplifies significantly.",
        category="cycle",
        catalyst_types=["protocol_event", "institutional_inflow", "etf_approval", "corporate_adoption"],
        activation_keywords=["bitcoin halving", "btc halving", "btc supply", "satoshi", "bitcoin etf inflow", "blackrock bitcoin", "spot btc etf", "bitcoin treasury"],
        invalidation_keywords=["btc regulation", "exchange hack", "tether depegged", "sec lawsuit crypto", "bitcoin ban"],
        beneficiaries={
            "crypto": ["BTC-USD", "ETH-USD", "COIN", "MSTR", "MARA", "CLSK"],
            "us": ["COIN", "MSTR"],
        },
        fades={"us": []},
        regime_alignment={"Q1": 1.80, "Q4": 1.40, "Q2": 1.10, "Q3": 0.40},
        typical_duration_weeks=52,
        conviction_ceiling=0.80,
        pump_risk=0.35,
        confirmation_signals=["btc_etf_inflow_above_500m_day", "crypto_fear_greed_above_70", "btc_above_200dma"],
    ),

    NarrativeTemplate(
        name="ETH Ecosystem / Staking Yield",
        description="ETH staking yield becomes institutional-grade fixed income alternative → massive inflow into ETH and liquid staking protocols.",
        category="cycle",
        catalyst_types=["protocol_upgrade", "etf_approval", "institutional_adoption", "yield_expansion"],
        activation_keywords=["ethereum staking", "eth etf", "lido", "liquid staking", "eigenlayer", "restaking", "eth yield", "eth institutional"],
        invalidation_keywords=["eth hack", "staking regulation", "sec staking", "competition layer1"],
        beneficiaries={
            "crypto": ["ETH-USD", "LDO-USD", "AAVE-USD", "UNI7083-USD"],
        },
        fades={"crypto": []},
        regime_alignment={"Q1": 1.60, "Q4": 1.20, "Q2": 1.00, "Q3": 0.30},
        typical_duration_weeks=20,
        conviction_ceiling=0.70,
        pump_risk=0.35,
        confirmation_signals=["eth_staking_rate_above_4pct", "ldo_tvl_all_time_high", "eth_etf_launch"],
    ),

    NarrativeTemplate(
        name="DePIN / Physical Infrastructure Crypto",
        description="Decentralized Physical Infrastructure Networks — crypto projects that tokenize real-world infrastructure (AI compute, wireless, energy). Early cycle, high pump risk but legitimate thesis.",
        category="technology",
        catalyst_types=["product_launch", "partnership_announcement", "research_breakthrough"],
        activation_keywords=["depin", "helium", "render network", "akash", "hivemapper", "filecoin", "decentralized compute", "distributed gpu", "io.net"],
        invalidation_keywords=["regulation depin", "centralization issue", "token unlock", "team dump"],
        beneficiaries={
            "crypto": ["RNDR-USD", "FET-USD", "TAO22974-USD", "GRT6719-USD", "HNT-USD"],
        },
        fades={"crypto": []},
        regime_alignment={"Q1": 1.70, "Q2": 1.10, "Q3": 0.30, "Q4": 0.50},
        typical_duration_weeks=12,
        conviction_ceiling=0.55,
        pump_risk=0.70,                                # high pump risk — early stage narrative
        confirmation_signals=["rndr_revenue_growth", "fetch_ai_enterprise_deals", "depin_tvl_growth"],
    ),

    # -----------------------------------------------------------------------
    # HEDGEYE APRIL 2026 ACTIVE NARRATIVES (sourced from Macro Week Summary)
    # -----------------------------------------------------------------------

    NarrativeTemplate(
        name="Flation Now Stag On A Lag",
        description=(
            "McCullough's defining 2026 macro memetic. Monthly Q2 (inflation NOW via oil/commodity bid) "
            "masking Structural Q3 (stagflation COMING via growth deceleration). "
            "Trade: Buy commodity inflation hedges NOW. Prepare Q3 shorts for when growth data rolls over. "
            "ISM Prices Paid 74.50 + CapEx spike = 'Flation Now'. "
            "Margin compression (Prices Paid > Prices Received by 19pts) = 'Stag On A Lag'."
        ),
        category="cycle",
        catalyst_types=["ism_prices_spike", "oil_bid", "iran_war", "tariff_import_costs", "capex_surge"],
        activation_keywords=["flation now stag on a lag", "prices paid", "ism 74", "margin compression",
                              "input costs rising", "stagflation later", "hybrid quad2 quad3"],
        invalidation_keywords=["ism prices paid below 55", "oil collapsed", "inflation dead",
                                "cpi below 2", "growth surge clears stagflation"],
        beneficiaries={
            "us": ["XLE", "XOP", "XLI", "XTL", "GLD", "SLV", "COM", "BNO"],
            "global": ["NORW", "EWW", "ARGT", "EWH", "UAE"],
            "crypto": ["IBIT"],
        },
        fades={
            "us": ["XLP", "XLY", "XLK", "XLF", "MAGS"],
            "bonds": ["TLT"],
        },
        regime_alignment={"Q1": 0.20, "Q2": 0.90, "Q3": 1.00, "Q4": 0.10},
        typical_duration_weeks=16,
        conviction_ceiling=0.90,
        pump_risk=0.10,
        confirmation_signals=["ism_prices_paid_above_70", "oil_trend_bullish", "breakeven_rising",
                               "capex_plans_above_20", "new_orders_above_20"],
    ),

    NarrativeTemplate(
        name="AI Buildout GPU→CPU Shift",
        description=(
            "Agentic AI workflows shift bottleneck from GPU compute to CPU processing. "
            "Morgan Stanley/Georgia Tech: complex orchestration = 95% CPU usage. "
            "Phase 1 winners: NVDA, AVGO (networking), GOOGL, AMZN. "
            "Phase 2 winners (NOW): Intel, AMD, memory (MU), photonics, power infrastructure. "
            "GPU dominance fades as AI becomes action-heavy (RAG → Multi-tool → Complex Orchestration). "
            "Reshoring + AI buildout = record CapEx Plans (24.15 April 2026). "
            "Concurrent: $BIRD and $MYSE tacked 'AI' onto names → market cap doubled overnight."
        ),
        category="technology",
        catalyst_types=["ai_agentic_deployment", "capex_surge", "earnings_beat", "datacenter_order",
                        "power_infrastructure", "cpu_bottleneck_news"],
        activation_keywords=["agentic ai", "cpu bottleneck", "ai infrastructure", "power consumption ai",
                              "hyperscaler capex", "datacenter buildout", "ai agent", "complex orchestration",
                              "gpu to cpu", "memory bandwidth"],
        invalidation_keywords=["ai hype bubble", "gpu demand collapse", "ai spending cuts",
                                "hyperscaler capex guide down", "ai disappointment"],
        beneficiaries={
            "us": ["NVDA", "AVGO", "GOOGL", "AMZN", "INTC", "AMD", "MU", "XLK", "XLRE"],
            "etfs": ["QQQ"],
        },
        fades={
            "us": ["MSFT", "legacy_tech"],
        },
        regime_alignment={"Q1": 0.90, "Q2": 0.85, "Q3": 0.60, "Q4": 0.20},
        typical_duration_weeks=52,
        conviction_ceiling=0.80,
        pump_risk=0.40,
        confirmation_signals=["hyperscaler_capex_beat", "power_demand_spike", "semiconductor_lead_times_rising",
                               "cpu_pricing_power", "memory_supply_tightening"],
    ),

    NarrativeTemplate(
        name="Western Hemisphere Supply Chain",
        description=(
            "Supply Chain Shock 3.0: COVID 2020 → Ukraine 2022 → Iran/Hormuz 2026. "
            "Geopolitical risk forcing companies off Hormuz-dependent supply chains. "
            "'All roads lead to Western Hemisphere.' "
            "Nearshoring hub = Mexico (EWW, #1 US trading partner). "
            "Energy alternative = Canada, Norway. Ag + Lithium = Argentina (ARGT). "
            "US industrial renaissance = domestic manufacturing + reshoring. "
            "This is a STRUCTURAL narrative — years, not months."
        ),
        category="geopolitical",
        catalyst_types=["hormuz_closure", "iran_war_escalation", "tariff_reshoring", "nearshoring_deal",
                        "manufacturing_relocation", "supply_chain_diversification"],
        activation_keywords=["strait of hormuz", "nearshoring", "reshoring", "supply chain diversify",
                              "western hemisphere", "mexico manufacturing", "onshoring",
                              "friend-shoring", "supply chain shock"],
        invalidation_keywords=["hormuz reopens fully", "iran peace deal stable", "china supply chain normalizes",
                                "mexico trade deal collapsed", "tariffs removed"],
        beneficiaries={
            "global": ["EWW", "ARGT", "EWC", "NORW"],
            "us": ["XLI", "IWM", "XLB"],
            "commodities": ["GLD", "SLV", "CL=F", "HG=F"],
        },
        fades={
            "global": ["EWG", "EWJ", "EWY"],
            "asia_em": ["EIDO", "EWM"],
        },
        regime_alignment={"Q1": 0.50, "Q2": 0.75, "Q3": 0.85, "Q4": 0.40},
        typical_duration_weeks=104,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["mexico_fdi_rising", "us_manufacturing_pmi_rising", "nearshoring_capex",
                               "argentina_reform_pace", "hormuz_risk_premium_sustained"],
    ),

    NarrativeTemplate(
        name="K-Shaped Economy Fourth Turning",
        description=(
            "SPX at all-time highs. Michigan Consumer Sentiment at 74-year low. "
            "The gap between financial asset owners and wage earners is the widest ever. "
            "McCullough: 'The brands of my youth are dead men walking.' "
            "Demographic + wealth divergence creates few winners, many losers in consumer space. "
            "Winners: premium/luxury (pricing power), healthcare, tech platforms. "
            "Losers: mid-market consumer brands, traditional retail, legacy media. "
            "This IS the macro backdrop of Structural Q3 — growth AVERAGE slows, but top decile thrives."
        ),
        category="cycle",
        catalyst_types=["consumer_sentiment_collapse", "credit_card_stress", "delinquency_rise",
                        "luxury_beat", "discount_retail_miss", "wage_data"],
        activation_keywords=["k-shaped economy", "consumer bifurcation", "sentiment low", "credit stress",
                              "fourth turning", "wealth inequality", "luxury vs discount", "consumer squeeze"],
        invalidation_keywords=["consumer confidence surge", "wage growth accelerates broadly",
                                "middle class spending revival", "credit stress eases"],
        beneficiaries={
            "us": ["XLV", "XLI", "premium_consumer"],
        },
        fades={
            "us": ["XLP", "KSS", "M", "legacy_retail", "XLY"],
        },
        regime_alignment={"Q1": 0.40, "Q2": 0.60, "Q3": 0.85, "Q4": 0.70},
        typical_duration_weeks=52,
        conviction_ceiling=0.70,
        pump_risk=0.05,
        confirmation_signals=["consumer_sentiment_new_low", "credit_card_delinquency_rising",
                               "luxury_earnings_beat", "mass_market_miss", "michigan_csi_below_65"],
    ),

    NarrativeTemplate(
        name="USD Mythic Variable Regime",
        description=(
            "When USD inverse correlations exceed -0.85 on 15D TRADE duration, "
            "the dollar becomes ALL THAT MATTERS. Everything mechanically follows USD direction. "
            "McCullough April 20: 'USD vs SPY -0.97, USD vs BTC -0.96, USD vs Gold -0.87.' "
            "This is the SIGNAL environment where process beats prediction: "
            "USD bearish → buy SPX, BTC, Gold, EM. USD bullish → short them all. "
            "The fractal memory of correlations determines outcome, not narrative."
        ),
        category="cycle",
        catalyst_types=["fed_pivot", "usd_trend_breakdown", "usd_trend_breakout",
                        "cpi_surprise", "gdp_surprise", "safe_haven_demand"],
        activation_keywords=["usd correlation", "dollar bearish trend", "dxy breakdown",
                              "mythic variable", "everything correlates to dollar",
                              "dollar drives", "usd inverse correlation -0.9"],
        invalidation_keywords=["usd correlations fade", "dollar decoupled", "correlation breaks",
                                "safe haven demand overrides", "carry trade reversal"],
        beneficiaries={
            "us": ["SPY", "QQQ", "GLD", "XLI"],
            "crypto": ["IBIT", "BTC-USD"],
            "global": ["EWH", "EWW", "ARGT", "EEM"],
        },
        fades={
            "us": ["USD-denominated cash", "money_market"],
        },
        regime_alignment={"Q1": 0.80, "Q2": 0.85, "Q3": 0.75, "Q4": 0.50},
        typical_duration_weeks=8,
        conviction_ceiling=0.95,
        pump_risk=0.20,
        confirmation_signals=["usd_spx_corr_below_neg85", "usd_btc_corr_below_neg90",
                               "dxy_bearish_trend", "vix_bearish_trend", "eurusd_bullish_trend"],
    ),

    NarrativeTemplate(
        name="Nuclear Energy Renaissance",
        description=(
            "AI power demand + geopolitical energy security driving nuclear revival. "
            "Data centers need 24/7 baseload power → solar/wind insufficient. "
            "Small Modular Reactors (SMRs) entering deployment phase. "
            "Tech companies (MSFT, AMZN, GOOGL) signing nuclear PPAs. "
            "Uranium supply constrained after decade of underinvestment. "
            "Confirm via: URA ETF inflow, CEG (Constellation) earnings, NNE/SMR permits."
        ),
        category="technology",
        catalyst_types=["nuclear_ppa", "smr_permit", "uranium_supply_squeeze",
                        "ai_power_demand_report", "constellation_earnings", "government_nuclear_policy"],
        activation_keywords=["nuclear", "smr", "small modular reactor", "ura_etf", "constellation energy",
                              "uranium", "nne", "oklo", "nuclear ppa", "ai power demand",
                              "nuclear renaissance", "nne", "oklo"],
        invalidation_keywords=["nuclear accident", "uranium price collapse", "smr cancellation",
                                "tech company cancels nuclear ppa", "nuclear moratorium"],
        beneficiaries={
            "us": ["CEG", "NNE", "SMR", "OKLO", "CCJ", "UEC", "XLU"],
            "etfs": ["URA"],
        },
        fades={
            "us": ["ENPH", "FSLR"],  # solar alternative power
        },
        regime_alignment={"Q1": 0.70, "Q2": 0.80, "Q3": 0.75, "Q4": 0.60},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.35,
        confirmation_signals=["ura_etf_inflow", "ceg_revenue_beat", "uranium_price_above_60",
                               "smr_permits_issued", "ai_datacenter_nuclear_ppa"],
    ),

    NarrativeTemplate(
        name="Defense Tech Autonomous Warfare Ramp",
        description=(
            "Iran war + Hormuz disruption = fastest military technology adoption cycle ever. "
            "Drones, autonomous systems, EW, AI-guided weapons replacing legacy platforms. "
            "Defense budget surge across NATO + Middle East allies. "
            "Bipartisan US defense spending — one of few things both parties agree on. "
            "Confirm via: ITA ETF inflow, LMT/RTX earnings beats, defense budget legislation."
        ),
        category="geopolitical",
        catalyst_types=["military_conflict_escalation", "defense_budget_increase",
                        "autonomous_weapons_deployment", "nato_spending_pledge", "ukraine_aid"],
        activation_keywords=["defense spending", "ita inflow", "autonomous weapons", "drone warfare",
                              "lockheed", "raytheon", "defense tech", "electronic warfare",
                              "military ai", "defense ramp", "war risk"],
        invalidation_keywords=["peace deal", "defense budget cut", "conflict de-escalation complete",
                                "treaty signed", "disarmament"],
        beneficiaries={
            "us": ["LMT", "RTX", "NOC", "GD", "HII", "CACI"],
            "etfs": ["ITA", "PPA"],
        },
        fades={},
        regime_alignment={"Q1": 0.50, "Q2": 0.65, "Q3": 0.85, "Q4": 0.60},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["ita_inflow", "defense_earnings_beat", "defense_budget_increase",
                               "conflict_sustaining", "nato_spending_up"],
    ),

    NarrativeTemplate(
        name="Tariff Trade Disruption",
        description=(
            "Trump tariff escalation disrupting global trade flows. "
            "Winners: reshoring beneficiaries (US industrials, Mexico). "
            "Losers: export-dependent economies (Germany, Japan, China). "
            "Short-term: inflation via import prices (Prices Paid 74.50). "
            "Long-term: growth slowdown as trade volumes contract. "
            "This is what drives the 'Flation Now, Stag On A Lag' narrative."
        ),
        category="policy",
        catalyst_types=["tariff_announcement", "trade_war_escalation", "tariff_retaliation",
                        "import_price_spike", "trade_deal_collapse"],
        activation_keywords=["tariff", "trade war", "import prices", "xme steel", "xme", "stld",
                              "tariff impact", "reshoring demand", "trade disruption"],
        invalidation_keywords=["tariff removal", "trade deal signed", "tariff pause extended",
                                "wto agreement", "trade normalization"],
        beneficiaries={
            "us": ["XLI", "NUE", "STLD", "X", "RS"],
            "global": ["EWW"],
        },
        fades={
            "global": ["EWG", "EWJ", "FXI", "MCHI"],
        },
        regime_alignment={"Q1": 0.30, "Q2": 0.50, "Q3": 0.90, "Q4": 0.60},
        typical_duration_weeks=20,
        conviction_ceiling=0.75,
        pump_risk=0.20,
        confirmation_signals=["xme_steel_relative_strength", "import_prices_rising",
                               "trade_deficit_widening", "industrial_tariff_announcements"],
    ),
]

# Build lookup dict
NARRATIVE_BY_NAME: Dict[str, NarrativeTemplate] = {n.name: n for n in _NARRATIVE_LIBRARY}
NARRATIVES_BY_CATEGORY: Dict[str, List[NarrativeTemplate]] = {}
for _n in _NARRATIVE_LIBRARY:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
