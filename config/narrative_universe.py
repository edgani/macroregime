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

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 3 — ASCHENBRUNNER + DOJJUNN BOTTLENECK CHAIN + MISSING RICKY THESES
# ═══════════════════════════════════════════════════════════════════════════════
_NARRATIVES_BATCH3: List[NarrativeTemplate] = [

    NarrativeTemplate(
        name="Aschenbrunner — AI Physical Layer (Power > Code)",
        description="""Leopold Aschenbrunner's landmark thesis (2026): 
"Owning the power and hardware to run models is MORE VALUABLE than owning the AI code itself."
Fund: Aschenbrunner Hedge Fund Tracker, +51.3% since March 5 2026, $5M+ AUM via Autopilot.
The bet: AI code (OpenAI, Anthropic, Mistral) will commoditize. 
Physical infrastructure CANNOT commoditize — land, permits, power grids, cooling take YEARS.
Picks: BE (fuel cells), CORZ (miner→AI pivot), SNDK (flash storage), IREN (green AI DC), APLD (purpose-built AI cloud).
Generalization: anyone who OWNS the physical layer (power + hardware + land) for AI = pricing power forever.
"One bottleneck leads to another" — after compute = power. After power = storage. After storage = networking.
Indonesia angle: GOTO/Gojek/TLKM as future AI DC operators? Watch BEST/KIJA for AI DC land play.""",
        category="technology",
        catalyst_types=["ai_dc_power_contract","hyperscaler_lease","fuel_cell_deal",
                         "miner_pivot_ai","renewable_power_ai","ai_storage_demand"],
        activation_keywords=["aschenbrunner","ai physical layer","power beats code","ai infrastructure owns",
                              "bloom energy ai","core scientific ai","applied digital","iren ai datacenter",
                              "sandisk ai storage","ai power infra","data center power","ai campus power",
                              "fuel cell ai dc","green ai datacenter","physical ai layer"],
        invalidation_keywords=["ai dc overbuild","power demand overestimated","AI spending collapse",
                                "hyperscaler capex cut","data center supply glut"],
        beneficiaries={
            "us":["BE","CORZ","IREN","APLD","SNDK","VST","GEV","ETN","CEG","VRT","WDFC"],
            "global":["SMCI","NVDA"],  # physical AI compute
        },
        fades={"us":["MSFT","GOOGL","AMZN"]},  # code/model owners commoditize
        regime_alignment={"Q1":1.60,"Q2":1.40,"Q3":0.80,"Q4":0.50},
        typical_duration_weeks=104, conviction_ceiling=0.85, pump_risk=0.20,
        confirmation_signals=["be_ai_dc_contract","corz_hpc_revenue","iren_new_capacity",
                               "apld_hyperscaler_lease","aschenbrunner_fund_holdings_change",
                               "ai_dc_power_waitlist_growing","interconnection_queue_record"],
    ),

    NarrativeTemplate(
        name="Dojjunn — Sequential Bottleneck Chain Migration",
        description="""@dojjunn's core investing framework (confirmed Apr 2026 screenshot):
"One bottleneck leads to another. Today it's memory, photonics, and CPUs. 
Tomorrow it could be GPUs, power, gas turbines, ABF substrates."
The CHAIN: 
Phase 1 (2023-2024): GPU shortage → NVDA monopoly → everyone scrambles
Phase 2 (2024-2025): Memory/HBM bottleneck → MU/SKHynix → HBM3E sold out
Phase 3 (2025-2026): Photonics/CPO → LITE/COHR → optical interconnect constraint
Phase 4 (2026): Power/Infra → ETN/GEV/VST → transformer lead times 3yr
Phase 5 (2026-2027 INCOMING): Gas Turbines → GEV/SIEGY → 24/7 firm power
Phase 6 (2027+ WATCH): ABF Substrates → AJINY → packaging bottleneck nobody sees yet
"A narrative is just a narrative. But when backed by strong cash flow, it's something special."
Key: each bottleneck is investable for 12-24 months before supply catches up.
The EDGE: identify the NEXT bottleneck 6-12 months before market consensus.""",
        category="technology",
        catalyst_types=["supply_constraint_new","lead_time_spike","capacity_announcement_insufficient",
                         "bottleneck_phase_shift","next_layer_constraint"],
        activation_keywords=["bottleneck chain","sequential bottleneck","next bottleneck",
                              "abf substrate","ajinomoto build-up film","gas turbine ai",
                              "bottleneck migration","ai supply chain next","packaging bottleneck",
                              "hbm shortage","optical interconnect constraint","power grid bottleneck",
                              "dojjunn","one bottleneck leads to another"],
        invalidation_keywords=["supply normalization","capacity catch up","no new bottleneck",
                                "AI demand plateau","capex cancelled"],
        beneficiaries={
            "us":["AJINY","AMKR","MU","GEV","ETN","BE","CORZ","ARM","QCOM","AMD","INTC"],
            "next_watch":["GEV","SIEGY_DE","ABF_substrate_players"],
        },
        fades={"us":[]},
        regime_alignment={"Q1":1.50,"Q2":1.30,"Q3":0.70,"Q4":0.45},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.25,
        confirmation_signals=["abf_lead_time_surge","gas_turbine_backlog_record",
                               "ajiny_order_acceleration","arm_qcom_amd_intc_all_up_same_day",
                               "next_bottleneck_mentioned_by_hyperscalers"],
    ),

    NarrativeTemplate(
        name="Ricky — Crisis Entry Playbook (ATH-20%/30% Buy Zones)",
        description="""Ricky2212's market behaviour framework — buy at puncak keburukan (peak of fear).
ATH Correction Zones:
• ATH-10% = Healthy correction → normal pullback, accumulate quality
• ATH-20% = Bear market territory → "media berteriak krisis, tapi fundamental belum rusak"
• ATH-30% = Big Crisis → MAXIMUM OPPORTUNITY untuk long-term investor

Crisis Entry Protocol:
Entry allocation: 60% di tranche pertama (paling pasti) + 20% + 20% sisanya.
"Jangan langsung masuk 100% — sisakan amunisi untuk penurunan lebih lanjut."
Crisis end signal (3 must confirm simultaneously):
1. "Too Big To Fail" statement dari pejabat
2. "We Will Do Whatever It Takes" dari central bank  
3. "Joint Global Coordination" (G7/G20 statement)
= TRIPLE SIGNAL = saatnya masuk maksimal.

Portfolio survival rule: "Beli saham yang meski harganya terus turun, perusahaannya masih berjalan."
= Quality + Cash flow + Dividend paying companies.""",
        category="cycle",
        catalyst_types=["market_crash","central_bank_intervention","government_bailout",
                         "coordinated_response","fear_extreme","vix_spike"],
        activation_keywords=["market crash","ath -20","ath -30","spy drawdown 20","crisis entry",
                              "too big to fail","whatever it takes","coordinated central bank",
                              "peak fear","maximum pessimism","buy the crash","ricky crisis",
                              "bear market opportunity","systematic entry crash"],
        invalidation_keywords=["no policy response","central bank credibility lost","hyperinflation",
                                "structural breakdown","banking system failure"],
        beneficiaries={"us":["SPY","QQQ","GLD","TLT","IWM","BBCA_JK"],
                       "ihsg":["BBCA.JK","BBRI.JK","KLBF.JK","UNVR.JK"]},
        fades={"us":[]},
        regime_alignment={"Q4":1.90,"Q3":1.40,"Q1":0.60,"Q2":0.50},
        typical_duration_weeks=13, conviction_ceiling=0.90, pump_risk=0.05,
        confirmation_signals=["spy_drawdown_above_20pct","vix_above_40",
                               "fed_emergency_statement","g7_coordination",
                               "too_big_to_fail_statement","fear_greed_below_15"],
    ),

    NarrativeTemplate(
        name="Ricky — CAT+GLEN Global Bellwether Breakout",
        description="""Ricky2212: "Caterpillar dan Glencore adalah dua perusahaan lama yang mencerminkan aktivitas ekonomi global."
"Saat keduanya mulai bergerak naik bersama → Sesi 3 berjalan."
Framework: "Old School Industrial" sebagai leading indicator.
CAT = makes equipment for mining, construction, energy globally. Revenue = proxy for global capex.
GLEN = Glencore = largest commodity trader + miner. Revenue = proxy for raw material demand.
"Saat CAT dan GLEN ATH bareng → seluruh supply chain commodity sedang berjalan."
DJ Transport confirmation: logistics/trucking naik = ekonomi gerak secara fisik.
Indonesia signal: saat CAT/GLEN breakout → ITMG/ADRO/INCO akan segera follow.
Ricky: "Perhatikan perusahaan-perusahaan ini. Mereka tidak bisa berbohong soal kondisi ekonomi." """,
        category="cycle",
        catalyst_types=["global_capex_recovery","china_infrastructure","commodity_demand",
                         "mining_equipment_order","industrial_breakout"],
        activation_keywords=["caterpillar ath","glencore breakout","cat glen signal",
                              "dj transport rally","industrial bellwether","global capex",
                              "mining equipment orders","old school industrial","copper demand",
                              "cat revenue beat","glencore earnings","iron ore recovery"],
        invalidation_keywords=["cat revenue miss","glencore loss","china infrastructure halt",
                                "global capex cut","recession confirmed"],
        beneficiaries={"us":["CAT","DE","GE","XLI","XME","FCX"],
                       "global":["GLEN.L","RIO","BHP","VALE"],
                       "ihsg":["ITMG.JK","ADRO.JK","INCO.JK","MDKA.JK","PTBA.JK"]},
        fades={"us":[]},
        regime_alignment={"Q2":1.70,"Q1":1.30,"Q3":0.70,"Q4":0.20},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.15,
        confirmation_signals=["cat_ath","glencore_52w_high","dj_transport_breakout",
                               "copper_above_4_50","bdi_above_2000","itmg_adro_foreign_buy"],
    ),

    NarrativeTemplate(
        name="Ricky — Seasonal / Sell in May + DM Sentiment Contrarian",
        description="""Ricky2212 seasonal + sentiment framework:
SEASONAL: "Sell in May and Go Away" = historical pattern. Market cenderung lemah Mei-Oktober.
Counter: ini hanya pattern, bukan law. Jika fundamental kuat dan cycle mendukung → abaikan.
"Jangan ikut sell in May kalau lu yakin dengan posisi lu."

DM SENTIMENT INDICATOR: "Saat DM gw penuh dari orang yang nanya beli saham apa → WARNING.
Saat DM sepi dan orang tidak tertarik saham sama sekali → BUY SIGNAL."
= Retail participation as contrarian indicator.
Inverse Cramer principle: "Saat Cramer teriak beli → pertimbangkan jual."
Peak retail euphoria = institutional distribution zone.
Peak retail fear = institutional accumulation zone.

"Pasar itu forward looking. Saat kabar buruk keluar → harga sudah jatuh duluan.
Saat kabar baik keluar → harga sudah naik duluan. Kita harus 1 langkah di depan news." """,
        category="cycle",
        catalyst_types=["sentiment_extreme","retail_capitulation","dm_volume_spike",
                         "seasonal_pattern","media_euphoria"],
        activation_keywords=["sell in may","seasonal pattern","retail euphoria","cramer buy signal",
                              "fear and greed extreme","retail capitulation","dm flood questions",
                              "inverse cramer","retail sentiment peak","market timing seasonal",
                              "contrarian signal","retail panic","wsb euphoria"],
        invalidation_keywords=["fundamental breakdown","no institutional buying","central bank tightening"],
        beneficiaries={"us":["SPY","QQQ","IWM"],"ihsg":["EIDO"]},
        fades={"us":[]},
        regime_alignment={"Q4":1.50,"Q1":1.30,"Q2":0.70,"Q3":0.60},
        typical_duration_weeks=8, conviction_ceiling=0.65, pump_risk=0.15,
        confirmation_signals=["fear_greed_below_20_retail_panic","google_trends_stocks_peak",
                               "reddit_wsb_euphoria_peak","institutional_net_buy_confirmed"],
    ),

    NarrativeTemplate(
        name="Ricky — Singa Tua vs Singa Muda (US/EU Decline, Asia Rise)",
        description="""Ricky2212's multi-decade geopolitical framework:
"Singa Tua" (Old Lions): US, Europe, Japan → peak power, declining relative dominance.
"Singa Muda" (Young Lions): China, India, ASEAN, Gulf → rising share of global GDP/trade.
"Amrik adalah singa tua yang mulai ompong. Dollar akan dikebiri oleh amrik sendiri."
Investment implication: 
→ Dollar structurally weak multi-decade (dedollarization)
→ EM equities re-rate as global share of earnings rises
→ Indonesia: beneficiary as ASEAN manufacturing + commodity hub
→ India: world's fastest growing large economy (INDA, SMIN)
→ Gulf: petrodollar recycling into local equity markets (Saudi, UAE)
This is NOT a trade — it's a 10-20 year positioning framework.
Short-term irrelevant. Medium-term: USD bear, EM bull. Long-term: ASEAN = new growth engine.""",
        category="geopolitical",
        catalyst_types=["dollar_reserve_decline","em_gdp_growth_outpace","asean_fdi",
                         "china_india_trade_deal","brics_expansion","us_deficit"],
        activation_keywords=["singa tua singa muda","dollar decline","em outperform",
                              "asean growth","india growth","gulf sovereign wealth",
                              "dedollarization","us deficit","EM re-rating",
                              "china gdp share","emerging market dominant","global south"],
        invalidation_keywords=["china hard landing","em crisis","dollar surge permanent",
                                "asean political crisis","india slowdown"],
        beneficiaries={"global":["EEM","VWO","INDA","EIDO","EWH","EWT","GXC","ARGT"],
                       "ihsg":["BBCA.JK","BMRI.JK","TLKM.JK"],
                       "commodities":["GC=F","CU=F"]},
        fades={"us":["UUP","BIL","TIP"]},
        regime_alignment={"Q1":1.20,"Q4":1.10,"Q3":0.80,"Q2":0.90},
        typical_duration_weeks=520, conviction_ceiling=0.70, pump_risk=0.10,
        confirmation_signals=["em_gdp_share_above_60","dollar_reserve_below_50",
                               "asean_fdi_record","india_gdp_above_us_gdp_growth"],
    ),
]

_NARRATIVES.extend(_NARRATIVES_BATCH3)
NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH3})
for _n in _NARRATIVES_BATCH3:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)


# Merge batch 2 into main list
_NARRATIVES.extend(_NARRATIVES_BATCH2)
# Rebuild lookup dicts
NARRATIVE_BY_NAME = {n.name: n for n in _NARRATIVES}
NARRATIVES_BY_CATEGORY = {}
for _n in _NARRATIVES:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 4 — ARTICLES 9-17 RICKY2212 EXHAUSTIVE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════
_NARRATIVES_BATCH4: List[NarrativeTemplate] = [

    NarrativeTemplate(
        name="Ricky — Gantian Donk: Consumer Goods Double Margin Hit",
        description="""Ricky2212's most actionable cycle rotation framework.
Phase 1 (Naik Pasti Turun): Komoditas berjaya → input cost naik → consumer goods margin compress.
ICBP, MYOR, ULTJ, UNVR terpukul: harga jual susah naik (daya beli lemah) tapi bahan baku naik.
Phase 2 (Naik Lupa Turun): Komoditas turun → consumer goods get DOUBLE HIT positif:
1. Harga jual TETAP tinggi (sudah dinaikkan, tidak akan diturunkan)
2. Cost produksi TURUN (bahan baku CPO/gandum/plastik/energi turun)
= ASP naik + cost turun + volume naik (daya beli membaik) = margin explosion.
"Coba cek kinerja Q1 2023 ICBP, MYOR, ULTJ bahkan UNVR semua naik lumayan."
"Jangan kaget nanti akan ketemu keadaan YANG NAIK DAN YANG TURUN, NANTI NAIK LAGI SEMUA BARENGAN."
= Sesi 3 Ricky: komoditas + consumer goods naik bareng = full cycle recovery.""",
        category="cycle",
        catalyst_types=["commodity_price_decline","input_cost_deflation","consumer_recovery",
                         "daya_beli_pulih","bbm_stable","pivot_monetary"],
        activation_keywords=["gantian donk","consumer goods margin","sudah naik lupa turun",
                              "icbp myor margin expand","ultj klbf recovery","consumer goods Q1 beat",
                              "input cost turun","cpo wheat deflation","bahan baku murah",
                              "margin expansion fmcg","asp stable cost down","consumer goods leverage"],
        invalidation_keywords=["komoditas naik lagi","bbm naik","input cost surge","consumer recession"],
        beneficiaries={"ihsg":["ICBP.JK","MYOR.JK","ULTJ.JK","KLBF.JK","SIDO.JK","UNVR.JK","CMRY.JK"]},
        fades={"ihsg":["ITMG.JK","ADRO.JK","PTBA.JK"]},
        regime_alignment={"Q1":1.70,"Q4":1.60,"Q2":0.60,"Q3":0.25},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.10,
        confirmation_signals=["icbp_myor_gross_margin_beat","q1_consumer_goods_results",
                               "cpo_wheat_below_peak","consumer_confidence_rising",
                               "bbm_stable_3months"],
    ),

    NarrativeTemplate(
        name="Ricky — Big Fund Flow Sequence (USD→IDR→Bond→Equity→Banking)",
        description="""Ricky2212's institutional money flow framework. The SEQUENCE matters:
Step 1: IDR strengthens (USD sold → IDR bought). If IDR stable during equity selloff = NOT real outflow.
Step 2: Bond market rallies (yield turun). Uang masih di Indonesia, cuma pindah ke obligasi.
Step 3: Equity inflow starts. Big fund akumulasi di saham → IHSG forming base.
Step 4: Perbankan dibeli duluan (BBCA, BBRI, BMRI). Bank = proxy recovery = first mover.
Step 5: Consumer goods, retail, industrial estate follow.
FAKE OUTFLOW DETECTOR: IDR + Bond cross-check. "Kalo IDR ga kemana-mana = uang masih stay di indo."
Capital outflow headline ≠ IDR collapse → equity selloff = BUY not SELL.
Ricky bought BTPS+consumer goods+bank during 'capital outflow' narrative while IDR was stable.""",
        category="cycle",
        catalyst_types=["idr_strengthen","bond_rally","foreign_buy_ihsg","asing_net_buy",
                         "institutional_accumulation","big_fund_entry"],
        activation_keywords=["big fund masuk","asing net buy","idr menguat","bond rally ihsg",
                              "uang masuk ihsg","capital inflow indonesia","obligasi rally indonesia",
                              "rupiah menguat signifikan","foreign flow ihsg","bbca bbri bbni akumulasi",
                              "institutional accumulation banking","fr65 fr yield turun"],
        invalidation_keywords=["idr collapse","bond yield spike","capital flight","banking npl surge"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK",
                                "ICBP.JK","KLBF.JK","ACES.JK","BEST.JK","KIJA.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q2":0.70,"Q3":0.30},
        typical_duration_weeks=13, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["idr_strengthen_while_equity_down","bond_yield_fr65_declining",
                               "banking_foreign_net_buy_sustained","bbca_bbri_accumulation_pattern"],
    ),

    NarrativeTemplate(
        name="Ricky — Debt Ceiling Drama Pattern (Always Resolved = Buy the Dip)",
        description="""Ricky2212's debt ceiling framework: "Sejarah selalu mencatat pagu hutang selalu dinaikkan."
90x raised in 20th century. Never once permanently defaulted.
Pattern: Lobi-lobi alot → drama headline → market dips → RESOLVED before deadline → RALLY.
"Mereka hanya bikin hutang buat bayar hutang. Gali lubang tutup lubang. Mesin printer epson bunyi lagi."
Implication: every debt ceiling scare = manufactured fear = BUY OPPORTUNITY not sell.
Secondary thesis: Dollar long-term weakening every time they print more. Gold structural bid.
Ricky: "Kalo dinaikkan debt ceiling → printer bunyi → uang makin ga ada harganya → GOLD bid."
Apply to any recurring fiscal cliff/shutdown drama pattern - ALL resolve, ALL create dip to buy.""",
        category="policy",
        catalyst_types=["debt_ceiling_drama","government_shutdown_fear","fiscal_cliff",
                         "us_default_headline","treasury_x_date"],
        activation_keywords=["debt ceiling","pagu hutang amrik","us default fear","treasury x-date",
                              "congress debt limit","government shutdown","debt ceiling raised",
                              "us credit downgrade","fitch moody downgrade us"],
        invalidation_keywords=["actual us default","constitutional crisis","dollar collapse extreme"],
        beneficiaries={"us":["SPY","QQQ","GLD","TLT"],"commodities":["GC=F"]},
        fades={"us":["BIL","cash_usd"]},
        regime_alignment={"Q4":1.60,"Q1":1.40,"Q2":0.90,"Q3":0.80},
        typical_duration_weeks=4, conviction_ceiling=0.85, pump_risk=0.05,
        confirmation_signals=["debt_ceiling_vote_scheduled","bipartisan_deal_framework",
                               "treasury_extraordinary_measures","white_house_congress_meeting"],
    ),

    NarrativeTemplate(
        name="Ricky — Oil Hulu ke Hilir: Complete Value Chain Play",
        description="""Ricky2212's complete oil value chain breakdown — each layer is an investable opportunity:
HULU (upstream): Pemetaan → ELSA (seismik, one player)
Konstruksi Rig: RUIS, APEX, INDY (margins lumayan, pilihan terbatas)
OSV Penunjang: WINS, LEAD, ELPI (kapal penunjang pengeboran offshore)
Drilling Chemical (anti-slip): OBMD (SATU-SATUNYA player, monopoly positioning)
FSO/FPSO Storage: SHIP (satu-satunya yang punya FSO/FPSO di bursa indo)
HILIR (downstream):
Crude Transport: SOCI, BULL, SMDR, HITS (dirty tanker)
Refinery: TIDAK ADA yang go public di Indonesia
Product Transport: BULL, SOCI, SMDR, HITS (clean/product tanker)
Distribution/Storage: AKRA (market leader, distribusi sampai ke bawah)
"Saya pilih HULU sebagai andalan saya. Disanalah muara investasi nya."
Margin terbesar ada di high-tech OSV dan monopoly positions (OBMD, SHIP).""",
        category="commodity",
        catalyst_types=["oil_investment_ramp","offshore_drilling_surge","petronas_capex",
                         "indonesia_1jt_bpd_target","oil_feasibility_price","opec_discipline"],
        activation_keywords=["oil hulu hilir","elsa seismik","obmd drilling chemical","ship fpso fso",
                              "wins lead osv kapal","akra fuel distribution","hulu migas value chain",
                              "oil field construction","rig construction indonesia","offshore drilling ramp",
                              "psc production sharing","konsesi minyak","exploration drilling"],
        invalidation_keywords=["oil price below 60","offshore moratorium","esdm block rejection",
                                "petronas capex cut","ruu migas stalled"],
        beneficiaries={
            "ihsg":["ELSA.JK","OBMD.JK","SHIP.JK","WINS.JK","LEAD.JK",
                    "RUIS.JK","MEDC.JK","ENRG.JK","ESSA.JK","AKRA.JK",
                    "SOCI.JK","BULL.JK","SMDR.JK"],
            "global":["SLB","HAL","BKR","TDW","VAL"],
        },
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.70,"Q1":1.20,"Q3":0.80,"Q4":0.20},
        typical_duration_weeks=78, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["petronas_block_award","elsa_new_seismic_contract",
                               "wins_lead_new_kontrak","obmd_revenue_surge",
                               "ship_fpso_contract","indonesia_lifting_increase"],
    ),

    NarrativeTemplate(
        name="Ricky — Banking CKPN Provisioning Cycle (NPL Peak → Laba Explosion)",
        description="""Ricky2212's banking investment thesis - the CKPN cycle is the key alpha signal.
CKPN = Cadangan Kerugian Penurunan Nilai = bank's provisioning for bad loans.
When economy deteriorates: Bank raises CKPN → LABA GEMBOS → stock price falls → BUY ZONE.
When economy recovers: CKPN declines + Write-back from recovery of written-off loans → DOUBLE LABA.
Key KPIs Ricky monitors:
NIM (Net Interest Margin) = bank's main profit engine. Higher = better.
CASA ratio = cheap funding (giro+tabungan). Higher CASA → lower cost of fund → wider NIM.
NPL < 5% = healthy. CKPN direction = leading signal.
BOPO = efficiency ratio. Lower = more efficient. BBCA = benchmark efficiency.
CAR ≥ 8% minimum. BUKU 4 bank = strongest.
"Ekonomi akan selalu bertumbuh dalam jangka panjang → bank akan selalu ikut bertumbuh."
"Bank tidak mengenal siklus seperti komoditas."
Peak CKPN → hold, then buy. Recovery confirmation = CKPN declining 2 quarters.""",
        category="cycle",
        catalyst_types=["ckpn_peak","npl_improving","nim_expansion","kredit_tumbuh",
                         "bi_rate_cut","economic_recovery","provision_write_back"],
        activation_keywords=["ckpn turun","npl membaik","bank provisioning peak","banking recovery",
                              "bbca bbri nim","bank laba explosion","kredit tumbuh","ldr meningkat",
                              "casa ratio tinggi","bopo turun","bank roe meningkat",
                              "write-back provisi","npl formation rate turun"],
        invalidation_keywords=["npl surge","ckpn naik lagi","credit crisis","bank gagal","recession deep"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK",
                                "BTPS.JK","BBTN.JK","BNGA.JK","NISP.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.70,"Q4":1.60,"Q2":0.80,"Q3":0.25},
        typical_duration_weeks=52, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["ckpn_declining_2quarters","npl_gross_below_3pct",
                               "bbca_bbri_nim_expanding","kredit_growth_above_10pct",
                               "banking_roa_roe_improving"],
    ),

    NarrativeTemplate(
        name="Ricky — China PMI Recovery + Dry Bulk Demand Confirmation",
        description="""Ricky2212: "China PMI <50 = kontraksi. Watch 2 consecutive months for trend."
"China haus akan resources. Data dry bulk tanker: demand iron ore + copper dari China sangat HOT."
PMI Manufacturing China adalah leading indicator TERBAIK untuk dry bulk demand.
PMI >52 sustained = commodities (iron ore, copper, coal) akan diangkut besar-besaran.
"Permintaan oil China sdh menyentuh ATH. Diprediksi tahun depan akan tumbuh kembali."
Framework: China PMI data → BDI (Baltic Dry Index) → commodity prices → IHSG coal/metal.
Sequence: PMI improve → BDI naik → ITMG/ADRO/INCO/MDKA foreign buy → price discovery.
Also: China property QE → construction recovery → iron ore + copper demand.
"China punya segudang senjata untuk ditembakkan. China punya fleksibilitas monetary policy tertinggi." """,
        category="cycle",
        catalyst_types=["china_pmi_recovery","china_stimulus","china_property_qe",
                         "china_iron_ore_demand","bdi_rally","china_coal_import"],
        activation_keywords=["china pmi above 50","china pmi recovery","china manufacturing PMI",
                              "china stimulus","pboc cut rrr","china property support",
                              "china iron ore import","china coal import","bdi rally",
                              "china demand recovery","china economic reopen"],
        invalidation_keywords=["china hard landing","china pmi below 48 sustained",
                                "china property crisis deepening","evergrande systemic"],
        beneficiaries={"ihsg":["ITMG.JK","ADRO.JK","PTBA.JK","INCO.JK","MDKA.JK","ANTM.JK","PSSI.JK"],
                       "global":["GOGL","SBLK","FCX","RIO","BHP","GLEN.L"],
                       "commodities":["HG=F","CL=F","CNA.L"]},
        fades={"us":["TLT","XLU"]},
        regime_alignment={"Q2":1.70,"Q1":1.30,"Q3":0.60,"Q4":0.30},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.25,
        confirmation_signals=["china_pmi_above_51_2months","bdi_above_1500","china_iron_ore_atw_high",
                               "itmg_adro_foreign_net_buy","pboc_rrr_cut"],
    ),

    NarrativeTemplate(
        name="Ricky — Dow ATH Ranging Pattern + Buying Time Thesis",
        description="""Ricky2212's Dow market structure insight (2023):
"Pattern: Saat Dow mau menembus upper range → ada saja berita buruk yang dikeluarkan."
"Saat Dow mendekati lower range → dikasih oksigen berita bagus → short-term rally."
Thesis: pasar 'sengaja' di-ranging sambil economic data settles. 
"Ada unsur kesengajaan. Mereka buying time sampai semua keadaan settled."
Two signals he watches simultaneously:
1. NASDAQ call option volume spike (risk-on approaching)
2. Tech fund inflow besar = institutional positioning sebelum rally
"Belakangan ada kenaikan volume call option di Nasdaq yang cukup besar."
"Ada capital inflow cukup besar ke TECH FUND belakangan ini."
Bellwether list (semua harus konfirmasi): CAT (52-week high) + GLEN ATH + Copper bid + BDI up + Gold up + UST 10Y mlandai = KONFIRMASI pivot incoming.""",
        category="cycle",
        catalyst_types=["nasdaq_call_option_spike","tech_fund_inflow","cat_52w_high",
                         "pivot_signal_bellwether","dow_lower_range_bounce"],
        activation_keywords=["nasdaq call option volume","tech fund inflow","caterpillar 52 week high",
                              "dow ranging pattern","dow lower range","dow ATH -10 -20",
                              "bellwether konfirmasi","copper bid caterpillar","dow relief rally",
                              "dow range breakout","ust 10y mlandai pivot"],
        invalidation_keywords=["tech fund outflow","nasdaq put spike","caterpillar miss","recession confirmed"],
        beneficiaries={"us":["QQQ","NVDA","MSFT","AAPL","META","SPY","IWM"],
                       "ihsg":["TLKM.JK","BBCA.JK"]},
        fades={"us":[]},
        regime_alignment={"Q1":1.50,"Q4":1.30,"Q2":0.90,"Q3":0.50},
        typical_duration_weeks=8, conviction_ceiling=0.70, pump_risk=0.20,
        confirmation_signals=["nasdaq_call_volume_spike","tech_fund_weekly_inflow_positive",
                               "cat_52w_high_confirmed","ust10y_below_4","copper_3m_positive"],
    ),

    NarrativeTemplate(
        name="Ricky — CPO Best-in-Class OER Ranking System",
        description="""Ricky2212's detailed CPO company ranking framework.
THE KEY METRIC: OER (Oil Extraction Rate) = berapa % buah sawit jadi CPO.
Average market OER: 20-21%. Best-in-class: 24-25%.
Also critical: Profil umur tanaman (prime = 8-15 tahun). Komposisi lahan inti vs plasma.
RANKING (Ricky's A+ to B- system):
A+ (TERBAIK): DSNG (OER tertinggi, prime age, ekspansi organic, ESG funded), TAPG (A+: OER tinggi, 90% lahan inti, pabrik ke-18, umur prime), STAA (A+: produktivitas tertinggi, 73% prime age, 90% lahan inti)
A: LSIP (sehat, diversified, tapi umur tua+no ekspansi), AALI (luas tapi tua, OER average)
A-: AALI (hanya luas + Astra brand sebagai kelebihan)
B: SGRO (OER terendah, hutang, plasma tinggi, margin buruk)
B-: SIMP (profit negative, lahan luas tapi tua), BWPT (poor management Eagle High, sering rugi)
Biodiesel angle: B40 → makin besar kebutuhan CPO. Malaysia RSPO=benchmark kualitas.
"OER tinggi + profil tanaman prime = leverage terbesar saat CPO naik. Bukan hanya luas lahan." """,
        category="commodity",
        catalyst_types=["cpo_price_rise","biodiesel_mandate_increase","la_nina",
                         "india_import_surge","sunflower_shortage","oer_beat"],
        activation_keywords=["cpo oer ranking","dsng tapg staa oer","kelapa sawit oer tertinggi",
                              "profil tanaman sawit prime","biodiesel B40 B50","dsng tapg best",
                              "cpo hulu ke hilir","minyak goreng naik","cpo malaysia bursa",
                              "palm oil inventory malaysia","india vegetable oil import"],
        invalidation_keywords=["esg ban permanent","palm oil oversupply sustained","replanting peak all companies",
                                "india import duty high","cpo below 3000 MYR"],
        beneficiaries={"ihsg":["DSNG.JK","TAPG.JK","SSMS.JK","STAA.JK","LSIP.JK","AALI.JK"],
                       "global":["KLK.KL","IOI.KL"]},
        fades={"ihsg":["BWPT.JK","SIMP.JK","SGRO.JK"]},
        regime_alignment={"Q2":1.80,"Q1":1.10,"Q3":0.70,"Q4":0.20},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.15,
        confirmation_signals=["dsng_tapg_oer_beat_quarterly","cpo_bursa_above_4000",
                               "biodiesel_mandate_increase","india_palm_oil_import_surge",
                               "malaysia_inventory_low"],
    ),

    NarrativeTemplate(
        name="Ricky — Shipping Sector Classification & Cycle Positioning",
        description="""Ricky2212's complete shipping sector classification for IHSG:
DRY BULK (komoditas curah kering: iron ore, coal, nickel, grain):
Index: Baltic Dry Index (BDI). Mostly time chartered 80%+.
PSSI (A+): most complete fleet, TnB to vessel, expansion agenda. TPMA, MBSS = TnB only.
OIL TANKER (crude + product):
Dirty tanker = crude oil dari sumur ke refinery. Index: Baltic Dirty Tanker.
Clean/Product tanker = dari refinery ke end user. Index: Baltic Clean Tanker.
SOCI (ONE AND ONLY VLCC in Indonesia) = highest leverage. BULL, HITS supporting.
CONTAINER (manufactured goods):
Cycle: 2020-2022 DONE. SMDR+TMAS = 10x+ already extracted. "Story sudah selesai."
OSV (offshore support vessel - hulu migas):
WINS (no.1, 42 kapal, high tier 28%, management transparent) rating A
LEAD (no.2, 43 kapal, NPM 30%+ at peak, tapi hutang concern) rating A-
OSV: most sensitive to oil price (hulu vs hilir). Kapal nganggur = fixed cost bleeding.
New orders = 0. Supply shortage akut. WINS buying 6 kapal proactively = management signal.""",
        category="commodity",
        catalyst_types=["bdi_rally","osv_day_rate_spike","tanker_rate_spike","china_coal_import",
                         "offshore_drilling_ramp","rerouting_war","opec_cut"],
        activation_keywords=["pssi dry bulk","soci vlcc tanker","wins lead osv","smdr tmas container selesai",
                              "bdi baltic dry","dirty tanker rate","clean tanker rate","shipping indonesia",
                              "kapal nganggur","tanker rate spike","pssi fleet expansion",
                              "aframax suezmax vlcc","chapter 11 shipping recovery"],
        invalidation_keywords=["bdi collapse","osv oversupply new build","tanker rate crash",
                                "dry bulk new vessel flood","shipping recession"],
        beneficiaries={"ihsg":["PSSI.JK","SOCI.JK","BULL.JK","WINS.JK","LEAD.JK","TPMA.JK","MBSS.JK"],
                       "global":["GOGL","SBLK","FRO","STNG","TDW"]},
        fades={"ihsg":["SMDR.JK","TMAS.JK"]},  # container cycle already done
        regime_alignment={"Q2":1.60,"Q3":1.20,"Q1":0.90,"Q4":0.20},
        typical_duration_weeks=39, conviction_ceiling=0.75, pump_risk=0.30,
        confirmation_signals=["bdi_above_2000","soci_vlcc_new_contract","wins_utilization_above_80",
                               "tanker_dirty_above_50000","pssi_new_vessel_active"],
    ),

]

_NARRATIVES.extend(_NARRATIVES_BATCH4)
NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH4})
for _n in _NARRATIVES_BATCH4:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 5 — ARTICLES 18-37 EXHAUSTIVE EXTRACTION
# Rich new theses: crisis playbook, portfolio framework, China timing, maker analysis
# ═══════════════════════════════════════════════════════════════════════════════
_NARRATIVES_BATCH5: List[NarrativeTemplate] = [

    NarrativeTemplate(
        name="Ricky — Pivot 3-Phase Trade (Slowing→Halt→Cut)",
        description="""Ricky2212's most precise monetary policy trading framework.
PHASE 1 (Slowing Pace): Central bank reduces hike size (75→50→25bps). Trade: buy quality growth.
PHASE 2 (Halt/Pause): Terminal rate reached, hold. Trade: buy duration (TLT), add defensives.
PHASE 3 (Cut): Rate decreases begin. Trade: max risk-on, buy EM, small cap, long duration.
"Thesis kami dari awal: slowing pace → halt → cut. Kami sudah kawal dari BOE dulu."
Ricky's timeline: BOE pivot first → Fed → ECB (last, most inflation pain).
UST signals each phase:
- Phase 1: UST 2Y still above FFR, UST 10Y mlandai
- Phase 2: UST 1Y,2Y fall below FFR = near halt
- Phase 3: All tenors below FFR, yield curve steepening = CUT incoming
"Saya hanya minta kasih waktu. Thesis kami berjalan on track."
Key add-on: Fed target migration 2%→3% = LEBIH DAHSYAT dari pivot (Bill Gross confirmed).""",
        category="policy",
        catalyst_types=["fed_slowing_pace","fomc_halt","fed_rate_cut","inflation_declining",
                         "ust_yield_signal","ecb_pivot","boe_pivot"],
        activation_keywords=["fed pivot slowing pace halt cut","fomc pause halt","rate cut incoming",
                              "terminal rate reached","ust 2y below ffr","yield curve steepening",
                              "central bank pivot","inflation 2 percent target abandon",
                              "fed target 3 percent","boe pivot first","ecb pivot last"],
        invalidation_keywords=["inflation re-accelerates","terminal rate raised","stagflation entrenched"],
        beneficiaries={
            "us":["TLT","IEF","QQQ","IWM","SPY","GLD","EEM"],
            "ihsg":["BBCA.JK","CTRA.JK","BEST.JK","BTPS.JK"],
        },
        fades={"us":["UUP","BIL","cash"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q3":1.10,"Q2":0.80},
        typical_duration_weeks=39, conviction_ceiling=0.90, pump_risk=0.05,
        confirmation_signals=["ust_1y_below_ffr","fomc_halt_statement","inflation_3month_trend_down",
                               "fed_minutes_hawkishness_fade","tlt_breakout_sustained"],
    ),

    NarrativeTemplate(
        name="Ricky — China Re-Open Timing Genius (3-6M Bunker Accumulation)",
        description="""Ricky2212's insight on China's masterstroke timing of re-opening.
China didn't open randomly — they opened EXACTLY when:
1. Raw material prices were at lows (copper, coal, iron ore all depressed)
2. Western economies were struggling (Amrik + Eropa morat-marit)
3. China could position as global economic balancer
"Satu kebetulan? China pasti happy banget dengan keadaan ini."
KEY MECHANISM: China has 3-6 MONTH storage bunker capacity for raw materials.
They don't buy when prices are high. They accumulate SILENTLY when prices are depressed.
Evidence: China coal import +71% YoY in early 2023. Iron ore import surge. Dry bulk rates rally.
"Masih mengalami peningkatan yang luar biasa." 
"China banned Australian coal → buka banned → banjirin supply → harga turun → China beli murah."
China oil: not buying from spot, buying from Russia at discount + Gulf area (Saudi mesra dengan China).
Investing implication: China activity visible in BDI BEFORE commodity prices spike. BDI = real-time.""",
        category="cycle",
        catalyst_types=["china_reopen_demand","china_commodity_accumulation","china_pmi_recovery",
                         "china_infrastructure_spend","pboc_stimulus","china_property_recovery"],
        activation_keywords=["china reopen","china coal import","china iron ore","china accumulation",
                              "china bunker storage","bdi rally china","china oil import record",
                              "china austral coal","china silently buy","china raw material surge",
                              "china gdp recovery","china economic take off","china pmi above 50"],
        invalidation_keywords=["china hard landing","china property collapse","china pmi below 48 sustained",
                                "china yuan crisis","xi covid lockdown return"],
        beneficiaries={"ihsg":["ITMG.JK","ADRO.JK","PTBA.JK","INCO.JK","MDKA.JK","ANTM.JK","PSSI.JK"],
                       "global":["FCX","VALE","RIO","BHP","GLEN.L","GOGL","SBLK"],
                       "commodities":["CL=F","HG=F","iron_ore"]},
        fades={"us":["TLT","XLU"]},
        regime_alignment={"Q2":1.70,"Q1":1.30,"Q3":0.70,"Q4":0.30},
        typical_duration_weeks=39, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["bdi_above_2000","china_coal_import_surge","iron_ore_price_recover",
                               "china_pmi_above_51","china_oil_import_record","dry_bulk_rate_rally_15days"],
    ),

    NarrativeTemplate(
        name="Ricky — Crisis End Signal (3 Keywords Must All Fire)",
        description="""Ricky2212's most powerful crisis entry framework. 20 years of pattern recognition.
THREE MANDATORY CONFIRMATION KEYWORDS (must ALL appear simultaneously):
1. "TOO BIG TO FAIL" — government/authority acknowledges systemic risk
2. "WE WILL DO WHATEVER IT TAKES" — central bank unlimited backstop
3. "JOINT GLOBAL COORDINATION" — G7/G20/central banks coordinate
When all 3 appear: CRISIS IS ENDING. Deploy capital aggressively.
Entry protocol: 60% → 20% → 20% (if very confident: 70% → 30%).
Cycle history: 2005 commodity shock → 2008 subprime → 2020 COVID = all resolved with same 3 keywords.
"Setelah mendapat Stempel LULUS, wealth mencapai ATH baru."
Ricky's observation: sehabis big crisis → medium crisis (not depression). 
"Sehabis siklus kejatuhan parah, biasanya diikuti oleh mid crisis bukan depresi."
"Krisis bukan kehancuran tapi peluang besar. Kalo market babak belur = time to prepare."
Cash management: raise cash during uncertainty, attack at 5% minimum remaining cash.""",
        category="cycle",
        catalyst_types=["financial_crisis","market_crash","central_bank_emergency","systemic_risk",
                         "coordinated_central_bank","government_bailout"],
        activation_keywords=["too big to fail","whatever it takes","joint coordination",
                              "crisis end signal","market crash entry","systemic risk",
                              "fed emergency meeting","central bank bailout","ath -30",
                              "market panic extreme","vix above 40","circuit breaker halt"],
        invalidation_keywords=["depression confirmed","banking system collapse permanent",
                                "no policy response","hyperinflation spiral"],
        beneficiaries={"us":["SPY","QQQ","GLD","IWM","TLT"],"ihsg":["BBCA.JK","BBRI.JK","KLBF.JK"]},
        fades={"us":[]},
        regime_alignment={"Q4":1.90,"Q3":1.30,"Q2":0.60,"Q1":0.50},
        typical_duration_weeks=8, conviction_ceiling=0.95, pump_risk=0.05,
        confirmation_signals=["too_big_to_fail_statement","whatever_it_takes_statement",
                               "g7_g20_coordinated_response","fed_emergency_rate_cut",
                               "fear_greed_below_15","vix_above_40"],
    ),

    NarrativeTemplate(
        name="Ricky — Om Salim Smart Money Tracker (BRMS→BUMI→MEDC)",
        description="""Ricky2212's institutional smart money framework: follow Om Salim (Anthony Salim).
"Kemana Om S berlabuh, ikutin aja. Dia pasti mencium sesuatu. Uang akan menanti buat kamu."
Track record: Every Salim investment leads to significant alpha.
RECENT SALIM MOVES (chronological):
1. DCII (Data Center) — masuk saat bisnis DC belum ramai → sekarang paling ramai
2. META (Jalan Tol Filipina+Indonesia) — 2017, sekarang massive expand
3. BBHI (Allo Bank digital) — sebelum digital banking boom
4. MEGA + Bank Ina — bank accumulation cycle
5. EMTK (SCTV+Indosiar+SCMA) — media konvergensi
6. MEDC 21% — hulu migas cycle (via hutang pinjaman ke MEDC)
7. BRMS 24% (via Agus Projo) — metals/minerals Om B's BRMS
8. BUMI — PP 24T senilai Rp120/saham (mega jumbo, Salim+Bakrie = full partnership)
Pattern: Om Salim goes WHERE THERE IS STRUCTURAL UNDERVALUATION + story besar di depan.
"Om S dan Om B sepertinya mesra sekali. B indikator makin makin ehem ehem." """,
        category="cycle",
        catalyst_types=["salim_group_entry","anthony_salim_acquisition","smart_money_flow",
                         "institutional_accumulation","conglomerate_strategic_move"],
        activation_keywords=["om salim masuk","anthony salim","agus projo","salim group akuisisi",
                              "om s om b mesra","brms salim","medc salim","bumi pp salim",
                              "salim smart money","b indicator","om b buka toko lagi",
                              "dcii salim","bbhi salim","emtk salim"],
        invalidation_keywords=["salim exit","anthony salim jual semua","salim group masalah"],
        beneficiaries={"ihsg":["BRMS.JK","BUMI.JK","MEDC.JK","DCII.JK","META.JK","BBHI.JK","MEGA.JK",
                                "EMTK.JK","INDF.JK","ICBP.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q2":1.50,"Q1":1.30,"Q3":0.80,"Q4":0.50},
        typical_duration_weeks=78, conviction_ceiling=0.80, pump_risk=0.30,
        confirmation_signals=["salim_new_acquisition_announcement","agus_projo_appointed_director",
                               "salim_right_issue_participation","brms_bumi_salim_filing"],
    ),

    NarrativeTemplate(
        name="Ricky — Coal ITMG Valuation Floor ($200 ASP = 7x PE, 10%+ Yield)",
        description="""Ricky2212's quantitative coal floor analysis:
"Saya sudah memfaktorkan batubara sampai $200 sejak lama."
ITMG Floor Math (at coal $200):
ASP = $200 x 75% = $150 actual realized
Production = 17M ton
Revenue = $2.5B
NPM = 25% (konservatif, actual >40% at peak) → Laba = $625M = Rp9.5T
HEAVY DISKON 40% → Laba = Rp5.7T → EPS = Rp5,000
At harga Rp33,000 → 7x PE (back to normal)
Dividen (DPR 70%) = Rp3,500 → yield = 10%+
"Masih menarik? Buat kondisi menunggu RESET sementara, harusnya menarik sih."
KEY LESSON: Saat semua berteriak selesai, berteriak coal habis → itulah saat harga paling murah.
"Sudah naik pasti ada waktunya turun (dulu). Sudah naik lupa turun."
Valuation: dijual 2-3x laba → kalo laba turun 50% → dijual 4-6x. Kalo turun 70% → dijual 7x.
= Downside terbatas, upside besar saat coal $300+ cycle returns.""",
        category="commodity",
        catalyst_types=["coal_bottom","itmg_dividend_yield","coal_sentiment_worst",
                         "contrarian_entry","coal_valuation_floor"],
        activation_keywords=["itmg valuasi murah","coal $200 normal","itmg deviden yield 10",
                              "coal floor valuation","itmg 7x pe","coal reset bottom",
                              "thermal coal cheap","itmg ptba 3x laba","coal contrarian",
                              "batubara murah abnormal","coal back to normal"],
        invalidation_keywords=["coal banned permanently","itmg dividend cut","coal $150 broken sustained",
                                "china coal self-sufficient","india solar replaces coal"],
        beneficiaries={"ihsg":["ITMG.JK","PTBA.JK","ADRO.JK","HRUM.JK","BYAN.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q4":1.50,"Q3":1.20,"Q2":0.90,"Q1":0.60},
        typical_duration_weeks=13, conviction_ceiling=0.80, pump_risk=0.30,
        confirmation_signals=["itmg_div_yield_above_10","coal_spot_200_250_stable",
                               "media_coal_doom_narrative_peak","itmg_pe_below_7",
                               "foreign_net_buy_itmg_returning"],
    ),

    NarrativeTemplate(
        name="Ricky — Market Maker Cycle Detection (Accumulation→Pump→Distribution)",
        description="""Ricky2212's 6-year insider market maker knowledge framework.
"Saya pernah menjalani 4 tahapan tersebut satu per satu. Tapi tidak semua bisa saya ceritakan."
4-PHASE MAKER CYCLE:
PHASE 1 ACCUMULATION:
- Offer tebal > Bid (create selling pressure perception)
- Harga dibuat sideways lama (shake out impatient holders)
- Nominee asing jualan heavy (retail panic) → actually same pool
- Berita buruk dikeluarkan beruntun → buy at maximum fear
SIGNAL: Berita buruk tapi harga stagnant. Volume menurun tapi tidak break support.

PHASE 2 PRICE INCREASE:
- Bid mulai tebal (demand perception)
- Volume naik perlahan
- Grafik mulai bagus (maker gambar sendiri)
- Tape reading: order besar dipecah-pecah (beli 1000 lot → 500 transaksi kecil)
SIGNAL: Bid tiba-tiba tebal, harga naik sedikit, volume mulai ada.

PHASE 3 DISTRIBUTION:
- Berita baik berlimpah tapi harga mulai stagnan
- Volume BESAR + harga sideways = distribusi
- Saham terlihat murah (trap) → turun perlahan tidak terasa
SIGNAL: All good news tapi harga ga naik lagi. Volume besar + sideways.

ANTI-BANDARMOLOGY: Broksum tidak bisa dipercaya. Semua nominee satu muara.
"Kalo bandar bisa dibaca → semua menang → ga mungkin."
Salim-style: follow the smart money (fundamental + conglomerate moves), not bandar.""",
        category="cycle",
        catalyst_types=["market_sentiment_extreme","retail_panic","institutional_accumulation",
                         "maker_accumulation_signal","distribution_warning"],
        activation_keywords=["maker accumulation","bandar akumulasi","harga sideways berita buruk",
                              "volume besar sideways","berita baik harga stagnan","distribusi saham",
                              "anti bandarmology","broksum semu","nominee maker","tape reading",
                              "market maker cycle","pump dump ihsg","gorengan ihsg"],
        invalidation_keywords=["fundamental breakdown permanent","company fraud"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.20,"Q4":1.20,"Q2":0.90,"Q3":0.80},
        typical_duration_weeks=26, conviction_ceiling=0.70, pump_risk=0.15,
        confirmation_signals=["accumulation_phase_confirmed","volume_dry_while_sideways",
                               "bad_news_price_stable","maker_transition_to_bid_side"],
    ),

    NarrativeTemplate(
        name="Ricky — Portfolio Architecture: 69/9/4/18 Framework",
        description="""Ricky2212's complete portfolio construction methodology.
ALLOCATION FRAMEWORK:
- 69% CORE THESIS (cyclical/story) = where alpha lives
  - 58% big cap (liquidity + dividend + risk buffer)
  - 42% small/mid cap (alpha generator, 10x potential)
- 9% BALANCING (non-cyclical) = smooth out cycle volatility
- 4% ETF (passive index exposure, low cost, catch all rallies)
- 18% CASH (psychological insurance, attack reserve)

KEY PRINCIPLES:
Big cap = "likuiditas, deviden cash flow, risk reduction"
Small cap = "big alpha dan alpha booster"
Cash = NEVER 0%. Minimum 5% even at full attack.
"Semakin turun harga saham, semakin tinggi posisi tawar kita."

ENTRY PROTOCOL for crashes:
60% first tranche → 20% → 20%. Or 70/30 at near-bottom.
"Beli saham saat diskon dan diobral. Bukan saat harga naik kejar-kejaran."

TIME FRAME HIERARCHY:
Short (day/month) = high risk. Medium (1-3yr) = medium. Long (3yr+) = low risk.
Legacy = TIDAK UNTUK DIJUAL (BTPS example: 5 years, 2 bear cycles, still hold).

PSIKOLOGI TITIK 0 = prerequisite for best investment decisions.
"Bayar diri anda. Nikmati perjalanan. Baru bisa berpikir jernih." """,
        category="cycle",
        catalyst_types=["portfolio_rebalancing","cycle_rotation","cash_deployment",
                         "market_crash_opportunity","time_frame_discipline"],
        activation_keywords=["portfolio allocation","diversifikasi portfolio","big cap small cap",
                              "cash management investasi","etf passive","portfolio balancing",
                              "ricky 69 9 4 18","core thesis allocation","alpha booster",
                              "legacy saham tidak dijual","psikologi titik 0","buy the dip strategy"],
        invalidation_keywords=["concentrated bet all-in","no cash reserve","panic sell all"],
        beneficiaries={"ihsg":["BBCA.JK","ITMG.JK","BTPS.JK","BEST.JK","ELSA.JK","BBRI.JK"],
                       "us":["SPY","QQQ","GLD"]},
        fades={"ihsg":[]},
        regime_alignment={"Q1":1.30,"Q4":1.40,"Q2":0.90,"Q3":0.70},
        typical_duration_weeks=260, conviction_ceiling=0.90, pump_risk=0.05,
        confirmation_signals=["portfolio_stress_test_passed","cycle_turn_confirmed",
                               "cash_reserve_above_15pct","big_cap_dividend_flowing"],
    ),

    NarrativeTemplate(
        name="Ricky — ACES / Om Robert Buy-at-Worst Strategy",
        description="""Om Robert's famous ACES trade and the principle behind it.
"Beli saham itu saat keadaan sedang tidak berpihak. Bukan kejar-kejaran harga."
ACES CASE STUDY:
- Found ACES at 700 (good fundamental, retail king, cash rich, moat intact)
- Freight naik, CPO naik (input cost pressure), daya beli hancur → ACES babak belur
- But: moat unchanged, cash reserve huge, margin bersih above peers
- Om Robert: "Beli dari 700, lanjut hajar besar di 450" (all-in at maximum pessimism)
- Ke 900+ → well above 2-bagger
KEY INSIGHT: "Saat keadaan sudah terlalu pesimis dan terlalu banyak hal buruk → yang tersisa apa?"
= Nothing worse to price in = BUY SIGNAL.
"Beli saat diskon → kasih waktu → return berlipat."
BEST (Mas Rizza): asset play at 100-120 → turun ke 120-130 → tambah lagi → naik ke 170+ → tambah lagi
Pattern: patience > timing. Entry saat diskon, hold saat naik, add saat turun lagi.""",
        category="cycle",
        catalyst_types=["extreme_pessimism","sector_out_of_favor","temporary_headwind",
                         "moat_intact_beaten_down","consumer_recovery_incoming"],
        activation_keywords=["aces hardware recovery","om robert aces","beli saat terburuk",
                              "buy maximum pessimism","beaten down quality stock",
                              "temporary headwind moat intact","consumer retail recovery",
                              "aces hardware ricky","buy the worst performing sector",
                              "contrarian value buy","best bekasi fajar asset play"],
        invalidation_keywords=["moat permanently broken","ecommerce destroy aces",
                                "fundamental structural decline","management fraud"],
        beneficiaries={"ihsg":["ACES.JK","AMRT.JK","MAPI.JK","BEST.JK","KIJA.JK","BTPS.JK"]},
        fades={"ihsg":[]},
        regime_alignment={"Q4":1.70,"Q1":1.50,"Q2":0.70,"Q3":0.30},
        typical_duration_weeks=52, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["aces_same_store_sales_turning","aces_margin_expanding",
                               "consumer_confidence_recovering","best_new_tenant_announcement",
                               "freight_cost_normalize"],
    ),

    NarrativeTemplate(
        name="Ricky — El Erian Thesis: Fed Depression Bluff (Supply>Monetary)",
        description="""Ricky2212's most contrarian thesis against Fed hawkishness.
El Erian: "Kalau Amerika bersikeras mau menekan inflasi sampai 2%, mereka harus bikin DEPRESI."
Ricky's counter: "Berani kah? Melihat sinyal oil dan copper, amrik takut melakukannya."
TWO PROOFS that Fed is bluffing:
1. Oil: hanya bergerak di range $72-80. Kalo mau depresi, oil seharusnya $40-50. Impossible to manipulate forever.
2. Copper: sama seperti oil, bergerak dalam range. Kalo ekonomi mau dihancurkan, copper sudah hancur.
3. BDI (dry bulk): rally 15 hari berturut. Kapal angkut copper/coal/iron ore. Kalau depresi → ga ada aktivitas.
4. Capex investasi offshore melonjak di LATAM+Afrika. Siapa mau invest saat mau depresi?
"Supply side is the real problem. Monetary policy only manages demand (temporary). Supply needs 3 years."
"Kalo bikin depresi: demand hancur → price oil turun → nobody invests new supply → shortage WORSE."
= Circular logic trap. Fed CANNOT go full hawkish without destroying themselves.
Implication: higher-for-longer is BLUFF. Real rate cuts coming sooner than market expects.""",
        category="policy",
        catalyst_types=["fed_bluff_revealed","oil_price_floor_holds","copper_stabilizes",
                         "bdi_rally_proves_economy_ok","supply_shortage_structural"],
        activation_keywords=["el erian fed depression","fed bluff hawkish","oil range bound",
                              "copper stabilizes","fed buying time supply","higher for longer bluff",
                              "supply side inflation","fed cannot destroy economy","oil price floor",
                              "bdi rally fed bluff","amrik takut depresi","inflasi supply driven"],
        invalidation_keywords=["fed actually causes depression","oil breaks below 60","depresi confirmed",
                                "copper crash below 3","bdi collapse long"],
        beneficiaries={"us":["GLD","TLT","XLE","XOM","SLB"],
                       "commodities":["CL=F","HG=F","GC=F"]},
        fades={"us":["UUP","BIL"]},
        regime_alignment={"Q2":1.40,"Q3":1.30,"Q4":1.20,"Q1":0.80},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.15,
        confirmation_signals=["oil_hold_above_70","copper_stabilize_above_3_50",
                               "bdi_sustained_above_1500","capex_announcements_continue",
                               "fed_minutes_hawkishness_fade","ust_1y_below_ffr"],
    ),

]

_NARRATIVES.extend(_NARRATIVES_BATCH5)
NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH5})
for _n in _NARRATIVES_BATCH5:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 6 — ARTICLES 38-52 + CURRENT MARKET (APR 2026)
# Key extractions: liquidity sequence, pivot phases, gold thesis, CKPN cascade
# ═══════════════════════════════════════════════════════════════════════════════
_NARRATIVES_BATCH6: List[NarrativeTemplate] = [

    NarrativeTemplate(
        name="Ricky — USD 8T Money Market Epic Cycle (Kerangkeng → Banjir)",
        description="""Ricky2212's most epic liquidity thesis from 2023 that played out perfectly.
"Uang sebesar USD 8-9 trilyun di kerangkeng money market (yield 5.5%, tenor pendek, zero risk)."
"Sudah dari sana nya sifat uang adalah greedy — akan mengalir ke tempat yang kasih return tinggi."
PHASE PROGRESSION (5 phases Ricky documented):
Phase 1: Data bagus tapi UST short tenor tidak bergeming = Fed bluffing
Phase 2: Crypto (dunia antah berantah) starts rally = risk-on appetitte returning
Phase 3: HALT confirmed = crypto accelerates, UST 2Y starts falling
Phase 4: CUT terendus = ALL 4 indicators confirm (BTC, Gold, Copper, UST)
Phase 5: CUT confirmed Dec 2023 = UST 2Y rallied 6.43% in one day
PHASE 5 CONFIRMATION CHECKPOINTS (all must hit):
- BTC above 40k ✅
- Gold above 2100 ✅
- Copper above 3.90 ✅
- UST 10Y below 4.2% ✅
- DOW back to ATH ✅
"JUST WAIT THE MONEY WILL SPREADING AND FLOODING AWAY."
Epic Cycle = when kerangkeng opens, ALL asset classes flood simultaneously.
Application to 2026: tariff shock → new kerangkeng forming? Watch same 4 indicators.""",
        category="cycle",
        catalyst_types=["fed_rate_cut","money_market_exodus","risk_on_return","pivot_confirmed",
                         "btc_breakout","gold_ath","usd_weakening"],
        activation_keywords=["money market exodus","epic cycle","usd 8 trillion","kerangkeng dibuka",
                              "btc 40k gold 2100","risk on flooding","uang parkir money market",
                              "just wait money spreading","greedy uang","likuiditas banjir",
                              "pivot cut confirmed","money market fund outflow"],
        invalidation_keywords=["rate hike resumes","usd strengthens sharply","risk off sustained",
                                "btc crash","gold dump"],
        beneficiaries={"us":["BTC-USD","GLD","HG=F","SPY","QQQ","EEM","IWM","TLT"],
                       "ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","ITMG.JK","INCO.JK"]},
        fades={"us":["UUP","BIL","money_market_funds"]},
        regime_alignment={"Q1":1.90,"Q4":1.60,"Q2":0.80,"Q3":0.50},
        typical_duration_weeks=52, conviction_ceiling=0.90, pump_risk=0.15,
        confirmation_signals=["btc_above_40k","gold_above_2100","copper_above_3_90",
                               "ust2y_rally_sustained","dow_ath","money_market_weekly_outflow"],
    ),

    NarrativeTemplate(
        name="Ricky — Pivot 5-Phase Leading Indicator Framework",
        description="""Ricky2212's most sophisticated leading indicator framework — 4 assets that lead the Fed:
LEADING INDICATOR HIERARCHY (most → least leading):
1. DUNIA ANTAH BERANTAH (Crypto) = "mother of all risk-on/risk-off." Leads by 6-12 weeks.
   "Dunia antah berantah adalah yang paling peka. Ini lebih ke risk appetitte signal."
2. UST (US Treasury yields) = monetary policy signal. UST 2Y/1Y lead FFR decisions.
   "UST tidak bisa berbohong. Kalo mau naik, tenor pendek naik duluan."
3. COPPER = economic bellwether. Leads real economy by 4-8 weeks.
   "Copper adalah proxy ekonomi terbaik. Kalo ekonomi mau recover, copper gerak duluan."
4. GOLD = inflation/debt/trust hedge. Confirms direction.
   "Gold bukan timing tool — gold is a confirming asset. Gold yang paling lambat bergerak."
READING THE SIGNALS:
All 4 up = MAX RISK ON (new cycle confirmed)
Crypto+UST up, Copper+Gold flat = early recovery signal
All 4 flat/down = max defensiveness
Crypto up, others still down = early warning only, not yet actionable
The framework PREDICTED the Dec 2023 FOMC dovish pivot 6 weeks in advance.""",
        category="cycle",
        catalyst_types=["btc_breakout","ust_rally","copper_recovery","gold_ath",
                         "risk_on_appetitte","pivot_signal"],
        activation_keywords=["pivot leading indicator","crypto ust copper gold","dunia antah berantah signal",
                              "btc leading fed","ust leading indicator","copper economic bellwether",
                              "4 leading indicators","pivot 5 phase","risk on signal",
                              "btc 40k","copper 4","gold 2000","ust 2y falling"],
        invalidation_keywords=["all 4 indicators down simultaneously","crypto crash broad",
                                "copper collapse below 3","gold dump institutional"],
        beneficiaries={"commodities":["GC=F","HG=F","BTC-USD"],
                       "us":["SPY","QQQ","IWM","TLT","GLD"],
                       "ihsg":["BBCA.JK","ITMG.JK"]},
        fades={"us":["UUP"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q2":0.90,"Q3":0.60},
        typical_duration_weeks=13, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["all_4_indicators_positive","btc_weekly_close_above_40k",
                               "copper_above_3_80","gold_above_2000","ust2y_falling_trend"],
    ),

    NarrativeTemplate(
        name="Ricky — Gold: Inflation Debt Trust Hedge (Bretton Woods End Game)",
        description="""Ricky2212's deepest gold thesis — based on monetary system structure, not price.
"Semua akan kembali ke emas. Bukan thesis jangka pendek. Ini thesis ribuan tahun."
ROOT CAUSE CHAIN:
1944: Bretton Woods — USD backed by gold (1 oz = $35)
1976: Nixon ends Bretton Woods — USD now backed only by TRUST
Post-1976: Central banks print unlimited money. Uang dicetak berdasarkan TRUST saja.
Now: US debt $33T. Interest expense = 19.5% of revenue (record). 25% within 10 years.
Result: TRUST eroding → Gold as hedge.
EVIDENCE:
- Central banks buying gold at fastest pace in 55 years
- Russia, China raising gold % of reserves continuously
- JP Morgan research: gold allocation rising significantly
- UNTR (Astra + gold), Salim (BRMS), INDY, Peter Sondakh all secretly accumulating
- Call options + long positions in gold surging
"Dari zaman kenabian: 3 dirham beli seekor kambing. Sekarang masih 3 dirham = 3 juta. Zero inflate."
TRIGGER: Fed raises inflation target to 3% = berdamai dengan inflasi = hawkish selesai = gold structural bull.""",
        category="commodity",
        catalyst_types=["dollar_debasement","central_bank_gold_buying","fed_target_migration",
                         "dedollarization","debt_crisis","trust_erosion","bretton_woods"],
        activation_keywords=["gold central bank buying","dollar trust erode","bretton woods collapse",
                              "uang tanpa back up emas","gold structural bull","inflation hedge gold",
                              "gold ATH","untr gold","salim brms gold","dedollarization gold",
                              "jp morgan gold allocation","gold 2000 2100 2500"],
        invalidation_keywords=["dollar surges structurally","gold dump central bank","crypto replaces gold",
                                "imf gold standard restored"],
        beneficiaries={"us":["GLD","GC=F","NEM","GOLD","AEM","WPM","FNV"],
                       "ihsg":["ANTM.JK","MDKA.JK","BRMS.JK","INDY.JK"],
                       "commodities":["GC=F","SLV"]},
        fades={"us":["UUP","TLT"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.30,"Q1":0.70},
        typical_duration_weeks=260, conviction_ceiling=0.90, pump_risk=0.05,
        confirmation_signals=["central_bank_gold_buying_sustained","fed_target_3pct","gold_ath_new",
                               "dollar_reserve_share_declining","untr_gold_acquisition_news"],
    ),

    NarrativeTemplate(
        name="Ricky — Ray Dalio Beautiful Deleveraging (China Property Cycle)",
        description="""Ricky2212 applying Ray Dalio's Big Debt Crisis framework to China's property situation.
"China harus melakukan beautiful deleveraging. Dan China mampu melakukannya dengan baik."
WHY CHINA CAN DO IT (vs why US can't do it easily):
1. Debt in OWN CURRENCY = can manage via PBOC printing without external default
2. Debt held by OWN CITIZENS = no sudden foreign capital flight
3. Capacity for QE without hyperinflation (Yuan not global reserve currency = less inflation risk)
4. Fiscal + monetary flexibility both available (unlike US with debt ceiling)
Beautiful Deleveraging = BALANCE between:
a) Deflationary defaults/restructurings (Evergrande, Country Garden)
b) Inflationary money printing/debt monetization (PBOC QE, RRR cuts)
→ Spread burden over time without collapse
China property = 20-30% GDP. Cannot be allowed to fail = backstop guaranteed.
"China masih punya banyak bazooka buat ditembakkan. Mereka belum keluarkan yang besar."
INVESTMENT ANGLE: China property crisis = priced in already when Evergrande news peak.
When PBOC fires bazooka = recovery thesis. BDI + copper + iron ore will signal first.""",
        category="geopolitical",
        catalyst_types=["pboc_mega_stimulus","china_property_bailout","china_rrr_cut",
                         "china_fiscal_stimulus","evergrande_resolved","country_garden_bailout"],
        activation_keywords=["china beautiful deleveraging","evergrande resolution","ray dalio china",
                              "china property recovery","pboc bazooka","china mega stimulus",
                              "china rrr cut","country garden resolved","china property 30 pct gdp",
                              "china deleveraging","pboc qe","china fiscal expansion"],
        invalidation_keywords=["china hard landing confirmed","pboc refuses bailout",
                                "china debt default foreign currency","xi property crackdown deepens"],
        beneficiaries={"ihsg":["ITMG.JK","INCO.JK","MDKA.JK","PSSI.JK"],
                       "global":["FXI","MCHI","FCX","RIO","VALE","GOGL"],
                       "commodities":["HG=F","iron_ore","GC=F"]},
        fades={"us":["TLT"]},
        regime_alignment={"Q1":1.50,"Q2":1.40,"Q4":0.80,"Q3":0.60},
        typical_duration_weeks=52, conviction_ceiling=0.75, pump_risk=0.25,
        confirmation_signals=["pboc_rrr_cut","china_property_sales_stabilize",
                               "bdi_above_2000_china_driven","iron_ore_recovery","copper_above_4"],
    ),

    NarrativeTemplate(
        name="Ricky — BREN/IHSG Pattern (Invisible Hand Index Management)",
        description="""Ricky2212's IHSG structure insight — the INVISIBLE HAND that manages indeks.
PATTERN: GOTO → BYAN → ARTO → BREN (each became index mover in its era)
GOTO: Rugi 20T, valuasi setara Bank Mandiri. Dipakai jaga indeks ATH-10%. Sekarang turun 80%.
BYAN: Backed by real earnings (coal). Still in top-5 market cap. Survived = EARNINGS matter.
ARTO (Bank Jago): Hype digital, menggeser ASII. Now 30T only. Valuasi tanpa earnings = temporary.
BREN: PE 543x, PBV 99x. Market cap 1000T vs BBCA 1100T. Laba BREN 1.3T vs BBRI 60T.
"Saat indeks jatuh ke 6600 (ATH-10%), BREN di-ARA paksa jaga indeks."
STRUCTURAL INSIGHT:
- Free float sangat kecil = mudah dimainkan
- Mining hype (EBT) = similar to digital banking hype 2021
- Prajogo strategy: IPO sedikit → price discovery → block sale later at high price
THESIS: Invisible hand gunakan BREN untuk jaga indeks di ATH-10%. Permainan selanjutnya = BANKING.
"Banking sektor yang akan mengambil alih jadi penggerak nyata indeks saat new cycle berjalan."
BREN will not collapse like GOTO (ada earnings) but will revert toward fundamental value (like BYAN).""",
        category="cycle",
        catalyst_types=["ihsg_rebalancing","bren_correction","banking_sector_rerating",
                         "index_composition_change","prajogo_block_sale"],
        activation_keywords=["bren ihsg","bren pe 543","bren correction","goto byan arto bren pattern",
                              "invisible hand ihsg","index mover ihsg","bren arb","banking ihsg next",
                              "prajogo pangestu bren","ihsg ath -10 defended","bren free float"],
        invalidation_keywords=["bren earnings surge","bren new massive project","EBT mega expansion"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK"]},
        fades={"ihsg":["BREN.JK"]},
        regime_alignment={"Q1":1.40,"Q4":1.30,"Q2":0.90,"Q3":0.60},
        typical_duration_weeks=26, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["bren_correction_below_pe200","banking_foreign_net_buy",
                               "ihsg_held_above_ath_minus_10","bbca_bbri_accumulation"],
    ),

    NarrativeTemplate(
        name="Ricky — CKPN Cascade (Ultra Mikro → Mikro → Middle Class → Big Bank)",
        description="""Ricky2212's MOST CURRENT (2025-2026) thesis on Indonesia banking stress cascade.
"Aliran dimulai dari bawah dan mengalir ke atas. Akan stop dimana alirannya?"
CASCADE SEQUENCE:
Stage 1 (DONE): Ultra mikro → BTPS. CKPN menggungung = akumulasi sampah COVID + judol + pinjol.
Stage 2 (CURRENT): Mikro → BBRI. BBRI CKPN naik 2x lipat, stop lending mikro.
  Signal: "BBRI sampai stop lending di segment mikro = kondisi sangat tidak kondusif."
Stage 3 (NEXT): Middle class bawah (income 10-15jt). Watch: NPL leasing motor + BBTN CKPN.
  "Motor adalah kendaraan utama mereka, KPR BTN adalah cicilan rumah mereka."
Stage 4 (LATER): Middle class atas. Watch: BNGA, NISP consumer banking stress.
IHSG IMPLICATION:
- Big banks: BBCA ATH-12%, BBRI ATH-32%, BMRI ATH-23%, BBNI ATH-28% (Apr 2026 data)
- VIX signal at low = bounce needed
- IDR weakness = bank saham kena pertama
ENTRY SIGNAL: "ATH-10% adalah pertahanan pertama indeks."
RECOVERY SIGNAL: Watch BTPS turnaround first (earliest in cycle) + BBRI CKPN formation peak.
"Saat CKPN sdh peak dan berangsur turun = bank saham mulai bisa dibeli."
RICKY DIRECT QUOTE (Apr 2026): "Market bermain pakai NARASI tanpa valuasi. Cari saham yang punya NARASI kuat." """,
        category="cycle",
        catalyst_types=["ckpn_cascade","npl_rising","bank_lending_stop","idr_weakness",
                         "credit_stress","consumer_balance_sheet_stress","pinjol_stress"],
        activation_keywords=["ckpn cascade","bbri ckpn naik","bbri stop lending mikro",
                              "btps ckpn peak","bank stress indonesia","npl leasing motor",
                              "bbtn ckpn","middle class stress","kredit macet ihsg",
                              "bank ihsg ath -30","bbca bbri dump","rupiah lemah bank",
                              "ekonomi bawah tidak bergerak","judol pinjol drain liquidity"],
        invalidation_keywords=["ckpn peak confirmed declining","economic recovery bottom",
                                "bi rate cut aggressive","government stimulus effective"],
        beneficiaries={"ihsg":["BTPS.JK","BBCA.JK"]},
        fades={"ihsg":["BBRI.JK","BMRI.JK","BBNI.JK","BJTM.JK"]},
        regime_alignment={"Q3":1.80,"Q4":1.50,"Q2":0.80,"Q1":0.50},
        typical_duration_weeks=26, conviction_ceiling=0.85, pump_risk=0.10,
        confirmation_signals=["bbri_ckpn_2x_lipat","bbri_stop_lending_mikro",
                               "leasing_motor_npl_spike","bbtn_ckpn_rising",
                               "btps_ckpn_declining_signal","vix_at_low_ihsg"],
    ),

    NarrativeTemplate(
        name="Ricky — End of Game Fed (Dovish Statement = New Cycle Start)",
        description="""Ricky2212's landmark article Dec 2023: "For the first time, Fed gives DOVISH statement."
"Ini untuk pertama kalinya dalam siklus pengetatan — pemangku kebijakan memberikan sinyal dovish."
WHAT HAPPENED Dec 2023 FOMC:
- Fed held rates (3rd consecutive HALT)
- Projected 4x CUT in 2024 (from 2x projected previously)
- Fed funds rate projection: 4.6% for 2024
Market response within hours:
- UST 1Y: rallied 4%
- UST 2Y: rallied 6.43%
- DOW and S&P500: closed at ATH
- Gold: spiked 2%+
- USD: immediate collapse vs all pairs
RICKY's TRACKING (perjalanan panjang terkonfirmasi):
2021: Year of inflation ✅
2022: Year of transition (hawkish) ✅
2023: Year of new base + HALT + PIVOT CUT ✅
2024: Year of new cycle (INCOMING)
"This is the END OF THE GAME (hawkish). Kita akan memasuki babak baru."
APPLICATION 2026: Same framework. Watch for "first dovish statement" after current tightening.
When it comes: UST 2Y will rally 4-6%, DOW ATH, gold spike, IDR strengthen.""",
        category="policy",
        catalyst_types=["fed_first_dovish","fomc_cut_projection","powell_pivot_confirmed",
                         "new_cycle_start","rate_cut_cycle_begin"],
        activation_keywords=["fed first dovish statement","fomc cut projection","end of game hawkish",
                              "powell pivot","4 cuts projected","fed dot plot dovish",
                              "monetary policy reversal confirmed","new cycle 2024","ust 2y rally",
                              "first time dovish fed","fed berdamai","year of new cycle"],
        invalidation_keywords=["fed resumes hiking","inflation re-accelerates sharply",
                                "terminal rate raised again","stagflation confirmed"],
        beneficiaries={"us":["SPY","QQQ","TLT","IWM","GLD","EEM"],
                       "ihsg":["BBCA.JK","BBRI.JK","CTRA.JK","BEST.JK"],
                       "commodities":["GC=F","HG=F"]},
        fades={"us":["UUP","BIL"]},
        regime_alignment={"Q4":1.90,"Q1":1.70,"Q2":0.80,"Q3":0.50},
        typical_duration_weeks=52, conviction_ceiling=0.95, pump_risk=0.05,
        confirmation_signals=["fed_dot_plot_below_current_rate","fomc_statement_dovish_first",
                               "ust2y_rally_above_5pct","dow_sp500_ath_post_fomc",
                               "gold_spike_2pct_fomc_day"],
    ),

    NarrativeTemplate(
        name="Ricky — Ber-Ber Period + October Fear Peak Pattern",
        description="""Ricky2212's seasonal + crisis timing framework.
"BER BER period = September Oktober November. Historis, market paling sering berkinerja buruk."
Historical data: Black Monday 1987 = Oktober. Krisis 2008 puncak = Oktober. Covid low 2020 = Maret.
DOW ATH-20% (2022) terjadi di Oktober = sama persis.
THESIS: "BER BER bukan law, hanya statistik. Tapi persiapkan diri untuk kemungkinan itu."
The MECHANISM:
- Big funds want "karpet merah" = harga murah sebelum deploy
- Terror market = force central bank to act faster
- October = puncak fear → historically best entry point for 3-6 month trade
ADDITIONAL PATTERN: "Saat semua yang terburuk sudah dimunculkan, apa yang tersisa? BUY."
"Kalaupun terjadi, yah itu bonus — sudah siap. Kalo ga terjadi, juga bonus."
2023 EXAMPLE: Bottomed Oktober 2023 → Fed went dovish December 2023 → ALL market ATH by Q1 2024.
HOW TO USE: NOT a prediction tool — a PREPARATION tool.
"Yang jelas uang yang punya sifat Greedy yang lagi di kerangkeng, kalo dilepas = buas banget.""",
        category="cycle",
        catalyst_types=["seasonal_october_fear","market_terror","big_fund_karpet_merah",
                         "september_selloff","october_bottom","year_end_rally"],
        activation_keywords=["ber ber period","sell in may","october fear","market bottom october",
                              "seasonal pattern bad months","big fund terror market",
                              "karpet merah harga murah","september oktober november",
                              "black monday october","maximum fear signal","ber ber 2024"],
        invalidation_keywords=["no seasonal pattern this year","structural bear market",
                                "no policy response coming"],
        beneficiaries={"us":["SPY","QQQ","IWM","GLD"],"ihsg":["BBCA.JK","ITMG.JK"]},
        fades={"us":[]},
        regime_alignment={"Q4":1.60,"Q3":1.20,"Q1":0.90,"Q2":0.80},
        typical_duration_weeks=8, conviction_ceiling=0.65, pump_risk=0.10,
        confirmation_signals=["vix_spike_above_30","october_drawdown_confirmed",
                               "fear_greed_below_20","fund_money_market_peak"],
    ),

]

_NARRATIVES.extend(_NARRATIVES_BATCH6)
NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH6})
for _n in _NARRATIVES_BATCH6:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 7 — CURRENT MARKET ARTICLES (Ricky Aug-Sep 2024 + Apr 2026 CKPN update)
# Real-time signal capture: IHSG ATH-10% hit, Fed 100% CUT, Blow-off-top, M2+
# ═══════════════════════════════════════════════════════════════════════════════
_NARRATIVES_BATCH7: List[NarrativeTemplate] = [

    NarrativeTemplate(
        name="Ricky — Soft vs Hard Landing Scorecard (GDP + Jobs = The Decisive Data)",
        description="""Ricky2212's definitive framework for reading landing type — the most important macro bet.
"Saya realistic dan objective bahwa besar kemungkinan kita akan menghadapi HARD landing."
FRAMEWORK:
Soft landing = no recession post-tightening. Last true soft landing in modern history: 1994 (Greenspan).
Hard landing = recession follows. Historical base rate: 90%+ of aggressive tightening cycles.
"Pengetatan paling cepat dalam 110 tahun. Chance soft landing less than 50%."
THE DECISIVE DATA POINTS:
1. Jobs data (NFP, unemployment rate) = #1 indicator
   - Unemployment rising = more people with less income = less spending = GDP falls
   - Powell specifically mentions jobs EVERY FOMC = watch for cracks HERE first
2. GDP data = confirmation
3. SINYAL CUT: Saat Powell berkali-kali bilang 'JOB NUMBER is VERY STRONG' = tunggu REVERSAL.
   Saat job number cracks = CUT INCOMING.
RICKY'S BET: Hard landing more likely, but either way CUT will come.
"Bedanya: Soft landing = gradually CUT. Hard landing = dramatically CUT."
KEY INSIGHT: "Jangan expect bank sentral CUT mendadak. Kalo mendadak = market crash (panic signal)."
"Market berekspektasi CUT karena GOOD economy = wrong. CUT datang karena ECONOMY IS SICK."
Warning: CUT followed by market ADJUSTMENT phase (normalized). Not immediately bullish.
"Ekspektasi 7x CUT berlebihan → market crash corrects → ekspektasi 1x CUT → REVERSE PSYCHOLOGY." """,
        category="policy",
        catalyst_types=["nfp_weak","unemployment_rising","gdp_below_trend","soft_landing_risk",
                         "hard_landing_confirmed","fed_cut_cycle","recession_signal"],
        activation_keywords=["soft landing hard landing","nfp jelek","unemployment naik",
                              "gdp revisi turun","resesi amrik","powell job number strong",
                              "job cracks fed cut","hard landing fed cut","non farm payroll weak",
                              "unemployment 4.3","gdp 1.3 pct","economic slowing",
                              "consumer spending down","saving rate zero"],
        invalidation_keywords=["jobs market remains tight","gdp above trend","no recession",
                                "soft landing confirmed economists"],
        beneficiaries={"us":["TLT","GLD","IEF","UUP reverse"],"ihsg":["BBCA.JK","BTPS.JK"]},
        fades={"us":["SPY","QQQ","IWM"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":0.80,"Q1":0.60},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["nfp_below_100k","unemployment_above_4_pct",
                               "gdp_below_1_pct","ust2y_below_4pct","powell_softens_tone"],
    ),

    NarrativeTemplate(
        name="Ricky — Blow-Off-Top + Fund De-Risking (Ada Rally Kita EXIT)",
        description="""Ricky2212's real-time signal: Fund sedang de-risking equity globally.
"Beberapa berita seragam. Fund mulai mempersiapkan diri."
CONFIRMED SIGNALS (per Ricky intel, Aug-Sep 2024):
1. Fund sedang unloading China equity Q2 2024 — jumlah sangat besar
2. Fund strategy: "Ada rally, kita EXIT. Ada rally, kita EXIT"
3. Fund rotating from equity → Bond (menunggu CUT)
4. M2 supply mulai positif untuk pertama kali = awal aliran uang ke sistem
BLOW-OFF-TOP MECHANICS (Ricky framework):
"Jack up → BUBBLE → BURST → reason untuk CUT → fase normalized"
"CUT akan datang selepas BURST. CUT adalah sesuatu yang dilakukan karena keadaan sudah buruk."
SMART MONEY BEHAVIOR:
- Michael Burry: short 2006, berjalan dengan thesis sampai 2008. Sabar.
- Howard Marks: Siram bensin ikuti bubble, TAPI pulang lebih awal.
- Ricky: "Saya tidak ambil langkah significant di equity. Siram bensin di asset yang ada euforia."
MARKET POSITIONING: Risk asset ditiup ke ATH untuk distribusi. Bukan real structural bullish.
"BullshiIT ini bukan structural bullish — hanya segelintir saham yang jalan."
WHAT TO WATCH: Fund de-risk equity seragam + M2 turning positive = karpet merah sedang digelar. """,
        category="cycle",
        catalyst_types=["fund_derisking","equity_outflow","smart_money_exit","m2_positive_turn",
                         "blow_off_top","bubble_warning","rally_sell"],
        activation_keywords=["fund de-risking","ada rally kita exit","blow off top",
                              "fund unloading china equity","smart money sell rally",
                              "fund rotate equity to bond","m2 supply positive",
                              "equity bubble distribution","magnificent seven expensive",
                              "disconnect market reality","fund seragam keluar"],
        invalidation_keywords=["fund re-entering equity aggressively","m2 surge sustained bullish",
                                "earnings support high valuations"],
        beneficiaries={"us":["TLT","GLD","GC=F","BIL"],"ihsg":["ITMG.JK","BTPS.JK"]},
        fades={"us":["SPY","QQQ","NVDA","MSFT"],"ihsg":["BREN.JK"]},
        regime_alignment={"Q3":1.70,"Q4":1.40,"Q2":0.80,"Q1":0.60},
        typical_duration_weeks=13, conviction_ceiling=0.75, pump_risk=0.15,
        confirmation_signals=["fund_equity_outflow_data","m2_positive_first_time",
                               "smart_money_short_positioning","options_put_call_ratio_elevated",
                               "rally_sold_by_institutions"],
    ),

    NarrativeTemplate(
        name="Ricky — 100% CUT Confirmed (NFP Shock → UST Free Fall → Banjiran Dimulai)",
        description="""The moment Ricky waited for: ALL indicators confirm Fed CUT is 100%.
"Sudah lah. Seperti yang dahulu saya bilang, Amrik itu bobrok banget. Data di manipulasi."
THE TRIGGER EVENT:
NFP: Jauh di bawah ekspektasi. Unemployment 4.1% → 4.3%.
UST RESPONSE (the real signal):
UST 1Y: fell to 4.43% (from ~5.3%)
UST 2Y: fell to 3.95% (BELOW 4% — VERY STRONG)
UST 10Y: fell to 3.81%
UST 30Y: fell to 4.15%
"UST dari tenor 1Y ke atas yield nya semua FREE FALL alias terjun bebas."
WHY THIS MATTERS:
UST 2Y below FFR (5.25-5.5%) by 130bps = market pricing in 5+ cuts
"100% CUT akan terjadi. Tidak ada keraguan lagi."
TIMING ESTIMATE (Ricky): "CUT pertama di Ber Ber Ber period sebelum Pemilu Amrik (November 2024)"
IMPORTANT CAVEAT:
"CUT bukan proses akhirnya. CUT adalah AWAL dari sebuah proses menuju perbaikan."
"Akan ada beberapa fase lagi yang kita lewati setelah CUT (NORMALIZED PHASE)."
"Koreksi setelah CUT: 2 alasan: 1) ekspektasi terlalu tinggi sebelum CUT. 2) Fase normalized adjustment."
WHAT HAPPENS NEXT: Market jatuh SAAT CUT diumumkan (ekspektasi sudah terlalu tinggi).
Then → NORMALIZED → then → STRUCTURAL BULL begins.""",
        category="policy",
        catalyst_types=["fed_cut_100pct","nfp_shock","unemployment_spike","ust_free_fall",
                         "monetary_policy_pivot_final","cut_cycle_start"],
        activation_keywords=["100 pct cut confirmed","nfp shock","unemployment 4.3",
                              "ust 2y below 4","ust free fall","fed cut before election",
                              "powell cut September","cut ber ber period",
                              "monetary policy pivot final","cut 2024"],
        invalidation_keywords=["fed resumes hiking","inflation re-accelerates above 4",
                                "nfp bounces strong","unemployment falls back below 4"],
        beneficiaries={"us":["TLT","IEF","GLD","IWM","EEM","SPY"],
                       "ihsg":["BBCA.JK","CTRA.JK","BEST.JK","BTPS.JK"],
                       "commodities":["GC=F","HG=F"]},
        fades={"us":["UUP","BIL"]},
        regime_alignment={"Q4":1.90,"Q1":1.70,"Q2":0.80,"Q3":0.50},
        typical_duration_weeks=26, conviction_ceiling=0.95, pump_risk=0.10,
        confirmation_signals=["ust2y_below_4pct","unemployment_above_4pct",
                               "fed_swap_100pct_cut","nfp_miss_large",
                               "m2_positive_confirmed","ust1y_below_ffr"],
    ),

    NarrativeTemplate(
        name="Ricky — Stimulus 5-Phase Pattern (Skeptis → Basa Basi → Reaksi Awal → Hints → Bazooka)",
        description="""Ricky2212's universal framework for reading stimulus cycles — applicable to ANY central bank.
"Pattern ini berulang dari waktu ke waktu. 2020 sama. 2008 sama."
5 PHASES OF STIMULUS:
Phase 1 — BASA BASI:
"Central bank kasih stimulus kecil buat perlihatkan bahwa mereka aware. Market skeptis."
Signal: Small policy easing, market doesn't react sustainably.
Phase 2 — MARKET PRESSURE:
"Market menekan central bank dengan menjatuhkan equity agar policy makers bereaksi lebih cepat."
Signal: Market turun terus berhari-hari. "Bursa adalah lambang negara — pemerintah pasti selamatkan."
Phase 3 — STIMULUS AWAL:
"Central bank luncurkan stimulus dosis awal. Market rebound beberapa hari. Lalu turun lagi."
Signal: Rally 2-5 hari setelah announcement, then fades. Market minta lebih banyak.
Phase 4 — HINTS UNTUK NEXT STIMULUS:
"Pemangku kebijakan bilang: kita sudah siapkan stimulus selanjutnya."
Signal: Volatile market, naik turun tinggi menunggu kepastian.
Phase 5 — KETOK PALU MEGA BAZOOKA:
"Final stimulus yang cukup buat menyelesaikan masalah. Market settled."
Signal: Market stops testing lows. Sustained rally begins.
APPLICATION RULE: "Jangan excited di Phase 1-3. REAL GAME baru di Phase 4-5."
"Saya skeptis saat China luncurkan stimulus awal. Skeptis juga saat Amrik kasih hints mau longgarkan."
China 2024 currently at: Phase 3 → Phase 4 transition.
Fed/ECB/BOE: Entering Phase 3-4 with CUT confirmed. """,
        category="policy",
        catalyst_types=["china_stimulus_phase","fed_cut_phase","pboc_rrr_cut",
                         "government_stimulus","policy_easing_cycle","central_bank_bazooka"],
        activation_keywords=["stimulus basa basi","stimulus phase 1","china stimulus cynical",
                              "pboc stimulus market skeptic","stimulus pattern","ketok palu bazooka",
                              "policy stimulus 5 phase","central bank hint next stimulus",
                              "market pressure central bank","china equity pressure pboc",
                              "stimulus real game phase 5","2020 stimulus pattern"],
        invalidation_keywords=["stimulus fired early no effect","hyperinflation prevents stimulus",
                                "fiscal constraint blocks bazooka"],
        beneficiaries={"us":["SPY","QQQ","GLD","EEM"],
                       "ihsg":["BBCA.JK","ITMG.JK"],
                       "global":["FXI","MCHI"]},
        fades={"us":["UUP"]},
        regime_alignment={"Q4":1.70,"Q1":1.60,"Q2":0.90,"Q3":0.70},
        typical_duration_weeks=26, conviction_ceiling=0.80, pump_risk=0.20,
        confirmation_signals=["stimulus_phase5_announcement","sustained_market_stabilization",
                               "china_pboc_1trillion_cny","ecb_rate_cut_confirmed",
                               "fed_125bps_cut_cycle"],
    ),

    NarrativeTemplate(
        name="Ricky — 7-Cut Expected → No-Cut Expected → ... Reverse Psychology",
        description="""Ricky2212's most sophisticated market psychology framework — Fed digantung market.
TIMELINE OF REVERSE PSYCHOLOGY:
Dec 2023: Fed dovish. Market: "7x CUT in 2024!" → CUT in March expected!
Jan-Mar 2024: CUT didn't happen. Market adjusts: "Maybe June..."
Apr 2024: Data hot. Market: "September at earliest... maybe November..."
Jul-Aug 2024: NFP shock. "NO CUT this year!" (extreme pessimism)
→ THEN CUT ACTUALLY HAPPENS = maximum surprise = maximum rally
"Optimistic 7x CUT → NULL realization. Pessimistic NO CUT → ...??? apa yang ada di bayangan anda?"
MECHANISM:
When market expects 7x CUT → price IN aggressively → rally → then disappoint when less CUT.
When market expects NO CUT → price OUT defensively → sell → then rally when CUT happens.
"Fed pintar sekali memainkan psikologis market."
RICKY'S LESSON: "Warning saya di awal tahun: hati-hati over expectation. Market liar."
"Ekspektasi CUT yang berlebihan yang akhirnya mendorong risk asset berlebihan → menghilang sekejap."
INVESTMENT STRATEGY: "Saat pesimistis NO CUT adalah saat terbaik untuk BUY."
"Saat optimistis 7x CUT = saat terbaik untuk EXIT."
KEY QUOTE: "CUT adalah keniscayaan. Tenang saja. Semua central bank PASTI akan lakukan CUT." """,
        category="policy",
        catalyst_types=["fed_cut_expectation_swing","reverse_psychology","fomc_surprise",
                         "market_expectation_reset","no_cut_pessimism","cut_surprise_rally"],
        activation_keywords=["7 cut expected","no cut expected reverse","fed reverse psychology",
                              "cut expectation swing","fomc surprise","market expectation reset",
                              "cut optimism to pessimism","digantung fed","ekspektasi cut liar",
                              "market overexpect cut","fed psychology game",
                              "snb boc ecb cut first fed last"],
        invalidation_keywords=["fed transparent no games","market correctly prices cut",
                                "no cut and no cut rally"],
        beneficiaries={"us":["TLT","GLD"],"ihsg":["BBCA.JK"]},
        fades={"us":[]},
        regime_alignment={"Q4":1.50,"Q3":1.30,"Q2":0.90,"Q1":0.80},
        typical_duration_weeks=8, conviction_ceiling=0.70, pump_risk=0.10,
        confirmation_signals=["market_no_cut_expectation_peak","pessimism_extreme_fed",
                               "fed_swap_below_50pct","ust2y_extreme_fall"],
    ),

    NarrativeTemplate(
        name="Ricky — Magnificent 7 Bubble + Unsustainable Disconnect (12 Points)",
        description="""Ricky2212's 12-point framework for identifying the current market bubble.
"Market yang menyentuh ATH adalah negara yang sedang penyakitan. Masuk akal kah?"
12 DISCONNECTS (Ricky's detailed analysis):
1. Market ATH tapi negara penyakitan (DJIA, S&P, Nikkei, DAX)
2. ATH hanya 7 saham (Magnificent 7). 70% Russell 2000 laporkan kinerja buruk.
3. Mag-7 valuasi: NVDA 75x, AAPL 27x, MSFT 38x, GOOGL 24x, META 35x, AMZN 61x, TSLA 39x
4. Saham beresiko kasih yield < 3%, money market 5.5% zero risk = irrasional
5. $8-9T masih parkir money market meski market ATH = smart money ga percaya
6. BoJ ultra easing, Nikkei ATH 35 tahun = bubble warisan
7. Inverted yield curve = pakem rusak
8. USD kuat tapi hutang $34T = trust illusion
9. Layoff dimana-mana tapi NFP bagus = manipulated data
10. GDP kuat tapi saving rate ~0%, konsumen kerja shift tambahan
11. Ekonomi kuat tapi laba bank amrik anjlok = contradiction
12. Crypto disconnect dari risk-off fundamentals
"BullshiIT: bukan structural bullish. Jack up without earnings support."
"Bidenomics = DISCONNECT yang paling sempurna. Cost of living +18%, real wages -2%."
"Bubble akan meletus. Kapan? Tidak tau. Tapi asset2x akan di Jack up menuju puncak sebelum burst." """,
        category="cycle",
        catalyst_types=["market_bubble","magnificent_7_overvalued","disconnect_signal",
                         "unsustainable_market","bubble_warning","smart_money_skeptical"],
        activation_keywords=["magnificent 7 bubble","nvda 75x pe","market disconnect reality",
                              "ihsg bubble","disconnect 12 points","bullishit not structural",
                              "bidenomics disconnect","inverted yield curve crack",
                              "layoff nfp contradiction","money market 9 trillion",
                              "unsustainable disconnect","blow off top signal",
                              "berkshire cash pile","market jack up distribute"],
        invalidation_keywords=["earnings catch up to valuations","soft landing confirmed",
                                "productivity surge supports pe"],
        beneficiaries={"us":["TLT","GLD","VXX"],"ihsg":["ITMG.JK","BTPS.JK"]},
        fades={"us":["NVDA","QQQ","SPY"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=13, conviction_ceiling=0.75, pump_risk=0.20,
        confirmation_signals=["fund_derisking_seragam","russell2000_divergence",
                               "insider_selling_surge","vix_complacency_extreme",
                               "mag7_pe_above_50_average"],
    ),

]

_NARRATIVES.extend(_NARRATIVES_BATCH7)
NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH7})
for _n in _NARRATIVES_BATCH7:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
