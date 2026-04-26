"""config/narrative_universe.py — BATCH 9
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Psikologi Sabar (Winning Series Part 3)
2.  Tutup Apps OLT / Jauhi Keramaian (Winning Series Part 4)
3.  B-Indikator Part 2 — Bakrie+Salim synergy (BUMI/BRMS/ENRG/DEWA/BIPI/MEDC)
4.  B-Indikator Part 3 — BRMS gold/copper/nickel/silver + Salim/Bakrie/Agus Projo
5.  B-Indikator Part 4 — Kemasan cerita siap dijalankan (MIP, Green ESG, China stimulus, end-cycle)
6.  Logindo — Kisah barang yang tertinggal (OSV cycle, supply shortage, WINS/ELSA/BBRM/LEAD)
7.  Logindo — Menanti restrukturisasi hutang (OCP Fund, debt restructuring)
8.  Logindo — Logamnya Login Do-nk (restrukturisasi selesai, revaluasi asset, Eddy Logam repo)
9.  Logindo — Kapalnya berlayar ke utara (Q1 2024 profit, go regional, spot charter)
10. Key Takeaway Logindo management (Denny Heryanto interview, go regional, revaluasi, utilization 80%)
11. Key Takeaway Logindo part 2 (Denny Heryanto/CFO, BP Berau spot, revaluasi, debt covenant)
12. Logindo — Wangi Corp Action (DES scenario, OCP zero-coupon, distressed fund mechanics)
13. Logindo — DES diumumin (harga 186, PT Jalan Terang Samudera, Oakshire Capital)
14. Logindo — Restrukturisasi tiba + Jalan Terang DES (ringkasan restruk + LK Q2 DES)

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

_NARRATIVES_BATCH9: List[NarrativeTemplate] = [

    # ── ARTICLE 1+2: Winning Series — Patience & Noise Immunity ───────────────
    NarrativeTemplate(
        name="Retail Multibagger Psychology — Patience & Noise Immunity",
        description="""Ricky2212 Winning Series framework for retail investors:
PART 3 — PSIKOLOGI SABAR: patience is the ultimate determinant of return magnitude.
- "Percuma riset dalam + beli diskon + time frame tepat kalau ga sabar."
- Three failure modes of impatience:
  (a) Sell too early at 1-2 bagger when champion stock just beginning its cycle
  (b) Chase greener grass (rumput tetangga) → abandon super company before it runs
  (c) Day-to-day noise shakes conviction → sell on temporary bad news during transformation
- Case studies: BYAN (15x), TMAS (20x), ULTJ (slow then rally), BUMI (5x post-restrukturisasi)
PART 4 — TUTUP APPS OLT: OLT apps destroy patience via tick-by-tick stimulation → thumb presses SELL.
- "Apps OLT = sarana paling ampuh merusak psikologi sabar."
- Pre-OLT era (phone dealer) forced distance from market noise → higher holding period.
- Property investors calm because no OLT; stock investors should emulate.
- Recommendation: use WA/call to dealer for execution; check price only occasionally.
Key insight: multibagger = cheap entry + long time frame + patience + noise immunity.""",
        category="psychology",
        catalyst_types=["retail_psychology","patience_breakdown","noise_immunity","multibagger_framework","long_term_hold"],
        activation_keywords=["psikologi sabar","multibagger","winning series","tutup apps olt","jauhi keramaian",
            "rumput tetangga lebih hijau","cacing kepanasan","tombol hijau","sabar investasi","noise immunity",
            "holding period panjang","olt apps","investasi jangka panjang","super company","bagger"],
        invalidation_keywords=["short_term_trading","scalping","day_trading","noise_chasing","impatient_selling"],
        beneficiaries={"ihsg":["BYAN.JK","TMAS.JK","ULTJ.JK","BUMI.JK","long_term_champions"],"us":["BRK-B","long_term_quality"]},
        fades={"ihsg":["high_beta_momentum","penny_stock_churn","day_trading_favorites"],"us":["meme_stocks","high_turnover"]},
        regime_alignment={"Q1":1.00,"Q2":1.00,"Q3":1.00,"Q4":1.00},
        typical_duration_weeks=156,
        conviction_ceiling=0.95,
        pump_risk=0.05,
        confirmation_signals=["retail_turnover_spike","average_holding_period_drop","fomo_selling_early",
            "social_media_noise_spike","brokerage_app_downloads_surge"],
    ),

    # ── ARTICLE 3+4+5: B-Indikator — Bakrie-Salim Commodity Conglomerate Cycle ─
    NarrativeTemplate(
        name="B-Indikator — Bakrie-Salim Commodity Super Cycle & Exit Architecture",
        description="""Ricky2212 B-Indicator framework: Om Bakrie (B) = pedagang ulung siklus ke siklus.
B-Indicator tracks 3 core Bakrie commodity vehicles: ENRG (oil & gas), BRMS (mineral: gold/copper/nickel/silver), BUMI (thermal coal).
PART 2 — Bakrie+Salim synergy forming "pusaran kuat" in commodities:
- Salim entered BRMS via multiple right issues; Salim entered BUMI via mega right issue ~Rp 24T
- DEWA (Bakrie contractor) → Salim entered via RI, targeting gold mine in Aceh
- BIPI (Joesoef/Bakrie-linked contractor) → Salim rumored entry via debt swap or RI
- MEDC (Panigoro) → Salim entered via debt-equity swap; Amman Mineral IPO stand-by buyer = BUMI
- Circular flow: BUMI→MEDC (Newmont sale), BRMS→Amman (concentrate), Salim+Agus Projo orchestrating
PART 3 — BRMS as "Bakrie Rusuhun Mainan Salim":
- BRMS narratives: Gold (ATH momentum), Copper (AI hype), Nickel (supply), Silver (uncertainty)
- Amman Mineral ARA 20% in one day = proof of Salim narrative engineering power
- BRMS PER 372x, PBV 2.38x = pure narrative play, valuation skipped in bubble phase
- "Om S, Om B, Om Agus manfaatkan NARASI sempurna untuk ciptakan permainan"
PART 4 — End-cycle packaging:
- BUMI/BRMS preparing exit stories: Green ESG (kokas/smelter acquisition), MIP (domestic market obligation) >90% chance before regime change
- ADRO/INDY/BUMI/PTBA all moving on MIP + Green narrative simultaneously
- China stimulus = macro cover for commodity rally
- "BUMI dari nothing jadi raksasa" → free debt post mega RI → unprecedented clean balance sheet
- Historical: Bakrie exit pattern = sell at peak cycle via placement/block sale (Nat Rothschild, Tata precedent)
- Warning: "Pulang sebelum pesta bubar" — when konglo exit, retail must not be left holding bag
Key signal: simultaneous Green + MIP + China stimulus + volume spike 5x = distribution phase loading.""",
        category="cycle",
        catalyst_types=["b_indicator","bakrie_salim_synergy","commodity_cycle_peak","mega_right_issue",
            "green_esg_narrative","mip_policy","china_stimulus_commodity","placement_exit","narrative_engineering"],
        activation_keywords=["b indicator","bakrie salim","om bakrie","om salim","om agus","brms","bumi resources",
            "enrg","dewa","bipi","medc","amman mineral","commodity cycle","pusaran kuat","mainan salim",
            "green energy","mip","domestic market obligation","thermal coal","kokas","smelter","placement",
            "right issue jumbo","exit strategy bakrie","narrasi emas","narrasi copper","narrasi nickel",
            "china stimulus komoditas","volume spike 5x","adro pattern","indy bumi ptba"],
        invalidation_keywords=["commodity_cycle_end","bakrie_exit_completed","mip_cancelled","china_stimulus_fails",
            "green_narrative_collapses","salim_sells_out"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","ENRG.JK","DEWA.JK","BIPI.JK","MEDC.JK","ADRO.JK","INDY.JK","PTBA.JK","ANTM.JK","TINS.JK"],
            "commodities":["GC=F","HG=F","CL=F","iron_ore"],"global":["FXI","MCHI"]},
        fades={"ihsg":["consumer_goods","property","high_flying_tech"],"us":["tech_growth","low_volatility"]},
        regime_alignment={"Q1":1.60,"Q2":1.50,"Q3":1.20,"Q4":0.90},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.30,
        confirmation_signals=["brms_volume_5x_avg","bumi_volume_5x_avg","mip_policy_draft_leak",
            "green_esg_announcement_bumi","china_stimulus_commodity_rally","salim_placement_brms",
            "amman_mineral_ara_20pct","adro_green_spin_off"],
    ),

    # ── ARTICLE 6+9+10+11: Indonesia OSV Offshore Vessel Supercycle ────────────
    NarrativeTemplate(
        name="Indonesia OSV Supercycle — Supply Shortage & Regional Rate Spike",
        description="""Ricky2212 OSV (Offshore Support Vessel) sector thesis:
Supply shortage: no new OSV building orders until 2026, existing fleet aging (avg 17.8 years low-tier).
Demand surge: offshore oil & gas blocks Geng North-1 (ENI) and Layaran-1 (Mubadala) = 5 largest reserves globally, requiring massive OSV mobilization.
Rate explosion: daily charter rate high-tier AHTS/PSV now USD 1.50-2.00 per HP (vs depressed local rates previously).
Key players: WINS (PSV-focused, go regional first → jawara), ELSA (diversified, solid), BBRM (small cap turnaround), LEAD/Logindo (AHTS-heavy, lagging but catching up).
Management guidance (Denny Heryanto/CFO Logindo):
- Utilization Q1 2024: ~80% and rising
- Revenue mix: 45% from outside Indonesia (regional spot charter)
- New customers: BP Berau (spot), Premier, Saka, Medco E&P Natuna (contract extended)
- Rates for overseas customers up to $2/HP
- Reversal of impairment possible if market trend continues; routine revaluation per PSAK 16
- Target: financial covenant net debt/EBITDA <2.4x by March 2025 via higher rates + utilization + cost control
Sector mechanics: when WINS/BBRM go regional → local supply tightens → LEAD fills local gap at higher rates → all boats rise.
Historical parallel: 2014-2015 cycle. WINS peaked 2013, Logindo peaked 2014 (lagging pattern repeating).
"Logindo kisah barang yang tertinggal" — laggard play within supercycle.""",
        category="sector",
        catalyst_types=["osv_shortage","offshore_rate_spike","regional_mobilization","new_oil_block","utilization_surge",
            "ahts_demand","psv_demand","supply_constraint"],
        activation_keywords=["osv shortage","offshore vessel","ahts","psv","daily charter rate","hulu migas",
            "supply shortage kapal","go regional","geng north-1","layaran-1","utilization 80","bp berau",
            "medco natuna","spot charter","wins","elsa","bbrm","logindo","lead","offshore supporting vessel",
            "new building order kosong","kapal osv","tarif sewa kapal","oil block eni","mubadala energy"],
        invalidation_keywords=["osv_orderbook_surge","oil_price_crash_below_60","offshore_project_cancelled",
            "regional_rate_collapse","new_building_orders_return"],
        beneficiaries={"ihsg":["WINS.JK","ELSA.JK","LEAD.JK","BBRM.JK","RIGS.JK","SSMS.JK"],"global":["TDW","CLB","OII"]},
        fades={"ihsg":["land_drilling","onshore_oil_services","coal_contractors"]},
        regime_alignment={"Q1":1.40,"Q2":1.40,"Q3":1.20,"Q4":1.00},
        typical_duration_weeks=78,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["wins_utilization_above_85","lead_utilization_80pct_confirmed","daily_charter_rate_above_1_50",
            "bp_berau_spot_contract","medco_natuna_extension","geng_north_1_drilling_start","osv_orderbook_stays_zero",
            "regional_dayrate_spike_2usd"],
    ),

    # ── ARTICLE 7+8+12+13+14: Logindo Distressed Turnaround & DES ─────────────
    NarrativeTemplate(
        name="Logindo (LEAD) Distressed Deleveraging — Debt-to-Equity Swap Turnaround",
        description="""Ricky2212 Logindo corporate restructuring & financial engineering deep-dive:
PHASE 1 — RESTRUCTURING (Apr 2024):
- Original debt: UOB + DBS ~Rp 1.2T, maturity Jun 2024
- OCP Asia Fund IV & V (distressed fund) bought debt from UOB/DBS and refinanced:
  * Facility A: ~$45M @ 12% cash + 3% PIK, quarterly from Jul 2025
  * Facility B: ~$10M zero-coupon (bullet)
  * Facility C: ~$39M zero-coupon (bullet)
  * Tenor: 48 months
- Zero-coupon facility = classic distressed fund setup for future Debt-to-Equity Swap (DES)
PHASE 2 — REKOGNISI TURNAROUND (Q1-Q2 2024):
- Q1 2024: first positive net profit (Rp 792M) since downturn, EBITDA highest since 2016
- Revenue +53% YoY, go regional confirmed, spot charter with BP Berau/Premier/Saka
- Eddy Kurniawan Logam repurchased 7% shares from HPAM repo (insider signal)
- LK Q2 audited = prerequisite for corporate action
PHASE 3 — DES EXECUTION (Sep-Nov 2024):
- LK Q2 disclosed: "opsi membayar sebagian pinjaman via penerbitan saham baru atau mengubah hutang jadi ekuitas"
- OCP transferred $15M rights to Oakshire Capital → PT Jalan Terang Samudera (Logam family nominee suspected)
- RUPSLB announced Oct 2024, execution Nov 14 2024
- DES price: Rp 186 (premium to market at announcement)
- Amount swapped: USD 20M total = PT JTS $15M + OCP $5M
- Post-DES share structure (approx): OCP ~27%, Alstonia/PacRad ~24%, Logam family ~26% (if JTS is Logam nominee)
- "OCP bukan Sinterklas — mereka mau yield besar. Karpet merah untuk exit strategy harus disiapkan."
PHASE 4 — WHAT COMES NEXT:
- Further revaluation of vessel assets (impairment reversal) = one-time gain + equity boost + dividend eligibility (retained earnings must be positive)
- Covenant relief: net debt/EBITDA target <2.4x by Mar 2025
- Potential final exit narrative engineered by IB for OCP
- "Logindo rating C → B+ post-restruk → A if DES + revaluasi complete"
Risk: distressed fund timeline pressure; OCP will demand exit path.""",
        category="corporate_action",
        catalyst_types=["debt_restructuring","distressed_fund_entry","debt_to_equity_swap","zero_coupon_conversion",
            "asset_revaluation","insider_repo","rupslb","deleveraging","financial_engineering"],
        activation_keywords=["logindo restrukturisasi","logindo debt equity swap","lead des","ocp fund","ocp asia",
            "distressed fund","zero coupon","debt to equity","rupslb","jalan terang samudera","oakshire capital",
            "revaluasi asset logindo","impairment reversal","eddy logam","pacific radiance","alstonia","logindo login",
            "deleveraging logindo","harga 186","pt jts","facility b","facility c","logindo turnaround",
            "logindo q1 profit","logindo audited","logindo covenant"],
        invalidation_keywords=["des_cancelled","rupslb_fails_quorum","ocp_demand_liquidation","revaluation_blocked",
            "regulator_rejects_des","logindo_bankruptcy"],
        beneficiaries={"ihsg":["LEAD.JK"],"distressed":["LEAD.JK"],"turnaround":["LEAD.JK"]},
        fades={"ihsg":["WINS.JK","ELSA.JK"],"us":["high_leverage_sector"]},
        regime_alignment={"Q1":1.20,"Q2":1.20,"Q3":1.00,"Q4":0.80},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.25,
        confirmation_signals=["des_price_186_confirmed","rupslb_quorum_75pct","ocp_fund_transfer_oakshire_jts",
            "logindo_q1_positive_profit","logindo_lk_audited_q2","eddy_logam_share_repo_7pct",
            "revaluation_asset_announcement","net_debt_ebitda_below_2_4"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH9)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH9})
# for _n in _NARRATIVES_BATCH9:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
