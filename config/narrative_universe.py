"""config/narrative_universe.py — BATCH 8
Artikel baru Ricky2212 (Apr 2026 extraction):
1. 2nd Unwinding of Carry Trade
2. Fed CUT 50bps / Pergantian Musim / Terminal Rate
3. Perubahan Pola Berita di Market
4. All about China: Bad → Illusion → Worst → Bazooka
5. Konglo Exit Strategy (Salim, PP, Tohir, PANI, AMMN, BUMI, BRMS)

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

_NARRATIVES_BATCH8: List[NarrativeTemplate] = [

    # ── ARTICLE 1: 2nd Unwinding of Carry Trade ─────────────────────────────
    NarrativeTemplate(
        name="JPY Carry Trade 2nd Unwinding — Deleveraging Storm",
        description="""Ricky2212 carry trade framework: JPY borrowed at 0.5-0.75% → deployed to USD T-Bills 5.5% or risk assets.
Unwinding = mass liquidation of risk assets → buy JPY → repay leverage.
1st unwinding = BoJ hike + US unemployment spike. 2nd unwinding = deeper Fed CUT + BoJ further hike → spread collapses from 4.75% to ~2%.
"Spread too small + global recession risk = carry trade no longer worth it."
Historical: carry crashes involved in every major banking crisis last 200 years (GFC 2007-08 confirmed by BIS).
Pattern: slowly then suddenly unemployment worsens → panic JPY repatriation.
$20T+ estimated leveraged carry trade exposure per BoJ balance sheet proxy.
Trigger: BoJ Oct meeting hawkish + Fed terminal rate 2.5-3% = spread compression + risk-off.
"Kalau skenario CUT FFR sampai 2-2.5%, tinggal berapa spreadnya? Makin ga menarik."
Deleveraging will cascade: JPY spike → risk asset dump → margin call → forced selling.""",
        category="cycle",
        catalyst_types=["boj_rate_hike","fed_deep_cut","unemployment_spike","risk_off_cascade","spread_compression"],
        activation_keywords=["carry trade unwinding","jpy spike","yen carry trade","boj hike","unwinding jilid 2",
            "jpy strengthen","deleveraging storm","spread compression","jpy repatriation","yen short squeeze",
            "carry trade collapse","boj october meeting","jpy 150","jpy 140","leverage unwind"],
        invalidation_keywords=["boj dovish pivot","fed halt cut","spread widens","jpy weakens","risk_on_return"],
        beneficiaries={"fx":["JPY=X","USDJPY=X"],"safe_haven":["GLD","TLT","BIL"],"us":["UUP"]},
        fades={"us":["SPY","QQQ","IWM","EEM"],"ihsg":["EIDO"],"crypto":["BTC-USD"]," leveraged":["margin_positions"]},
        regime_alignment={"Q3":1.80,"Q4":1.60,"Q2":1.20,"Q1":0.40},
        typical_duration_weeks=8,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["jpy_strengthen_3pct_week","usdjpy_below_140","vix_spike_above_30",
            "risk_asset_dump_post_boj","fed_swap_pricing_4plus_cuts","unemployment_above_4_5pct"],
    ),

    # ── ARTICLE 2: Fed CUT 50bps / Terminal Rate / Hard Landing ───────────────
    NarrativeTemplate(
        name="Fed Deep CUT Cycle — Terminal Rate 2.5-3% Hard Landing",
        description="""Ricky2212: "Pergantian musim kemarau likuiditas" = Fed CUT 50bps.
Terminal rate estimation from UST:
- UST 2Y 3.62% − 50-75bps premium = 2.87-3.12%
- UST 10Y 3.71% − 100-125bps premium = 2.46-2.71%
→ Terminal rate ~2.5-3% (IF inflation 2% and economy doesn't collapse further).
"Hard landing more likely — sejarah pengetatan moneter selalu diakhiri hard landing."
Powell: "Time is come for CUT" but still denies recession. Pattern: slowly then suddenly data revised down.
Market reaction: initial cheer → concern ("why 50bps? economy that bad?") → normalized phase.
Timeline: maintained until US Election Nov 2024, possibly extend to inauguration.
Watch BoJ Oct meeting as potential disruptor.
Blow-off-top still running. Final phase = oil + crypto dragged up.
Key point: don't focus on 25 vs 50bps start — focus on TOTAL DOSE (terminal rate).
Deeper CUT = economy sicker than admitted.""",
        category="policy",
        catalyst_types=["fed_50bps_cut","terminal_rate_migration","nfp_shock","ust_free_fall","hard_landing_signal"],
        activation_keywords=["fed cut 50 bps","terminal rate","deep cut","hard landing fed","pergantian musim",
            "ust 2y below 4","ust free fall","powell time is come","cut cycle","jumbo cut","fed front load",
            "terminal rate 2.5","terminal rate 3%","fomc 50bps","deeper cut","blow off top final"],
        invalidation_keywords=["fed pause cut","soft landing confirmed","nfp strong","terminal rate above 4",
            "inflation reaccelerates"],
        beneficiaries={"us":["TLT","IEF","GLD","IWM","EEM","SPY"],"ihsg":["BBCA.JK","CTRA.JK","BEST.JK","BTPS.JK"],
            "commodities":["GC=F","HG=F"]},
        fades={"us":["UUP","BIL","money_market_funds"]},
        regime_alignment={"Q4":1.90,"Q1":1.70,"Q3":1.20,"Q2":0.70},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.10,
        confirmation_signals=["fed_cut_50bps_confirmed","ust2y_below_4pct","unemployment_above_4pct",
            "nfp_revised_down_12months","terminal_rate_priced_3pct","tlt_breakout_sustained"],
    ),

    # ── ARTICLE 3: Perubahan Pola Berita ──────────────────────────────────────
    NarrativeTemplate(
        name="News Pattern Shift — Bad News is Bad News Post-Pivot",
        description="""Ricky2212 market psychology framework: news pattern has SHIFTED.
OLD PATTERN (Hawkish era): Bad News is Good News → bad data = mission accomplished for CB = HALT/CUT coming = equity rally.
NEW PATTERN (Post-pivot / CUT era): Bad News is Bad News → bad data = economy truly suffering = recession/depression fear = bond rally (flight to safety) but equity confused/tanking.
GOOD NEWS is GOOD NEWS → good data (retail sales beat) = no recession = equity rallies even if bond yields spike.
Mechanism: when CUT is already priced/expected, bad news no longer signals "end of tightening" — it signals "economic damage."
"Market melihat realnya. Bad news is bad news."
Bond market: bad news → massive bond buying (yields collapse) = risk-off confirmation.
Equity market: bad news → confusion/sell-off ("jangan-jangan resesi").
Data to watch: NFP, unemployment, CPI, GDP, retail sales.
Valid until ultimate CUT / normalized phase completes.""",
        category="cycle",
        catalyst_types=["news_pattern_shift","data_dependency","market_psychology_flip","bond_equity_divergence"],
        activation_keywords=["bad news is bad news","good news is good news","news pattern shift",
            "retail sales beat","bond yield spike equity rally","bad news equity sell off",
            "market psychology change","post pivot pattern","data buruk saham turun",
            "data bagus saham naik","pattern berita berubah"],
        invalidation_keywords=["bad news is good news returns","market ignores fundamentals","soft landing no fear"],
        beneficiaries={"us":["QUAL","SPY","QQQ"],"ihsg":["BBCA.JK","BBRI.JK","KLBF.JK"]},
        fades={"us":["IWM","XLY","high_beta_momentum"],"ihsg":["BREN.JK","high_flyer"]},
        regime_alignment={"Q3":1.20,"Q4":1.10,"Q2":0.90,"Q1":0.80},
        typical_duration_weeks=26,
        conviction_ceiling=0.75,
        pump_risk=0.10,
        confirmation_signals=["retail_sales_beat_equity_rally_yield_spike","nfp_miss_equity_drops_yield_collapse",
            "bad_news_bond_rally_equity_sell","good_news_both_rally"],
    ),

    # ── ARTICLE 4: All about China — Bad → Illusion → Worst → Bazooka ─────────
    NarrativeTemplate(
        name="China Structural Crisis → Mega Bazooka QE Pipeline",
        description="""Ricky2212 China framework: Bad → Illusion → Worst → Bazooka.
CURRENT STATE (Bad/Worst):
- Property index -83%, 40 banks closed, nickel smelter Chapter 11
- Deflation longest since 1999 (5 consecutive quarters worse than 2008)
- Unemployment worst in a decade
- Bank credit contraction worst in 2 decades
- Capital flight $15B in Q2 alone
- Steel giant Baowu warning of industrial turmoil
- Copper & iron ore dragged down
ILLUSION (Current stimulus):
- PBOC RRR cut 50bps, mortgage rate cut 50bps, DP 25%→15%
- £50B stock market support, buyback push
- Market rallied 10%+ on stimulus = ILLUSI
- "Bond market China belum berkata begitu" — China 2Y 1.38% vs official 3% = deeper CUT demanded
BAZOOKA (Coming):
- China has options: debt in own currency, can QE without hyperinflation risk (yuan not global reserve)
- Timing: waits for Fed easing massive (FFR ~2%) to avoid competitive devaluation cost
- Estimated need: $1T minimum (5% GDP) to fix economy
- Rumor: $1.4T fiscal stimulus pipeline
- China building domestic supply capacity to absorb bazooka internally
- "China akan jadi juara nantinya" — Indonesia commodities (coal, nickel, CPO) will surge on China bazooka
Investment angle: watch FXI, MCHI, commodities, IHSG resource plays for entry when bazooka confirmed.""",
        category="geopolitical",
        catalyst_types=["china_property_crisis","pboc_rrr_cut","china_fiscal_stimulus","china_qe_bazooka",
            "china_deflation","capital_flight_china","fed_easing_china_trigger"],
        activation_keywords=["china bazooka","china stimulus","china property crisis","china deflation",
            "pboc rrr cut","china illusion","china bad to worst","china mega stimulus",
            "china fiscal stimulus 1 trillion","china qe","baowu steel warning","china bank closed",
            "china capital flight","china unemployment worst","china deeper cut","china jack up before storm"],
        invalidation_keywords=["china hard landing avoided","china property recovers","pboc stops easing",
            "china exports surge_without_stimulus"],
        beneficiaries={"global":["FXI","MCHI","EEM","VWO","DBC"],"commodities":["HG=F","CL=F","iron_ore"],
            "ihsg":["ITMG.JK","ADRO.JK","INCO.JK","MDKA.JK","ANTM.JK","PSSI.JK","TAPG.JK","DSNG.JK"]},
        fades={"global":["ASHR"],"ihsg":["BWPT.JK","SIMP.JK"]},
        regime_alignment={"Q1":1.60,"Q2":1.40,"Q4":0.80,"Q3":0.60},
        typical_duration_weeks=104,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["china_fiscal_stimulus_1t_announcement","pboc_rrr_cut_100bps","china_property_sales_stabilize",
            "china_2y_yield_below_1pct","bdi_above_2000_china_driven","copper_above_4_50_china"],
    ),

    # ── ARTICLE 5: Konglo Exit Strategy ─────────────────────────────────────────
    NarrativeTemplate(
        name="Indonesia Konglo Exit Wave — Smart Money Distribution Signal",
        description="""Ricky2212 institutional smart-money contrarian signal: konglomerat EXIT en masse.
OBSERVED EXITS:
- PP: hitungan waktu EXIT (placement/block sale)
- Tohir: already EXIT-ing, repeating 2008 peak-cycle playbook
- Salim: EXIT from AMMN, next PANI via placement ("moment sudah lepas landas, lebih beresiko ketemu ujungnya")
- Salim+Bakrie partnership in BUMI/BRMS = if they EXIT there = strongest signal of cycle peak
PATTERN: "Exit saat keramaian datang dan euphoria di market. Bukan saat market down."
"Perfect Exit Strategy" = sell into retail euphoria, use placement/block sale to avoid market impact.
WHY: mereka mencium bau ga enak dari keadaan ekonomi dunia. "Pulang lebih cepat adalah pilihan terbaik."
SIGNAL INTERPRETATION:
- Konglo exit + retail euphoria = DISTRIBUTION PHASE
- When multiple konglo exit simultaneously = cycle peak warning
- "Fenomena exit para konglomerasi dilakukan dalam waktu berdekatan"
CONTRARIAN PLAY: when konglo exit = prepare for storm. Raise cash, add gold, defensive positioning.
IHSG: avoid high-beta konglo-driven names at peak. Wait for re-entry post-correction.""",
        category="cycle",
        catalyst_types=["konglo_exit","block_sale","placement","smart_money_distribution","euphoria_peak"],
        activation_keywords=["konglo exit","salim exit","pp exit","tohir exit","pani placement",
            "ammn block sale","bumi brms exit","smart money exit indonesia","konglomerat jual saham",
            "placement indonesia","exit strategy konglo","euphoria distribution","retail euphoria institutional exit",
            "bau ga enak ekonomi","pulang lebih cepat","perfect exit strategy"],
        invalidation_keywords=["konglo buyback","salim accumulation","tohir entry","placement cancelled",
            "fundamental supports euphoria"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","KLBF.JK","GLD"],"us":["GLD","TLT"],"cash":["IDR_cash","USD_cash"]},
        fades={"ihsg":["PANI.JK","AMM.JK","BREN.JK","high_beta_konglo"],"us":["IWM","high_beta"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":0.80,"Q1":0.50},
        typical_duration_weeks=13,
        conviction_ceiling=0.85,
        pump_risk=0.20,
        confirmation_signals=["salim_pani_placement_announcement","pp_block_sale","tohir_2008_pattern_repeat",
            "multiple_konglo_exits_same_quarter","ihsg_retail_participation_peak","foreign_net_sell_ihsg"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH8)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH8})
# for _n in _NARRATIVES_BATCH8:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
