"""config/narrative_universe.py — BATCH 13
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Main Stages in a Bubble — bubble lifecycle framework (smart money → fear)
2.  Indonesia economic deep trouble — PMI 49.6, consumer down-trading, PPN 12%
3.  Canada, Swiss and China Warning — global synchronized easing panic
4.  Fed final cut in 2024 / Fed 1st meeting 2025 — dot plot, Trump disinflation
5.  Fenomena Back door listing — shell company criteria, PANI/KARW/LABA/FUTR/PACK
6.  Kilas Balik 2024 — personal journey, siram bensin plays, crypto, junior miner
7.  Preserve and Protect Capital 2025 — 40:60 equity:cash, global macro pessimism
8.  US DEBT COLLAPSE — $7T rollover, QE→debt→deleveraging, L/W shape
9.  Derrreesss Bro / Last Signal — optimism returning, 5 bull reasons, 4 peak signals, Big Boyz reverse psychology

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

_NARRATIVES_BATCH13: List[NarrativeTemplate] = [

    # ── ARTICLE 1: Bubble Lifecycle Framework ─────────────────────────────────
    NarrativeTemplate(
        name="Bubble Lifecycle — Current Phase: Greed→Delusional→New Paradigm",
        description="""Ricky2212 bubble stage framework (Elon Musk socmed meme adapted):
STAGE 1 — SMART MONEY (2020-2022): CB bazooka stimulus → cheap money → asset bubble creation. Indices immune to bad news (COVID, war). "Even monkey can win." 2020-2022 pre-inflation = take-off.
STAGE 2 — FIRST SELL OFF & BEAR TRAP (Sep-Oct 2022): Inflation explodes (US 9%), CB hikes fast & steep. Market sells off ~23%. Recession fears. Bear trap forms.
STAGE 3 — MEDIA ATTENTION (Oct 2022-Sep 2023): Despite hikes, market comes back. "Heran: dicekek habis-habisan tapi indeks rally." Headlines everywhere. Fed pauses hikes.
STAGE 4 — ENTHUSIASM (Sep 2023-Q2 2024): Powell signals 2024 CUTs. Market calculates timing/magnitude. ATH after ATH. "Wuzz, market buru-buru ngacir." NVIDIA, Palantir, SOFi, PP stocks surge.
STAGE 5 — GREED (Q3 2024-now): First CUT 50bps. Trump victory. BTC $100k. Households pour savings into stocks. "Do or Die, CNI (Cacing Naga Investing)." Indices ATH while economy sempoyongan. "Jack Up Before Storm" thesis born here.
STAGE 6 — DELUSIONAL (coming): CUT #3, Trump inauguration. Market ATH→ATH. Hope after hope, expectation after expectation. IWM (70% constituents unprofitable) hits ATH. BTC narratives become absurd. "This Time is Different" echoes. Buffett mocked by retail. No logic remains.
STAGE 7 — NEW PARADIGM (coming): "AI economy, tech economy, low-cost economy" = new theories deviating from proven economics. Retail happiest. Narrative justifies absurd valuations.
STAGE 8 — DENIAL (coming): Slow bleed begins. "Slowly then suddenly." Big Boyz media: "just normal correction, economy still good." CB: "under control, on track." Retail calmed by lullabies.
STAGE 9 — BULL TRAP & RETURN TO NORMAL: Dead cat bounce. Justification: "economy adjusting, rates helping." CB still supportive. "All returning to normal."
STAGE 10 — FEAR: Suddenly all bad news erupts. "Tiada hari tanpa berita buruk." Rationality returns. VIX spikes. Bonds rally (flight to safety). Ultimate CUT demanded.
Key insight: "Prepare not Predict." We are currently in GREED transitioning to DELUSIONAL.""",
        category="cycle",
        catalyst_types=["bubble_stage","smart_money","bear_trap","media_attention","enthusiasm","greed",
            "delusional","new_paradigm","denial","bull_trap","fear","slowly_then_suddenly"],
        activation_keywords=["bubble stage","smart money","bear trap","media attention","enthusiasm","greed",
            "delusional","new paradigm","denial","bull trap","fear","slowly then suddenly",
            "main stages bubble","even monkey can win","jack up before storm","cacing naga investing",
            "cni","this time is different","buffett mocked","iwm ath unprofitable","btc 100k narrative",
            "prepare not predict","bubble lifecycle","current phase bubble","where are we now bubble"],
        invalidation_keywords=["bubble_cancelled","soft_landing_no_bubble","fundamentals_return",
            "no_delusional_phase","early_fear_phase"],
        beneficiaries={"us":["SQQQ","VIX","TLT","GLD"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK"],
            "safe_haven":["USD_cash","IDR_cash","money_market"]},
        fades={"us":["IWM","QQQ","NVDA","PLTR","SOFI","high_beta_momentum","meme_stocks"],
            "ihsg":["BUMI.JK","BRMS.JK","BREN.JK","high_flyer","narrative_play"],"crypto":["BTC-USD","ETH-USD"]},
        regime_alignment={"Q3":1.90,"Q4":1.80,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=78,
        conviction_ceiling=0.90,
        pump_risk=0.10,
        confirmation_signals=["iwm_ath_with_unprofitable_constituents","btc_above_100k_sustained",
            "nvda_ath_without_earnings_growth","retail_household_allocation_record","vix_below_15",
            "buffett_cash_record_high","delusional_narratives_mainstream","new_paradigm_theories"],
    ),

    # ── ARTICLE 2+3+4+9: Global Synchronized Easing Panic & Macro Warning ─────────
    NarrativeTemplate(
        name="Global Synchronized Easing Panic — CBs Cutting into Weakness",
        description="""Ricky2212 global macro warning framework: "Prepare not Predict."
CANADA: BoC cut 50bps to 3.25% (5th consecutive cut). GDP growth 1% vs 1.5% target. Unemployment ticking up. "Sound panic?"
SWISS: SNB jumbo 50bps cut to 0.5%. Inflation 0.7%, forecast 2025: 0.2%. Negative rates possible in 2025. "Negative rates = only during economic destruction."
CHINA: 10T yuan ($1.4T) local debt swap over 5 years = NOT fresh money stimulus. Hidden debt 14.3T→2.3T by 2028. No new workflow created. China futures -5% post-announcement. Bond yield 10Y at lowest since GFC 2008. Property still crashing. Deflation persistent. "Still challenging and full of uncertainty."
EUROZONE: ECB 4th cut 2024. Germany deindustrializing. Auto factories closing. Bundesbank guidance: contraction ahead. Italy, France, Greece, Spain all weak.
BRAZIL: Chaos, riots, stomach-empty populace.
FED DEC 2024: Cut 25bps to 4.25-4.5%. Dot plot: only 2 cuts in 2025 (halved from Sep). Neutral rate 3%. GDP 2024 revised up to 2.5% but long-term 1.8%. Core inflation 2.4-2.8% (above 2% target). Trump tariffs/deportation = inflationary risk per Powell.
FED JAN 2025: Hold at 4.25-4.5%. Unanimous. Removed "progress" language on inflation. "Inflation remains somewhat elevated." Flexibility for March 17-18 meeting.
TRUMP EXPORTING DISINFLATION:
- Mass deportation = cheap labor gone → NFP data manipulation ends → NFP turns bad
- Federal worker cuts = less spending → economic weakness
- Cheap energy (Drill Baby Drill) = energy cost down → disinflationary
- Tariffs = cost-push but no demand = prices must fall → disinflationary
- DeepSeek = AI cost 1/20 → disinflationary
- "Trump is exporting disinflation, not inflation"
Ricky stance: "Weak USD? Big chance. Already slowly building long FX positions."
Key signal: When all CBs cutting simultaneously while economies weak = synchronized global downturn.""",
        category="policy",
        catalyst_types=["global_synchronized_easing","boc_cut","snb_cut","ecb_cut","china_stimulus_fake",
            "fed_dot_plot_hawkish","trump_disinflation","deportation_economic_impact","negative_rates_warning"],
        activation_keywords=["global synchronized easing","boc 50bps","snb 50bps","snb negative rates",
            "china 10 trillion","china debt swap","china bond yield lowest since 2008","ecb 4th cut",
            "fed dot plot 2025","fed 2 cuts 2025","trump exporting disinflation","trump deportation",
            "trump cheap energy","drill baby drill","deepseek disinflation","fed hold january 2025",
            "inflation somewhat elevated","canada panic cut","swiss deflation","china deflation",
            "germany deindustrialization","bundesbank contraction","brazil riots","weak usd",
            "prepare not predict","cb cutting into weakness"],
        invalidation_keywords=["global_growth_rebounds","china_fresh_money_1t","fed_4_cuts_2025",
            "trump_inflation_confirmed","snb_positive_rates"],
        beneficiaries={"us":["TLT","IEF","GLD","UUP"],"global":["EEM","VWO","FXI"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"],
            "fx":["USDJPY","DXY","EURUSD"]},
        fades={"us":["IWM","high_beta","small_cap"],"ihsg":["high_flyer","property","consumer_discretionary"],
            "europe":["auto_sector","industrial_germany"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q3":1.20,"Q2":0.80},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.10,
        confirmation_signals=["boc_5th_consecutive_cut","snb_inflation_0_2_forecast","china_10y_below_1pct",
            "ecb_4th_cut_confirmed","fed_dot_plot_2_cuts","trump_deportation_executed","deepseek_ai_cost_crash",
            "german_auto_factory_closures","brazil_riot_spread"],
    ),

    # ── ARTICLE 2: Indonesia Domestic Economic Trouble ──────────────────────────
    NarrativeTemplate(
        name="Indonesia Domestic Collapse — PMI Contraction & Consumer Down-Trading",
        description="""Ricky2212 Indonesia on-the-ground economic reality check:
PMI: 49.6 (5th consecutive month below 50). Last time 5 months below 50 = COVID 2020.
Ricky's assessment: "Kondisi sekarang bahkan jauh lebih buruk dari pandemic."
ON-THE-GROUND EVIDENCE:
1. Business revenue down vs COVID era (even in upper-class housing areas). Margin 40%→20%. Customers asking for tempo/credit.
2. Cigarette down-trading: consumers switching to cheaper brands. "Rokok aja down trading."
3. Ojol food orders dropping. People cooking at home to save money.
4. Indomaret/Alfamart/Naga/Tip Top = primary shopping destinations (cheap). Traditional markets emptying.
5. Used car showrooms closing (Pondok Bambu, Buaran, Jatinegara, Bekasi Kranji). "Orang ga mikirin beli mobil dulu. Sekarang mah pikirin bertahan dulu."
POLICY FAILURES:
- "Dimakan diatas, Dibejek dibawah" — policies not pro-growth
- PPN 11%→12% (Jan 1, 2025) = multiplier effect drain on consumer spending
- BI trapped: cut rates to help economy OR defend IDR? IDR at 15,100+ vs USD
- Trump pressure on IDR
BANKING SECTOR:
- BBRI, BTPS most sempoyongan. CKPN still flowing.
- BBNI, BMRI will follow with CKPN increases.
- BBCA best positioned but will also face CKPN pressure.
- "Pergerakan saham perbankan tidak akan pernah bohong."
TIMELINE: "In line with global, especially US. Now bad, but worst hasn't arrived yet."
"Deep Trouble Ahead? Merinding lah. Stay away from big bank dulu, nanti aja buat next cycle."
"JACK UP is for EXIT."""",
        category="geopolitical",
        catalyst_types=["pmi_contraction","consumer_down_trading","ppn_increase","idr_weakness",
            "ckpn_cycle","bi_rate_dilemma","traditional_market_collapse","retail_shift_discounter"],
        activation_keywords=["indonesia pmi","pmi 49.6","indonesia economic trouble","consumer down trading",
            "ppn 12%","ppn naik","idr 15100","bi rate dilemma","ckpn bank","bbri ckpn","btps ckpn",
            "bbni ckpn","bmri ckpn","traditional market sepi","indomaret naga tiptop","ojol order drop",
            "cigarette down trading","showroom mobil tutup","margin bisnis turun","tempo payment",
            "indonesia deep trouble","dimakan diatas dibejek dibawah","kebijakan tidak pro growth",
            "jack up is for exit indonesia","stay away big bank"],
        invalidation_keywords=["pmi_above_50","consumer_spending_surge","ppn_cancelled","idr_strengthens",
            "ckpn_cycle_ends","bi_cuts_rates"],
        beneficiaries={"ihsg":["BBCA.JK","BMRI.JK","KLBF.JK","UNVR.JK","TLKM.JK"],"us":["EIDO"],
            "safe_haven":["IDR_cash","USD_cash","money_market"]},
        fades={"ihsg":["BBRI.JK","BTPS.JK","property","consumer_discretionary","auto_sector","high_beta"]},
        regime_alignment={"Q3":1.30,"Q4":1.10,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["pmi_5months_below_50","ppn_12%_implemented","idr_above_15500",
            "ckpn_spike_banking_sector","traditional_market_revenue_drop","ojol_order_volume_drop",
            "cigarette_volume_shift_cheap","used_car_showroom_closures"],
    ),

    # ── ARTICLE 8: US Debt Collapse & De-leveraging ───────────────────────────
    NarrativeTemplate(
        name="US Debt Collapse — $7T Rollover & Global De-leveraging Cycle",
        description="""Ricky2212 debt crisis framework: "The Storm is Coming."
THE NUMBERS:
- US debt: ~$37T (nearly doubled in 7 years)
- 2025 rollover: $7T debt maturing = tipping point
- Annual interest: ~$1T
- Deficit spending continues
- Debt-to-GDP surpassing WWII levels
QE = THE DEVIL'S CANDY:
- "Setan QE = candu narkotik." Easy now, destruction later.
- 2008 GFC: QE launched to save economy
- 2020 COVID: $4-5T bazooka (Fed alone)
- Pattern: more QE → more debt → more interest → uncontrollable inflation
- "Bom waktu yang mereka siapkan untuk mereka sendiri"
THE TRAP:
- Hikes to fight inflation → interest costs explode
- Debt rolls over at higher rates → debt service unsustainable
- "Jebakan hutang tutup hutang. Terbitin hutang lebih gede buat bayar pokok+bunga sebelumnya."
DE-LEVERAGING (The Only Way Out):
Mathematically 3 options to reduce Debt/GDP:
1. Grow economy faster than debt (impossible now)
2. Reduce debt massively (via austerity)
3. Increase government revenue (taxes)
AUSTERITY = ECONOMIC DEATH:
- Y = C + G + I + (X-M); G (govt expenditure) gets cut
- Euro zone already asked to tighten spending
- US will be "forced" to cut spending
- "Kombinasi pengetatan pengeluaran + digencarkannya pajak = ekonomi mediocre"
TAX EXPLOSION:
- Extensification + intensification of taxes
- US/Canada investors facing higher capital gains tax
- "Ciri negara lagi kere"
THE OUTCOME:
- De-leveraging → economic downturn + stubborn inflation (debt service costs remain)
- "Ekonomi bertumbuh mediocre tapi inflasi tumbuh"
- Loss of confidence → capital flight from developed markets
- "Exodus besar-besaran: uang kabur dari sana"
- Emerging markets = rising star (China = main beneficiary)
HISTORICAL PARALLELS:
- 1940s (WWII reset), 1970s (stagflation), or L-shape/W-shape recovery
- "L-shape = downturn then flat for long; W-shape = bumpy over extended period"
- "Minimal 1 year, bisa lebih dari 3 tahun"
Ricky's call: "Nanti uang akan mengalir deras dari yang kemarin di kerangkeng. Emerging akan jadi rising star. Saya pilih China sebagai bintang utama."""",
        category="cycle",
        catalyst_types=["us_debt_crisis","de_leveraging","austerity","tax_explosion","capital_flight_developed",
            "emerging_market_beneficiary","qe_devil","rollover_wall","interest_cost_spiral"],
        activation_keywords=["us debt collapse","7 trillion rollover","us debt 37 trillion","debt crisis",
            "de-leveraging","austerity","tax explosion","capital flight","emerging star","qe devil",
            "setan qe","quantitative easing candu","bom waktu hutang","jebakan hutang","hutang tutup hutang",
            "y equals c plus g plus i","government expenditure cut","tax extensification","tax intensifikasi",
            "capital gains tax increase","euro zone austerity","us forced austerity","l shape recovery",
            "w shape recovery","1940 style","1970 style","china bintang utama","exodus uang",
            "loss of confidence","inflation stubborn","mediocre growth"],
        invalidation_keywords=["debt_restructured_smoothly","growth_outpaces_debt","austerity_avoided",
            "tax_cuts_instead","capital_returns_to_us","china_bazooka_fails"],
        beneficiaries={"global":["EEM","VWO","FXI","MCHI","KWEB"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK"],
            "commodities":["GC=F","HG=F"],"safe_haven":["GLD","USD_cash"]},
        fades={"us":["SPY","QQQ","IWM","TLT"],"europe":["auto_sector","industrial"],"developed":["high_beta"," leveraged"]},
        regime_alignment={"Q4":1.80,"Q1":1.60,"Q3":1.20,"Q2":0.80},
        typical_duration_weeks=104,
        conviction_ceiling=0.85,
        pump_risk=0.10,
        confirmation_signals=["us_debt_above_40t","7t_rollover_spreads_widen","austerity_announcements_eu",
            "us_spending_cuts_proposed","capital_gains_tax_hike","capital_flight_em_record","china_fxi_inflows",
            "gold_demand_emerging_surge","dxy_weakening_trend"],
    ),

    # ── ARTICLE 5+6: Backdoor Listing Frenzy & 2024 Tactical Journey ──────────
    NarrativeTemplate(
        name="Indonesia Backdoor Listing Frenzy & 2024 Tactical Journey",
        description="""Ricky2212 backdoor listing + personal 2024 performance framework:
BACKDOOR LISTING PHENOMENON:
- Definition: private company acquires majority of listed shell → changes business → no IPO needed
- Trending 2024: PANI, KARW, LABA, FUTR, PACK, and more
- Why trending: OJK tightening IPO scrutiny → backdoor faster/cheaper
- Shell company prices rising: Rp 15M → Rp 30M base price
- 6 criteria for shell target:
  (1) Going concern questionable
  (2) Majority PSP ownership (higher = better)
  (3) Almost no debt, positive equity
  (4) Market cap <Rp 50B (ideal), max Rp 70B
  (5) Not under bursa surveillance
  (6) No legal disputes
- Risk: not all succeed (CMPP/AirAsia, SUGI oil field, DKFT history)
- "Permainan liar sebelum transaksi; setelah transaksi = kembali ke fundamental"
- "CNI (Cacing Naga Investing) — max Rp 10M, isi waktu cari yield"
RICKY'S 2024 JOURNEY (Adaptive Investor):
- Theme: "Siram Bensin" = narrative + konglo + CA plays with controlled capital
- Phase 1 (moderate): SMDR (+40% + div), SMRA (+30% + div), DYAN/SICO/MCOR/BEST (+20-30%)
- Phase 2 (aggressive): LEAD/Logindo (narrative→CA→exit strategy, avg up, partial exit 140-150, buyback lower), BRMS (2 bagger, gold narrative + konglo + indexing rumor, exit), DKFT (bagger, credit to Mas Rizza), BUMI (hold as cycle closer)
- Phase 3 (mini/judi): Backdoor plays — GPSO (missed), AYLS (3 bagger), Nine (OTW 3 bagger), MENN (OTW), 4 others unpublished
- Crypto: 2023 Sep entry $2K → 4-5 bagger exit Q1 2024; re-entry post-crash, still riding Trump crypto bro narrative
- Junior miner crypto: BTC/ETH producer stocks (with Mas Rizza)
- Core liquidations: partial ITMG, full INCO exit for cash raising
- Cash deployment: Time Deposit, Money Market, Bond Fund
- "2024 = tahun penuh tantangan, kegilaan, ketidakrasionalan. Saya memilih jadi investor yang adaptif."
- "2025 = Preserve and Protect Capital"
- "Tetap WARAS apapun keadaannya. Tetap jadi DIRI SENDIRI."
Key principle: "Asymmetrical bet with measured capital. Never risk significant capital."""",
        category="corporate_action",
        catalyst_types=["backdoor_listing","shell_company","corporate_action","narrative_play","konglo_play",
            "siram_bensin","adaptive_investing","asymmetrical_bet"],
        activation_keywords=["backdoor listing","perusahaan cangkang","shell company","pani backdoor",
            "karw backdoor","laba backdoor","futr backdoor","pack backdoor","ojk ipo scrutiny",
            "backdoor criteria","going concern questionable","psp mayoritas","no debt positive equity",
            "market cap dibawah 50 milyar","cacing naga investing","cni","siram bensin","ricky 2024 journey",
            "kilas balik 2024","adaptive investor","logindo journey","brms 2 bagger","dkft bagger",
            "bumi cycle closer","crypto 4 bagger","junior miner crypto","gpso missed","ayls 3 bagger",
            "nine 3 bagger","menn otw","preserve capital 2025","asymmetrical bet"],
        invalidation_keywords=["backdoor_banned","ojk_blocks_backdoor","shell_prices_crash",
            "backdoor_failures_spike","fundamentals_return"],
        beneficiaries={"ihsg":["PANI.JK","KARW.JK","LABA.JK","FUTR.JK","PACK.JK","shell_companies_under_50b"],
            "strategy":["asymmetrical_bet","small_cap_narrative"]},
        fades={"ihsg":["big_cap_fundamental","low_liquidity_micro"],"us":["large_cap_value"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=26,
        conviction_ceiling=0.75,
        pump_risk=0.35,
        confirmation_signals=["backdoor_announcement_spike","shell_volume_surge","pani_karw_pattern_repeat",
            "ojk_backdoor_regulation","ricky_portfolio_exit_timing","narrative_volume_5x_avg"],
    ),

    # ── ARTICLE 7: 2025 Preserve & Protect Capital ──────────────────────────────
    NarrativeTemplate(
        name="2025 Strategy — Preserve and Protect Capital",
        description="""Ricky2212 2025 strategic framework: "Preserve and Protect the Capital."
RATIONALE:
- "Gimana tahun 2025? Rasanya kaya saya membohongi diri sendiri kalau bilang tahun baik."
- "Walau dibungkus apapun tetap terlihat buruk."
- Capital risk = primary concern
- "Daripada konyol, kadang diam jauh lebih baik. Menang dalam investasi bukan hanya nilai naik, tidak kehilangan modal pun sudah dianggap menang."
ALLOCATION FRAMEWORK:
- Aggressive max: 40% equity : 60% cash & equivalents
- Example Rp 100M:
  * 40M equity @ 20% return = 8M profit
  * 60M cash @ 5% p.a. = 3M profit
  * Total = 11M = 11% yield (above deposit/bond average)
- "Masih diatas rata2 deposito and obligasi. Not bad."
- "Kecil amat return segitu? Buset, otak masih ngeres cari return di kala keadaan kurang baik = SELAMAT."
CAPITAL PROTECTION MATH:
- 100M capital:
  * -40% loss = 60M remaining → bagger to 120M
  * -30% loss = 70M remaining → bagger to 140M
  * -20% loss = 80M remaining → bagger to 160M
  * -10% loss = 90M remaining → bagger to 180M
- "Pahami perbedaannya. Dengan begitu paham kenapa saya concern preserve capital."
GLOBAL 2025 ASSESSMENT:
- US: $36T debt + $1T interest/year. Shutdown budget battles. Tariffs = more destruction. "Tidak ada satu hal baik pun."
- EU: Most squeezed. Energy crisis + China competition + US tariffs. Deindustrialization. Germany contracting. "Urban area kaya Indo: pengangguran, pengemis, kriminal."
- Japan: BoJ must hike rates. JPY weakness = nightmare. "Masa indah low rates berakhir."
- China: Basa-basi stimulus continues. No fresh money yet. Wait-and-see. "Paling siap dengan bazooka."
- Indonesia: PPN 12%, BI trapped, consumer collapsing. "Jangan banyak berharap."
CONCERNS:
1. Global debt-to-GDP highest ever (surpassing pre-WWII)
2. No good data anywhere
3. CBs ready for zero/negative rates
4. China 10Y bond yield near 0% = GFC-level destruction
5. Mega-cap concentration in indices = unhealthy
6. Big Boyz stopped screaming recession = reverse signal
"The best way to preserve capital = cash keras tanpa embel-embel cari yield."
"2025 = PRESERVE and PROTECT the CAPITAL."""",
        category="psychology",
        catalyst_types=["preserve_capital","capital_protection","defensive_strategy","cash_positioning",
            "2025_macro_pessimism","risk_reward_asymmetry"],
        activation_keywords=["preserve capital","protect capital","2025 strategy","defensive mode",
            "40 60 equity cash","capital risk","not losing money","diam lebih baik","cash keras",
            "2025 preserve","ricky 2025 theme","global pessimism 2025","us 36 trillion debt",
            "eu deindustrialization","japan boj hike","china wait and see","indonesia ppn 12",
            "capital protection math","bagger recovery math","stay away big bank","no yield chasing",
            "preserve and protect","sesuaikan dengan diri sendiri"],
        invalidation_keywords=["global_growth_surprise","market_rally_sustained","fundamentals_return",
            "recession_avoided","china_bazooka_early"],
        beneficiaries={"safe_haven":["USD_cash","IDR_cash","money_market","deposito","TLT"],
            "ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK"],"us":["BRK-B","JNJ","PG"]},
        fades={"ihsg":["high_beta","property","consumer_discretionary","narrative_play"],
            "us":["IWM","high_beta_momentum","leveraged_etfs"],"crypto":["BTC-USD","high_leverage"]},
        regime_alignment={"Q1":1.60,"Q2":1.40,"Q3":1.20,"Q4":1.00},
        typical_duration_weeks=52,
        conviction_ceiling=0.90,
        pump_risk=0.05,
        confirmation_signals=["cash_allocation_above_60pct","equity_reduction_executed","deposito_rates_stable",
            "global_pmi_below_50","us_debt_spreads_widen","china_10y_below_1pct","big_boyz_stop_recession_calls"],
    ),

    # ── ARTICLE 9+10: Peak Signals & Big Boyz Reverse Psychology ──────────────
    NarrativeTemplate(
        name="Peak Euphoria Signals — Big Boyz Reverse Psychology & Final Dessert",
        description="""Ricky2212 peak detection framework: 4 signals + reverse psychology.
4 PEAK SIGNALS:
1. IWM (Russell 2000) ATH→ATH repeatedly: "On going." Small caps with 70% unprofitable constituents hitting ATH = delusional.
2. Gold rallying simultaneously with market rally: "Gold is uncertainty hedge; if market jacks up and Gold also ATH = something uncertain ahead." (from 13 key point)
3. BTC / Dunia Antah Berantah ATH→ATH: "Milestone: BTC $100k breached." Flow: BTC → Mega Cap → Big Cap → Mid Cap → Shitcoins. "Typical Do or Die."
4. BUMI as final dessert: "ADII aja lagi dipersiapkan, masa si itu tuh yang jadi puncak Dessert ga dihidangkan." BUMI = cycle closer signal. "BUMI akan di-BRMS-kan."
BIG BOYZ REVERSE PSYCHOLOGY:
- 2022-2023: UBS, GS, Citi, BoA, JPM all screaming RECESSION. Didn't happen.
- 2024-2025: All stopped recession calls. Now upgrading Dow/SPX/IWM/QQQ targets every rally. "Naik = upgrade, naik = upgrade lagi."
- "Ini BAKAL JADI BULL MARKET PANJANG dan LUAR BIASA. DIS TAIM is DIPPEREN."
- Ricky's interpretation: "Typical Fund motto: 'Lebih baik Mati and Bego Bareng daripada Fund gw di beat sama fund lain.'"
- "Saat mereka serempak teriak resesi = ga kejadian. Saat mereka serempak teriak ekonomi seeeetrong = harusnya yang terjadi berikutnya adalah?"
- "Saya selalu jadi pihak yang reverse the psycho."
5 REASONS BULL COMING (Short-term tactical):
1. Crypto risk-on extreme: money flowing BTC→mega→big→mid→shitcoins
2. DXY at top, IDR cheap, IHSG beaten = perfect setup for fund inflow
3. Banking-led reversal pattern (common reversal start)
4. IHSG back above ATH-10% = defense level holds
5. Only 1 dessert served (BUMI/BRMS), ADII still preparing = party not over
TACTICAL WARNING:
- "Nikmati blow off top sampai muntah-muntah. Jangan sampai mabuk, jangan lupa pulang."
- "Bull yang bakal bikin FOMO luar biasa."
- "Saat sinyal diatas makin kuat datangnya = bersiap."
- "For now, nikmati dulu."
Key principle: Big Boyz consensus = contrarian signal. When they all agree = opposite happens.""",
        category="cycle",
        catalyst_types=["peak_signals","iwm_ath","gold_market_divergence","btc_ath","bumi_dessert",
            "big_boyz_reverse","contrarian_psychology","euphoria_peak","bull_trap_setup"],
        activation_keywords=["peak signal","iwm ath","russell 2000 ath","gold rally market rally",
            "btc 100k","btc ath","dunia antah berantah ath","bumi dessert","adii preparing",
            "big boyz reverse psychology","big boyz recession","ubs gs citi boa jpm recession",
            "upgrade target dow","upgrade target spx","bull market panjang","dis taim is dipperen",
            "reverse the psycho","fund motto mati bego bareng","5 reasons bull","dxy top idr cheap",
            "banking led reversal","ath minus 10 defense","blow off top muntah","fomo luar biasa",
            "sinyal puncak","4 sinyal puncak","last signal","derrreesss bro","optimisme kembali"],
        invalidation_keywords=["iwm_corrects_20pct","gold_divergence_resolves","btc_below_80k",
            "big_boyz_recession_returns","fundamentals_return","no_peak_formed"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","BEST.JK","MCOR.JK","DYAN.JK","LEAD.JK"],
            "us":["IWM","BTC-USD","ETH-USD"],"crypto":["BTC-USD","ETH-USD","MSTR","COIN"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"],"us":["TLT","GLD","VIX"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.30,
        confirmation_signals=["iwm_ath_sustained","gold_ath_while_market_ath","btc_above_100k",
            "bumi_volume_bludak","big_boyz_upgrade_spree","retail_fomo_extreme","cheerleader_peak",
            "adii_movement_starts","crypto_shitcoin_volume_surge"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH13)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH13})
# for _n in _NARRATIVES_BATCH13:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
