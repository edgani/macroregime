"""config/narrative_universe.py — Full Narrative Universe

Ported from macroregime v9_fixed + April 2026 updates.
Each narrative has: catalyst types, activation keywords, 
beneficiaries/fades per market, regime alignment, conviction ceiling.

The narrative engine scores these against current price data + news.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class NarrativeTemplate:
    name: str
    description: str
    category: str       # technology | geopolitical | policy | commodity | cycle | disruption
    catalyst_types: List[str]
    activation_keywords: List[str]
    invalidation_keywords: List[str]
    beneficiaries: Dict[str, List[str]]   # {market: [tickers]}
    fades: Dict[str, List[str]]           # {market: [tickers]}
    regime_alignment: Dict[str, float]    # {quad: multiplier}
    typical_duration_weeks: int
    conviction_ceiling: float
    pump_risk: float
    confirmation_signals: List[str]

_NARRATIVES: List[NarrativeTemplate] = [
    # ── TECHNOLOGY ────────────────────────────────────────────────────────
    NarrativeTemplate(
        name="AI Photonics / CPO Supply Constraint",
        description="NVIDIA $4B to LITE+COHR (March 2026). CPO replacing copper in AI data centers. InP laser supply constrained through 2027+.",
        category="technology",
        catalyst_types=["supply_contract","hyperscaler_capex","product_launch","earnings_beat"],
        activation_keywords=["cpo","co-packaged optics","silicon photonics","inP laser","1.6T transceiver","lite cohr nvidia","photonics constraint","optical interconnect","eml lumentum"],
        invalidation_keywords=["cpo adoption delay","pluggable modules survive","photonic decoherence","nvidia cancels"],
        beneficiaries={"us":["LITE","COHR","POET","VIAV","CIEN","GLW"],"etfs":["SMH"]},
        fades={"us":[]},
        regime_alignment={"Q1":0.85,"Q2":0.78,"Q3":0.62,"Q4":0.38},
        typical_duration_weeks=52, conviction_ceiling=0.88, pump_risk=0.20,
        confirmation_signals=["lite_cohr_revenue_beat","nvidia_cpo_deployment","optical_transceiver_market_growth"],
    ),
    NarrativeTemplate(
        name="AI Chip Supply Constraint",
        description="AI compute demand exceeds supply → pricing power for chip designers and equipment. NVDA-led but benefits entire stack.",
        category="technology",
        catalyst_types=["earnings_beat","hyperscaler_capex_raise","supply_bottleneck","government_restriction"],
        activation_keywords=["ai chip demand","gpu shortage","h100","blackwell","cuda","ai infrastructure","hyperscaler capex","data center build","nvda earnings","gb200"],
        invalidation_keywords=["ai bubble","capex slowdown","nvidia competitor","custom chip","huawei chip"],
        beneficiaries={"us":["NVDA","AVGO","AMD","AMAT","KLAC","LRCX","ASML","TSM","ARM","SMCI"],"etfs":["SOXX","SMH"]},
        fades={"us":["INTC","QCOM"]},
        regime_alignment={"Q1":1.40,"Q2":1.20,"Q3":0.75,"Q4":0.60},
        typical_duration_weeks=16, conviction_ceiling=0.80, pump_risk=0.25,
        confirmation_signals=["nvda_revenue_beat","hyperscaler_capex_up","smh_relative_strength"],
    ),
    NarrativeTemplate(
        name="Transformer / Switchgear Infrastructure Bottleneck",
        description="AI data centers need massive power upgrades. Transformer lead times 2-3 years. Switchgear (dry, 3-4yr bottleneck ~23% of market). Can't build AI DC without these components.",
        category="technology",
        catalyst_types=["supply_constraint","data_center_buildout","grid_upgrade","utility_capex"],
        activation_keywords=["transformer shortage","switchgear bottleneck","power infrastructure","data center power","grid upgrade","transformer lead time","electrical infrastructure","power delay","interconnection queue"],
        invalidation_keywords=["transformer supply normalizes","grid buildout slows","data center capex cuts"],
        beneficiaries={"us":["ETN","GEV","EMR","HUBB","NVT","AYI","AMETEK","ROP"],"global":["ABB","SIEGY","HAM.TO"]},
        fades={"us":[]},
        regime_alignment={"Q1":0.75,"Q2":0.85,"Q3":0.80,"Q4":0.55},
        typical_duration_weeks=52, conviction_ceiling=0.85, pump_risk=0.15,
        confirmation_signals=["etn_backlog_growth","transformer_lead_times_rising","interconnection_queue_above_2000gw"],
    ),
    NarrativeTemplate(
        name="SiC / GaN Power Semiconductor Bottleneck",
        description="800V EV + AI DC power supply = dual demand for SiC/GaN. Only 5 companies can make SiC at volume. 52+ week lead times. Wolfspeed distress = ON pricing umbrella.",
        category="technology",
        catalyst_types=["supply_constraint","ev_adoption","ai_power_demand","competitor_distress"],
        activation_keywords=["silicon carbide","sic","gan","gallium nitride","onsemi","wolfspeed","800v ev","power semiconductor","elitesic","ev powertrain"],
        invalidation_keywords=["sic oversupply","ev slowdown kills sic","wolfspeed recovery","sic competitor entry"],
        beneficiaries={"us":["ON","WOLF","STM","MPWR","AEHR","FORM"]},
        fades={"us":[]},
        regime_alignment={"Q1":0.78,"Q2":0.82,"Q3":0.65,"Q4":0.45},
        typical_duration_weeks=24, conviction_ceiling=0.80, pump_risk=0.25,
        confirmation_signals=["on_sic_revenue_beat","sic_lead_times_rising","ev_800v_adoption","aehr_fox_orders"],
    ),
    NarrativeTemplate(
        name="Nuclear Energy Renaissance",
        description="AI data center electricity demand + carbon goals → nuclear the only viable 24/7 baseload. SMRs entering deployment. Tech companies signing nuclear PPAs.",
        category="technology",
        catalyst_types=["government_contract","tech_company_deal","regulatory_approval","plant_restart"],
        activation_keywords=["nuclear power","smr","small modular reactor","data center nuclear","microsoft nuclear","amazon nuclear","constellation energy","oklo","nuscale","kairos","nuclear ppa"],
        invalidation_keywords=["nuclear accident","reactor shutdown","nuclear waste","solar cheaper","nuclear moratorium"],
        beneficiaries={"us":["CEG","NNE","SMR","OKLO","UUUU","UEC","CCJ","VST"],"etfs":["URA","NLR"]},
        fades={"us":["FSLR","ENPH"]},
        regime_alignment={"Q1":1.20,"Q2":1.30,"Q3":1.10,"Q4":0.90},
        typical_duration_weeks=52, conviction_ceiling=0.80, pump_risk=0.30,
        confirmation_signals=["ura_etf_inflow","ceg_revenue_beat","uranium_price_above_60","smr_permits"],
    ),
    NarrativeTemplate(
        name="AI Agent / Agentic Computing Breakout",
        description="AI moves from chatbot to autonomous agent → massive software platform re-rating. Winners: agent infrastructure, orchestration layers.",
        category="technology",
        catalyst_types=["product_launch","enterprise_adoption","research_breakthrough","earnings_beat"],
        activation_keywords=["ai agent","agentic ai","autonomous agent","openai agent","multi-agent","workflow automation ai","enterprise ai deployment","computer use"],
        invalidation_keywords=["ai regulation","agent safety failure","hallucination problem","ai liability"],
        beneficiaries={"us":["MSFT","NOW","CRM","PLTR","ORCL","SNOW"],"etfs":["BOTZ","AIQ"]},
        fades={"us":["ACN","MAN"]},
        regime_alignment={"Q1":1.50,"Q2":1.10,"Q3":0.55,"Q4":0.65},
        typical_duration_weeks=20, conviction_ceiling=0.80, pump_risk=0.30,
        confirmation_signals=["now_crm_enterprise_wins","pltr_margin_expansion"],
    ),
    NarrativeTemplate(
        name="Quantum Photonics Disruption",
        description="Superconducting quantum hits scaling wall → photonic quantum companies gain credibility. Pattern: dominant player admits limitation → challenger benefits.",
        category="technology",
        catalyst_types=["competitor_admission","government_contract","research_breakthrough","partnership_announcement"],
        activation_keywords=["photonic quantum","room temperature quantum","xanadu","ionq photonic","darpa quantum","quantum networking"],
        invalidation_keywords=["superconducting milestone","google quantum supremacy","ibm quantum record","photonic decoherence"],
        beneficiaries={"us":["IONQ","QUBT","RGTI","QBTS"],"watchlist":["XNDU"]},
        fades={"us":["IBM","GOOGL"]},
        regime_alignment={"Q1":1.30,"Q2":1.10,"Q3":0.60,"Q4":0.50},
        typical_duration_weeks=8, conviction_ceiling=0.65, pump_risk=0.55,
        confirmation_signals=["unusual_volume_ionq_qubt","institutional_filing_increase","darpa_contracts"],
    ),
    # ── GEOPOLITICAL ──────────────────────────────────────────────────────
    NarrativeTemplate(
        name="Iran-Hormuz Oil Supply Shock",
        description="Iran conflict or Strait of Hormuz disruption → 20% of global oil supply at risk → energy stocks front-run geopolitical premium. War→Oil→Tanker→Refiner chain.",
        category="geopolitical",
        catalyst_types=["conflict_escalation","sanctions","shipping_disruption","military_action"],
        activation_keywords=["iran war","hormuz strait","oil tanker attack","iran sanctions","middle east war","houthi attack shipping","red sea closure","opec spare capacity","tanker rates spike","shipping disruption"],
        invalidation_keywords=["iran deal","ceasefire hormuz","saudi spare capacity released","strategic reserve release"],
        beneficiaries={
            "us":["XLE","XOP","CVX","OXY","COP","SLB","HAL","FTI","MPC","VLO","PSX","STNG","EURN","TK"],
            "commodity":["CL=F","BZ=F","RB=F","NG=F"],
            "global":["NORW","EWC"],
        },
        fades={"us":["XLY","XLK","airlines","IWM"]},
        regime_alignment={"Q2":1.50,"Q3":1.40,"Q1":0.90,"Q4":0.70},
        typical_duration_weeks=8, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["oil_above_90","tanker_rates_spike","shipping_route_closure","iran_military_action"],
    ),
    NarrativeTemplate(
        name="Defense Tech / Autonomous Warfare Ramp",
        description="Geopolitical conflict escalation → defense modernization → tech-enabled defense (drones, AI warfare). Bipartisan US defense spending.",
        category="geopolitical",
        catalyst_types=["conflict_escalation","budget_increase","government_contract","alliance_formation"],
        activation_keywords=["defense budget","ukraine war","taiwan tensions","drone warfare","autonomous weapons","pentagon ai","nato spending","lockheed contract","rtx contract","palantir defense"],
        invalidation_keywords=["peace deal","defense cut","budget sequester","ceasefire permanent"],
        beneficiaries={"us":["LMT","RTX","NOC","GD","BA","PLTR","CACI","KTOS","AXON","BWXT"],"etfs":["ITA","XAR","DFEN"]},
        fades={"us":[]},
        regime_alignment={"Q2":1.30,"Q3":1.50,"Q1":1.00,"Q4":0.90},
        typical_duration_weeks=12, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["ita_inflow","lmt_rtx_book_to_bill_up","congress_defense_appropriation"],
    ),
    NarrativeTemplate(
        name="Western Hemisphere Supply Chain",
        description="Supply Chain Shock 3.0: COVID→Ukraine→Iran/Hormuz. 'All roads lead to Western Hemisphere.' Nearshoring hub = Mexico. Energy = Canada/Norway. Ag+Lithium = Argentina. STRUCTURAL years-long narrative.",
        category="geopolitical",
        catalyst_types=["hormuz_closure","iran_war_escalation","tariff_reshoring","nearshoring_deal","supply_chain_diversification"],
        activation_keywords=["strait of hormuz","nearshoring","reshoring","supply chain diversify","western hemisphere","mexico manufacturing","onshoring","friend-shoring","supply chain shock"],
        invalidation_keywords=["hormuz reopens fully","iran peace deal","china supply chain normalizes","mexico trade collapsed"],
        beneficiaries={"global":["EWW","ARGT","EWC","NORW"],"us":["XLI","IWM","XLB"],"commodity":["GLD","SLV","CL=F","HG=F"]},
        fades={"global":["EWG","EWJ","EWY"],"asia_em":["EIDO","EWM"]},
        regime_alignment={"Q1":0.50,"Q2":0.75,"Q3":0.85,"Q4":0.40},
        typical_duration_weeks=104, conviction_ceiling=0.85, pump_risk=0.15,
        confirmation_signals=["mexico_fdi_rising","us_manufacturing_pmi_rising","nearshoring_capex","hormuz_risk_premium"],
    ),
    # ── POLICY / MACRO ────────────────────────────────────────────────────
    NarrativeTemplate(
        name="Flation Now Stag On A Lag",
        description="McCullough's 2026 macro memetic. Monthly Q2 (inflation NOW via oil/commodity) masking Structural Q3 (stagflation COMING via growth deceleration). ISM Prices Paid 74.50 + CapEx spike = 'Flation Now'. Margin compression = 'Stag On A Lag'.",
        category="cycle",
        catalyst_types=["ism_prices_spike","oil_bid","iran_war","tariff_import_costs","capex_surge"],
        activation_keywords=["flation now stag on a lag","prices paid","ism 74","margin compression","input costs rising","stagflation later","hybrid quad2 quad3"],
        invalidation_keywords=["ism prices paid below 55","oil collapsed","inflation dead","cpi below 2"],
        beneficiaries={"us":["XLE","XOP","XLI","GLD","SLV","BNO"],"global":["NORW","EWW","ARGT","EWH","UAE"],"crypto":["IBIT"]},
        fades={"us":["XLP","XLY","XLK","XLF","MAGS"],"bonds":["TLT"]},
        regime_alignment={"Q1":0.20,"Q2":0.90,"Q3":1.00,"Q4":0.10},
        typical_duration_weeks=16, conviction_ceiling=0.90, pump_risk=0.10,
        confirmation_signals=["ism_prices_paid_above_70","oil_trend_bullish","breakeven_rising","capex_plans_above_20"],
    ),
    NarrativeTemplate(
        name="Fed Pivot / Rate Cut Cycle",
        description="Fed signals end of hiking → duration assets, rate-sensitive sectors, and EM FX all re-rate. The Q4→Q1 transition playbook.",
        category="policy",
        catalyst_types=["central_bank_statement","inflation_print_miss","labor_market_softening","fed_speech"],
        activation_keywords=["fed cut","rate cut","powell pivot","fed pause","inflation cooling","pcf below target","fed funds futures","dot plot dovish","softish landing"],
        invalidation_keywords=["fed hike","inflation surprise","hot cpi","labor market tight","powell hawkish"],
        beneficiaries={"us":["TLT","IWM","XLP","XLU","IYR","HOOD","COIN"],"ihsg":["BBCA.JK","BMRI.JK","BSDE.JK","CTRA.JK"],"fx":["EURUSD=X","AUDUSD=X"],"crypto":["BTC-USD","ETH-USD"]},
        fades={"us":["UUP","BIL"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q2":0.80,"Q3":0.50},
        typical_duration_weeks=16, conviction_ceiling=0.85, pump_risk=0.15,
        confirmation_signals=["tlt_above_200ma","gold_above_2200","usdinr_declining","hyg_tightening"],
    ),
    NarrativeTemplate(
        name="Tariff War / Trade Disruption",
        description="US-China or broader tariff escalation → supply chain reshoring, domestic producers win. Stagflation risk amplifier via import price spikes.",
        category="policy",
        catalyst_types=["policy_announcement","executive_order","retaliation_measure","election_result"],
        activation_keywords=["tariff","trade war","china tariff","trump tariff","export control","reshoring","friend-shoring","decoupling","sanctions"],
        invalidation_keywords=["trade deal","tariff rollback","wto ruling","trade truce","exemption"],
        beneficiaries={"us":["LMT","RTX","NUE","STLD","CLF","MLM","VMC","PLTR"],"etfs":["ITA","XME"],"ihsg":["ADRO.JK","ANTM.JK"]},
        fades={"us":["AAPL","TSLA","NVDA","AVGO"],"ihsg":["ASII.JK"]},
        regime_alignment={"Q3":1.50,"Q2":1.20,"Q4":1.00,"Q1":0.70},
        typical_duration_weeks=12, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["xme_steel_relative_strength","freight_rate_spike","ism_supplier_deliveries_slow"],
    ),
    NarrativeTemplate(
        name="USD Mythic Variable Regime",
        description="When USD inverse correlations exceed -0.85, the dollar becomes ALL THAT MATTERS. USD bearish → buy SPX, BTC, Gold, EM. 'USD vs SPY -0.97, USD vs BTC -0.96, USD vs Gold -0.87' (McCullough April 2026).",
        category="cycle",
        catalyst_types=["fed_pivot","usd_trend_breakdown","usd_trend_breakout","cpi_surprise","gdp_surprise"],
        activation_keywords=["usd correlation","dollar bearish trend","dxy breakdown","mythic variable","everything correlates to dollar","dollar drives","usd inverse correlation"],
        invalidation_keywords=["usd correlations fade","dollar decoupled","correlation breaks","safe haven demand overrides"],
        beneficiaries={"us":["SPY","QQQ","GLD","XLI"],"crypto":["IBIT","BTC-USD"],"global":["EWH","EWW","ARGT","EEM"]},
        fades={"us":["UUP","money_market"]},
        regime_alignment={"Q1":0.80,"Q2":0.85,"Q3":0.75,"Q4":0.50},
        typical_duration_weeks=8, conviction_ceiling=0.95, pump_risk=0.20,
        confirmation_signals=["usd_spx_corr_below_neg85","usd_btc_corr_below_neg90","dxy_bearish_trend","vix_bearish_trend"],
    ),
    NarrativeTemplate(
        name="AI Buildout GPU→CPU Shift",
        description="Agentic AI workflows shift bottleneck from GPU to CPU processing. Phase 2 winners: Intel, AMD, memory (MU), photonics, power infrastructure. Reshoring + AI buildout = record CapEx Plans.",
        category="technology",
        catalyst_types=["ai_agentic_deployment","capex_surge","earnings_beat","datacenter_order","cpu_bottleneck_news"],
        activation_keywords=["agentic ai","cpu bottleneck","ai infrastructure","power consumption ai","hyperscaler capex","datacenter buildout","ai agent","complex orchestration","gpu to cpu"],
        invalidation_keywords=["ai hype bubble","gpu demand collapse","ai spending cuts","hyperscaler capex guide down"],
        beneficiaries={"us":["NVDA","AVGO","GOOGL","AMZN","INTC","AMD","MU","XLRE"],"etfs":["QQQ"]},
        fades={"us":["MSFT","legacy_tech"]},
        regime_alignment={"Q1":0.90,"Q2":0.85,"Q3":0.60,"Q4":0.20},
        typical_duration_weeks=52, conviction_ceiling=0.80, pump_risk=0.40,
        confirmation_signals=["hyperscaler_capex_beat","power_demand_spike","semiconductor_lead_times_rising"],
    ),
    # ── INDONESIA-SPECIFIC ────────────────────────────────────────────────
    NarrativeTemplate(
        name="Indonesia Coal Super-Cycle",
        description="Coal remains IHSG top earner. China/India thermal coal demand + export premium. Indonesia coal proxy for global energy insecurity.",
        category="commodity",
        catalyst_types=["china_coal_demand","india_power_crisis","weather_event","coal_export_price"],
        activation_keywords=["coal price","thermal coal","indonesia coal","adro itmg ptba","icx coal index","china coal import","india coal deficit"],
        invalidation_keywords=["coal price collapse","china coal surplus","carbon tax","coal ban"],
        beneficiaries={"ihsg":["ITMG.JK","ADRO.JK","PTBA.JK","HRUM.JK","BUMI.JK","DOID.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.50,"Q1":1.20,"Q3":0.70,"Q4":0.30},
        typical_duration_weeks=12, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["coal_spot_price_above_130","foreign_net_buy_itmg_adro","china_coal_import_data"],
    ),
    NarrativeTemplate(
        name="Indonesia Nickel / EV Battery Supply Chain",
        description="Indonesia nickel ore export ban → pricing power. EV battery secular demand. Indonesia = 40%+ of global nickel reserves. HPAL projects ramping.",
        category="commodity",
        catalyst_types=["nickel_price_spike","ev_adoption","export_ban_enforcement","china_ev_demand"],
        activation_keywords=["indonesia nickel","nickel export ban","hpal","ev battery","battery supply chain","lme nickel","inco vale indonesia","mdka"],
        invalidation_keywords=["nickel oversupply","ev slowdown","export ban lifted","china nickel surplus"],
        beneficiaries={"ihsg":["INCO.JK","MDKA.JK","ANTM.JK","NCKL.JK"],"global":["VALE3.SA"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.40,"Q1":1.10,"Q3":0.60,"Q4":0.30},
        typical_duration_weeks=20, conviction_ceiling=0.75, pump_risk=0.25,
        confirmation_signals=["nickel_lme_above_18000","foreign_inco_antm_buying","hpal_offtake_agreement"],
    ),
    NarrativeTemplate(
        name="BI Rate Cut / IDR Stability",
        description="Bank Indonesia cuts rates OR signals dovish → IHSG banks, property, and consumer cyclicals re-rate. Requires USD weakness for BI to have cutting room.",
        category="policy",
        catalyst_types=["central_bank_statement","inflation_print_miss","bi_meeting","current_account_improvement"],
        activation_keywords=["bank indonesia","bi rate","bi cut","rupiah stable","idr strengthen","indonesia inflation","bi dovish"],
        invalidation_keywords=["bi hike","rupiah weak","idr pressure","inflation indonesia","bi intervene"],
        beneficiaries={"ihsg":["BBCA.JK","BMRI.JK","BBRI.JK","BBNI.JK","BSDE.JK","CTRA.JK","SMRA.JK","AMRT.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.50,"Q4":1.40,"Q2":0.90,"Q3":0.50},
        typical_duration_weeks=12, conviction_ceiling=0.80, pump_risk=0.10,
        confirmation_signals=["usdidr_below_15800","bi_rate_cut_confirmed","foreign_net_buy_ihsg"],
    ),
    # ── CRYPTO-SPECIFIC ───────────────────────────────────────────────────
    NarrativeTemplate(
        name="BTC Halving Supply Shock",
        description="Bitcoin halving reduces new supply 50% → historically triggers 12-18 month bull cycle if demand holds. Q1 macro regime amplifies significantly.",
        category="cycle",
        catalyst_types=["protocol_event","institutional_inflow","etf_approval","corporate_adoption"],
        activation_keywords=["bitcoin halving","btc halving","btc supply","bitcoin etf inflow","blackrock bitcoin","spot btc etf","bitcoin treasury"],
        invalidation_keywords=["btc regulation","exchange hack","tether depegged","sec lawsuit crypto","bitcoin ban"],
        beneficiaries={"crypto":["BTC-USD","ETH-USD","COIN","MSTR","MARA","CLSK"],"us":["COIN","MSTR","IBIT","FBTC"]},
        fades={"us":[]},
        regime_alignment={"Q1":1.80,"Q4":1.40,"Q2":1.10,"Q3":0.40},
        typical_duration_weeks=52, conviction_ceiling=0.80, pump_risk=0.35,
        confirmation_signals=["btc_etf_inflow_above_500m_day","crypto_fear_greed_above_70","btc_above_200dma"],
    ),
    NarrativeTemplate(
        name="TAO / Bittensor AI Decentralized Intelligence",
        description="TAO (Bittensor) = decentralized AI network. Each subnet specializes (language, vision, trading signals). March 2026 surge on subnet expansion + institutional discovery. Tokenomics: 21M max supply, ~7-8M circulating. Supply constraint is structural.",
        category="technology",
        catalyst_types=["subnet_launch","institutional_discovery","narrative_breakout","technical_breakout"],
        activation_keywords=["tao","bittensor","decentralized ai","subnet","ai token","tao pump","bittensor subnet","opentensor","cortex subnet"],
        invalidation_keywords=["bittensor hack","tao regulatory","subnet failure","token unlock cliff","centralization issue"],
        beneficiaries={"crypto":["TAO22974-USD"],"related":["FET-USD","RNDR-USD","OCEAN-USD","GRT6719-USD"]},
        fades={"crypto":[]},
        regime_alignment={"Q1":1.70,"Q2":1.20,"Q3":0.35,"Q4":0.45},
        typical_duration_weeks=6, conviction_ceiling=0.65, pump_risk=0.70,
        confirmation_signals=["tao_volume_spike","subnet_count_increasing","institutional_wallet_activity","tao_above_200dma"],
    ),
    NarrativeTemplate(
        name="ETH Ecosystem / Staking Yield",
        description="ETH staking yield becomes institutional-grade fixed income alternative → massive inflow into ETH and liquid staking protocols.",
        category="cycle",
        catalyst_types=["protocol_upgrade","etf_approval","institutional_adoption","yield_expansion"],
        activation_keywords=["ethereum staking","eth etf","lido","liquid staking","eigenlayer","restaking","eth yield","eth institutional"],
        invalidation_keywords=["eth hack","staking regulation","sec staking","competition layer1"],
        beneficiaries={"crypto":["ETH-USD","ETHA"]},
        fades={"crypto":[]},
        regime_alignment={"Q1":1.60,"Q4":1.20,"Q2":1.00,"Q3":0.30},
        typical_duration_weeks=20, conviction_ceiling=0.70, pump_risk=0.35,
        confirmation_signals=["eth_staking_rate_above_4pct","eth_etf_inflow","eth_tvl_alltime_high"],
    ),
    NarrativeTemplate(
        name="DePIN / Physical Infrastructure Crypto",
        description="Decentralized Physical Infrastructure Networks — crypto projects tokenizing real-world infrastructure (AI compute, wireless, energy). Early cycle, high pump risk but legitimate thesis.",
        category="technology",
        catalyst_types=["product_launch","partnership_announcement","research_breakthrough"],
        activation_keywords=["depin","helium","render network","akash","hivemapper","filecoin","decentralized compute","distributed gpu","io.net"],
        invalidation_keywords=["regulation depin","centralization issue","token unlock","team dump"],
        beneficiaries={"crypto":["RNDR-USD","FET-USD","TAO22974-USD","GRT6719-USD","HNT-USD"]},
        fades={"crypto":[]},
        regime_alignment={"Q1":1.70,"Q2":1.10,"Q3":0.30,"Q4":0.50},
        typical_duration_weeks=12, conviction_ceiling=0.55, pump_risk=0.70,
        confirmation_signals=["rndr_revenue_growth","fetch_ai_enterprise_deals","depin_tvl_growth"],
    ),
    # ── MACRO CYCLE ───────────────────────────────────────────────────────
    # ── RICKY2212 SIKLUS BESAR — 3-SESSION FRAMEWORK ─────────────────────────
    # Ricky's framework: Super-cycle berjalan dalam 3 sesi (pesta).
    # Sesi 1 = 2020-2022 spike (selesai). Sesi 2 = 2023-? recovery/reset (berjalan).
    # Sesi 3 = "The King is Back" = supercycle resumes dengan harga jauh lebih tinggi.
    # "MC pesta akan memanggil lagi masuk ke dalam saat pesta sesi 2 berjalan."
    NarrativeTemplate(
        name="Ricky Sesi 2 — New Cycle Base (Banking + Consumer Recovery)",
        description="""Ricky2212 Sesi 2 framework: Setelah RESET monetary policy, ekonomi membentuk new cycle base.
Banking jadi proxy utama pemulihan (kredit tumbuh, CKPN turun, NIM expand).
Consumer goods/retail recovery karena daya beli pulih. Industrial estate dari relokasi pabrik + data center.
"2023 adalah tahun dimana ekonomi akan membuat pijakan baru setelah semua stimulus dicabut." 
Siklus: Perbankan → Consumer Goods → Industrial Area → Retail.
Signal: BBCA/BBRI/BMRI leading IHSG, BTPS recovery, ACES/KLBF improving, BEST/KIJA industrial area capex.""",
        category="cycle",
        catalyst_types=["bi_rate_cut","rupiah_stability","fed_pivot","china_reopen_demand","consumer_confidence_recovery"],
        activation_keywords=["banking recovery","consumer recovery","industrial estate","kredit tumbuh","BI rate cut","pivot",
                              "bbca","bbri","bmri","btps recovery","consumer durable","industrial relocation","data center jakarta"],
        invalidation_keywords=["NPL melonjak","kredit macet tinggi","rupiah collapse","BI rate hike","consumer sentiment crash"],
        beneficiaries={
            "ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BTPS.JK","BJTM.JK",
                    "KLBF.JK","MYOR.JK","ICBP.JK","INDF.JK","ACES.JK","AMRT.JK",
                    "BEST.JK","KIJA.JK","DMAS.JK","CTRA.JK","BSDE.JK"],
            "us":["XLF","KRE","XLY","COST"],
        },
        fades={"ihsg":["ITMG.JK","ADRO.JK"]},  # cyclical takes backseat in sesi 2
        regime_alignment={"Q1":1.50,"Q4":1.40,"Q2":0.80,"Q3":0.30},
        typical_duration_weeks=52, conviction_ceiling=0.80, pump_risk=0.15,
        confirmation_signals=["bi_rate_cut_confirmed","bbca_lead_ihsg","klbf_aces_margin_recovery",
                               "rupiah_strengthen","industrial_estate_new_tenant_announcement"],
    ),
    NarrativeTemplate(
        name="Ricky Sesi 3 — THE KING IS BACK (Supercycle Resumes)",
        description="""Ricky2212 Sesi 3: "The King is Back" = komoditas supercycle resumes setelah RESET selesai.
"Saat nanti ekonomi masuk gigi 2, gigi 3 dst, apa yang akan terjadi?"
Key thesis: (1) Supply-side underinvestment akut sejak 2015 belum diperbaiki.
(2) China demand resumes fully + India infrastructure boom = demand > supply permanently.
(3) B indicator (Bakrie/Om B) masih pegang + terus akumulasi = signal cycle belum selesai.
(4) OSV/tanker rates spike karena fleet shortage akut (bertahun nganggur → di-scrap → supply habis).
(5) Coal cash machine kembali: ITMG dividend yield 20%+ saat harga normalized $200-250.
"Saya tetap di cyclical karena siklus panjangnya belum berakhir. Hanya butuh di-RESET dulu."
Entry signal: China PMI >52 sustained 3 bulan + coal spot >$200 + BDI (Baltic Dry Index) rally + OSV day rates spike.""",
        category="cycle",
        catalyst_types=["china_demand_recovery","supply_shortage_bites","osv_rate_spike","coal_price_recovery",
                         "underinvestment_thesis","opec_cut","china_property_recovery"],
        activation_keywords=["king is back","supercycle resume","coal recovery","itmg ptba back","b indicator",
                              "osv day rate","baltic dry","china demand","india coal","coal $200","coal $250",
                              "wins lead osv","tanker rate","bdi rally","copper breakout","iron ore recovery",
                              "commodity supercycle","caterpillar glencore","petronas capex","hulu migas"],
        invalidation_keywords=["coal price collapse","china hard landing","india growth stall",
                                "osv oversupply","coal ban permanent","opec surge","china coal surplus"],
        beneficiaries={
            "ihsg":["ITMG.JK","ADRO.JK","PTBA.JK","HRUM.JK","BUMI.JK","DOID.JK",  # coal
                    "WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK","MEDC.JK",              # OSV/hulu
                    "SOCI.JK","TMAS.JK","SMDR.JK","BULL.JK",                        # tanker/shipping
                    "INCO.JK","MDKA.JK","ANTM.JK","NCKL.JK",                        # nickel
                    "DSNG.JK","TAPG.JK","AALI.JK","LSIP.JK"],                       # CPO
            "global":["GLEN.L","CAT","SLB","HAL","BKR","FCX","CLF","RIO","BHP",    # global miners/oil services
                      "TDW","WTCO","SDRL"],                                           # offshore/OSV global
            "commodities":["CL=F","CNA.L","coal_futures","BDI_proxy"],
        },
        fades={"us":["TLT","XLU","QUAL","XLP"]},
        regime_alignment={"Q2":1.80,"Q3":1.20,"Q1":0.90,"Q4":0.15},
        typical_duration_weeks=104,  # multi-year cycle
        conviction_ceiling=0.85, pump_risk=0.30,
        confirmation_signals=["coal_spot_above_200","bdi_above_2000","osv_utilization_above_85pct",
                               "china_pmi_above_52_3months","b_indicator_buying","caterpillar_ath",
                               "glencore_ath","copper_above_10000","itmg_adro_foreign_net_buy"],
    ),
    NarrativeTemplate(
        name="Ricky OSV Supercycle — Offshore Support Vessel Shortage",
        description="""Ricky2212's deepest thesis: OSV (Offshore Support Vessel) supply shortage akut.
"1 dekade underinvestment → kapal di-scrap → supply habis. Pengeboran offshore mau dimulai tapi kapal ga ada."
Thesis: ESG campaign 2015 → no funding → companies went bankrupt → fleet scrapped.
Now: energy shortage → offshore drilling revives → OSV demand spikes → NOT ENOUGH BOATS.
New orders = ZERO (bikin kapal butuh 3 tahun). So existing fleet = monopoly pricing.
Petronas mega capex announcement + Indonesia ESDM 1jt BPD 2030 target = demand catalyst.
Wintermar (WINS) & Logindo (LEAD) = dominant Indonesia OSV players. Utilization trending 85%+.
History: NPM 30%+ at peak (LEAD); recovery from chapter-11/scrapping era.
"Tidak akan ada supply baru selama 3 tahun ke depan. Kapal yang ada PASTI dicari." """,
        category="commodity",
        catalyst_types=["offshore_drilling_ramp","petronas_capex","indonesia_oil_target","osv_day_rate_spike",
                         "new_contract_win","fleet_utilization_surge"],
        activation_keywords=["osv offshore","offshore support vessel","wins lead","logindo wintermar",
                              "day rate osv","petronas capex","offshore drilling","hulu migas",
                              "oil field development","rig utilization","tidewater pubex","jackup rig",
                              "subsea installation","dynamic positioning","ahts psv"],
        invalidation_keywords=["osv oversupply","new build flood","oil price crash","offshore moratorium",
                                "petronas capex cut","indonesia oil miss"],
        beneficiaries={
            "ihsg":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK","BBRI.JK"],
            "global":["TDW","VAL","SDRL","DO","RIG","BHGE","SLB","HAL","BKR"],
        },
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.60,"Q1":1.20,"Q3":0.80,"Q4":0.25},
        typical_duration_weeks=78, conviction_ceiling=0.80, pump_risk=0.25,
        confirmation_signals=["osv_day_rate_above_15000usd","wins_lead_new_contract","petronas_capex_announcement",
                               "bkr_rig_count_offshore_rising","wins_utilization_above_80pct"],
    ),
    NarrativeTemplate(
        name="Ricky CPO Supercycle — Palm Oil Best-in-Class (DSNG/TAPG/STAA)",
        description="""Ricky2212 CPO methodology: Bukan sekedar beli CPO play — beli yang punya edge.
"Saat kenaikan CPO, siapa yang paling diuntungkan? Yang punya OER tertinggi dan profil tanaman termuda."
Best-in-class ranking (Ricky): TAPG=DSNG=STAA > LSIP > AALI >> SGRO > SIMP >> BWPT.
Key metrics: (1) OER (Oil Extraction Rate) — TAPG/DSNG 24-25% vs average 20-21%.
(2) Profil tanaman: usia prime 8-15 tahun = produksi maksimal.
(3) Lahan inti dominan (>85%) vs plasma. (4) Ekspansi organik aktif.
Catalysts: La Nina weather event (reduced supply), biodiesel mandate B40+, China demand recovery,
India cooking oil import, dedolarisasi membuat soft commodities naik, Rusia-Ukraina gandum disruption.
"OER tinggi + usia tanaman prime = leverage terbesar saat CPO naik. Bukan hanya luas lahan." """,
        category="commodity",
        catalyst_types=["la_nina_weather","biodiesel_mandate","india_india_import","china_demand",
                         "sunflower_substitution","palm_supply_disruption"],
        activation_keywords=["cpo palm oil","kelapa sawit","palm oil price","dsng tapg staa","oer extraction",
                              "biodiesel b40","la nina","bursa malaysia cpo","indian vegetable oil",
                              "sunflower ukraine","malaysia inventory","indonesia export"],
        invalidation_keywords=["esg boycott permanent","palm oil ban","oversupply","replanting peak",
                                "india import duty","biofuel mandate reduced"],
        beneficiaries={
            "ihsg":["TAPG.JK","DSNG.JK","SSMS.JK","LSIP.JK","AALI.JK","SGRO.JK"],
            "global":["KLK.KL","IOI.KL","SDPL.KL"],
        },
        fades={"ihsg":["BWPT.JK","SIMP.JK"]},
        regime_alignment={"Q2":1.70,"Q1":1.10,"Q3":0.80,"Q4":0.20},
        typical_duration_weeks=26, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["cpo_bmde_above_4000","dsng_tapg_oer_beats","biodiesel_mandate_increase",
                               "india_malaysia_import_surge","inventory_bursa_malaysia_low"],
    ),
    NarrativeTemplate(
        name="Ricky Tanker & Shipping Cycle",
        description="""Ricky2212 shipping thesis: Perang → rute memutar → SCARCITY kapal → tarif spike.
"Rute yang biasanya langsung sekarang harus muter jauh. Kapal yang ada ga cukup. Tarif terbang."
Sesi 1: Container (SMDR, TMAS) — 2020-2022 — SELESAI. Return 10x+ di SMDR.
Sesi 2: Crude/Product Tanker (SOCI, BULL) — Rusia → rerouting crude → dirty+clean tanker rates.
Sesi 3: OSV (WINS, LEAD) — offshore drilling revival → see separate OSV narrative.
Current focus: Product tanker (clean) + crude tanker (dirty). Baltic Clean/Dirty Tanker Index.
SOCI punya VLCC — satu-satunya di Indonesia — leverage tertinggi ke global crude flow.
"Kapal tanker itu bukan bisnis volume, bisnis TIMING dan SCARCITY." """,
        category="commodity",
        catalyst_types=["war_oil_rerouting","opec_cut","russia_sanctions","suez_canal_closure",
                         "red_sea_disruption","houthi_attack","iran_hormuz","tanker_shortage"],
        activation_keywords=["tanker rates","baltic dirty","baltic clean","crude tanker","product tanker",
                              "soci bull","vlcc aframax","dirty tanker","clean tanker","shipping rates",
                              "iran sanctions","russia crude","opec rerouting","houthi red sea","suez tanker"],
        invalidation_keywords=["tanker oversupply","ceasefire","oil demand crash","new tanker delivery flood",
                                "peace deal russia ukraine","opec surge"],
        beneficiaries={
            "ihsg":["SOCI.JK","BULL.JK","TMAS.JK","SMDR.JK","PSSI.JK"],
            "global":["FRO","STNG","TNK","TEN","INSW","DHT","NAT"],
        },
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.50,"Q3":1.30,"Q1":0.80,"Q4":0.20},
        typical_duration_weeks=26, conviction_ceiling=0.75, pump_risk=0.30,
        confirmation_signals=["bct_baltic_dirty_above_1500","soci_new_contract","tanker_utilization_above_90",
                               "red_sea_escalation","russia_crude_sanctions_tighten"],
    ),
    NarrativeTemplate(
        name="Ricky Gold — I'm to G-old for this Game",
        description="""Ricky2212 gold thesis (Jan 2023): "Central Bank memborong emas dalam fastest pace 55 tahun."
Core thesis: (1) Fed sadar target 2% inflasi tidak achievable → akan raise target ke 3% → accommodative.
(2) De-dollarization: China + Russia + India + OPEC transact in yuan/rupee → dollar loses dominance.
(3) Central banks ADD gold reserves to hedge against dollar debasement (Russia 2299T, China 1949T+).
"Saat central bank menyerah dari target inflasi 2%, emas adalah hedge terbaik."
"Dollar akan dikebiri oleh amrik sendiri."
Indonesia exposure: emas sebagai lindung nilai + ANTM/MDKA sebagai leveraged play.
Trigger: Bill Gross statement "raise inflation target to 3%" = confirmasi thesis.
Current 2026 status: Gold at/near ATH — King of the Cycle.""",
        category="commodity",
        catalyst_types=["fed_inflation_target_change","central_bank_buying","dedollarization","dollar_weakness",
                         "geopolitical_risk","deficit_expansion","real_yield_fall"],
        activation_keywords=["gold central bank buying","dedollarization","gold reserve","yuan trade settlement",
                              "gold ath","real yields fall","fed target 3%","dollar weakness gold",
                              "antm gold","mdka gold","petroyuan","saudi yuan","brics gold"],
        invalidation_keywords=["dollar surge","real yield spike","fed hawkish surprise","gold dump",
                                "china gold selling","imf sdr gold"],
        beneficiaries={
            "ihsg":["ANTM.JK","MDKA.JK","BRMS.JK"],
            "global":["GLD","GC=F","NEM","GOLD","AEM","WPM","FNV","RGLD"],
            "commodities":["GC=F","GLD","SLV"],
        },
        fades={"us":["TLT","BND"]},
        regime_alignment={"Q3":1.80,"Q4":1.60,"Q2":1.20,"Q1":0.60},
        typical_duration_weeks=52, conviction_ceiling=0.90, pump_risk=0.10,
        confirmation_signals=["gold_above_2500","central_bank_gold_buying_sustained",
                               "fed_raise_inflation_target","dedollarization_opec_deal",
                               "real_yields_negative_or_falling"],
    ),
    NarrativeTemplate(
        name="K-Shaped Economy Fourth Turning",
        description="SPX at ATH but Michigan Sentiment at 74-year low. Financial asset owners vs wage earners gap is widest ever. 'The brands of my youth are dead men walking.' (McCullough). THIS is Structural Q3 backdrop.",
        category="cycle",
        catalyst_types=["consumer_sentiment_collapse","credit_card_stress","delinquency_rise","luxury_beat","discount_miss"],
        activation_keywords=["k-shaped economy","consumer bifurcation","sentiment low","credit stress","fourth turning","wealth inequality","luxury vs discount","consumer squeeze"],
        invalidation_keywords=["consumer confidence surge","wage growth accelerates","middle class spending revival","credit stress eases"],
        beneficiaries={"us":["XLV","XLI","COST","NVO","LLY"]},
        fades={"us":["XLP","KSS","M","legacy_retail","XLY"]},
        regime_alignment={"Q1":0.40,"Q2":0.60,"Q3":0.85,"Q4":0.70},
        typical_duration_weeks=52, conviction_ceiling=0.70, pump_risk=0.05,
        confirmation_signals=["consumer_sentiment_new_low","credit_card_delinquency_rising","luxury_earnings_beat","mass_market_miss"],
    ),
]

NARRATIVE_BY_NAME: Dict[str, NarrativeTemplate] = {n.name: n for n in _NARRATIVES}
NARRATIVES_BY_CATEGORY: Dict[str, List[NarrativeTemplate]] = {}
for _n in _NARRATIVES:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

def get_all_narratives() -> List[NarrativeTemplate]:
    return _NARRATIVES

def get_by_quad(quad: str) -> List[NarrativeTemplate]:
    """Get narratives sorted by alignment to given quad."""
    return sorted(_NARRATIVES, key=lambda n: n.regime_alignment.get(quad, 0.5), reverse=True)

def get_by_market(market: str) -> List[NarrativeTemplate]:
    """Get narratives that have beneficiaries in given market."""
    return [n for n in _NARRATIVES if market in n.beneficiaries]
