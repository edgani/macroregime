"""config/narrative_universe.py — BATCH 12
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Kalau memang baik keadaanya, kenapa harga emas harus SPIKE? (USD debt, stagflation, gold signal)
2.  Kalau market memang Bullish, koq saya bermain defensive? (tricky market, structural vs fake bullish)
3.  Jack up => perfect timing for EXIT (smart money distribution, Buffett cash, peaked market)
4.  2 menu Dessert sebagai puncak penanda penutup Cycle (BUMI/BRMS, crypto 100-120k, Russell/Gold ATH)
5.  Same Scenario / ATH -10% (IHSG 7119, June 2024 deja vu, retail fleeing, MSCI underweight)
6.  Fresh Money, Fresh Money (China $1.4T debt swap ≠ stimulus, no fresh money, QE theory)
7.  (Perfect Set and Jack) UP (FOMC Dec, DXY top, OPEC cut, war, crypto meme = final jack up setup)
8.  Fundamental is Dead, hhmmm yeah but just for a while (no fundamentals, big funds avoid big cap)
9.  From Bad to Worst. Setannya adalah Over leverage (leverage devil, MSTR, retail margin, JPY carry)
10. ATH -10% for last jack up? (IHSG 7900→7300, siram bensin at pessimism, narrative+konglo play)

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

_NARRATIVES_BATCH12: List[NarrativeTemplate] = [

    # ── ARTICLE 1: Gold Spike = Macro Collapse Signal ─────────────────────────
    NarrativeTemplate(
        name="Gold ATH Spike — USD Debt Crisis & Stagflation Warning",
        description="""Ricky2212 gold framework: Gold spike is NOT a good sign — it signals something big is broken.
GOLD AS INFLATION HEDGE? No — world is in DISINFLATION/DEFLATION, not inflation. Central banks cutting rates. So why gold +35% YTD and +50% since Sep 2023?
GOLD AS UNCERTAINTY HEDGE? No — CBs already signaled certainty of CUTs. So what uncertainty?
Ricky's thesis: Gold spike = signal of MASSIVE macro instability ahead.
1. USD COLLAPSE / DEBT CRISIS:
- US debt ~$38T (nearly doubled in 7 years)
- Interest cost ~$1T/year + deficit spending = must print MORE
- Debt-to-GDP surpassing 1930s-1940s levels → approaching 100-year debt cycle peak
- "Cetak uang untuk bayar hutang + bunga = inflasi lebih parah nanti"
- Stagflation ('70s style) = most feared period for nations and CBs
- China & Russia hoarding gold = preparing for super bazooka stimulus without destroying currency value (gold-backed credibility)
2. GEOPOLITICAL RESET VIA CONFLICT:
- US doesn't want to collapse alone → drags world down
- Wars force resource hoarding, drain budgets, destroy economies post-war
- '40s style = WWII reset; Pearl Harbor → Hiroshima/Nagasaki pattern
- "Cara terbaik reset ekonomi dunia = perang"
- Gold = hedge against geopolitical uncertainty
3. CENTRAL BANK STUPIDITY HEDGE:
- CBs know they made massive mistakes; not ashamed to admit it
- They know where this ends → buying gold as insurance against their own policy failures
- "Gold = STUPIDITY HEDGE"
Key data: Gold ATH while market ATH = classic pre-crash divergence. "Kalau memang baik keadaanya, kenapa harga emas harus SPIKE?"
Historical styles: '40s (war reset), '70s (stagflation), or worst case 1929 (Great Depression).
China needs massive gold reserves before launching $1T+ bazooka.""",
        category="cycle",
        catalyst_types=["gold_ath_spike","usd_debt_crisis","stagflation","central_bank_gold_hoarding",
            "100_year_debt_cycle","geopolitical_reset","china_bazooka_prep"],
        activation_keywords=["gold spike","emas spike","gold ath","harga emas rekor","usd debt 38 trillion",
            "debt to gdp","stagflation","70s style","40s style","1929 style","central bank gold buying",
            "china gold hoarding","russia gold","dollar collapse","debt crisis","100 year debt cycle",
            "cetak uang","bunga hutang 1 trilyun","inflasi parah","stupidity hedge","geopolitical uncertainty",
            "perang dunia","pearl harbor","hiroshima","reset ekonomi","china bazooka gold"],
        invalidation_keywords=["gold_corrects_20pct","usd_strengthens","debt_restructured_smoothly",
            "peace_agreement","china_bazooka_cancelled"],
        beneficiaries={"global":["GLD","IAU","PHYS","SGOL"],"ihsg":["ANTM.JK","MDKA.JK","BRMS.JK","AMMN.JK"],
            "fx":["USDJPY","DXY"],"commodities":["GC=F"]},
        fades={"us":["SPY","QQQ","IWM","high_beta"],"ihsg":["property","consumer_discretionary"],"crypto":["BTC-USD"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["gold_ath_sustained_weeks","usd_debt_above_40t","dxy_weakening_trend",
            "central_bank_gold_purchases_record","china_gold_reserves_surge","stagflation_data_emerging",
            "us_10y_above_5pct","debt_service_cost_above_1t"],
    ),

    # ── ARTICLE 2: Tricky Market — Structural vs Fake Bullish ───────────────────
    NarrativeTemplate(
        name="Tricky Market — Fake Bullish vs Structural Bullish Divergence",
        description="""Ricky2212 market structure framework: "Ini bukan market bullish yang sempurna."
FAKE BULLISH (Current):
- Market ATH but driven by konglo narrative plays, not fundamentals
- Banking sector (BBRI, BBCA, BBNI, BMRI) NOT leading = economy not truly growing
- Old industrial (ASII) NOT performing = consumer purchasing power weak
- "Konglo plays filling void of 'mainan' in market" = distribution phase
- "Market naik tapi lihat saham yang menopang kenaikan indeks"
STRUCTURAL BULLISH (Historical benchmark 2003-2007):
- BBRI profit: 2.58T→6T (2003-2008); stock price surged massively
- ASII profit: 4.4T→9.2T (2003-2008); became largest market cap
- All sectors performed; big cap, mid cap, small cap all rallied
- Real economic growth reflected in corporate earnings
- Credit from banks flowed abundantly to economy
- "Beli saham apa aja, baik big cap, mid cap, apalagi small cap kesemuanya dapat return mumpuni"
CURRENT SIGNS OF WEAKNESS:
- Retail FOMO shifting from stocks to crypto ("retail frustasi pindah ke dunia antah berantah")
- Super bullish voices fading; pessimism replacing euphoria
- "Tricky Market = banyak tipu muslihat, tidak dalam pattern standard bullish"
- Short seller turned public bull ("beli big cap US dan tutup mata") = smart money covering?
Ricky's stance: defensive, not all-out; "siram bensin" only with prepared loss capital
"It's a narrative play, it's a konglo play, it's a corp action play — itu tema yang saya mainkan."
"Saya yang siramin bensin saat semua optimis menghilang."""",
        category="cycle",
        catalyst_types=["fake_bullish","structural_bearish","konglo_distribution","banking_not_leading",
            "retail_to_crypto_flight","pessimism_spike","tricky_market"],
        activation_keywords=["tricky market","fake bullish","structural bullish","market naik tapi","konglo play",
            "narrative play","banking not leading","bbri baca bbni bmri","asii not performing",
            "old industrial weak","consumer purchasing power","retail frustasi","retail pindah crypto",
            "super bullish fading","pessimism market","short seller bull","defensive positioning",
            "siram bensin","optimis menghilang","market tipu muslihat","2003 2007 bullish",
            "beginner luck 2003","fundamental dead","big cap not leading"],
        invalidation_keywords=["banking_sector_leads","asii_surges","retail_returns_to_stocks",
            "structural_bullish_confirmed","fundamentals_return"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK"],"us":["BRK-B","JNJ","PG"]},
        fades={"ihsg":["high_beta_konglo","property","consumer_discretionary","narrative_play"],"us":["IWM","high_beta_momentum"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["bbri_underperforms_index","asii_weak_relative","retail_turnover_to_crypto",
            "konglo_volume_spike_distribution","banking_index_flat_while_ihsg_rises","pessimism_breadth_surge"],
    ),

    # ── ARTICLE 3+10: Jack Up = EXIT / Smart Money Distribution ───────────────
    NarrativeTemplate(
        name="Jack Up = Perfect EXIT — Smart Money Distribution Phase",
        description="""Ricky2212 exit timing framework: "Jack Up is Perfect Timing for EXIT."
SMART MONEY SELLING INTO STRENGTH:
- Warren Buffett: sold 50% of Apple (favorite stock); continued selling; cash position $325B
- Berkshire: selling Bank of America continuously
- Stan Druckenmiller: sold NVDA and AMZN
- George Soros: sold NVDA
- Jensen Huang (NVDA CEO): selling own company shares at rapid pace
- All increasing cash, not buying
KONGLO EXIT STRATEGY:
- "Konglo aja melakukan exit strategy; mereka punya jangkauan akses informasi cepat"
- "Mereka mencium sesuatu hal yang tidak mengenakkan"
- "Jack Up euphoria sangat mereka butuhkan untuk mengeluarkan posisi besar"
PSYCHOLOGY OF EXIT:
- Better to sell into rally than into crash
- "Coba bayangkan kalau keadaan sebaliknya: bursa diiris pelan-pelan, ga berasa. Gimana psikologi anda?"
- "Ah rebound biarin dulu, siapa tau ini awal rally" = trap psychology
- "Jack Up membuat psikologi lebih rela menjual"
ATH -10% AS LAST JACK UP:
- IHSG ATH 7910; -10% = 7119 (hit 7122 intraday, closed 7161)
- "Saya siramin bensin saat semua optimis menghilang"
- "Nanti yang hilang tadi optimisnya akan muncul lagi saat pasar kita dapat inflow"
- Risk more measured at 7300-7100 than FOMO at 7900
- "Mainnya siram bensin and tetap pada narrative play, konglo play"
TACTICAL FRAMEWORK:
- "Nikmati blow off top sampai rentang waktu Pemilu US dan Inagurasi, tapi tetap waras dalam euphoria"
- "Tujuan artikel: menggerakkan pola pikir agar bisa membuat keputusan terbaik"
- "Jack Up bukan buat kusak-kusuk cari FOMO; Jack Up is Perfect Timing for EXIT"""",
        category="cycle",
        catalyst_types=["smart_money_exit","buffett_cash","distribution_phase","jack_up_exit",
            "ath_minus_10","konglo_distribution","retail_fomo_trap"],
        activation_keywords=["jack up exit","perfect timing for exit","smart money selling","buffett cash 325b",
            "buffett sell apple","berkshire sell bank of america","druckenmiller sell nvda","soros sell nvda",
            "jensen huang sell","nvda insider selling","distribution phase","konglo exit strategy",
            "ath minus 10","ihsg 7119","ihsg 7122","siram bensin saat pesimis","optimis menghilang",
            "retail frustasi","fomo trap","blow off top exit","sell into rally","jack up before storm",
            "pemilu us inagurasi","narrative play exit","konglo play exit"],
        invalidation_keywords=["smart_money_buying","buffett_stops_selling","retail_returns","fundamentals_return",
            "structural_bullish_confirmed"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK","GLD"],
            "us":["TLT","GLD","BIL","money_market"],"cash":["USD_cash","IDR_cash"]},
        fades={"ihsg":["BUMI.JK","BRMS.JK","BREN.JK","high_beta_konglo"],"us":["NVDA","AAPL","QQQ","IWM"]},
        regime_alignment={"Q3":1.80,"Q4":1.60,"Q2":1.20,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.85,
        pump_risk=0.20,
        confirmation_signals=["buffett_cash_325b_confirmed","nvda_insider_selling_accelerates",
            "berkshire_bac_position_drop","druckenmiller_13f_exit_nvda","ihsg_ath_minus_10_hit",
            "retail_pessimism_peak","konglo_block_sale_announcement","smart_money_cash_levels_rise"],
    ),

    # ── ARTICLE 4+5+6: Peak Cycle Dessert Menu & ATH-10% Pattern ────────────────
    NarrativeTemplate(
        name="Peak Cycle Dessert Menu — BUMI/BRMS + Crypto + ATH-10% Deja Vu",
        description="""Ricky2212 peak cycle signal framework: "2 menu dessert sebagai puncak penanda penutup cycle."
MENU 1 — BUMI & BRMS (Bakrie Cycle Closer):
- ADRO pattern → BUMI/BRMS will follow same playbook
- BUMI: Green ESG narrative (kokas, smelter, hilirisasi) + MIP policy + 2 secret stories
- BRMS: Gold narrative (ATH momentum) + Copper (AI) + Nickel + Silver
- "Bakrie adalah menu sinyal penutup cycle"
- "BUMI Beneran Untung Mestinya Ini; semoga BUMI akan di-BRMS-kan"
- Volume bludak, fund participation = distribution loading
MENU 2 — CRYPTO / DUNIA ANTAH BERANTAH:
- Both appetizer (pre-CUT signal) and dessert (post-CUT peak signal)
- Post-CUT rally in crypto = massive capital rotation
- Trump victory = crypto bro narrative exploited
- BTC target: 100k-120k ±10%
- "Kalau BTC berjalan dari ATH ke ATH, bersiap dan waspada"
- Retail fleeing stocks to crypto = classic pre-bottom signal
ATH -10% PATTERN:
- IHSG ATH 7910; -10% = 7119 (hit 7122, closed 7161)
- June 2024: same pattern at 6700 (ATH -10% then come-back rally to 7910)
- Deja vu signals:
  (a) Retail super bullish → sudden pessimism ("harus ada yang disalahkan")
  (b) Retail fleeing to crypto/bursa global ("pindah ke dunia antah berantah yang on fire")
  (c) Big Boyz downgrade at exact low (Morgan Stanley Jun 2024, MSCI underweight 2.5%→1.5%, JP Morgan downgrade Nov 2024)
- "Makin frustasi makin bagus" = contrarian buy signal
- "Cap cip cup, tetap B for B"
CHINA STIMULUS REALITY CHECK:
- $1.4T = local government hidden debt swap, NOT fresh money stimulus
- "No Fresh Money = bukan stimulus"
- Market disappointed: China futures -5% post-announcement
- Real bazooka needs $1T+ FRESH money injected into financial system
- "We want Fresh Money" = market chant
- China waiting for right timing (Fed deep easing, market not at ATH)
- When real bazooka comes = commodity explosion + inflation reacceleration""",
        category="cycle",
        catalyst_types=["peak_cycle_dessert","bumi_brms_peak","crypto_ath","ath_minus_10","china_stimulus_fake",
            "retail_to_crypto_flight","big_boyz_downgrade","bakrie_cycle_closer"],
        activation_keywords=["dessert menu","peak cycle signal","bumi brms dessert","bakrie cycle closer",
            "crypto ath","btc 100k","btc 120k","dunia antah berantah","ath minus 10","ihsg 7119","ihsg 7122",
            "june 2024 deja vu","retail pessimism","retail fleeing crypto","morgan stanley downgrade",
            "msci underweight indonesia","jp morgan downgrade indonesia","big boyz downgrade","frustasi bagus",
            "china stimulus fake","no fresh money","local debt swap","china bazooka we want fresh money",
            "china futures minus 5","1.4 trillion not stimulus","fresh money chant","cap cip cup",
            "b for b","bumi brms peak signal","adro pattern bumi"],
        invalidation_keywords=["btc_below_80k","bumi_brms_collapse","china_fresh_money_1t","retail_returns_stocks",
            "big_boyz_upgrade"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK"],"crypto":["BTC-USD","ETH-USD"],"global":["MSTR","COIN","GLD"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"],"us":["SPY","QQQ"],"crypto":["altcoins_low_cap"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":1.00,"Q1":0.70},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["btc_above_100k","brms_volume_bludak","bumi_volume_5x_avg",
            "ihsg_ath_minus_10_hit","msci_underweight_indonesia","jp_morgan_downgrade_ihsg",
            "retail_crypto_rotation_spike","china_stimulus_disappointment","mip_policy_announcement"],
    ),

    # ── ARTICLE 7: Perfect Setup for Final Jack Up ────────────────────────────
    NarrativeTemplate(
        name="Perfect Setup for Final Jack Up — All Catalysts Aligning",
        description="""Ricky2212 tactical setup framework: "Perfect Set Up for Jack Up."
CATALYST ALIGNMENT (Dec 2024):
1. FOMC MEETING (Dec 17-18):
- Market pricing hawkish (no cut or hold) due to Trump policies (immigration, tariffs)
- Best case: 25bps cut; hold = 40% probability
- "Biasanya: semakin di-hawkishkan, kalau sedikit saja ga sesuai harapan = market rally"
- Historical: when market expects hawkish and gets dovish surprise = explosive rally
2. DXY AT RESISTANCE TOP:
- DXY "mondar-mandir" 2 years = managed currency game by global CBs
- "DXY kepentok atas, nanti ada berita buruk bikin USD keok"
- When DXY falls: global markets rally, IDR strengthens, commodities jack up
3. OPEC+ PRODUCTION CUT EXTENSION:
- Originally planned normalization Dec 2024 → extended
- Supply constraint maintained
4. RUSSIA-UKRAINE ESCALATION:
- Biden pushing war in final term
- Ukraine advanced missiles → Russia brutal retaliation
- Europe energy stocks empty → must refill
- "Stok minyak dan gas Eropa kosong dan harus diisi"
5. CRYPTO MEME MANIA:
- "Typical Do or Die"
- Meme coins surging = risk-on at peak
- Institutions rushing to BTC ("cepek ceng sudah dekat")
- "Ini awal dari puncak kegilaan"
SYNTHESIS:
- FOMC + DXY top + OPEC cut + war + crypto mania = "Damn I Love This Game"
- "USD melemah, OPEC CUT, Perang, Rusia kosong stok energi, dunia antah berantah menggila"
- All aligning for one final jack up before the storm
- "Sabar dikit, jangan mengeluh terus. Semua sudah saya ceritakan perjalanannya."
- "LK BRMS keluar mingdep and bakal bagus. Party selanjutnya bareng Om B akan dimulai."
Risk: if FOMC truly hawkish + DXY breaks out = setup fails.""",
        category="cycle",
        catalyst_types=["fomc_surprise","dxy_top","opec_cut_extension","war_escalation","crypto_mania",
            "perfect_setup","jack_up_catalyst","risk_on_peak"],
        activation_keywords=["perfect set up","jack up catalyst","fomc december","dxy top","dxy kepentok atas",
            "opec cut extension","opec perpanjang","russia ukraine escalation","biden war","ukraina rudal",
            "europe energy stock empty","crypto meme mania","do or die","cepek ceng","btc institution rush",
            "damn i love this game","usd melemah","komoditas jack up","idr kuat","banking driver indeks",
            "brms q3 bagus","party om bakrie","fomc surprise cut","hawkish expectation dovish surprise",
            "perfect set and jack up"],
        invalidation_keywords=["fomc_hawkish_hold","dxy_breaks_out","opec_flood_market","peace_agreement",
            "crypto_mania_ends"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","BEST.JK","MCOR.JK","DYAN.JK","LEAD.JK","WINS.JK","ELSA.JK"],
            "us":["IWM","QQQ","BTC-USD","ETH-USD"],"commodities":["CL=F","GC=F","HG=F"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK"],"us":["TLT","GLD","VIX"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=8,
        conviction_ceiling=0.75,
        pump_risk=0.30,
        confirmation_signals=["fomc_25bps_cut_surprise","dxy_reverses_from_top","opec_cut_extension_confirmed",
            "russia_ukraine_escalation_spike","crypto_meme_volume_surge","brms_q3_beat","ihsg_rally_post_fomc",
            "commodity_jack_up_oil_gold"],
    ),

    # ── ARTICLE 8+9: Fundamental is Dead / Over Leverage Doom ────────────────────
    NarrativeTemplate(
        name="Fundamental is Dead & Over-Leverage — The Devil in the Details",
        description="""Ricky2212 endgame framework: "From Bad to Worst. Setannya adalah Over leverage."
FUNDAMENTAL IS DEAD (Temporary):
- PAxx, BRxx, MLPT, KARx, PANI, AMMN moving without fundamentals
- Two choices: (a) Idealist = hold quality, skip party, no envy; (b) Player = join narrative, manage risk
- Soros interview: "Index rising while economy bad = signal of impending crash" (repeated phenomenon)
- Nifty Fifty parallel (1960s)
- WHY BIG FUNDS AVOID BIG CAP:
  - Big cap performance = driven by actual earnings + earnings expectations
  - If economy bad → big cap earnings will disappoint → funds avoid
  - "KARENA FUND SUDAH TAHU BAHWA KEADAAN SEDANG TIDAK BAIK-BAIK SAJA"
  - Funds think long-term, not 1 week/month/quarter
  - They can access deep company information
- "Fundamental is Dead, yeah but just for a while"
- Asymmetrical bet strategy: small capital in narrative play vs large capital in big cap
  - Big cap: 1M capital, 20-30% return = 200-300M; but 40% drop = 400M loss
  - Narrative: 200M capital, 1 bagger = 200M profit; 50-60% drop = 100-120M loss
  - "Cara defensive saya di masa Fundamental is Dead"
OVER LEVERAGE = THE DEVIL:
- Jack Up Before Storm + market disconnect = Soros crash signal
- Household allocation to paper assets rising = Do or Die phase
- LEVERAGE EXPLOSION:
  - MSTR (MicroStrategy): bond → buy BTC → BTC up → MSTR up → sell MSTR → buy more BTC → infinite loop
  - Retail margin: T+0, haircut adjustments, low-rate margin offers, konglo stocks marginable
  - Crypto leverage: even shitcoins now leverageable
  - Apps offering margin with low rates, konglo stocks as collateral
- LEVERAGE MATH:
  - 2x leverage: 30% drop = 60% loss
  - 5x leverage: small drop = total wipeout
  - "Makin tinggi leverage, makin parah kejatuhannya"
- JPY CARRY TRADE UNWINDING:
  - "2nd Unwinding Carry Trade" = additional leverage layer
  - When panic hits: JPY repatriation → forced selling across all assets
- DOMINO EFFECT:
  - Leveraged players panic first → forced liquidation → accelerates crash
  - "Dunia sekarang masuk gigi 3 dalam hal setan leverage"
  - "Efek diatas akan membuat domino effect ke semua asset tanpa tersisa"
- COMPARISON: Could be worse than 2008, 2000, 1987, 1974, or even 1929
- ADVICE: "Jangan pernah terpikir buat mengambil leverage. Berjalan normal dan aman saja."""",
        category="cycle",
        catalyst_types=["fundamental_dead","over_leverage","margin_explosion","crypto_leverage",
            "mstr_infinite_loop","retail_margin","jpy_carry_unwind","domino_effect","household_paper_assets"],
        activation_keywords=["fundamental is dead","over leverage","setan leverage","margin explosion",
            "mstr microstrategy","mstr bond btc loop","retail margin","t plus zero","haircut adjustment",
            "crypto leverage","shitcoin leverage","apps margin","konglo stocks marginable",
            "do or die","household paper assets","soros index up economy bad","nifty fifty",
            "fund avoid big cap","fund know economy bad","asymmetrical bet","capital allocation risk",
            "domino effect","jpy carry trade unwinding","leverage 2x","leverage 5x","leverage 10x",
            "forced liquidation","panic selling leverage","gigi 3 leverage","1929 style","2008 style",
            "no leverage advice","normal aman","fundamental dead temporary"],
        invalidation_keywords=["fundamentals_return","leverage_collapses_cleanly","mstr_loop_breaks",
            "retail_deleverages_early","jpy_carry_resolved"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK","GLD"],
            "us":["TLT","GLD","BIL","VIX","SQQQ"],"cash":["USD_cash","IDR_cash"]},
        fades={"ihsg":["high_beta_konglo","marginable_stocks","narrative_play"],"us":["MSTR","NVDA","high_beta","leveraged_etfs"],"crypto":["BTC-USD","high_leverage_coins"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=16,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["mstr_btc_loop_accelerates","retail_margin_debt_surge","crypto_leverage_ratio_spike",
            "household_paper_allocation_record","jpy_carry_unwinding_starts","margin_call_events",
            "fund_big_cap_underweight_confirmed","vix_spike_above_30"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH12)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH12})
# for _n in _NARRATIVES_BATCH12:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
