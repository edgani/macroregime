"""config/narrative_universe.py — BATCH 10
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Meneropong deviden ITMG / Bye SMDR / Update BTPS / Thanks BRMS / Edisi siram bensin / DEWA RUPSLB / Segudang cerita Solo ke Hambalang (Prabowo macro)
2.  Kemana saja saya menaruh uang (full asset class allocation framework)
3.  OMON OMON Pemilu dan IHSG (election cycle 2004-2024)
4.  Semua tentang sektor transportasi kapal (container, drybulk, oil tanker, OSV)
5.  Minyak, minyak — oil & gas hulu-hilir deep dive + IEA data

Copy-paste block ini ke bawah file config/narrative_universe.py yang sudah ada,
lalu append merge lines di bagian paling bawah file.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class NarrativeTemplate:
    name: str
    description: str
    category: str
    catalyst_types: List[str]
    activation_keywords: List[str]
    invalidation_keywords: List[str]
    beneficiaries: Dict[str, List[str]]
    fades: Dict[str, List[str]]
    regime_alignment: Dict[str, float]
    typical_duration_weeks: int
    conviction_ceiling: float
    pump_risk: float
    confirmation_signals: List[str]

_NARRATIVES_BATCH10: List[NarrativeTemplate] = [

    # ── ARTICLE 1: Indonesia Macro & Political Transition ─────────────────────
    NarrativeTemplate(
        name="Indonesia Political Transition & Macro Debt Overhang",
        description="""Ricky2212 Indonesia macro framework: "Segudang cerita dari Solo ke Hambalang".
10-year Jokowi (Mulyono) legacy assessment:
- GDP growth mediocre ~5% (never hit 7% target); SBY era reached 6.9% in 2007
- IHSG +52% in 10 years (Jokowi) vs +489% in 10 years (SBY)
- Government debt exploded: Rp 2,601T → Rp 8,444T (+224%); interest cost +200%
- K-shape economy: rich richer, poor poorer; middle class shrunk 57.3M→47.9M (2019→2024)
- 5-month deflation in 2024 = collapsing consumer purchasing power
- 2025 debt wall: ~Rp 800T principal + interest maturing; global refinancing scramble
Prabowo (08) transition:
- Campaign promises: 8% GDP growth, 3M houses, free lunch program
- Cabinet "gemuk" = bloated, political accommodation, potential fiscal waste
- Key economic team: Sri Mulyani, Airlangga, Bahlil, Zulkifli Hasan
- "Melanjutkan" = risk of continuing same non-pro-growth policies
- 08's advantage: patriotism, wide network, loyal capable circle, legacy motivation
Election cycle history (Pilpres framework):
- 2004: SBY-JK win → IHSG +18% (market darling correct)
- 2009: SBY-Boediono win → IHSG +53.7% (commodity supercycle + China)
- 2014: JKW-JK win → IHSG +17.6% (new leader euphoria)
- 2019: JKW-Ma'ruf win → IHSG +4.6% (weaker, market already priced in)
- 2024: Prabowo-Gibran = "keberlanjutan" = market priced in continuity
Key risk: global Western economic weakness + Indonesia domestic demand collapse.
Opportunity: if even slightly pro-growth policy emerges, foreign capital floods in.
"Semoga 08 bukan Mulyono, semoga 08 adalah Modi buat Indonesia."""",
        category="geopolitical",
        catalyst_types=["political_transition","election_cycle","debt_maturity_wall","deflation","cabinet_formation",
            "fiscal_policy_shift","middle_class_collapse","consumer_demand_collapse"],
        activation_keywords=["pilpres","pemilu","prabowo","08","solo ke hambalang","jokowi","mulyono",
            "debt indonesia","utang negara","k shape economy","kelas menengah","deflasi indonesia",
            "apbn 2025","hutang jatuh tempo","kabinet gemuk","sri mulyani","airlangga","bahlil",
            "pertumbuhan ekonomi 8%","3 juta rumah","market darling pilpres","ihsg pilpres",
            "sbys era","modi indonesia","fiscal stimulus indonesia","rupiah","middle class shrink"],
        invalidation_keywords=["prabowo reformasi","pro growth cabinet","debt restructured_smoothly",
            "middle_class_recovers","deflation_ends","8% gdp_achieved"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK"],"us":["EIDO","IDX"],
            "bonds":["INDO_gb","IDR_ust"],"fx":["USDIDR"]},
        fades={"ihsg":["high_beta_konglo","property","consumer_discretionary"],"us":["EM_high_beta"]},
        regime_alignment={"Q1":1.30,"Q2":1.10,"Q3":0.90,"Q4":0.70},
        typical_duration_weeks=52,
        conviction_ceiling=0.75,
        pump_risk=0.15,
        confirmation_signals=["cabinet_announcement_prabowo","apbn_2025_deficit_widens","deflation_6months",
            "middle_class_data_shrink","debt_refinancing_spread_widens","ihsg_pilpres_reaction"],
    ),

    # ── ARTICLE 2: Portfolio Allocation & Asset Class Framework ─────────────────
    NarrativeTemplate(
        name="Ricky2212 Personal Portfolio — Multi-Asset Allocation Framework",
        description="""Ricky2212 complete asset allocation philosophy (Kiyosaki Cashflow Quadrant inspired):
A. STOCKS (majority): compounding wealth + dividend cashflow; local + foreign bursa
B. BONDS: FR series fixed coupon + capital appreciation; cycle-driven entry
C. MUTUAL FUNDS: money market (emergency fund) + equity ETF (low-cost big cap grab)
D. OPTIONS: small allocation, leveraged call options on foreign stocks
E. MARGIN FUTURES: oil & gold futures contracts when clear macro indicator (e.g., oil <$70)
F. CRYPTO: "spekulasi terukur" — small cap coins, not majors; macro-policy-linked timing
G. PROPERTY: 2 rental hunian; capital appreciation + monthly rental cashflow
H. DEPOSITO: 5-year monthly expense equivalent = emergency fortress; "5 tahun cukup untuk cycle pasar membaik"
I. REAL BUSINESS: 4 UMKM businesses; monthly cashflow to "dapur"
J. DIGITAL GOLD: stored digitally, convertible to physical; yield-bearing deposit
K. INSURANCE: 4 polis (life + health) = "investasi yang melindungi investasi"; bought young & healthy
Philosophy:
- "Melek financial" = explore all products from low-risk to high-risk, legal to money game
- "Free debt" = only minimal operational debt
- No CFA/certification; pure passion-driven self-education
- As age increases: prioritize comfort and happiness over maximum return
- Stocks remain best compounding instrument, but diversification protects the journey""",
        category="psychology",
        catalyst_types=["asset_allocation","portfolio_diversification","financial_literacy","compound_wealth",
            "emergency_fund","multi_asset","risk_management"],
        activation_keywords=["portfolio allocation","asset class","cashflow quadrant","kiyosaki","melek financial",
            "reksadana","obligasi","deposito","crypto","property","option","margin futures","digital gold",
            "asuransi","bisnis riil","umkm","compounding wealth","free debt","dana darurat","multi asset",
            "financial literacy","investasi jangka panjang","dividen cashflow"],
        invalidation_keywords=["all_in_stocks","no_diversification","ignore_insurance","ignore_emergency_fund"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ITMG.JK","BYAN.JK","TMAS.JK"],
            "us":["VTI","VOO","TLT","GLD"],"global":["EIDO","IDX","DBC"]},
        fades={"ihsg":["penny_stock_gamble"],"us":["leveraged_etfs","0dte_options"]},
        regime_alignment={"Q1":1.00,"Q2":1.00,"Q3":1.00,"Q4":1.00},
        typical_duration_weeks=260,
        conviction_ceiling=0.95,
        pump_risk=0.05,
        confirmation_signals=["portfolio_rebalancing","asset_class_rotation","emergency_fund_fully_funded",
            "insurance_policies_active","real_business_cashflow_positive"],
    ),

    # ── ARTICLE 3: Indonesia Shipping Sector Comprehensive ────────────────────
    NarrativeTemplate(
        name="Indonesia Shipping Sector — Subsector Moat & Supply-Demand Matrix",
        description="""Ricky2212 shipping sector deep-dive with subsector ratings:
NATURE: capital intensive, barrier to entry high, revenue = charter rates.
CONTRACT TYPES: Time Charter (long-term, fixed, certainty) vs Spot Charter (short-term, volatile, upside).
SUBSECTOR 1 — CONTAINER SHIPPING (SMDR, TMAS):
- Post-COVID boom fading; orderbook delivery 2023 peak; supply-demand rebalancing
- Red Sea = only normalized rates back from depressed levels, not supercycle
- SMDR Rating B+ (regional exposure + tanker diversification); TMAS Rating B- (local dominant)
- Ricky EXIT SMDR: "conditional situation, not structural; too many cheerleaders early"
SUBSECTOR 2 — DRYBULK SHIPPING (TPMA, MBSS, HAIS, PSSI, NELY):
- Supply tight until 2026; new orders minimal (shipyards busy with containers)
- Capesize rates spiked post-Russia-Ukraine; fading but supply side still constrained
- Red Sea impact moderate; demand forced down by central bank tightening
- TPMA/HAIS Rating A/A- (aggressive expansion); MBSS/PSSI/NELY Rating A/A- (stable + dividend)
SUBSECTOR 3 — OIL TANKER (BULL, SOCI, HUMI):
- "SUPER SUPER AKUT" supply shortage; no new orders until 2026+; fleet aging
- Russia-Europe route disruption → longer hauls; Red Sea → even longer hauls
- OPEC cuts = temporary demand dampener; when demand returns = explosion
- IMO 2024 + EEXI = more scrapping + slow steaming (20% speed reduction) = tighter supply
- BULL Rating C (bad GCG); SOCI Rating B- (Pertamina offtaker = rate suppression); HUMI Rating B (GCG black spot)
- Ricky prefers foreign tanker plays for spot sensitivity
SUBSECTOR 4 — OSV (WINS, LEAD, ELPI, BBRM):
- "Supply shortage paling parah"; zero new orders; high-tier AHTS/PSV rates $1.50-2.00/HP
- Offshore discoveries (Geng North-1, Layaran-1) = massive OSV demand
- WINS Rating A- (high+mid tier dominant, regional first-mover)
- LEAD Rating B-→A (if restructuring + DES complete)
- ELPI no rating (low tier, low margin); BBRM too small fleet
- "Kapal mana yang berlayar? Container = lewat. Drybulk = better. Oil tanker = berjaya. OSV = no excuse berjaya."
Key catalysts: Red Sea prolongation, OPEC production increase, offshore drilling ramp, IMO regulation enforcement.""",
        category="sector",
        catalyst_types=["shipping_supply_shortage","red_sea_disruption","imo_2024","eexi_regulation",
            "oil_tanker_shortage","osv_rate_spike","drybulk_tightness","container_orderbook_delivery"],
        activation_keywords=["shipping sector","kapal container","drybulk shipping","oil tanker","osv",
            "offshore vessel","red sea","suez canal","time charter","spot charter","daily charter rate",
            "supply shortage kapal","imo 2024","eexi","slow steaming","shipyard orderbook","smdr","tmas",
            "tpma","mbss","hais","pssi","nely","bull","soci","humi","wins","lead","elpi","bbrm",
            "capesize","vlcc","ahts","psv","dirty tanker","clean tanker","tarif sewa kapal"],
        invalidation_keywords=["shipyard_orderbook_surge","oil_price_crash_60","red_sea_resolved",
            "container_rates_collapse","new_building_orders_return"],
        beneficiaries={"ihsg":["WINS.JK","LEAD.JK","TPMA.JK","MBSS.JK","HAIS.JK","PSSI.JK","NELY.JK",
            "SMDR.JK","TMAS.JK","BULL.JK","SOCI.JK","HUMI.JK","ELPI.JK","BBRM.JK"],
            "global":["ZIM","TNP","FRO","STNG","TNK","TDW"]},
        fades={"ihsg":["container_pure_play","low_tier_osv"],"us":["shipping_etfs_broad"]},
        regime_alignment={"Q1":1.30,"Q2":1.20,"Q3":1.10,"Q4":0.90},
        typical_duration_weeks=78,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["smdr_volume_spike_cheerleader","wins_utilization_85","lead_des_complete",
            "oil_tanker_rates_spike","red_sea_rerouting_sustained","imo_scrapping_accelerates",
            "new_offshore_block_drilling","baltic_dry_index_above_2000"],
    ),

    # ── ARTICLE 4: Oil & Gas Hulu-Hilir Value Chain ───────────────────────────
    NarrativeTemplate(
        name="Oil & Gas Sector — Hulu-Hilir Value Chain & Supply Gap",
        description="""Ricky2212 oil & gas comprehensive framework:
MACRO BACKDROP:
- Underinvestment since 2015 (Paris Climate Act → banks stop funding fossil → capex constrained)
- Post-Russia-Ukraine: world woke up to structural supply shortage
- IEA 2024: demand growth +1.2 mb/d (vs +2.3 in 2023); supply +1.5 mb/d to 103.5 mb/d record
- China = 70-80% of demand growth; India overtaking China as largest demand growth driver through 2030
- India diesel = half of demand rise; gasoline growth muted by EVs; petrochemicals = key
- Current oil price ~$80 = still feasible for new investment; capex continues flowing
- "Turunnya harga minyak sekarang adalah keadaan yang DIPAKSA oleh Central Bank dunia"
- When monetary easing returns → demand jumps → supply gap explodes (no spare capacity)
INDONESIA DISCOVERIES:
- Geng North-1 (ENI) + Layaran-1 (Mubadala) = top 5 global discoveries 2023; 6 tcf gas-in-place
- SKK Migas: "future gas luar biasa di Indonesia"
- RUU Migas baru pending = regulatory catalyst
HULU-HILIR VALUE CHAIN:
1. PEMETAAN: ELSA (Rating A-; minus BUMN)
2. KONSTRUKSI RIG: APEX (B-), RUIS (B), INDY (no rating, non-migas majority)
3. OFFSHORE SUPPORT: WINS, LEAD, BBRM, ELPI (OSV supercycle)
4. DRILLING: APEX (only local listed player)
5. STORAGE FPSO/FSO: SHIP (Rating A; expensive valuation)
6. DRILLING MUD: OBMD (B+)
7. DIRTY TANKER (crude transport): BULL (C), SOCI (B-), HUMI (B)
8. REFINERY: no public listed refinery in Indonesia
9. PRODUCT TANKER/CLEAN: BULL, SOCI, SMDR, HITS, HUMI
10. STORAGE & DISTRIBUTION: AKRA (A+), ELSA
11. PIPELINE: PGAS (A), RAJA (B)
12. CONCESSION HOLDERS: ENRG (B), MEDC (B+), Pertamina (state)
SENSITIVITY: Hulu extremely sensitive to oil price; when price unfeasible = drilling stops.
"Saya tetap berjalan di hulu bersama OSV dan si eneng geulis."
Key data: OPEC+ voluntary cuts; non-OPEC+ (US, Brazil, Guyana, Canada) driving supply growth.
Risk: Middle East escalation disrupting Red Sea/Suez (10% seaborne oil trade).""",
        category="sector",
        catalyst_types=["oil_supply_shortage","iea_demand_surge","india_oil_demand","china_petrochemical",
            "offshore_discovery","ruu_migas","opec_cut","non_opec_supply","monetary_easing_oil_demand"],
        activation_keywords=["minyak","oil and gas","hulu migas","hilir migas","iea report","oil demand",
            "oil supply","opec","non opec","geng north-1","layaran-1","skk migas","ruu migas","underinvestment fossil",
            "paris climate act","cost recovery","psc","production sharing contract","fpso","fso","drilling mud",
            "oil tanker","dirty tanker","clean tanker","product tanker","refinery","akra","pgas","raja",
            "apex","ruis","elsa","ship","obmd","enrg","medc","pertamina","oil price 80","brent","wti",
            "india oil demand","china oil demand","petrochemical","gas discovery","offshore drilling"],
        invalidation_keywords=["oil_price_crash_50","iea_demand_cut_forecast","ruu_migas_rejected",
            "offshore_project_cancelled","renewable_replacement_accelerates","opec_flood_market"],
        beneficiaries={"ihsg":["ELSA.JK","LEAD.JK","WINS.JK","BBRM.JK","OBMD.JK","SHIP.JK","AKRA.JK",
            "PGAS.JK","RAJA.JK","ENRG.JK","MEDC.JK","BULL.JK","SOCI.JK","HUMI.JK"],"global":["XLE","OIH","USO","XOM","CVX"]},
        fades={"ihsg":["renewable_energy_pure","coal_exit_plays"],"us":["clean_energy_etfs"]},
        regime_alignment={"Q1":1.40,"Q2":1.30,"Q3":1.20,"Q4":1.00},
        typical_duration_weeks=104,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["iea_demand_revision_up","india_demand_6_6mbd_2030","geng_north_1_production_start",
            "layaran_1_production_start","ruu_migas_passed","oil_tanker_orderbook_zero","brent_above_90_sustained",
            "offshore_rig_count_global_rise"],
    ),

    # ── ARTICLE 5: Tactical Micro Plays & Exit Signals ──────────────────────────
    NarrativeTemplate(
        name="Indonesia Tactical Micro Plays — Exit Timing & Short-Term Narrative Rides",
        description="""Ricky2212 tactical short-term framework ("siram bensin" / "mencopet" / "nyiram bensin"):
PHILOSOPHY:
- "Sekarang saya ga bisa bermain panjang. Yang bisa dilakukan = permainan pendek dengan narrative kuat."
- "Semakin kuat reason & narrative, semakin pede menikmati permainan pendek."
- "Saya ga berniat MERAMPOK, hanya MENCOPET."
- "Pulang kalau pestanya sudah terlalu meriah, sudah banyak cheerleader, sudah ada yang mabuk-mabukan."
- "Bukan untuk ditiru. Sesuaikan dengan risk profile masing-masing."
EXIT SIGNALS:
1. SMDR (container): "conditional situation, not structural; too many cheerleaders at early cycle; peace talks at peak rates = exit"
2. BRMS (B-Indicator gold): "Thanks BRMS, saatnya pulang pesta. Saya tau kamu lagi kejar Perfect Exit Strategy."
3. ITMG (coal dividend): DPR ~65% = total div ~Rp 4,450; interim Rp 2,660; final ~Rp 1,790; DY ~7% @ 26,000 = defensive hold
4. BTPS (microfinance bank): QoQ progress smooth; CKPN cycle ending Oct 2024; DPR 50-60%; EPS FY24 ~150; DY 6.8-8% @ 1,140; "worst is over"
5. DEWA (Bakrie-Salim gold): RUPSLB Jun 2025 = potential board change (Salim trusted person as commissioner) + "agenda besar" beyond imagination
CURRENT "SIRAM BENSIN" PORTFOLIO:
- BEST: asset play too cheap + IDR strengthening bet (performing well)
- MCOR: post-CCB transformation, premium segment, Chinatown branches (performing well)
- DYAN: agile small cap (performing well)
- BRMS: gold narrative pure ride (exited)
- LEAD: OSV narrative + DES catalyst (ultimate siram bensin)
- SICO: healthy upstream oil, MC ~80B, PE ~4x, strong clients (new addition)
Framework: "Enjoy while it lasts. Euphoria not yet peak but signs visible."
Warning: "Jangan ikut-ikutan. Ini cara saya menikmatinya. Anda punya cara lain?"""",
        category="cycle",
        catalyst_types=["tactical_short_term","narrative_ride","exit_timing","cheerleader_peak","siram_bensin",
            "dividend_play","microfinance_recovery","corporate_action_de_dewa"],
        activation_keywords=["siram bensin","mencopet","permainan pendek","short term play","narrative ride",
            "exit strategy","pulang pesta","cheerleader","mabuk dalam pesta","conditional situation",
            "smdr exit","brms exit","itmg dividen","btps progress","dewa rupslb","best","mcor","dyan",
            "sico","lead","enjoy while it lasts","euphoria signs","risk profile","tactical micro"],
        invalidation_keywords=["narrative_collapses","exit_missed","holding_too_long","cheerleader_exodus",
            "dividend_cut","corporate_action_cancelled"],
        beneficiaries={"ihsg":["BEST.JK","MCOR.JK","DYAN.JK","SICO.JK","ITMG.JK","BTPS.JK","DEWA.JK"],"us":["short_term_momentum"]},
        fades={"ihsg":["high_flyer_peak","overcrowded_trade","retail_favorite_at_top"],"us":["meme_stocks"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=8,
        conviction_ceiling=0.75,
        pump_risk=0.35,
        confirmation_signals=["brms_volume_peak_then_drop","smdr_cheerleader_spike","itmg_rups_dividend_1790",
            "btps_ckpn_oct2024_end","dewa_rupslb_salim_board","best_mcor_dyan_price_momentum",
            "sico_contract_award","euphoria_breadth_indicator_peak"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH10)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH10})
# for _n in _NARRATIVES_BATCH10:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
