"""config/narrative_universe.py — BATCH 11
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Semester kedua / Sell in May / Ber-Ber-Ber / July-Aug peak / Fed CUT politics
2.  Pelajaran dari UST & leading indicator (terminal rate, IYC, Copper, hard landing)
3.  Blow off the top (euphoria rally, peaked market, denial phase, tactical plays)
4.  Segudang cerita Solo ke Hambalang (Prabowo transition, Jokowi legacy, debt, deflation)
5.  Beneran Untung Mestinya Ini (BUMI desert/penutup siram bensin, konglo peak)
6.  Logindo — mencari harga untuk berlabuh (post-DES, oil+CA+exit, Q3 outstanding)
7.  Teeeee Saatttteeeeee (MPIX Madura Investment, tech boom, WIFI effect, QRIS fintech)
8.  TOBA — ada apa? (Danantara EBT, waste-to-energy, Pandu Sjahrir, Green project)
9.  WIRG terbang (metaverse→edutech, Hashim/08, smart screen 288k schools, pure narrative)

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

_NARRATIVES_BATCH11: List[NarrativeTemplate] = [

    # ── ARTICLE 1+2+3: Fed CUT Cycle → Blow-Off-Top → Market Peak ─────────────
    NarrativeTemplate(
        name="Fed CUT Cycle → Blow-Off-Top → Peaked Market Denial",
        description="""Ricky2212 integrated macro-cycle framework:
SELL IN MAY: not about May itself, but portfolio reduction ahead of summer holiday.
JULY-AUGUST PEAK: indices hit ATH as market anticipates H1 earnings; Nasdaq, Nikkei breaking records.
BER-BER-BER PERIOD (Sept-Oct): historically worst months — GFC 2008, WTC 2001, Asian Crisis 1997, dot-com 2002, Great Depression.
- 2022: Oct correction ~25% from ATH (fastest Fed tightening)
- 2023: Oct bottom before recovery
FED CUT TIMING:
- UST leading indicator: 1M 5.37%, 3M 5.21% (signals 25bps Sep), 1Y 4.48% (100bps+ in 1yr), 2Y 3.97% (150-175bps in 2yr), 10Y 3.84% (terminal rate ~2.5-2.75%)
- IYC normalization: 2Y<30Y already normal; 2Y vs 10Y spread narrowing = full normalization imminent
- Copper crashed >20% from highs = bellwether of economic weakness = hard landing signal
- JPM: 100bps cut this year; Citi: 3×25bps now + 8×25bps next year; BoA: 2×50bps + 1×25bps
- Powell dovish pivot: "can cut before hitting 2% inflation" = admission economy suffering
- Political angle: Democrats using CUT as campaign tool to save market before election
BLOW-OFF-TOP:
- Post-CUT euphoria rally = market spikes to new ATH repeatedly = peaked market
- Denial phase: "mana resesi?" crowd mocks bears while market forms top
- Signs of peak: IWM/Russell 2000 ATH, crypto ATH, wild volatility (+1000/-1000 frequent)
- Historical precedents: 2008, 2001, 1929, Japan Lost Decade pre-bubble
- 48 weeks without meaningful correction while disconnect from real economy widens
TACTICAL PLAYS IN BLOW-OFF-TOP: SMDR (exited), SMRA (exited), BRMS (exited), Logindo, BEST, DYAN, MCOR = "siram bensin" short-term narrative rides
Strategy: raise cash during euphoria; "prepared" portfolio = defensive positioning before storm""",
        category="cycle",
        catalyst_types=["fed_cut_cycle","blow_off_top","market_peak","ber_ber_ber","ust_yield_signal",
            "copper_crash","hard_landing","election_politics_fed","euphoria_rally","denial_phase"],
        activation_keywords=["sell in may","ber ber ber","blow off the top","market peaked","euphoria rally",
            "ust 2y","ust 10y","terminal rate","copper crash","hard landing","jpm 100bps cut","citi 8 cut",
            "powell dovish","cut before 2% inflation","biden campaign cut","denial phase","iwm ath",
            "russell 2000 ath","crypto ath","volatile 1000","48 weeks no correction","disconnect market real economy",
            "semester kedua","july august peak","september october crash","fed meeting september",
            "fed meeting november","odds cut 85%","iyc normalization","yield curve normalization"],
        invalidation_keywords=["soft landing confirmed","no cut needed","market_ignores_macro","blow_off_top_cancelled",
            "copper_recovers","ust_yields_rise","fed_hawkish_pivot"],
        beneficiaries={"us":["TLT","IEF","GLD","VIX","SQQQ","SH"],"ihsg":["BBCA.JK","BBRI.JK","KLBF.JK","UNVR.JK"],
            "safe_haven":["USD_cash","IDR_cash","money_market"]},
        fades={"us":["IWM","QQQ","SPY","high_beta_momentum","meme_stocks","crypto"],"ihsg":["high_flyer","property","consumer_discretionary"]},
        regime_alignment={"Q3":1.90,"Q4":1.70,"Q2":1.30,"Q1":0.80},
        typical_duration_weeks=16,
        conviction_ceiling=0.85,
        pump_risk=0.20,
        confirmation_signals=["ust_2y_below_4pct","copper_down_20pct_from_highs","iwm_breaks_ath",
            "crypto_total_market_cap_ath","vix_spike_then_collapse","fed_cut_50bps_confirmed",
            "ber_ber_ber_september_sell_off","nfp_revised_down_12months","unemployment_above_4_5pct"],
    ),

    # ── ARTICLE 4: Prabowo Transition & Indonesia Macro Debt Overhang ─────────
    NarrativeTemplate(
        name="Indonesia Prabowo Transition — Debt Wall & K-Shape Economy",
        description="""Ricky2212 Indonesia political transition deep-dive:
JOKOWI 10-YEAR LEGACY:
- GDP growth mediocre ~5% (never hit 7% target); SBY peaked 6.9% in 2007
- IHSG +52% in 10 years (Jokowi) vs +489% in 10 years (SBY)
- Government debt: Rp 2,601T → Rp 8,444T (+224%); interest cost +200%
- K-shape economy: rich richer, poor poorer; middle class 57.3M→47.9M (2019→2024)
- 5-month deflation 2024 = collapsing consumer purchasing power
- PHK 52,993 (Sep 2024), up 25.3% YoY
- "Bangun infrastruktur" = BAU (business as usual), not extraordinary achievement
- MP3EI master plan laid foundation; current government just executed pre-planned projects
PRABOWO (08) TRANSITION:
- Campaign: 8% GDP growth, 3M houses, free lunch program
- Cabinet "gemuk" = bloated, political accommodation, potential fiscal waste
- Economic team: Sri Mulyani, Airlangga, Bahlil, Zulkifli Hasan
- "Melanjutkan" = risk of continuing same non-pro-growth policies
- 08 advantages: patriotism, wide network, loyal capable circle, legacy motivation
- Risk: still seen as shadow of Jokowi/Mulyono regime
2025 DEBT WALL:
- ~Rp 800T principal + interest maturing in 2025
- Global 5-year COVID debt cycle refinancing scramble
- APBN ~Rp 3,000T; 30% to regions; debt service eats massive portion
- Fiscal space for government spending severely constrained
OPPORTUNITY:
- Global Western weakness = capital flight to EM
- "Sedikit saja kebijakan pro Growth → uang bakal ngucur deres ke Indonesia"
- 08 as "Modi for Indonesia" = hope for reform and breakout growth
Key data: Q3 2024 GDP likely below 5%; Q4 saved by seasonal factors (Pilkada, Christmas).
"Semoga 08 bukan Mulyono, semoga 08 adalah Modi buat Indonesia."""",
        category="geopolitical",
        catalyst_types=["political_transition","debt_maturity_wall","deflation","cabinet_formation",
            "fiscal_policy_shift","middle_class_collapse","consumer_demand_collapse","pilkada"],
        activation_keywords=["prabowo","08","solo ke hambalang","jokowi","mulyono","debt indonesia","utang negara",
            "k shape economy","kelas menengah","deflasi indonesia","apbn 2025","hutang jatuh tempo 2025",
            "kabinet gemuk","sri mulyani","airlangga","bahlil","zulkifli hasan","pertumbuhan 8%",
            "3 juta rumah","makan siang gratis","modi indonesia","phk indonesia","middle class shrink",
            "q3 gdp below 5","pilkada 2024","refinancing hutang","fiscal space","pro growth policy"],
        invalidation_keywords=["prabowo reformasi","pro growth cabinet","debt_restructured_smoothly",
            "middle_class_recovers","deflation_ends","8% gdp_achieved"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK","WIFI.JK"],
            "us":["EIDO","IDX"],"bonds":["INDO_gb","IDR_ust"],"fx":["USDIDR"]},
        fades={"ihsg":["high_beta_konglo","property","consumer_discretionary","high_flyer"],"us":["EM_high_beta"]},
        regime_alignment={"Q1":1.30,"Q2":1.10,"Q3":0.90,"Q4":0.70},
        typical_duration_weeks=52,
        conviction_ceiling=0.75,
        pump_risk=0.15,
        confirmation_signals=["cabinet_announcement_prabowo","apbn_2025_deficit_widens","deflation_6months",
            "middle_class_data_shrink","debt_refinancing_spread_widens","phk_above_50k","q3_gdp_below_5pct"],
    ),

    # ── ARTICLE 5: BUMI as Konglo Peak Desert / Penutup Siram Bensin ───────────
    NarrativeTemplate(
        name="BUMI — Konglo Peak Desert & Narrative Engineering Finale",
        description="""Ricky2212 BUMI as the final "desert" in the konglo siram-bensin feast:
CONTEXT: konglo plays all surging — BREN (PP), AMMN (Salim), MLPT (Lippo), PANI (Salim super-star), BRMS (Salim+Bakrie+Agus).
BUMI = "Beneran Untung Mestinya Ini" = the remaining konglo play with highest potential ceiling.
NARRATIVE ENGINEERING (Om AP / Agus Projo):
- Phase 1: diversification statement → "non-coal & renewable energy" = opening remarks
- Phase 2: Green ESG narrative (kokas/smelter acquisition) = appetizer
- Phase 3: MIP (Domestic Market Obligation) >90% chance before regime change = main course
- Phase 4: 2 more undisclosed stories = dessert (Ricky hints but keeps secret)
- Phase 5: potential index inclusion (LQ45/FTSE/MSCI) = ultimate exit door for konglo
VOLUME SIGNAL: daily turnover bludak (5x normal) + fund participation rumors = distribution loading
HISTORICAL PATTERN: Bakrie always exits at peak cycle via placement/block sale (Nat Rothschild precedent ~7-8x, Tata precedent even higher). Salim never exits for "cuan mini" — thinks 5 steps ahead.
CURRENT STATE: BUMI free debt post mega RI (unprecedented in 20 years); clean balance sheet = ready for final act.
"Saham edisi nyiram bensin ini punya potensi sama seperti konglo play yang bernaung di bawahnya."
"BUMI akan jadi penutup saya dalam edisi siram bensin."
Risk: when konglo exits, retail left holding bag. "Pulang sebelum pesta bubar."
"From sini lah sinyal akan datang untuk memperlihatkan ... [next article]."""",
        category="cycle",
        catalyst_types=["b_indicator","bakrie_salim_synergy","commodity_cycle_peak","narrative_engineering",
            "green_esg_narrative","mip_policy","index_inclusion","placement_exit","volume_bludak"],
        activation_keywords=["beneran untung mestinya ini","bumi desert","bumi penutup siram bensin","bumi konglo peak",
            "om ap","agus projo","bumi green","bumi kokas","bumi smelter","bumi mip","domestic market obligation",
            "bumi index inclusion","bumi lq45","bumi ftse","bumi msci","bumi volume bludak","bumi fund participation",
            "bakrie exit bumi","salim exit bumi","bumi free debt","bumi mega ri","bumi placement",
            "bumi turnover 5x","bumi narrative engineering","bumi diversification","bumi renewable"],
        invalidation_keywords=["bumi_exit_completed","mip_cancelled","green_narrative_collapses",
            "salim_sells_out","index_inclusion_rejected"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","ENRG.JK","DEWA.JK","BIPI.JK","ADRO.JK","INDY.JK","PTBA.JK"],
            "commodities":["GC=F","HG=F","CL=F"]},
        fades={"ihsg":["consumer_goods","property","high_flying_tech"],"us":["tech_growth"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":0.80,"Q1":0.50},
        typical_duration_weeks=13,
        conviction_ceiling=0.85,
        pump_risk=0.30,
        confirmation_signals=["bumi_volume_5x_avg","mip_policy_draft_leak","green_esg_announcement_bumi",
            "index_inclusion_announcement_bumi","salim_placement_bumi","adro_green_spin_off","fund_participation_bumi"],
    ),

    # ── ARTICLE 6: Logindo Post-DES Exit Architecture ──────────────────────────
    NarrativeTemplate(
        name="Logindo (LEAD) Post-DES — Exit Architecture & Karpet Merah",
        description="""Ricky2212 Logindo post-Debt-Equity-Swap framework:
POST-DES STATUS (Nov 2024):
- DES executed @ Rp 186: PT JTS $15M + OCP $5M = $20M total swapped
- OCP (distressed fund) now holds equity; must engineer exit with profit
- "OCP bukan Sinterklas — mereka mau yield besar. Karpet merah untuk exit harus disiapkan."
CURRENT THESIS: Oil narrative + Corporate Action + Exit Strategy (no longer pure oil thesis)
- "Logindo is oil narrative, CA, Exit Strategy Play"
- "Alpha stock — when value unlocked, no need to stay"
Q3 2024: outstanding performance; Q4 expected to continue
- Management has calculated story trajectory into financials
- Revaluation asset: "bisa saja dijadikan story tambahan; tinggal kapan dibutuhkan"
PRICE ACTION POST-DES:
- DES announcement spike but NO FOMO created (retail sold into strength = reverse psychology)
- Unlike WINS where cheerleaders created perfect euphoria setup
- "Maker rapi mainnya — pihak terlibat mau cari sejumlah barang di pasar sebelum puncak aksi"
- OCP exit must be ABOVE DES price (186) to generate profit
- "Harusnya OCP exit di berapa? Dikira2x aja gimana caranya supaya OCP cuan."
EXIT SCENARIOS:
- IB engineers final exit narrative (karpet merah)
- Oil narrative jack-up (small bump sufficient)
- Revaluation asset as bonus story
- Final peak = OCP exit + retail FOMO
"Logindo sedang mencari harga terbaik buat kapalnya berlabuh."
"Sabar aja — siapa tau kejutannya datang."""",
        category="corporate_action",
        catalyst_types=["post_des_exit","distressed_fund_exit","oil_narrative_jack_up","revaluation_asset",
            "karpet_merah","fomo_creation","cheerleader_activation"],
        activation_keywords=["logindo post des","logindo exit architecture","logindo karpet merah","ocp exit",
            "logindo oil narrative","logindo ca","logindo exit strategy","logindo alpha stock","logindo value unlocked",
            "logindo q3 outstanding","logindo q4","logindo revaluasi","logindo maker rapi","logindo fomo",
            "logindo cheerleader","logindo puncak aksi","logindo berlabuh","logindo harga terbaik",
            "logindo above 186","logindo distressed exit","logindo ib narrative","logindo story trajectory"],
        invalidation_keywords=["logindo_des_fails","ocp_forced_liquidation","logindo_bankruptcy","oil_narrative_collapses",
            "revaluation_blocked"],
        beneficiaries={"ihsg":["LEAD.JK"],"distressed":["LEAD.JK"],"turnaround":["LEAD.JK"]},
        fades={"ihsg":["WINS.JK","ELSA.JK"],"us":["high_leverage_sector"]},
        regime_alignment={"Q3":1.20,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["logindo_volume_spike_fomo","logindo_cheerleader_activation","logindo_price_above_250",
            "logindo_revaluation_announcement","ocp_exit_placement","logindo_q4_outstanding","oil_narrative_jack_up_small"],
    ),

    # ── ARTICLE 7+9: Indonesia Tech Sector Boom — WIFI Effect & Fintech ────────
    NarrativeTemplate(
        name="Indonesia Tech Sector Boom — WIFI Effect & Fintech Narrative Plays",
        description="""Ricky2212 Indonesia tech sector narrative framework:
MACRO TRIGGER:
- China DeepSeek effect → Alibaba, JD, Xiaomi, chip/AI support stocks surging
- Hong Kong Tech Index broke 3-year high
- Foreign funds rotating back to China tech (Tepper, Dalio, Burry already positioned)
- Indonesia tech sector catching tailwind
WIFI EFFECT:
- WIFI (WIFI Indonesia) acquired by 08's brother (Hashim family) → speculation of big plans
- WIFI = "big cap" of Indonesia tech; DOOH, INET, EDGE, ELIT, ATIC = "meme coins" that move when big cap moves
- WIRG (Wir Asia) = metaverse→edutech pivot; Hashim/08 related; CA right issue incoming
- Smart screen 288k schools to remote Indonesia = government edutech contract
- WIRG + WIFI synergy: WIFI provides internet, WIRG provides hardware
- Pure FINDIMINTIL play (no fundamentals, pure narrative); "Waktunya Indonesia Riang Gembira"
MPIX (Mitra Pedagang Indonesia / Madura Investment):
- QRIS + PoS + digital goods + loan channeling for UKM/UMKM
- 588,341 registered users (CAGR 66%); 309,099 QRIS merchants (CAGR 3.4%); 62,007 PoS merchants (CAGR 164%)
- Revenue 1,027B, Net Profit 18.1B, PER 5.84x, PBV 0.73x, ROE 12.74%
- "Tech company dijual tidak sampai 5x laba" = asymmetrical risk/reward
- Madura family business network = strong grassroots distribution
- "Sate Madura menjamur dimana-mana karena koordinatornya kuat" = MPIX business model
RISK WARNING:
- "No Funda, bagian kecil dari perjalanan Jack Up"
- "Saham seperti WIRG sangat risky — tidak semua cocok"
- "Endingnya nanti belum tentu semua gembira"
- "Jangan ikut-ikutan jadi penggembira kalau tidak mengerti resiko"
Current plays: WIFI (big cap anchor), ELIT (follower), MPIX (fintech value), WIRG (pure narrative)""",
        category="sector",
        catalyst_types=["tech_sector_boom","wifi_effect","china_deepseek","fintech_narrative","edutech_government",
            "qris_growth","umkm_digitalization","hashim_related","08_family","findimintil_play"],
        activation_keywords=["wifi effect","tech sector boom","indonesia tech","deepseek","china tech boom",
            "wirg","wifi indonesia","dooh","inet","edge","elit","atic","mpix","madura investment","qris",
            "pos merchant","umkm digital","edutech","smart screen sekolah","hashim","08 brother","findimintil",
            "metaverse","wir asia","hong kong tech index","tepper china","dalio china","burry china",
            "tech narrative","fintech indonesia","digital payment","loan channeling","sate madura"],
        invalidation_keywords=["tech_narrative_collapses","wifi_acquisition_cancelled","wirg_ri_fails",
            "government_edutech_cancelled","china_tech_crash","qris_growth_stalls"],
        beneficiaries={"ihsg":["WIFI.JK","WIRG.JK","MPIX.JK","ELIT.JK","DOOH.JK","INET.JK","EDGE.JK","ATIC.JK"],
            "global":["KWEB","MCHI","FXI"]},
        fades={"ihsg":["traditional_retail","low_digital_adoption","legacy_banks"],"us":["tech_growth_overvalued"]},
        regime_alignment={"Q1":1.30,"Q2":1.20,"Q3":1.10,"Q4":0.90},
        typical_duration_weeks=26,
        conviction_ceiling=0.75,
        pump_risk=0.40,
        confirmation_signals=["wifi_price_doubles","wirg_ri_announcement","mpix_revenue_growth_50pct",
            "hong_kong_tech_index_3y_high","china_fund_inflows_tech","government_smart_screen_contract",
            "elit_volume_spike_follows_wifi","qris_transaction_volume_surge"],
    ),

    # ── ARTICLE 8: Danantara Green Energy & TOBA EBT ──────────────────────────
    NarrativeTemplate(
        name="Danantara Green Energy — TOBA Waste-to-Energy & EBT Project Pipeline",
        description="""Ricky2212 Danantara/Prabowo green energy framework:
DANANTARA (08's sovereign wealth fund):
- Mandate: drive EBT (Energi Baru Terbarukan) / renewable energy projects
- Pandu Sjahrir (nephew of Luhut / "9 Haji" circle) = key figure in Danantara
- "9 Haji" = Luhut Binsar Pandjaitan, close to 08, assigned green energy portfolio
TOBA (Toba Bara Sejahtera):
- Recent acquisition: waste management company → waste-to-electricity
- Electricity offtakers: PLN + Singapore (market already secured)
- Project pipeline: potentially 10-30 EBT projects; 7-30T Rp value
- Comparable: OASA (Bobby Gafur Umar / Bakrie disciple) already executing 3 EBT projects @ 2T Rp
- Danantara Instagram: waste management players invited; Pandu Sjahrir attended (TOBA as Indonesia rep)
- "Kalo benar 10 project EBT masuk TOBA → 7-8T Rp; kalo 15 project → 15T Rp"
- Market cap TOBA ~3-4.5T = massive project-to-cap ratio
FINANCING SCENARIOS:
- Debt: bond issuance; Danantara could buy bonds as EBT support
- Equity: right issue most likely; price must be above current market → explains price spike
- "TOBA naik banyak buat mengejar harga Right issue nya"
NARRATIVE STACK:
- Konglo circle 08 (Hashim/Salim network)
- Corporate Action (RI imminent)
- Green/ESG narrative (Danantara EBT mandate)
- "Real fundamental belum bicara — project masih setup phase"
- "Selama CA masih gelap, harga bisa bergerak liar mencari FOMO"
Ricky position: "MAIN" = narrative + CA play; asymmetrical risk/reward; "siram bensin"
Warning: "Ada kandungan resiko melekat sejak kenaikan; pikirkan matang2x"
"Nanti ada dari konglo haji lagi yang kebagian project Green — kantornya sudah di set up."
Key data: TOBA = coal company pivoting to green = classic Indonesian transition narrative.""",
        category="corporate_action",
        catalyst_types=["danantara_ebt","waste_to_energy","green_project","right_issue","prabowo_green_policy",
            "konglo_08","corporate_action","narrative_play","renewable_energy"],
        activation_keywords=["danantara","toba","waste to energy","ebt","energi baru terbarukan","pandu sjahrir",
            "luhut","9 haji","08 green","prabowo renewable","toba right issue","toba project","toba acquisition",
            "pln offtake","singapore offtake","oasa ebt","bobby gafur umar","green energy indonesia",
            "sovereign wealth fund","danantara instagram","waste management","konglo 08","hashim green",
            "toba coal pivot","toba market cap","toba narrative","toba ca","toba fomo"],
        invalidation_keywords=["danantara_cancelled","toba_project_rejected","toba_ri_fails","green_policy_reversed",
            "pln_offtake_cancelled","prabowo_cabinet_no_green"],
        beneficiaries={"ihsg":["TOBA.JK","OASA.JK","WIFI.JK","WIRG.JK","ENRG.JK","MEDC.JK"],"global":["ICLN","PBW"]},
        fades={"ihsg":["pure_coal_no_pivot","traditional_utilities"],"us":["fossil_fuel_etfs"]},
        regime_alignment={"Q1":1.40,"Q2":1.30,"Q3":1.10,"Q4":0.90},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.30,
        confirmation_signals=["danantara_official_launch","toba_ri_announcement","toba_waste_project groundbreaking",
            "pandu_sjahrir_toba_meeting","pln_ppa_signed_toba","government_ebt_policy_2025",
            "toba_price_spike_volume","oasa_ebt_project_progress"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH11)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH11})
# for _n in _NARRATIVES_BATCH11:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
