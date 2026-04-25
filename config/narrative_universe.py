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

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 2 — RICKY2212 EXHAUSTIVE EXTRACTION + CITRINI + HEDGEYE ADDITIONS
# Mining 40k-word article for ALL distinct investable theses
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVES_BATCH2: List[NarrativeTemplate] = [

    # ── RICKY2212: SPECIFIC IHSG PLAYS ────────────────────────────────────────

    NarrativeTemplate(
        name="BTPS Bank Syariah Turnaround",
        description="""Ricky2212's highest-conviction banking thesis.
\"Bank dengan model bisnis paling unik di bursa. Entry barrier sangat tinggi — sistem jemput bola 
ke nasabah mikro. TIDAK bisa ditiru bank lain.\"
Thesis: CKPN peak → provisioning cycle ends → NIM tertinggi di perbankan kembali mengkilap.
\"Bukan perubahan bisnis — hanya perubahan PERSEPSI. Saat persepsi hilang, harga jatuh irasional.\"
Ricky masuk BTPS sejak 5 tahun lalu — time frame: TIDAK UNTUK DIJUAL (legacy holding).
\"Saat CKPN sdh membaik, anda ga akan mendapatkan harga diskon lagi.\"
Trigger: CKPN provisioning turun 2 quarter berturut + NIM kembali ke 30%+ + 
nasabah baru acquisition cost normalisasi.""",
        category="cycle",
        catalyst_types=["ckpn_peak","nim_recovery","bi_rate_cut","micro_credit_demand","provisioning_normalization"],
        activation_keywords=["btps bank syariah","bank syariah indonesia","npl peak","ckpn turun",
                              "micro credit recovery","jemput bola","ultra mikro","syariah banking turnaround",
                              "btps recovery","bri syariah","bank syariah"],
        invalidation_keywords=["btps ckpn naik lagi","syariah credit crisis","bi tightening","npl surge btps"],
        beneficiaries={"ihsg":["BTPS.JK","BRIS.JK","BMSI.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.70,"Q4":1.50,"Q2":0.80,"Q3":0.25},
        typical_duration_weeks=52, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["btps_ckpn_declining","btps_nim_above_30","btps_nasabah_growth_resumes",
                               "btps_roa_improving","micro_lending_delinquency_fall"],
    ),

    NarrativeTemplate(
        name="BUMI / Bakrie 'Om B' Cycle — The Market Maker at Work",
        description="""Ricky2212's most sophisticated IHSG thesis — Om B sebagai PEDAGANG bukan investor.
\"Dia dagang HANYA saat ada moment. Saat toko dibuka, itu sinyal siklus berjalan.\"
Framework: Om B exit via Nat Rothschild 2007 → rente ke perusahaan sendiri saat siklus buruk → 
hutang menumpuk → OWK diterbitkan → Om B borong OWK murah → saat siklus baik dia konversi jadi saham →
mega jumbo PP 24T (Salim masuk) → toko dibuka → harga naik → Om B jual ke fund asing.
\"B indicator: selama Om B belum tutup toko, siklus masih berjalan.\"
Signal terbaru: PP 24T Rp120/saham + Salim masuk via Agus Projo = KARPET MERAH = sesi baru.
Korelasi: BUMI rally = institutional fund asing masuk = coal supercycle dikonfirmasi.
BUKAN saham untuk investasi murni — ini TRADING play mengikuti Om B.""",
        category="cycle",
        catalyst_types=["bumi_pp_announcement","salim_masuk","owk_conversion","institutional_buying",
                         "coal_cycle_resume","b_indicator_signal"],
        activation_keywords=["bumi resources","bumi b indicator","bakrie","owk konversi","pp bumi",
                              "salim bumi","agus projo bumi","bumi rights issue","bumi institutional",
                              "b indicator coal","bakrie akumulasi","bumi asing net buy"],
        invalidation_keywords=["bumi delisting","bakrie court case","coal ban permanent","b indicator tutup toko"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","ENRG.JK","DOID.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.60,"Q3":1.10,"Q1":0.80,"Q4":0.10},
        typical_duration_weeks=26, conviction_ceiling=0.65, pump_risk=0.70,
        confirmation_signals=["bumi_foreign_net_buy_sustained","owk_conversion_accelerating",
                               "bumi_institutional_14f_filing","coal_spot_above_180"],
    ),

    NarrativeTemplate(
        name="IHSG Industrial Estate — Data Center Relocation + EV Factory Wave",
        description="""Ricky2212 industrial estate thesis: 3 concurrent catalysts creating unprecedented demand.
(1) DATA CENTER: Singapore moratorium on new data centers → Indonesia jadi tujuan utama.
(2) EV FACTORY: Produsen EV global bangun pabrik baru → butuh industrial land + infrastruktur.
(3) ONSHORING: Supply chain diversification dari China → Southeast Asia.
\"Kawasan industri adalah proxy kebangkitan ekonomi. Saat ekonomi bangkit, manufaktur ekspansi.\"
Best picks: BEST (Bekasi Fajar) = Ricky's pick karena infrastructure paling siap. 
KIJA (Jababeka), DMAS (Puradelta).
Mas Rizza's BEST thesis: asset play + data center story = beli di 100-130, target 300+.
\"Asset play luar biasa murah + story data center = once in a decade setup.\" """,
        category="cycle",
        catalyst_types=["data_center_singapore_moratorium","ev_factory_announcement",
                         "supply_chain_relocation","foreign_direct_investment"],
        activation_keywords=["industrial estate","kawasan industri","data center jakarta",
                              "best bekasi fajar","kija jababeka","dmas puradelta",
                              "ev factory indonesia","google data center","hyperscaler indonesia",
                              "manufacturing relocation","fdi industrial","special economic zone"],
        invalidation_keywords=["industrial land oversupply","fdi freeze","ev demand crash",
                                "data center moratorium lifted"],
        beneficiaries={"ihsg":["BEST.JK","KIJA.JK","DMAS.JK","SSIA.JK","MMLP.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.60,"Q4":1.40,"Q2":0.90,"Q3":0.30},
        typical_duration_weeks=78, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["google_microsoft_data_center_jakarta","ev_oem_land_acquisition_ihsg",
                               "fdi_investment_hit_record","best_kija_new_tenant_announcement"],
    ),

    NarrativeTemplate(
        name="IHSG Consumer Goods Margin Recovery",
        description="""Ricky2212: \"Consumer goods babak belur 2022-2023 terpukul BBM naik + inflasi.\"
\"2023 akan menjadi titik balik. Daya beli konsumen perlahan pulih. Margin membaik.\"
Dua driver bersamaan: (1) Revenue recovery karena spending pulih pasca BBM shock.
(2) Margin expansion karena input cost (minyak sawit, gandum, plastik) turun dari peak.
\"Kombinasi volume naik + margin naik = leverage laba tinggi.\"
Best picks dari Ricky: cari perusahaan yang punya POSITIONING dan HISTORY CHAMPION.
ICBP (Indofood CBP), KLBF (Kalbe), MYOR (Mayora), SIDO (Sido Muncul).
\"Consumer good tidak punya siklus seperti komoditas — lebih steady, lebih predictable.\" """,
        category="cycle",
        catalyst_types=["bi_rate_cut","rupiah_strengthen","consumer_confidence_recovery",
                         "input_cost_deflation","bbm_subsidy_recovery"],
        activation_keywords=["consumer goods margin","fmcg recovery","icbp klbf margin expand",
                              "myor mayora recovery","sido muncul","consumer spending indonesia",
                              "daya beli pulih","bbm stable","food inflation cooling","retail sales recover"],
        invalidation_keywords=["bbm naik lagi","consumer confidence crash","input cost surge","rupiah collapse"],
        beneficiaries={"ihsg":["ICBP.JK","INDF.JK","KLBF.JK","MYOR.JK","SIDO.JK","ULTJ.JK","CMRY.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.50,"Q4":1.40,"Q2":0.70,"Q3":0.20},
        typical_duration_weeks=52, conviction_ceiling=0.75, pump_risk=0.15,
        confirmation_signals=["klbf_icbp_margin_beat","consumer_confidence_index_rising",
                               "retail_sales_3month_trend_up","input_cost_cpo_wheat_stable"],
    ),

    NarrativeTemplate(
        name="IHSG Modern Retail Rebound (ACES / AMRT / MAPI)",
        description="""Ricky2212: \"Retail kena pukulan paling telak sejak pandemic + kenaikan BBM.\"
\"2023 adalah saat titik balik — semakin babak belur, semakin menarik saat recovery datang.\"
Om Robert's thesis: ACES dibeli dari 700 lalu hajar besar di 450 → return ke 900+.
\"Beli saham saat diskon dan diobral. Beli saat keadaan sedang tidak berpihak.\"
ACES: raja modern living retail. Cash reserve besar. Margin bersih di atas rata-rata retail.
AMRT: Alfamart — proxy consumer spending paling luas (jaringan 17,000+ gerai).
MAPI: premium retail exposure.
Signal: same-store-sales recovery + gross margin expansion + consumer credit normalization.""",
        category="cycle",
        catalyst_types=["consumer_confidence_recovery","daya_beli_pulih","modern_retail_traffic",
                         "same_store_sales_recovery","credit_normalization"],
        activation_keywords=["aces hardware","amrt alfamart","mapi retail","modern retail recovery",
                              "same store sales","retail traffic","consumer spending ihsg",
                              "daya beli","retail modern","indomaret alfamart"],
        invalidation_keywords=["consumer recession","retail margin squeeze","ecommerce disruption",
                                "minimum wage impact","BBM naik lagi"],
        beneficiaries={"ihsg":["ACES.JK","AMRT.JK","MAPI.JK","ERAA.JK","HERO.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.60,"Q4":1.40,"Q2":0.70,"Q3":0.15},
        typical_duration_weeks=39, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["aces_same_store_sales_positive","amrt_revenue_acceleration",
                               "retail_sssg_beat_2quarters","consumer_credit_stable"],
    ),

    NarrativeTemplate(
        name="IHSG Property / KPR Recovery (BTN + Developers)",
        description="""Ricky2212 mentions BTN (Bank BTN) as housing specialist. BI rate cut = KPR cheaper.
\"Saat suku bunga turun, cicilan KPR turun → more Indonesians can afford housing.\"
China property QE precedent: Indonesia property sector could see same stimulus.
BTBN = proxy KPR pasar menengah bawah + subsidi rumah program.
Developer: CTRA, BSDE, PWON, SMRA as beneficiaries of rate cut + pent-up demand.
Ricky's framework: perbankan → consumer goods → industrial area → PROPERTI sebagai siklus lanjutan.
Catalyst: BI rate cuts sustained 3x+ + KPR rate < 8% + Tapera program.""",
        category="cycle",
        catalyst_types=["bi_rate_cut","kpr_rate_decline","subsidized_housing_program",
                         "urbanization","government_property_stimulus"],
        activation_keywords=["kpr rate cut","property indonesia","btn kpr","citra property",
                              "bsde pwon smra","properti ihsg","rumah subsidi","tapera","perumahan"],
        invalidation_keywords=["bi rate hike","property oversupply","kpr delinquency","rupiah weak"],
        beneficiaries={"ihsg":["BBTN.JK","CTRA.JK","BSDE.JK","PWON.JK","SMRA.JK","DMAS.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.50,"Q4":1.60,"Q2":0.60,"Q3":0.20},
        typical_duration_weeks=52, conviction_ceiling=0.70, pump_risk=0.25,
        confirmation_signals=["bi_cut_3x_confirmed","kpr_rate_below_8pct","btn_kredit_growth_accelerate",
                               "property_sales_volume_rising","tapera_launch"],
    ),

    NarrativeTemplate(
        name="IHSG Tourism / Pariwisata Recovery",
        description="""Post-COVID tourism recovery thesis for Indonesia. China re-open = tourist wave.
Ricky briefly mentions pariwisata as portfolio component (small position due to liquidity).
Indonesia = 10th largest tourism destination globally pre-COVID. Bali + Labuan Bajo.
China tourists = historically #1 foreign visitors to SE Asia → return post-zero-COVID.
\"Perumahan + pariwisata + consumer = trifecta recovery saat ekonomi membuat base baru.\"
Beneficiaries: PNBN (Hotel), INPP, PGAS/HITS (leisure + infrastructure).
Global context: cruise lines, SE Asia hotel chains recovering faster than expected.""",
        category="cycle",
        catalyst_types=["china_reopen_travel","visa_free_expansion","airline_capacity_restoration",
                         "bali_labuan_bajo_tourism","g20_indonesia"],
        activation_keywords=["pariwisata indonesia","bali tourism","china tourist return","inbound tourism",
                              "hotel occupancy","GIAA garuda","PNBN","airline recovery","tourism recovery"],
        invalidation_keywords=["tourism ban","pandemic restriction","yuan weak","flight capacity cut"],
        beneficiaries={"ihsg":["INPP.JK","PNBN.JK","WSKT.JK","GIAA.JK"],
                       "global":["BKNG","ABNB","H","MAR"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.40,"Q4":1.20,"Q2":0.80,"Q3":0.30},
        typical_duration_weeks=39, conviction_ceiling=0.65, pump_risk=0.30,
        confirmation_signals=["china_outbound_travel_record","bali_hotel_occupancy_above_80",
                               "indonesia_tourist_arrivals_pre_covid_level"],
    ),

    # ── RICKY2212: GLOBAL MACRO THESES ────────────────────────────────────────

    NarrativeTemplate(
        name="Oil Crack Spread Normalization → Inflation Moderation",
        description="""Ricky2212's key insight: 2022 inflation had TWO components — crude price AND refinery margin.
\"Harga minyak naik + biaya refinery (oil crack) melonjak = BBM konsumen kena double punch.\"
Now: crack spread has collapsed back to normal → even if crude rebounds, 
end-user inflation impact is MUCH less severe.
\"Konsumen tidak perlu bayar mahal seperti kemarin. Satu bottleneck sdh terpecahkan.\"
This is WHY oil $100 in next cycle ≠ inflation 9% again.
Dashboard implication: GIP model should weight inflation signal less aggressively 
when crack spreads are normalized. Fed can tolerate oil at $90-100.
Proxy: crack spread via $CLR vs $CL=F, or RBOB-crude spread.""",
        category="commodity",
        catalyst_types=["crack_spread_normalization","refinery_capacity_restored",
                         "supply_chain_bottleneck_resolved","oil_demand_moderate"],
        activation_keywords=["oil crack spread","refinery margin","rbob crack","diesel crack",
                              "oil inflation moderation","crack spread collapse","refinery utilization",
                              "gasoline crack","heating oil crack","petroleum product margin"],
        invalidation_keywords=["crack spread surge","refinery shutdown","hurricane season hit",
                                "product shortage","europe energy crisis"],
        beneficiaries={"us":["PSX","VLO","MPC","DK"],
                       "commodities":["RBOB_crack","HO_crack"]},
        fades={"commodities":[]},
        regime_alignment={"Q1":0.80,"Q2":0.90,"Q3":1.20,"Q4":0.60},
        typical_duration_weeks=26, conviction_ceiling=0.65, pump_risk=0.20,
        confirmation_signals=["crack_spread_below_20usd","refinery_utilization_above_90",
                               "gasoline_inventory_normal","cpi_energy_decelerating"],
    ),

    NarrativeTemplate(
        name="US SPR Refill Trade + OPEC Supply Management",
        description="""Ricky2212: \"SPR amrik sdh berada pada level terendah lebih dari 30 tahun.\"
\"Ada peraturan batas minimum yang harus mereka jaga. Mereka HARUS isi ulang.\"
SPR refill = government MUST buy crude at market price = guaranteed buyer = price floor.
OPEC+ counter: Saudi saying \"watch out\" = they'll cut further to defend price.
Ricky: \"Amrik mati-matian menghabiskan SPR untuk tekan harga minyak. Tapi sampai kapan?\"
Two forces: US wants cheap oil (refill SPR cheap), OPEC wants high price (defend fiscal break-even).
Net result: oil has structural price floor + OPEC discipline = $70-90 base case sustained.
This is DIFFERENT from simple bullish oil — it's about DURATION of elevated prices.""",
        category="commodity",
        catalyst_types=["spr_refill_announcement","opec_cut_extension","us_energy_policy",
                         "geopolitical_supply_risk","strategic_reserve_replenishment"],
        activation_keywords=["spr refill","strategic petroleum reserve","opec cut","saudi aramco",
                              "oil price floor","eia spr level","us crude purchase","opec discipline",
                              "prince abdulaziz","opec basket price","brent floor"],
        invalidation_keywords=["opec overproduction","us shale surge","demand destruction",
                                "spr sale extended","iran deal crude surge"],
        beneficiaries={"us":["XLE","XOM","CVX","COP","OXY","SLB"],
                       "commodities":["CL=F","BZ=F"]},
        fades={"us":["TLT","XLP"]},
        regime_alignment={"Q2":1.50,"Q3":1.30,"Q1":0.90,"Q4":0.30},
        typical_duration_weeks=26, conviction_ceiling=0.75, pump_risk=0.25,
        confirmation_signals=["doe_spr_purchase_announcement","opec_cut_85pct_compliance",
                               "wti_hold_above_70","saudi_fiscal_break_even_respected"],
    ),

    NarrativeTemplate(
        name="De-dollarization / Petroyuan — Dollar Hegemony Decline",
        description="""Ricky2212's geopolitical thesis: \"Dollar akan kehilangan dominasinya. 
China + Russia + India + OPEC bertransaksi pakai yuan/rupee → dollar loses trade currency role.\"
\"Kejatuhan dollar akan trs berjalan di depan. Amrik adalah singa tua yang mulai ompong.\"
Key evidence: (1) Saudi Arabia considering yuan payment for oil.
(2) India-Russia rupee/ruble trade. (3) China-Gulf petro-yuan deal.
(4) BRICS expansion (Saudi, UAE, Iran, Ethiopia, Egypt, Argentina invited).
Asset implications: Dollar structural decline → EM FX relief → gold (already thesis) → 
commodity currencies (AUD, CAD, NOK, BRL, IDR) → EM equities re-rating.
\"Kenaikan target inflasi Fed ke 3% + de-dollarization = USD structurally weaker for years.\" """,
        category="geopolitical",
        catalyst_types=["petroyuan_agreement","brics_expansion","imf_sdr_reform",
                         "opec_yuan_settlement","dollar_reserve_share_decline"],
        activation_keywords=["de-dollarization","petroyuan","brics currency","yuan trade",
                              "dollar hegemony","usd reserve currency","saudi yuan",
                              "india russia rupee","imf sdr","global south dollar",
                              "dollar decline","bretton woods","gold backing"],
        invalidation_keywords=["dollar surge","china yuan crisis","brics collapse","fed hawkish indefinite"],
        beneficiaries={"global":["GLD","GC=F","GLDM","IAU","EEM","VWO","DBC","PDBC"],
                       "fx":["AUDUSD=X","USDCAD=X","USDBRL=X","USDIDR=X"],
                       "commodities":["GC=F","SLV","CU=F"]},
        fades={"us":["UUP","DXY"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":1.20,"Q1":0.60},
        typical_duration_weeks=260, conviction_ceiling=0.70, pump_risk=0.15,
        confirmation_signals=["dollar_global_reserve_share_below_55",
                               "opec_yuan_settlement_confirmed","brics_currency_pilot_launch",
                               "gold_central_bank_buying_sustained_2years"],
    ),

    NarrativeTemplate(
        name="Dry Bulk / Baltic Dry Index Recovery — China Activity Bellwether",
        description="""Ricky2212: \"Baltic Dry Index rally 15 hari berturut-turut tanpa henti = ekonomi gerak.\"
\"Kapal dry bulk mengangkut copper, coal, iron ore. Kalo hancur, mana ada aktivitas di dry bulk.\"
BDI is THE most real-time indicator of China industrial activity — can't be faked.
Ricky uses BDI as confirmation tool: \"Saat BDI rally, itu konfirmasi Sesi 3 approaching.\"
Dry bulk carriers: PSSI (Indonesia's largest, TnB + vessel), TPMA, MBSS.
Global: GOGL, SBLK, NMM.
\"Delivery dan aktivitas ekonomi yang sesungguhnya tercermin di BDI — bukan di headline GDP China.\" """,
        category="commodity",
        catalyst_types=["china_iron_ore_demand","china_coal_import","india_infrastructure",
                         "grain_trade_recovery","bdi_breakout"],
        activation_keywords=["baltic dry index","bdi rally","dry bulk","capesize","panamax",
                              "pssi tpma mbss","gogl sblk","dry bulk recovery","iron ore china",
                              "coal shipping","grain shipping","capsize rally","drybulk rates"],
        invalidation_keywords=["bdi collapse","china demand crash","dry bulk oversupply",
                                "new vessel delivery flood","china iron ore inventory surge"],
        beneficiaries={"ihsg":["PSSI.JK","TPMA.JK","MBSS.JK"],
                       "global":["GOGL","SBLK","NMM","EGLE","SB"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.60,"Q1":1.20,"Q3":0.80,"Q4":0.20},
        typical_duration_weeks=26, conviction_ceiling=0.75, pump_risk=0.35,
        confirmation_signals=["bdi_above_2000_sustained","china_iron_ore_import_monthly_high",
                               "capesize_rate_above_15000","pssi_mbss_new_contract"],
    ),

    NarrativeTemplate(
        name="Coal RESET Bottom — Buy Max Pessimism (ATH-50% Rule)",
        description="""Ricky2212's contrarian coal thesis: \"Stay Coal Stay Cool Stay Calm.\"
\"Harga coal sudah dipaksa turun oleh monetary policy — ini SEMENTARA, bukan akhir siklus.\"
ATH $400+ → reset ke $200-250 = normalize. At $200, ITMG still yields 10-20% dividen.
\"Dengan harga batubara $200, ITMG dijual 7x laba. Back to reality, back to normal.\"
This is the ENTRY POINT narrative — not a bullish thesis yet, but a VALUE thesis.
\"Panitia pesta istirahat. Sesi 2 menuju puncak acara. Kita tunggu MC panggil masuk ke dalam.\"
Key: coal supply structure (underinvestment) + demand (Asia power deficit) unchanged.
Just monetary policy suppressing demand temporarily. When policy eases → Sesi 3.
Market behaviour: saat semua pada berteriak coal selesai → that's the buy signal.""",
        category="commodity",
        catalyst_types=["coal_bottom_formation","sentiment_extreme_pessimism",
                         "china_coal_import_resuming","itmg_dividend_yield_double_digit"],
        activation_keywords=["coal reset bottom","coal valuasi murah","itmg dividend yield",
                              "coal di $200","coal at trough","coal sentiment worst",
                              "coal buy contrarian","thermal coal bottom","coal undervalued",
                              "coal ex dividend","itmg ptba adro cheap"],
        invalidation_keywords=["coal secular decline","china coal self-sufficient",
                                "coal $150 broken","itmg dividend cut"],
        beneficiaries={"ihsg":["ITMG.JK","PTBA.JK","ADRO.JK","HRUM.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q4":1.40,"Q3":1.20,"Q2":0.90,"Q1":0.60},
        typical_duration_weeks=13, conviction_ceiling=0.75, pump_risk=0.35,
        confirmation_signals=["coal_spot_200_250_range_stable","itmg_div_yield_above_10",
                               "sentiment_negative_news_peak","china_restart_australia_coal"],
    ),

    NarrativeTemplate(
        name="Indonesia Hulu Migas Recovery — ELSA + MEDC + ESSA",
        description="""Ricky2212 hulu migas thesis (separate from OSV):
\"Aktivitas hulu migas di Indonesia mengalami peningkatan luar biasa. Indo hanya suka lagging.\"
Indonesia ESDM target: 1 juta BPD minyak + 12 Bscfd gas by 2030.
RUU Migas baru (insentif baru) → raksasa minyak dunia mau investasi lagi.
\"Petronas sebagai dominant player Asia Tenggara sdh announce mega jumbo capex 2023.\"
Play: ELSA (pemetaan/seismik) + MEDC (pemegang konsesi) + ESSA (gas hulu) + ENRG.
Different from OSV: ini tentang SIAPA yang PUNYA sumurnya, bukan yang service-nya.
\"Kalo ada pengeboran, ada yang untung dari royalti/split. Itulah pemain hulu kita.\" """,
        category="commodity",
        catalyst_types=["petronas_capex","indonesia_lifting_target","esdm_drilling_approval",
                         "ruu_migas_insentif","oil_feasibility_price"],
        activation_keywords=["hulu migas","elsa elnusa","medc medco","essa gas hulu",
                              "petronas indonesia","oil lifting target","1jt bpd",
                              "seismic survey","production sharing contract","blok migas",
                              "east kalimantan gas","natuna","masela"],
        invalidation_keywords=["oil price crash","indonesia lifting miss","ruu migas stalled",
                                "esdm reject block","capex freeze"],
        beneficiaries={"ihsg":["ELSA.JK","MEDC.JK","ESSA.JK","ENRG.JK","RUIS.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.50,"Q1":1.10,"Q3":0.80,"Q4":0.25},
        typical_duration_weeks=52, conviction_ceiling=0.70, pump_risk=0.30,
        confirmation_signals=["petronas_block_award_indonesia","elsa_new_seismic_contract",
                               "indonesia_oil_lifting_increase","medc_production_target_beat"],
    ),

    # ── CITRINI RESEARCH THESES ────────────────────────────────────────────────

    NarrativeTemplate(
        name="Citrini — AI White-Collar Disruption Bear (Labor Market Shock)",
        description="""Citrini Research's landmark 2026 thesis that triggered global market selloff.
Key claim: AI will cut 5% of white-collar workers within 18 months.
\"White-collar workers = 50% of employment, drive 75% of discretionary consumer spending.\"
If true: consumer spending collapses → GDP shock → earnings miss for discretionary names.
Short thesis: companies dependent on white-collar consumer spending.
Long thesis: semiconductor/AI infrastructure that enables the disruption.
Citrini: \"We generally have a set of shorts against businesses disrupted by AI.
On the other side, we own semiconductors that benefit.\"
Cross-asset implication: stagflation risk if productivity gains don't offset income loss fast enough.""",
        category="technology",
        catalyst_types=["mass_layoffs_white_collar","ai_automation_announcement",
                         "unemployment_spike","earnings_miss_discretionary"],
        activation_keywords=["ai job displacement","white collar automation","ai layoffs",
                              "mass layoffs tech","ai replace workers","citrini ai disruption",
                              "automation unemployment","ai gdp impact","worker displacement"],
        invalidation_keywords=["ai hype dies","regulatory ai ban","productivity offset jobs",
                                "full employment despite ai","ai winter"],
        beneficiaries={"us":["NVDA","AMD","AVGO","TSM","AMAT","KLAC","META","MSFT","GOOG"]},
        fades={"us":["SBUX","MCD","CMG","BKNG","EXPE","retail_exposed_to_white_collar"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=78, conviction_ceiling=0.75, pump_risk=0.25,
        confirmation_signals=["nonfarm_payrolls_white_collar_miss","indeed_job_postings_decline",
                               "unemployment_rate_above_5pct","consumer_confidence_collapse"],
    ),

    NarrativeTemplate(
        name="Citrini — Humanoid Robotics Wave",
        description="""Citrini covers humanoid robotics as one of the biggest structural themes.
The thesis: humanoid robots will replace physical labor the way AI replaces white-collar work.
Key players: Figure AI, 1X, Boston Dynamics, Agility Robotics — all private.
Public plays: NVDA (AI brain), TSLA (Optimus), GOOGL (DeepMind robotics),
component suppliers: actuators, sensors, torque motors, lidar.
\"The addressable market is every human labor job — $50T+ opportunity.\"
Timeline: 2025-2027 = factory deployments. 2028+ = consumer/healthcare.
Indonesia angle: manufacturing automation threat to labor-intensive exports.""",
        category="technology",
        catalyst_types=["humanoid_robot_deployment","factory_automation_order",
                         "figure_1x_ipo","tesla_optimus_production"],
        activation_keywords=["humanoid robot","optimus tesla","figure ai","1x robot",
                              "agility robotics","boston dynamics","robot manufacturing",
                              "physical ai","robot actuator","robot supply chain",
                              "labor automation","robot arms"],
        invalidation_keywords=["robot failure","humanoid ai winter","cost too high",
                                "regulatory restriction robots"],
        beneficiaries={"us":["TSLA","NVDA","GOOGL","ISRG","ROK","FANUY"]},
        fades={"global":["labor_intensive_manufacturers","EWT_taiwan_workers"]},
        regime_alignment={"Q1":1.40,"Q2":1.20,"Q3":0.70,"Q4":0.50},
        typical_duration_weeks=104, conviction_ceiling=0.70, pump_risk=0.35,
        confirmation_signals=["tesla_optimus_10k_units","figure_factory_contract",
                               "robot_capex_above_1bn_announced","nvidia_robotics_revenue"],
    ),

    NarrativeTemplate(
        name="GLP-1 / Ozempic Economy — Weight Loss Drug Structural Impact",
        description="""Citrini covers GLP-1 as cross-sector structural theme.
Direct beneficiaries: LLY (Eli Lilly), NVO (Novo Nordisk) — obvious.
Second-order LONGS: bariatric surgery device makers (EW, SYK), kidney disease drugs,
heart failure treatment, sleep apnea devices (RESMED), dialysis (FMS, DVA — short term).
Second-order SHORTS: fast food (MCD, YUM), snack companies (MDLZ, KO/PEP partially),
clothing retailers for plus-size, mobility scooters, insulin manufacturers.
\"GLP-1 reshapes the entire consumer economy around obesity — $150B+ market by 2030.\"
Indonesia: belum ada major play but watch imported drug costs impacting healthcare system.""",
        category="technology",
        catalyst_types=["glp1_label_expansion","novo_lilly_capacity","insurance_coverage",
                         "obesity_data","glp1_heart_failure","glp1_renal"],
        activation_keywords=["glp1","ozempic","wegovy","mounjaro","semaglutide","tirzepatide",
                              "obesity drug","weight loss drug","lilly novo",
                              "glp1 side effects","glp1 heart","glp1 kidney","glp1 dementia"],
        invalidation_keywords=["glp1 safety recall","weight regain problem","access denied insurance",
                                "generic glp1 collapse price","renal failure glp1"],
        beneficiaries={"us":["LLY","NVO","RPRX","HALO","EW","SYK","BSX","ABBV"],
                       "global":["NVO.DK","SAN.PA"]},
        fades={"us":["MCD","YUM","BYND","MDLZ","KO","PEP","DVA","FMS"]},
        regime_alignment={"Q1":1.30,"Q2":1.10,"Q3":0.80,"Q4":0.70},
        typical_duration_weeks=156, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["glp1_insurance_coverage_50pct","lilly_revenue_above_20bn",
                               "mcd_same_store_miss_attributed_glp1","glp1_renal_fda_approval"],
    ),

    NarrativeTemplate(
        name="Modern Warfare Tech — Drone + EW + C-UAS + Loitering Munition",
        description="""Ukraine war revealed: drones dominate. Every nation re-arming with drone tech.
The shift: from expensive platforms (F-35, tank) → cheap attritable autonomous systems.
\"A $400 drone took out a $4M tank. The math of warfare changed forever.\"
Citrini covers defense tech intersect with AI — autonomous targeting, sensor fusion, ECM.
Key segments: (1) UAS/drone manufacturers, (2) Counter-UAS (C-UAS), 
(3) Electronic warfare (EW), (4) Loitering munitions (kamikaze drones).
US stocks: KTOS (Golden Horde), AVAV (AeroVironment), PLTR (battlefield AI),
RCAT, JOBY-adjacent for military.
NATO obligation + Taiwan risk + Red Sea = multi-year rearming cycle.""",
        category="geopolitical",
        catalyst_types=["ukraine_war_lessons","nato_drone_procurement","taiwan_strait_tension",
                         "houthi_red_sea","defense_budget_increase","c_uas_program"],
        activation_keywords=["drone warfare","loitering munition","c-uas","electronic warfare",
                              "kratos ktos","aerovironment avav","palantir military","rcat drone",
                              "fpv drone","ukraine drone","shahed drone","counter-drone",
                              "autonomous weapon","swarm drone","electronic jamming"],
        invalidation_keywords=["ceasefire","defense budget cut","drone ban treaty","sequestration"],
        beneficiaries={"us":["KTOS","AVAV","LMT","RTX","NOC","PLTR","CACI","LDOS","HII"]},
        fades={"us":["BA_commercial","AAL"]},
        regime_alignment={"Q2":1.30,"Q3":1.50,"Q1":0.90,"Q4":1.10},
        typical_duration_weeks=104, conviction_ceiling=0.80, pump_risk=0.15,
        confirmation_signals=["pentagon_drone_budget_increase","nato_c_uas_contract","ktos_golden_horde_production",
                               "taiwan_defense_spending_gdp_3pct","europe_drone_procurement"],
    ),

    NarrativeTemplate(
        name="Hedgeye — Fed Inflation Target Migration (2%→3%)",
        description="""McCullough's thesis + Ricky2212 corroboration: \"Fed akan sadar target 2% tidak achievable.\"
\"Tools yang mereka gunakan tidak efektif. Supply-side inflation tidak bisa direm dengan suku bunga.\"
El-Erian statement: \"If Fed insists on 2%, they need DEPRESSION, not recession.\"
Bill Gross statement: \"Sudah saat Fed raise target ke 3% dan berdamai.\"
Implication: When Fed accepts 3% inflation target → rates normalize lower → 
bonds rally → equity multiple expansion → EM relief → the great repricing.
\"Ini lebih dahsyat dari PIVOT efeknya.\"
This is THE regime-changing catalyst for Q4→Q1 transition in this cycle.""",
        category="policy",
        catalyst_types=["fed_inflation_target_change","powell_speech_3pct","fed_minutes_hawkish_fade",
                         "inflation_normalization","fed_framework_review"],
        activation_keywords=["fed 3 percent target","inflation target change","fed framework",
                              "powell inflation tolerance","2 percent target abandon",
                              "bill gross 3pct","el erian fed","fed target migration",
                              "average inflation targeting","flexible fed"],
        invalidation_keywords=["fed reaffirms 2pct","inflation surge 10pct","volcker moment",
                                "fed independence removed"],
        beneficiaries={"us":["TLT","IEF","QQQ","SPY","GLD","EEM","IWM"],
                       "ihsg":["BBCA.JK","BBRI.JK","CTRA.JK","BEST.JK"]},
        fades={"us":["UUP","cash"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q3":1.20,"Q2":0.90},
        typical_duration_weeks=52, conviction_ceiling=0.85, pump_risk=0.15,
        confirmation_signals=["fed_official_3pct_statement","fomc_minutes_hawkishness_fade",
                               "ten_year_yield_below_4","tlt_breakout_sustained"],
    ),

    NarrativeTemplate(
        name="Hedgeye — Quad2 Inflation Now Stag-on-a-Lag 2026",
        description="""Hedgeye's current 2026 thesis (April 2026): Monthly Q2 inflation NOW masking Structural Q3.
\"ISM Prices Paid 74.50 + CapEx spike = Flation NOW. Growth decelerating = Stag ON A LAG.\"
Two-phase play: (1) Near-term — commodity/energy trades still work (Q2 beneficiaries).
(2) 3-6 months — growth rolls, margin compression hits, defensive rotation accelerates.
\"Old Wall is still buying growth cyclicals. We're already selling them.\"
The trap: everyone sees Q2 inflation. Smart money is positioning for Q3 stagflation ON A LAG.
Key signal: if ISM Manufacturing falls below 50 while CPI stays above 3.5% → confirmed Q3 structural.
IHSG: coal/CPO exporters may have short window of outperformance before growth scare hits.""",
        category="cycle",
        catalyst_types=["ism_prices_paid_surge","capex_spike","margin_compression",
                         "stagflation_signal","growth_deceleration"],
        activation_keywords=["quad 2 inflation","flation now stag lag","ism prices paid",
                              "stagflation 2026","margin compression q2 q3","mccullough q2 q3",
                              "hedgeye stagflation","old wall q2","capex boom inflation"],
        invalidation_keywords=["inflation cools fast","ism rebound","growth re-accelerates",
                                "soft landing confirmed","fed cuts aggressively"],
        beneficiaries={"us":["XLE","XLB","GLD","XLI","TIPS"],
                       "ihsg":["ITMG.JK","ADRO.JK","AALI.JK","MEDC.JK"]},
        fades={"us":["XLK","XLY","IWM","HYG","EM_equities"]},
        regime_alignment={"Q2":1.70,"Q3":1.50,"Q1":0.50,"Q4":0.40},
        typical_duration_weeks=13, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["ism_prices_paid_above_70","ism_manufacturing_below_50",
                               "gdp_nowcast_decelerate","payrolls_miss_2consecutive"],
    ),

]

# Merge batch 2 into main list
_NARRATIVES.extend(_NARRATIVES_BATCH2)
# Rebuild lookup dicts
NARRATIVE_BY_NAME = {n.name: n for n in _NARRATIVES}
NARRATIVES_BY_CATEGORY = {}
for _n in _NARRATIVES:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
