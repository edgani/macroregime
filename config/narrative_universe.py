"""config/narrative_universe.py — BATCH 14 + BATCH 15 + BATCH 16 (Apr 2026)
Artikel Ricky2212 / MentorBaik extraction:

BATCH 14:
1. Gold ATH — historical parallels + Trump uncertainty + physical hoarding
2. Banking CKPN cycle — structural bearish vs fake bullish
3. M2 Bubble Indicator — market cap/M2 ratio
4. IHSG Correction Depth — pyramid buying at 6500/6324
5. Blow Off Top Setup — AI/DeepSeek/Copper/Gold/Crypto/Konglo Tech
6. Danantara SWF — $900B AUM Indonesia sovereign wealth fund
7. Bear Market Entry — IHSG -21%, MSCI rebalancing, banking rebound
8. Market Come Back — 3 factors jack up (DXY, JPY carry, local fund cash)
9. Trump Tariff Shock Therapy — not the main show

BATCH 15:
10. Market Cetar Bergetar — IHSG halt, margin call BREN/TPIA/PANI, force sell cascade
11. Play Book IHSG — China playbook comparison, policy demand, -25% to -30% target
12. Things happen when no one talk about it — recession calls fail, Trump pessimism, blow off top
13. It's just a game — market manipulation thesis, 08 circle, Danantara timing, Himbara ex-date
14. Different game play — big cap banking vs conglo play, asymmetrical risk reward
15. Trump will Trim and reset US Economy — Reaganomics 1981-1982 comparison, mega tariff, reset
16. Trump tariff Good or Bad — debt $36T, weak USD, negotiation tactic, Fed forced cut
17. DxY hancur Rp lemah — DXY below 100, IDR 16800, inflow signal, BBRI ex-date smooth
18. World need another Store of Value — Bretton Woods, BRICS commodities, US BTC reserve
19. DxY sudah 98 time to shifting — USD trust decline, risk asset shift, LATAM outperform
20. Market bakal jatuh dalam — buying opportunity, cash wins, bear market correction, CUT narrative

BATCH 16:
21. Next Conglo Narrative (Narasi 9 Haji) — Tohir, Bakrie, H Isam, 08 circle plays
22. Next rally is not FINDIMINTIL rally — inflow rally, peaked market, CUT euphoria
23. Market bakal RISK ON pake banget — JPY carry, BTC/ETH spike, small cap ATH, liquidity driven
24. Trump doing a great job — Bidenomics cleanup, tax cut, tariff, fossil energy, recession base
25. Blow off the top skenario — UST spike trap, foreign bond buying, CUT FOMO, market peaked
26. Sun Tzu Art of War — Iran-Israel conflict as market driver, Hormuz, oil, WW3 theme
27. Get Ready TFF — OJK changes, lot shrink, tax amnesty, liquidity flood Indonesia
28. BER BER BER curse — Sep-Oct crash pattern, FOMC cut timing, TFF peak
29. TFF part 3 Puncak Kegilaan — BTC strategic reserve, US debt payoff, crypto hegemony
30. Perfect Classic Game Play — Big Fund rotation IDR→bonds→equity, weak hand shakeout
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

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 14 — Artikel Ricky2212 (Apr 2026 extraction)
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVES_BATCH14: List[NarrativeTemplate] = [

    # ── ARTICLE 1: Gold ATH Historical Framework ──────────────────────────────
    NarrativeTemplate(
        name="Gold ATH — Historical Parallels & Trump Uncertainty Hedge",
        description="""Ricky2212 gold framework with historical cycle mapping:
HISTORICAL GOLD SPIKES:
- 1979-1980: Iranian Revolution → geopolitical fear → gold +300%
- 2007-2011: GFC → $650/oz (mid-2007) → $1,900 (Sep 2011) = financial crisis hedge
- 2019-2020: COVID → $1,500 (mid-2019) → $2,075 (Aug 2020) = pandemic panic hedge
COMMON THEME: "KETAKUTAN" — fear of unknown → panic → sell risky assets → buy "safe" gold
CURRENT CONTEXT (2024-2025):
- Gold +40% in one year = unprecedented for safe-haven asset
- Physical hoarding at record levels: Bank of England withdrawal wait 4-8 weeks (was days)
- $82B stored in New York vaults
- Identical to COVID 2020 panic hoarding pattern
- Citadel 13F: massive GLD call/put spread (8M+ underlying shares on call side)
- Hedge funds now paying attention
TRUMP AS CATALYST:
- Full Republican control (House, Senate, Supreme Court) = can change everything
- Tax cuts, spending cuts, tariffs = massive uncertainty
- "Memotong pajak akan meningkatkan defisit; memotong pengeluaran mungkin mengimbangi"
- Pre-weekend tariff tweets on China/Mexico/Canada before official policy
- Investors seeking protection from economic uncertainty → gold
GOLD AS SIGNAL:
- 13 key point: "Gold rallying while market also rallying = peak cycle signal"
- "Market ATH + Gold ATH = something uncertain ahead"
- Target: $3,000/oz "in a matter of weeks" per market consensus
- "Prepare not Predict"
Key data: Gold is sending massive message to the world. "Kalau memang baik keadaanya, kenapa harga emas harus SPIKE?"""",
        category="cycle",
        catalyst_types=["gold_ath","historical_gold_spike","trump_uncertainty","physical_gold_hoarding",
            "hedge_fund_gold","geopolitical_fear","safe_haven_demand"],
        activation_keywords=["gold ath","gold spike","gold 3000","gold historical","1979 gold","2008 gold",
            "2020 gold","trump gold","physical gold hoarding","bank of england gold","gold withdrawal",
            "citadel gld","hedge fund gold","gold safe haven","gold ketakutan","gold fear","gold panic",
            "gold 40% ytd","gold record","gold demand","gold uncertainty hedge","trump tariff gold",
            "gold message","gold signal peak","gold 13 key point","prepare not predict gold"],
        invalidation_keywords=["gold_corrects_20pct","trump_dovish_pivot","peace_agreement",
            "gold_hoarding_ends","hedge_funds_exit_gold"],
        beneficiaries={"global":["GLD","IAU","PHYS","GC=F"],"ihsg":["ANTM.JK","MDKA.JK","BRMS.JK","AMMN.JK"],
            "us":["NEM","GOLD","AEM"]},
        fades={"us":["SPY","QQQ","IWM","high_beta"],"ihsg":["property","consumer_discretionary"],"crypto":["BTC-USD"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=26,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["gold_above_3000","physical_gold_premium_spike","gld_call_volume_surge",
            "trump_tariff_announced","bank_of_england_withdrawal_delay","hedge_fund_13f_gold_increase",
            "gold_ath_sustained_months"],
    ),

    # ── ARTICLE 2: Banking Sector CKPN Cycle & Structural Bearish ────────────
    NarrativeTemplate(
        name="Indonesia Banking CKPN Cycle — Structural Bearish Confirmation",
        description="""Ricky2212 banking sector deep-dive: "Bullish or Bullish-it?"
THE COLLAPSE:
- BBRI: profit announcement → stock ambruk. UMKM sector hardest hit.
- BBNI: profit announcement → stock ambruk. "Bobrok tata kelola."
- BMRI: profit announcement → stock dropped nearly 10%. "Sekelas BMRI turun hampir 10% = kurang apa?"
- BBCA: best positioned but also facing CKPN pressure
- Banking sector dropped >2% in single day = majority of index decline
WHY BANKING COLLAPSES:
1. REAL ECONOMY IS BAD: "Bank adalah pusat sirkulasi uang. Saat ekonomi tidak baik, bank pasti terseret."
2. CKPN CYCLE JUST STARTED: Post-COVID restructuring package ended Q1 2024. NPLs creeping up. Provisions must rise.
    - "Siklus CKPN bank besar baru dimulai pertengahan 2024."
    - BTPS started earlier; big banks just beginning now
    - "Sampah2x di bank besar akan dibuka. Perlahan NPL merangkak naik."
    - Duration: 6 months to 1 year+ depending on economy
3. FUND FACTORING IN BAD NEWS: "Big fund sedang mengabsorb dan memfaktorkan keburukan ekonomi real."
STRUCTURAL vs FAKE BULLISH:
- Structural bullish = banking + old industrial leading
- Fake bullish (Bullish-it) = konglo plays filling void while banking flat/weak
- "Sekarang? Banking NOT leading = economy NOT truly growing"
- "Mau dikemas kaya apa, keadaan Bank tetap tidak bisa dibohongi."
Ricky's warning: "Stay away from big bank dulu, nanti aja buat next cycle."
"Saya sudah berkali2x warning masalah perbankan dari tahun lalu."
"PHK 52,993 (Sep 2024), up 25.3% YoY."
"K-shape economy: rich richer, poor poorer."
Key data: Banking is the lie detector of the real economy. When banking collapses, the economy is truly sick.""",
        category="sector",
        catalyst_types=["banking_ckpn_cycle","npl_rise","profit_disappointment","structural_bearish",
            "fake_bullish","umkm_collapse","consumer_down_trading"],
        activation_keywords=["banking collapse","bbri ambruk","bbni ambruk","bmri turun 10%","bbca drop",
            "ckpn cycle","ckpn bank besar","npl naik","banking sector drop","structural bullish",
            "bullish or bullish-it","fake bullish","banking not leading","bank lie detector",
            "ekonomi buruk banking","bank pusat sirkulasi","fund factor bad news","umkm kena pukul",
            "btps ckpn","bbri ckpn","bmri ckpn","bbni ckpn","phk naik 25%","k shape economy",
            "stay away big bank","banking warning","ckpn siklus baru","restrukturisasi covid berakhir"],
        invalidation_keywords=["banking_recovers","ckpn_cycle_ends","npl_stabilizes","profit_beat_banking",
            "structural_bullish_confirmed"],
        beneficiaries={"ihsg":["BBCA.JK"],"safe_haven":["IDR_cash","USD_cash","money_market","deposito"]},
        fades={"ihsg":["BBRI.JK","BTPS.JK","BBNI.JK","BMRI.JK","banking_sector","financial_sector"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=26,
        conviction_ceiling=0.85,
        pump_risk=0.10,
        confirmation_signals=["bbri_profit_miss","bmri_drop_10pct","banking_index_drop_2pct",
            "ckpn_provision_spike_q4","npl_above_3pct_banking","umkm_default_rate_rise",
            "phk_above_50k_indonesia","consumer_loan_growth_negative"],
    ),

    # ── ARTICLE 3: M2 Bubble Indicator ────────────────────────────────────────
    NarrativeTemplate(
        name="M2 Money Supply vs Market Cap — Bubble Ratio Indicator",
        description="""Ricky2212 M2 framework: "Banjir M2, market jadi bullish?"
M2 DEFINITION: Broad money supply = cash + savings + money market + time deposits + liquid assets
M2 MECHANICS:
- M2 growth after tightening period = economy starting to move
- M2 flood + low rates = banks aggressively lending → consumer spending up → economy grows → stock market rises
- Extreme M2 flood + near-zero rates = speculation in paper assets (stocks, commodities, crypto)
- "Contoh terdekat 2020: M2 banjir → spekulasi paper asset"
THE RATIO: Total Market Cap / M2 Money Supply
- Ratio rising = market cap driven far above M2 = irrational, expensive, bubble forming
- Ratio peak = gray area/recession follows
- Ratio crash = bubble burst → ratio falls back down
HISTORICAL PATTERNS:
- 2000 Dot-com (blue circle): Ratio spiked to extreme → bubble burst → ratio crashed
- 2007-2008 (green circle): Pre-crisis ratio rose steadily with real growth → peaked → GFC → ratio crashed
- 2020-now (red circle): "Lihat ujung paling kanan. Apa yang anda lihat?"
- "Makin tinggi grafiknya makin ga rasional dan mahal kapitalisasi pasarnya."
CURRENT STATE:
- M2 growing but market cap growing FASTER = ratio at dangerous levels
- "Dorongan M2 itu real mendorong ekonomi atau digunakan buat ajang jack up paper asset belaka?"
- "Resiko menarik time frame terlalu pendek akan lebih besar dibanding melihat time frame lebih besar"
Ricky's interpretation: Current ratio spike resembles 2000 and 2007 peaks. "Prepare not Predict."
Key insight: Don't look at M2 in isolation. Look at Market Cap/M2 ratio + time frame.""",
        category="cycle",
        catalyst_types=["m2_bubble","market_cap_m2_ratio","liquidity_flood","speculation_indicator",
            "paper_asset_bubble","monetary_easing_speculation"],
        activation_keywords=["m2 money supply","banjir m2","market cap m2 ratio","m2 bubble indicator",
            "liquidity flood","paper asset speculation","m2 vs market cap","broad money supply",
            "m2 growth","m2 speculation","monetary easing speculation","2000 dotcom ratio","2008 gfc ratio",
            "2020 m2 flood","ratio naik tinggi","kapitalisasi pasar mahal","time frame pendek resiko",
            "prepare not predict m2","m2 mechanism","bank lending m2","consumer spending m2"],
        invalidation_keywords=["m2_ratio_normalizes","fundamentals_drive_market","m2_growth_real_economy",
            "ratio_declines_healthy"],
        beneficiaries={"us":["SQQQ","VIX","TLT","GLD"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK"],
            "safe_haven":["USD_cash","IDR_cash","money_market"]},
        fades={"us":["SPY","QQQ","IWM","high_beta","meme_stocks"],"ihsg":["high_flyer","property","narrative_play"]},
        regime_alignment={"Q3":1.70,"Q4":1.60,"Q2":1.20,"Q1":0.90},
        typical_duration_weeks=52,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["market_cap_m2_ratio_all_time_high","m2_growth_accelerating","margin_debt_surge",
            "retail_speculation_index_spike","crypto_volume_vs_m2_spike","2000_pattern_resemblance"],
    ),

    # ── ARTICLE 4+7: Correction Depth & Bear Market Entry Strategy ─────────────
    NarrativeTemplate(
        name="IHSG Correction Depth — Pyramid Buying at 6500/6324 Bear Territory",
        description="""Ricky2212 correction framework & entry strategy:
THE NUMBERS:
- ATH: 7,910
- Low: 6,500 (intraday near 6,500)
- Correction: -17.8% (1,410 points)
- ATH -10%: 7,119 (hit 7,122, closed 7,161) — June 2024 deja vu
- ATH -20%: 6,324 = bear market territory
- Beyond ATH-20% sustained = crisis territory
- "Bisa tembus lebih jauh? kalo tembus lebih jauh = crisis correction"
STRATEGY — PYRAMID BUYING:
- "Saya ga tau dimana bottom. Yakin ga ada yang bisa menebak."
- Risk/reward based entry:
    * At 6,500 (-17.8%): Start entry. Risk to ATH-20% (6,324) = ~3% more downside
    * At 6,324 (-20%): Add more. Risk to ATH-30% (~5,500) = prepared but not expected
    * "Semakin dalam, semakin banyak saya membelinya"
    * Example: 50 lot allocation = 3, 5, 10, 12, 20 lots at progressively lower levels
    * "Panjangin nafas"
WHAT RICKY BOUGHT:
- JPY: "Kejatuhan JPY membuatnya cukup murah. Keyakinan USD akan keok."
- Banking (4 banks): 3 state banks + 1 private bank (larger private allocation)
    * "Saya ga tau mana yang come back terbaik. Daripada pusing, masukkan ke 4 bank sekaligus."
    * "3 bank pelat merah seimbang + 1 bank swasta lebih besar"
    * "Sistem piramid buying. Titip sendal buat entry pertama."
- Konglo (saudara muda): "Story tidak selesai karena harga turun."
    * BUMI/BRMS younger sibling plays
    * "Kalau turun = bisa masuk lebih murah."
- MPIX (Madura): "Dikasih turun lagi pasca spike."
- Reserve cash: Max 10-15% from reserve deployed. "Belum pada posisi the worst."
MSCI REBALANCING:
- Morgan Stanley downgrade → index drop → foreign selling
- "Nadahin barang FULE (Foreign Bule) di level bawah"
- "Nanti di-upgrade lagi, saham anda yang dimakan FULE kembali"
- Morgan Stanley then upgrades banking sector days later = "typical positioning"
COME BACK CONFIRMATION:
- +3.97% (249pt) to 6,519 with Rp 16T value
- Banking-led: BBRI +9.23%, BMRI +6.52%, BBNI +5.71%, BBCA +4.45%
- "Full Body Cover" candle pattern
- 6,324 and 6,500 both reclaimed quickly
- "Worstnya baru saja kita lewati Jumat."
- Fund local still skeptical = "mereka yang akan dorong indeks ke atas nanti"
- "Pungutin barang dari FULE di bawah, nanti mereka yang mengantarkan posisi anda ke atas."
"One Great Moment can change your wealth."
"Jack Up is for EXIT."""",
        category="cycle",
        catalyst_types=["correction_depth","bear_market_entry","pyramid_buying","msci_rebalancing",
            "morgan_stanley_downgrade","banking_rebound","full_body_cover","foreign_bule_nadah"],
        activation_keywords=["correction depth","ihsg 6500","ihsg 6324","ath minus 20","bear market territory",
            "pyramid buying","piramid buying","entry bertahap","beli saham turun","jpy entry","jpy murah",
            "banking entry","4 bank sekaligus","titip sendal","konglo saudara muda","mpix madura",
            "msci rebalancing","morgan stanley downgrade","morgan oey","nadahin fule","foreign bule",
            "full body cover","market come back","bbri naik 9%","bmri naik 6%","ihsg naik 3.97%",
            "worst over","fund local skeptis","one great moment","jack up is for exit","reserve cash 10%",
            "ath minus 30","crisis correction","ihsg rebound","banking rebound"],
        invalidation_keywords=["ihsg_breaks_6000","msci_further_downgrade","foreign_exodus_accelerates",
            "banking_continues_collapse","idr_above_17000"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BUMI.JK","BRMS.JK","MPIX.JK"],
            "fx":["JPY=X","USDJPY"],"safe_haven":["IDR_cash","USD_cash"]},
        fades={"ihsg":["high_flyer","property","consumer_discretionary"],"us":["high_beta"]},
        regime_alignment={"Q3":1.20,"Q4":1.10,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["ihsg_reclaims_6500","ihsg_reclaims_6324","banking_index_leads_rebound",
            "msci_rebalancing_complete","morgan_stanley_upgrade_banking","foreign_net_buy_returns",
            "jpy_strengthens_from_low","idr_stabilizes_below_16500"],
    ),

    # ── ARTICLE 5: Blow Off Top Setup ─────────────────────────────────────────
    NarrativeTemplate(
        name="Blow Off Top Setup — AI/DeepSeek/Copper/Gold/Crypto/Konglo Tech Convergence",
        description="""Ricky2212 blow-off-top catalyst convergence framework:
1. AI NARRATIVE:
- "Narasi AI dengan segala embel2xnya kembali digulirkan. Luar biasa kuat."
- Chip stocks surging (NVDA, AMD, etc.)
- Palantir: "terang2an busuk aja kebagian jack up. Perusahaan valuasi 50x sales."
- Supporting AI stocks all jacked up
2. CHINA TECH / DEEPSEEK:
- DeepSeek effect: "menawarkan banyak opportunity buat tech China"
- Alibaba, JD.com, Xiaomi, TSMC, and all China tech support stocks rallying
- "Narasi tech and deepseek kuat banget sampai ke akarnya"
- Hong Kong Tech Index broke 3-year high
3. COPPER RALLY:
- "Copper sih harusnya sudah masuk fase jack up"
- Copper = signal of commodity revival = risk-on
- "Sinyal kebangkitan komoditas"
4. GOLD MONSTER RALLY:
- "Untuk ukuran safe haven, rally 30% = luar biasa"
- "Demmand emas naik luar biasa"
- Gold ready to switch head to $3,000
- "Gold rally dibarengi market rally = peak cycle signal" (13 key point)
5. USD EASE:
- "Pergerakan USD perlahan mulai melempem"
- "Tanda menuju pelemahan USD perlahan mulai terlihat"
- "Slow but sure"
- Weak USD = risk-on trigger
6. CRYPTO:
- BTC in big consolidation phase
- "If consol selesai and bullish trend continues = one more risk-on signal"
- "BTC juga jadi salah satu sinyal penutup"
- Flow: BTC → Mega Cap → Big Cap → Mid Cap → Shitcoins
7. KONGLO TECH (Indonesia):
- WIFI acquired by 08's circle → conglo tech play
- DATA, DOOH, INET, ELIT all moving on tech optimism
- "Conglo tech related. Risk on mulai nampak kembali."
8. KONGLO PLAY (No PP):
- PP/PANI cooling down post-indexing frustration
- "Dejavu saat AMMN selesai panggungnya, uang langsung mengalir ke bawah konglo satu groupnya"
- "Likuiditas group pak PP dan PANI mau lari kemana?"
- BRMS/BUMI younger sibling: "Saudara Muda value transaksi menebal, saham merengsek naik"
- "The ultimate? Jagoan selalu belakangan."
Ricky's call: "Dengan segala sinyal risk on yang dikirim market, masa masih bertanya 'Pak kapan jack up?'"
"Jack Up is for EXIT."
"No price action question. Bawa thesis dahulu, baru diskusi."""",
        category="cycle",
        catalyst_types=["ai_narrative","deepseek_china","copper_rally","gold_rally","usd_weakness",
            "crypto_consolidation","konglo_tech","konglo_play","risk_on_convergence"],
        activation_keywords=["blow off top setup","ai narrative","deepseek effect","china tech rally",
            "alibaba rally","jd rally","xiaomi rally","tsmc rally","copper rally","copper jack up",
            "gold monster rally","gold 3000","gold safe heaven rally","usd ease","usd melemah",
            "crypto consolidation","btc consol","btc bullish trend","konglo tech","wifi conglo",
            "data dooh inet elit","risk on signal","blow off top ai","blow off top deepseek",
            "blow off top copper","blow off top gold","blow off top crypto","blow off top konglo",
            "pani cooling down","ammn dejavu","saudara muda konglo","brms bumi younger sibling",
            "jagoan belakangan","jack up is for exit","no price action question"],
        invalidation_keywords=["ai_narrative_collapses","deepseek_banned","copper_corrects_20pct",
            "usd_strengthens","crypto_breaks_down","konglo_tech_fades"],
        beneficiaries={"ihsg":["WIFI.JK","WIRG.JK","MPIX.JK","ELIT.JK","DOOH.JK","INET.JK","DATA.JK",
            "BUMI.JK","BRMS.JK","ADII.JK"],"us":["NVDA","PLTR","AMD","TSM","BABA","JD"],
            "commodities":["HG=F","GC=F"],"crypto":["BTC-USD","ETH-USD","MSTR","COIN"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"],"us":["TLT","GLD","VIX"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["nvda_ath_sustained","deepseek_adoption_spike","copper_above_4_50",
            "gold_above_3000","dxy_reverses_from_top","btc_breaks_consolidation","wifi_doubles",
            "elit_volume_spike","brms_bumi_volume_bludak","china_tech_index_3y_high"],
    ),

    # ── ARTICLE 6: Danantara SWF ────────────────────────────────────────────────
    NarrativeTemplate(
        name="Danantara — Indonesia Sovereign Wealth Fund ($900B AUM Target)",
        description="""Ricky2212 Danantara/Indonesia SWF framework:
WHAT IS SWF:
- Sovereign Wealth Fund = government-owned investment vehicle
- Manages surplus national income (oil, gas, commodities, forex reserves)
- Goals: economic stability, diversification, long-term returns, generational wealth
GLOBAL SWF LANDSCAPE:
1. Norway GPF Global: $1.4T (oil/gas) — top holdings: NVDA, MSFT, AAPL
2. China CIC: $1.2T (forex) — holdings: Blackstone, Morgan Stanley, Alibaba, Tencent, BUMI
3. Abu Dhabi ADIA: $850B (oil) — MSFT, GOOGL, AMZN, AAPL, JPM, GS, BLK
4. Kuwait KIA: $750B (oil) — pioneer SWF (1953)
5. Singapore GIC: $700B (forex)
6. Hong Kong HKMA: $600B (forex)
7. Saudi PIF: $700B (oil) — target $2T by 2030. SoftBank, Nintendo, Uber, Newcastle United
8. Singapore Temasek: $490B — DBS, Alibaba, Mastercard, Telkomsel
9. Qatar QIA: $450B — Volkswagen, Uber, SpaceX, PSG, F1, Tiffany
10. Dubai ICD: $300B — Emirates, Emaar, DP World
INDONESIA EXISTING:
- INA (Indonesia Investment Authority): ~$20B AUM (2021), infrastructure + renewable energy
DANANTARA (Dayā Anagata Nusantara):
- Launched Feb 24, 2025 by President Prabowo
- Consolidates INA + 7 BUMN:
    * Bank Mandiri, Bank BRI, PLN, Pertamina, Bank BNI, Telkom Indonesia, MIND ID
- Model: Similar to Temasek but broader (all state assets in one vessel)
- Target AUM: $900B (evaluasi awal)
- Initial funding: $20B
- Mandate: renewable energy, manufacturing, downstreaming, food security
- Target GDP contribution: 8% annual growth
- Leadership: Rosan Roeslani (CEO), Burhanuddin Abdullah (controversial — past corruption case)
RICKY'S ASSESSMENT:
- "Kalau dijalankan dengan baik = mampu bersuara di kancah global"
- "Saya selalu jadi pihak pesimis dulu untuk awal perjalanan"
- Risks: corruption mentality ("orang atas suka kemaruk and aji mumpung"), Jiwasraya/ASABRI history, 1MDB Malaysia precedent
- "Kalo salah urus, bukan jadi Temasek. Yang ada = kaya 1MDB."
- "Tapi apapun itu kita sambut DANANTARA sebagai buah karya luar biasa dari 08."
Key data: If $900B achieved = Indonesia becomes one of world's largest SWFs.""",
        category="geopolitical",
        catalyst_types=["danantara_launch","swf_indonesia","sovereign_wealth_fund","bumn_consolidation",
            "prabowo_policy","state_asset_optimization","corruption_risk_swf"],
        activation_keywords=["danantara","sovereign wealth fund","swf indonesia","ina swf","daya anagata nusantara",
            "danantara launch","danantara 900 billion","danantara aum","danantara bumn","mandiri danantara",
            "bri danantara","pln danantara","pertamina danantara","bni danantara","telkom danantara",
            "mind id danantara","rosan roeslani","burhanuddin abdullah","temasek model","swf comparison",
            "norway gpf","china cic","abudhabi adia","kuwait kia","singapore gic","saudi pif","qatar qia",
            "dubai icd","hong kong hkma","swf global ranking","danantara corruption risk","1mdb precedent",
            "jiwasraya asabri","prabowo swf","state asset consolidation","indonesia 8% gdp target"],
        invalidation_keywords=["danantara_cancelled","corruption_scandal_danantara","bumn_resist_consolidation",
            "danantara_aum_fails","prabowo_cabinet_no_danantara"],
        beneficiaries={"ihsg":["BMRI.JK","BBRI.JK","BBNI.JK","TLKM.JK","PTBA.JK","ANTM.JK","MEDC.JK"],
            "global":["EIDO","IDX"]},
        fades={"ihsg":["private_sector_competing_with_danantara"],"us":["swf_underperformers"]},
        regime_alignment={"Q1":1.40,"Q2":1.20,"Q3":1.00,"Q4":0.80},
        typical_duration_weeks=52,
        conviction_ceiling=0.75,
        pump_risk=0.20,
        confirmation_signals=["danantara_official_operations","900b_aum_roadmap","rosan_roeslani_appointment",
            "bumn_transfer_to_danantara_complete","renewable_energy_project_funding","international_investor_interest"],
    ),

    # ── ARTICLE 8+9: Market Come Back + 3 Jack Up Factors ───────────────────────
    NarrativeTemplate(
        name="Market Come Back — 3 Factors Driving Jack Up",
        description="""Ricky2212 market recovery & jack-up catalyst framework:
MARKET COME BACK CONFIRMATION:
- IHSG +3.97% (+249pt) to 6,519. Value: Rp 16T
- Banking-led: BBRI +9.23%, BMRI +6.52%, BBNI +5.71%, BBCA +4.45%
- 6,324 (ATH-20%) and 6,500 both reclaimed = "Full Body Cover" candle
- "Worstnya baru saja kita lewati Jumat."
- MSCI rebalancing complete = foreign selling pressure ends
- Morgan Stanley downgrade then upgrade = "typical positioning, sekutuan mereka"
- Fund local still skeptical = "mereka yang akan dorong indeks ke atas nanti"
- "Pungutin barang dari FULE di bawah, nanti mereka yang mengantarkan posisi anda ke atas."
- OJK called exchange members = "ada yang mau bergerak menjaga pasar"
3 FACTORS FOR STRONG JACK UP:
1. DXY WEAKNESS:
    - "DXY pelemahan jelas jadi support paling kuat buat dorong global market"
    - "USD kabur dari kandang, mencari tempat baru buat membenamkan uang"
    - Weak USD = global indices can run faster
2. JPY CARRY TRADE RESTART:
    - "JPY menguat significant = JPY mahal, USD lemah"
    - "Pinjam JPY (mahal), tukar ke USD (murah) = dapat USD lebih banyak"
    - "Investasi ke paper asset = kedorong harga"
    - "Carry trade sifatnya leverage = double shoot, kekuatan dorongan double"
3. LOCAL FUND SKEPTICS WITH CASH:
    - "Mayoritas Fund lokal masih sangat skeptis, menyimpan cash cukup lumayan"
    - "Fund lokal akan jadi mesin pendorong saat perjalanan hampir setengah jalan"
    - "Fund ga mau di out-perform satu sama lain. Pinter barengan atau Goblok barengan."
    - "Begitu satu memulai, yang lain membebek."
    - "Percaya? itulah kondisi fund lokal kita."
Ricky's call: "3 faktor tersebut menentukan kencangnya jack up. Kalau seirama dan berbarengan = mungkin yah begitulah."
"Data ekonomi mah nanti akan mengikuti dan menyelaraskan dengan aliran uang saja."
"Berita kan memang dibuat saat memang dibutuhkan."
"Ini Last Call super paling terakhir."
"Jack Up is for EXIT."""",
        category="cycle",
        catalyst_types=["market_come_back","dxy_weakness","jpy_carry_restart","local_fund_cash",
            "msci_rebalancing_end","banking_rebound","full_body_cover","foreign_inflow_return"],
        activation_keywords=["market come back","ihsg naik 3.97%","banking rebound","bbri 9%","bmri 6%",
            "full body cover","6324 reclaimed","6500 reclaimed","msci rebalancing complete","morgan stanley upgrade",
            "fule nadah","foreign inflow","3 faktor jack up","dxy weakness","usd kabur","jpy carry trade",
            "jpy menguat","carry trade restart","double shoot","fund lokal skeptis","fund cash",
            "fund mesin pendorong","pinter barengan goblok barengan","fund membebek","last call terakhir",
            "jack up factors","dxy support global","idr menguat","aliran uang masuk","ojk panggil bursa",
            "worst over","market recovery indonesia"],
        invalidation_keywords=["ihsg_breaks_6000","dxy_strengthens","jpy_weakens","fund_local_selling",
            "foreign_exodus_accelerates","banking_reversal"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BUMI.JK","BRMS.JK","WIFI.JK","MPIX.JK"],
            "fx":["USDIDR","JPY=X"],"us":["IWM","QQQ","BTC-USD"]},
        fades={"ihsg":["property","consumer_discretionary"],"us":["TLT","GLD","VIX"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["ihsg_sustains_above_6500","dxy_reverses_down","jpy_strengthens_above_145",
            "local_fund_net_buy_starts","foreign_net_buy_5days","banking_index_leads_3days",
            "msci_rebalancing_complete","idr_strengthens_below_16000"],
    ),

    # ── ARTICLE 10: Trump Tariff Shock Therapy ────────────────────────────────
    NarrativeTemplate(
        name="Trump Tariff Shock Therapy — Not the Main Show",
        description="""Ricky2212 Trump tariff framework: "It's not the main show."
2016-2020 DEJA VU:
1. Trump framed badly during campaign → Dow crashed on election night → Big Boyz: "Trump not as bad as thought" → massive come-back
2. Trump loves surprise Twitter policy announcements (weekend bombshells)
3. Trump loves tariff wars — 2016-2020 full of tariff policies
CURRENT TARIFFS (Feb 2025):
- Mexico: 25%
- Canada: 25%
- China: 10%
- Canada retaliates: 25% on US goods. Trudeau warns "painful times ahead."
- Mexico retaliates: 25% on US goods.
- China: "Anteng2x sambil duduk and makan gorengan dengan segelas teh panas" — watching US & allies fight
MARKET REACTION:
- Weekend tariff war → Monday shock therapy
- "Kena Flush secara massal. Ibarat closet, pencet tombol Flush = semua disapu bersih."
- "Panik? kalau menghadapi keadaan seperti ini aja sudah panik = harus ikut Mbasecamp."
- "Ini bukan real show penurunannya. Ini belum ada apa2x. Lebih ke short Shock Theraphy."
- "Kebayang ga nanti real show penurunannya?"
RICKY'S STANCE:
- Defensive mode from the start
- "Bermain cenderung lebih konservative dengan menaikkan porsi cash."
- "Kalau ada apa2x, saya masih bisa tersenyum."
- "Santai, tenang, main show nya belum datang."
- "Trump minta nego tuh sama yang kena tariff. Nanti pasti pada negoisasi ujungnya."
KONGLO PLAYS:
- "Om Alim, Om Agus, Om Roti aja belum manggung."
- "Ga kasian sama mereka yang on process siapin permainannya."
- "Siapin gorengan dan teh panas."
MBASECAMP:
- "History repeat itself — basecamp selalu sold out."
- "Daripada trade war, mendingan pikirin besok bakal tiket war."
Ricky's call: "Perjalanan sekarang bisa jadi proses ke sesuatu yang lebih besar di depan."
"Sudah siapkah anda?"
"Yah jack up dulu dunk. Last leg. Jangan lupa kalo ada jack nanti jangan lupa pulangnya."
Key insight: Trump tariff = negotiation tactic, not permanent war. Short-term flush, not the main crash.""",
        category="geopolitical",
        catalyst_types=["trump_tariff","trade_war","shock_therapy","mexico_tariff","canada_tariff",
            "china_tariff","retaliation","negotiation_tactic","weekend_bombshell"],
        activation_keywords=["trump tariff","trade war","shock therapy","not the main show","mexico 25%",
            "canada 25%","china 10%","trump twitter","weekend tariff","flush massal","closet flush",
            "trump dejavu","2016 2020 trump","trump campaign","dow crash election night","big boyz trump",
            "trudeau painful","canada retaliation","mexico retaliation","china anteng","china teh panas",
            "trade war negotiation","trump nego","defensive mode","main show belum datang","jack up dulu",
            "last leg","mbasecamp","tiket war","om alim","om agus","om roti","gorengan teh panas"],
        invalidation_keywords=["tariff_cancelled","trade_war_escalates","china_retaliates_hard",
            "permanent_tariff","trump_impeached"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","KLBF.JK"],
            "us":["TLT","GLD","VIX"],"safe_haven":["USD_cash","IDR_cash"]},
        fades={"ihsg":["export_oriented","auto_sector","consumer_discretionary"],"us":["IWM","high_beta"],
            "global":["trade_sensitive_sectors"]},
        regime_alignment={"Q3":1.30,"Q4":1.10,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=8,
        conviction_ceiling=0.75,
        pump_risk=0.20,
        confirmation_signals=["trump_tariff_announced","canada_retaliates_25","mexico_retaliates_25",
            "china_watches_passive","market_flush_monday","vix_spike_above_25","defensive_positioning_spike",
            "negotiation_signals_emerge"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 15 — Artikel Ricky2212 (Apr 2026 extraction)
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVES_BATCH15: List[NarrativeTemplate] = [

    # ── ARTICLE 11: Market Cetar Bergetar — IHSG Halt & Force Sell Cascade ─────
    NarrativeTemplate(
        name="Market Cetar Bergetar — IHSG Halt, Margin Call & Force Sell Cascade",
        description="""Ricky2212 market crash day analysis: IHSG -248pt to 6223, Halted at 11:09 WIB (-5%)
THE CASCADE:
- Group PP (BREN, TPIA) rontok barengan → indeks tertekan
- Banking tadinya bertahan menyeimbangkan indeks
- BREN & TPIA makin parah ditekan → MARGIN CALL di kedua saham tersebut
- Margin Call = posisi dilikuidasi at any price at that time
- Force Sell berlanjut → kepanikan merembet
- PANI tadinya anteng langsung ambrol hampir ARB → margin call juga
- Force Sell BREN + TPIA + PANI → posisi mengamankan semua saham lain (perbankan, big cap)
- Keadaan makin tidak kondusif → HALT indeks 30 menit
- Post-HALT: tambah kepanikan → sempat turun 7% → covering position → ditutup -3%
KEY INSIGHTS:
- "Market luar anteng2x aja bahkan menghijau dan hanya kita sendiri yang mengalami penurunan cukup dalam"
- IDR tidak jatuh mengikuti indeks = "Uang masih tetap di dalam pasar kita"
- "Market memang lagi merotasi uangnya dan coba menormalisasi saham2x ANEH yang gerakkin indeks"
- "Mereka mau seimbangkan lagi bobot investasinya"
- BI meeting minggu ini → possible BI Rate CUT
- "Market memang sudah minta BI rate buat di CUT karena BI lagging"
- "Happy? saya sih super tenang"
- "Banyak teman2x DM: Gila ini toh rasanya pegang cash saat kejatuhan market. Mereka siap dan dalam posisi loading peluru."
- "Yang nagih kapan jack up mulu, saya tau sudah tidak tenang dan tidak siap"
Ricky's call: "Belum and bukan sekarang waktu kejatuhannya koq, di luar saja masih anteng2x aja."
"Tunggu saja, nanti di luar akan datang narasi CUT akan keluar lebih banyak dan QT bakal dipercepat."
"Kaya hari ini penurunan market, andai anda sedikit tenang dan berpikir jernih saja nantinya anda akan tau kenapa terjadi penurunan hari ini"
"Buat yang pertama kali melihat market di HALT, selamat datang di real market."
"Disinilah peluang buat menaikkan Wealth Anda""",
        category="cycle",
        catalyst_types=["ihsg_halt","margin_call","force_sell","cascade_selling","group_pp_collapse",
            "bi_rate_cut_expectation","idr_stability","cash_is_king"],
        activation_keywords=["market cetar bergetar","ihsg halt","halt indeks","margin call","force sell",
            "bren margin call","tpia margin call","pani margin call","group pp rontok","bren tpia ambrol",
            "ihsg turun 248","ihsg 6223","halt 11.09","cooling down bursa","covid dejavu","market luar hijau",
            "idr tidak jatuh","uang masih di pasar","rotasi uang","normalisasi saham aneh","bi rate cut",
            "bi meeting","suku bunga bi","loading peluru","pegang cash","real market","first time halt",
            "wealth opportunity","panic selling indonesia","arb pani","force sell cascade"],
        invalidation_keywords=["ihsg_recovers_same_day","bren_tpia_rebound","margin_call_resolved",
            "bi_holds_rate"],
        beneficiaries={"ihsg":["BBCA.JK","BMRI.JK","BBNI.JK","TLKM.JK","UNVR.JK"],"safe_haven":["IDR_cash","USD_cash"]},
        fades={"ihsg":["BREN.JK","TPIA.JK","PANI.JK","high_margin_stocks","property"]},
        regime_alignment={"Q3":1.30,"Q4":1.10,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=4,
        conviction_ceiling=0.85,
        pump_risk=0.05,
        confirmation_signals=["ihsg_halt_triggered","bren_tpia_limit_down","pani_arb","margin_call_widens",
            "force_sell_spreads","bi_announces_emergency_meeting","idr_stable_during_crash"],
    ),

    # ── ARTICLE 12: Play Book IHSG — China Comparison & Policy Demand ─────────
    NarrativeTemplate(
        name="Play Book IHSG — China Playbook Comparison & Policy Demand",
        description="""Ricky2212 IHSG playbook framework via China historical parallel:
CHINA 2022-2024 PLAYBOOK:
- Awful economic news daily, almost no good data
- Stock market rontok ga tertahankan, index terkapar
- Bond market diburu, yield rontok to worst since GFC 2008
- Property market jatuh 80% from peak
- Big Boyz: bad reports and downgrades non-stop
- Big Boyz: massive outflow reports
- RMB rontok
- "Semua di paket di waktu yang sama. Diberondong dalam term waktu berbarengan."
- Market demanded something from policymakers
- "Market seakan-akan menginginkan sesuatu dan harus dipenuhi"
CHINA SOLUTION (Gradual):
- Policy packages launched from time to time
- Bottlenecks broken slowly
- "Bottle neck nya dipecah dengan baik dan perlahan sehingga apa yang buruk perlahan membaik"
- Fiscal expansion: deficit raised to 4% = ~$800B-$1T new money into system
INDONESIA NOW (Parallel):
- Bad economic news everywhere, financial market jatuh, stock market rontok
- FX market ga berdaya, bond market nyerah
- Big Boyz: bad analysis and downgrades on Indonesia
- "Saya melihat pola yang sama akan terjadi. Mereka menakan pemangku kebijakan untuk melakukan sesuatu."
- "Market ga minta makan siang Gratis, market ga minta danantara."
- "Market minta dosis yang lebih besar"
WHAT MARKET WANTS:
1. BI Rate CUT (Indonesia lagging on rate cuts)
2. Government boost economy → money circulation → consumer purchasing power
3. "Market ga minta makan siang Gratis, market ga minta danantara."
4. "Rasanya ini yang paling vital dan penting dan sifatnya urgent"
Ricky's target: "7900 ke 6000 mayan lah 25%, resiko selanjutnya ada di -30% plus."
"Risk reward nya makin terlihat reasonable buat saya untuk perlahan bermain sedikit offensive"
"LKH lahir dari kejatuhan market, Banyak Trilyuner lahir dari kejatuhan market"
"Pasar turun itu biasa saja, yang ga bikin jadi ga biasa kan kita sendiri"
"Pasar naik itu hanya masalah waktu saja setelah terjadi penurunan""",
        category="cycle",
        catalyst_types=["china_playbook","policy_demand","ihsg_bottoming","fiscal_expansion",
            "bi_rate_cut","government_stimulus","trillionaire_opportunity"],
        activation_keywords=["play book ihsg","china playbook","china comparison","policy demand",
            "market minta sesuatu","market meminta kebijakan","big boyz downgrade indonesia","bond yield rontok",
            "property jatuh 80%","rmb rontok","outflow massive","bottle neck dipecah","fiscal expansion",
            "defisit 4% china","indonesia parallel china","bi rate cut indonesia","lagging rate cut",
            "government boost economy","daya beli konsumen","danantara bukan solusi","makan siang gratis",
            "risk reward reasonable","offensive strategy","trilyuner lahir","lkh lahir","ihsg 6000",
            "ihsg 7900","minus 25%","minus 30%","bottom market","jack up is time"],
        invalidation_keywords=["china_playbook_fails","policy_ignored","bi_holds","government_inaction",
            "ihsg_breaks_5500"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","TLKM.JK","UNVR.JK","BUMI.JK"],
            "safe_haven":["IDR_cash","USD_cash","SBN"]},
        fades={"ihsg":["property","consumer_discretionary","high_flyer"]},
        regime_alignment={"Q3":1.20,"Q4":1.00,"Q2":0.80,"Q1":0.60},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["bi_announces_cut","government_stimulus_package","fiscal_expansion_indonesia",
            "china_style_recovery","big_boyz_upgrade_indonesia","foreign_inflow_returns","idr_strengthens"],
    ),

    # ── ARTICLE 13: Things happen when no one talk about it ─────────────────────
    NarrativeTemplate(
        name="Things Happen When No One Talks About It — Recession Calls & Blow Off Top",
        description="""Ricky2212 contrarian cycle framework:
HISTORICAL PATTERN:
- "If u want to see a Recession, no one talk about it"
- 2022: ALL Big Boyz screamed STAGFLATION → RECESSION. Media + Socmed all same thesis. Result? NO RECESSION.
- 2023: Same screams, even louder because rates went crazy high. Result? NO RECESSION.
- "Things Happen when no one talk about it"
TRUMP OPTIMISM TO PESSIMISM FLIP:
- Trump elected: world celebrated with extraordinary optimistic cheers
- "Banyak yang bilang Trump akan membawa perubahan"
- Post-inauguration: Trump executes planned policies (tariffs, immigration, DOGE cuts)
- "Seketika saja semua optimisme menghilang tanpa tersisa"
- Market sees all Trump policies bringing US to recession cliff
- Big Boyz: "this bakal RESESI nih kalo begini"
- Media: hyperbolic headlines — "Pertama kali dalam sejarah", "Terburuk sejak..."
- "Semua berlomba keluar dari pasar"
- Influencers who were super bullish now say "Cash aja dulu", "ini mau crash"
- "Katanya dulu zaman bullish, ini zamannya AI, Ga mungkin Crash"
FUND CASHING OUT:
- "Fund-fund sudah cashing out dengan kinerja YTD -40 - -50%"
- "Anda ga sendiri kalo memang dalam posisi buruk, fund aja segitu parahnya"
RICKY'S THESIS:
- "Simple sih buat saya, semoga tidak ada halangan di depan sana bahwa BLOW OFF the TOP akan datang."
- "Pesimisme berlebihan sudah datang dan mulai tidak ada optimisme yang tersisa lagi."
- "Kita sudah dekat pada fase Hopeless to Flawless"
- "Resesi and Deep Correction tuh ga akan datang saat semua sudah banyak yang bersiap."
- "Kalo sudah bersiap, lah siapa yang mau dimakan?"
BLOW OFF TOP SEQUENCE:
1. Skeptics see rally but don't believe it's real bull
2. Skeptics push market far toward euphoria
3. "Puncaknya? si skeptis akan mendorong jauh pasar menuju euforia"
4. At euphoria peak: deep correction arrives when no one expects it
- "Di titik Euforia itu biasanya nanti deep correction akan datang."
- "Semua lagi pada Euforia dan tidak siap menyambut hal tersebut"
- Nov 2024: clowns bullish, forgot reality before being swept to now
Ricky's call: "Things Happen when no one talk about it"
"Danantara pengurus: mayoritas fund happy dengan kepengurusan. Satu kekhawatiran terkikis.""",
        category="cycle",
        catalyst_types=["recession_call_fail","contrarian_cycle","blow_off_top","hopeless_to_flawless",
            "trump_pessimism_flip","fund_cash_out","euphoria_peak"],
        activation_keywords=["things happen when no one talk","recession call","stagflation 2022","recession 2023",
            "no recession","trump optimism","trump pessimism","blow off top","hopeless to flawless",
            "pesimisme berlebihan","tidak ada optimisme","fund cashing out","ytd minus 40%","ytd minus 50%",
            "cash aja dulu","mau crash","influencer flip","big boyz recession","media hyperbola",
            "pertama kali dalam sejarah","terburuk sejak","semua keluar pasar","fund parah",
            "blow off top sequence","skeptis dorong euforia","deep correction datang","nov 2024 dejavu",
            "danantara pengurus","fund happy danantara"],
        invalidation_keywords=["recession_confirmed","deep_correction_now","trump_dovish_pivot",
            "optimism_returns","fund_redeploys"],
        beneficiaries={"us":["SPY","QQQ","IWM"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK"],
            "safe_haven":["GLD","TLT"]},
        fades={"us":["SQQQ","VIX"],"ihsg":["property","high_beta"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":1.20,"Q1":0.90},
        typical_duration_weeks=20,
        conviction_ceiling=0.85,
        pump_risk=0.20,
        confirmation_signals=["recession_calls_peak","fund_cash_levels_high","vix_spike_then_calm",
            "trump_policy_executed","media_fear_index_max","influencer_bullish_to_bearish","danantara_resolved"],
    ),

    # ── ARTICLE 14: It's just a game — Market Manipulation Thesis ──────────────
    NarrativeTemplate(
        name="It's Just a Game — Market Manipulation & 08 Circle Thesis",
        description="""Ricky2212 market manipulation framework: "Permainan yang diciptakan"
THE STRUCTURED COLLAPSE:
- "Penurunan tambahan yang terjadi hanyalah sebuah dagelan and ada sebuah PERMAINAN yang diciptakan"
- "Wong kalo mau fair mah, dunia tuh semua lagi ga baik2x saja dan kebetulan market luar juga lagi bagus koq."
- "Cuma kita aja kayaagi 'Dikerjain' sendirian"
PLAYERS:
1. Big Boyz: "tiba2x saja terus barengan mendown grade pasar kita tanpa henti"
2. Media: "memperkeruh berita nya dengan bahasa2x menakutkan"
3. Sekuritas: "nyalahin Pemerintah — 'Tidak Peka', 'Tidak Care', 'Tidak ngerti pasar'"
4. Influencers: "akhir tahun lalu sok pada bullish taunya kecele. Suaranya keras banget katanya 08 bla bla"
- "Pahlawan kesiangan, AI nya mana? katanya ini zama AI"
- "Bermuara dan berujung pada sangkutter saham di pucuk yang kepalanya sudah panas"
08 IS A CAPITALIST:
- "08 itu seorang kapitalis, kapitalis itu pasti menyangkut pasar bebas termasuk bursa saham"
- Father of 08: "penganut super kapitalis, buka PKP2B, kontrak karya Freeport/Newmont/Inco, izin migas Exxon/Conoco — semua 1968"
- Brother of 08 ("bersin2x"): "orang lama di bursa, pernah punya perusahaan Tbk sejak dulu"
- Brother of 08: "baru saja menciptakan permainan di WIFI dan ikut Main di AADI"
- Circle: Tohir, Bakrie, H Isam, Luhut — all capitalists with many Tbk companies
- "Siapa yang datangin Dalio? rasanya itu andil 08 buat datangin Dalio ke Indonesia"
DANANTARA TIMING:
- "Danantara ? itu juga sepertinya ada andil agar danantara bisa masuk saat keadaan buruk"
- "Danantara adalah pertaruhan 08 yang paling besar"
- "Aneh nya sebagai SWF bukan mengambil dari kelebihan kas negara tapi SWF ini ngambil bagian asset dan anggaran negara"
CHECKLIST PATTERN:
- "Fund-fund akan dikumpulkan di istana" → CHECKLIST: done, invited to DEN
- "Riset baik yang keluar pasca semua dikumpulkan" → CHECKLIST: done, research released
- "Danantara Beres, mayoritas fund suka dan menerima tim di dalam nya"
- "Moneter ? nanti juga BI akan melakukan CUT rate dan CUT GWM"
- "Masalah pajak ? nanti juga keluar berita kalau penerimaan pajak di Maret juga akan improved"
- "Politik ? habis ini mingkem semua karena sudah selesai agendanya"
HIMBARA EX-DATE:
- "Tinggal 1 hal yang mungkin bisa mengerek market yaitu Ex-Date Dividen nya Himbara"
- BBRI DY 8%, BMRI DY 10%
- "Harus ada yang gendong nanti pas Ex date"
Ricky's call: "Its just a game, kalo bisa menebak arah permainannya terus kenapa harus khwatir?"
"Penurunan market yang di Create justru mendatangkan peluang buat kita."
"Jack up ? Jack down aja lah yah"
"Tanda2x ujung penurunan: volatilitas makin tinggi, big boyz downgrade""",
        category="geopolitical",
        catalyst_types=["market_manipulation","08_circle","danantara_timing","capitalist_play",
            "fund_istana_meeting","himbara_ex_date","checklist_pattern"],
        activation_keywords=["its just a game","market manipulation","permainan diciptakan","dikerjain sendirian",
            "big boyz downgrade","media menakutkan","sekuritas nyalahin pemerintah","influencer kecele",
            "08 kapitalis","08 bursa","dalio indonesia","wifi permainan","aadi permainan",
            "danantara pertaruhan 08","danantara masuk saat buruk","fund dikumpulkan istana",
            "den dewan ekonomi nasional","riset baik keluar","bi cut rate","cut gwm","pajak maret improved",
            "politik selesai","himbara ex date","bbri dividen 8%","bmri dividen 10%","gendong indeks",
            "jack down","ujung penurunan","volatilitas tinggi","big boyz downgrade ujung",
            "tanda bottom","market create peluang"],
        invalidation_keywords=["08_not_capitalist","danantara_fails","fund_rejects_danantara",
            "bi_no_cut","political_noise_returns"],
        beneficiaries={"ihsg":["BBRI.JK","BMRI.JK","BBNI.JK","BBCA.JK","WIFI.JK","AADI.JK"],
            "safe_haven":["IDR_cash"]},
        fades={"ihsg":["property","consumer_discretionary"],"us":["high_beta"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["fund_istana_meeting_confirmed","danantara_team_accepted","bi_cut_announced",
            "himbara_ex_date_smooth","tax_revenue_improved","political_silence","wifi_aadi_rally"],
    ),

    # ── ARTICLE 15: Different Game Play — Big Cap Banking vs Conglo Play ──────
    NarrativeTemplate(
        name="Different Game Play — Big Cap Banking vs Conglo Play",
        description="""Ricky2212 strategy framework: "Different game play, different treatment"
BIG CAP / BANKING GAME PLAY:
- "Penggerak indeks. Saat ada kenaikan indeks, saham2x ini yang akan banyak diincar oleh Dana besar"
- "Risiko yang melekat lebih rendah dibanding kita bermain Conglo Play"
- "Jangan juga berharap return yang Waahhh"
- "Bermain Big Cap seperti banking itu berharap perjalanan ekonomi membaik dan indeks ikut mengekor"
- "Offering Dividen sebagai penambah waktu tunggu nya"
- "Duduk manis dan Tidur tenang apalagi beli sahamnya saat kejatuhan kemarin"
- "Game play nya dari beli Big Cap: duduk manis, tidur tenang"
CONGLO PLAY GAME PLAY:
- "Pattern dipenuhi aksi corp action, financial engineering. Akan banyak akrobat yang terjadi di depan"
- "Tidak ada yang pasti semua corp action, akrobat and financial engineering nya akam berjalan 100% sesuai rencana"
- "Resiko yang lebih besar melekat pada saham tersebut"
- "Kalau perjalanannya sesuai rencana, tentunya ada reward yang besar menanti"
- "Akrobat tersebut nantinya akan merubah fundamental perusahaan secara keseluruhan yang akan mengerek harga cukup mumpuni"
- "Bermain Conglo play Karena banyak akrobat maka kita harus terus mencermati perkembangan yang terjadi"
- "at the end selama risk reward nya masuk yah bermain conglo play juga enak koq"
RICKY'S PORTFOLIO:
- Banking: "Saya ga milih koq, saya beli tuh semua Himbara saking bingung nya mana yang akan outperform nanti"
    * 3 state banks + 1 private bank (larger private allocation)
    * "Kenapa ga BBCA? penurunan nya ga terlalu dashyat dibanding Himbara yang memang sedang ada PERMAINAN"
- Conglo: "Beberapa Conglo Play saya masukkan ke dalam portdolio saya"
    * "Saya sempat dapat kepala 7x an dengan volume yang cukup lumayan besar"
    * "ada 1 konglo play lagi yang beda konglo, rasanya menarik karena faktor politik nya"
    * "Saudara Muda value transaksi menebal, saham merengsek naik"
- "Saya bermain di 2 Game play market. Market kedorong karena big cap yah saya ikutan, yah kalo conglo play sebagai Alpha bermain juga saya akan kebagian"
Ricky's wisdom: "MARKET MERAH adalah MARKET HIJAU yang TERTUNDA"
"Market kalau sudah jenuh dengan pesimisme, apa lagi yang tersisa? Market naik hanya masalah waktu saja."
"Pasar turun itu biasa saja, yang ga bikin jadi ga biasa kan kita sendiri"
"Bursa saham bukan tempat menjadi kaya secara cepat"
"Pegang cash itu adalah level dasarnya, tapi level lanjutannya adalah berani menembakkan cash saat ketakutan luar biasa sedang terjadi""",
        category="sector",
        catalyst_types=["big_cap_banking","conglo_play","dividend_play","corp_action","financial_engineering",
            "asymmetrical_risk_reward","dual_strategy"],
        activation_keywords=["different game play","big cap banking","conglo play","banking vs conglo",
            "penggerak indeks","dividend play","corp action","financial engineering","akrobat saham",
            "risk reward asymetris","himbara beli semua","bbca tidak dashyat","konglo alpha",
            "saudara muda konglo","market merah market hijau tertunda","pesimisme jenuh","market naik waktu",
            "level dasar cash","level lanjut tembak cash","dual strategy","2 game play",
            "duduk manis banking","tidur tenang banking","conglo monitoring","big cap low risk",
            "conglo high reward","financial engineering reward"],
        invalidation_keywords=["banking_leads_fails","conglo_corp_action_fails","dividend_cut",
            "asymmetrical_risk_breaks"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BUMI.JK","BRMS.JK","WIFI.JK"],
            "safe_haven":["IDR_cash"]},
        fades={"ihsg":["property","consumer_discretionary"]},
        regime_alignment={"Q3":1.30,"Q4":1.10,"Q2":0.90,"Q1":0.70},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["banking_index_leads","conglo_volume_spike","dividend_yield_attractive",
            "corp_action_announced","financial_engineering_executed","himbara_all_rally"],
    ),

    # ── ARTICLE 16: Trump will Trim and Reset US Economy ──────────────────────
    NarrativeTemplate(
        name="Trump Will Trim and Reset US Economy — Reaganomics 1981-1982 Parallel",
        description="""Ricky2212 Trump reset framework via Reaganomics historical parallel:
REAGAN 1981-1982 RESET:
- "Reset Ekonomi" created by Reagan → launched greatest bull market in history
- Stagflation: inflation 13.5% (1980), unemployment 7.5% (1980)
- Volcker: Fed Funds Rate to 20% (Jun 1981) to crush inflation
- Reaganomics:
    1. Economic Recovery Tax Act 1981: 25% income tax cut over 3 years
    2. Corporate tax cut to stimulate private investment
    3. Spending cuts (except defense +35% vs Soviet Union)
    4. Deregulation: energy, transport, banking
    5. Tight monetary policy maintained
- RESULT: Deep recession Jul 1981-Nov 1982
    * Unemployment 10.8% (Dec 1982) — highest since Great Depression
    * GDP contracted 6 quarters straight
    * Businesses collapsed due to high rates
    * Inflation fell: 13.5% → 3.2% (1983)
    * Deficit exploded: $74B (1980) → $208B (1983)
- POST-1982: Explosion
    * GDP growth 3.5%/year avg
    * Bull market 1982-2000: Dow +1,400% over 18 years
    * Unemployment down to 5.3% (1989)
DOW JONES 1981-1982:
- Opened 950-1,000 early 1981
- Aug 12, 1982: low 776.92 (-23% from early 1981)
- Dec 1982: closed 1,046 (+35% from Aug low)
TRUMP 2025 PARALLEL:
- "Tim Trump sengaja membiarkan ini terjadi. Mereka merancang reset ekonomi total"
- Shift from Biden government spending to private sector economy
- Bessent: "periode detoks" — detox period
- "Trump benar2x ga mau cebokkin Bidenomics"
- Trump focus: Treasury 10-year yield (not stock market like 2016-2020)
- Bessent: "Ekonomi yang kami warisi mungkin mulai goyah" = let the house of cards collapse
FISCAL REALITY:
- Pre-COVID: government spending 21% of GDP
- Now: 23% of GDP — highest outside COVID spike
- CRITICAL DATES:
    1. Aug 4: Congress recess → must pass laws
    2. September: government funding deadline
    * "Jika gagal? Pasar akan hancur lebur..."
- Bessent: "Akan ada periode detoks saat ekonomi beralih dari belanja pemerintah."
- "Gangguan" and "gejolak" expected during transition
TRUMP CLEANUP:
- DOGE: massive government employee cuts
- Immigration: all illegal immigrants returned
- Tariffs: Mega Reciprocal Tariff launched → weakens economy short-term
- "Trump mau lowering rate → all policies point to economic weakness alias RESET"
- "Ekonomi lemah → Disinflation → CUT rate → Weak USD"
- GDP Q1: 0.2% (Goldman Sachs), negative (Fed Atlanta)
Ricky's call: "Saat Base dari hancur tercipta dan sedikit saja ada improvement maka terasa ada perbaikkan"
"at the end Trump akan terlihat sebagai pahlawan"
"Trump ga mau cebokkin kerjaan biden. Sekalian gw bobrokin, nanti gw yang beresin tuh semua"
Key insight: 1982-style engineered collapse → reset → new bull market.""",
        category="geopolitical",
        catalyst_types=["trump_reset","reaganomics_parallel","mega_tariff","economic_detox",
            "government_spending_cut","deregulation","fiscal_crisis","weak_usd_intentional"],
        activation_keywords=["trump trim reset","reaganomics 1981","reaganomics 1982","reset ekonomi",
            "trump reset us economy","bessent detox","periode detoks","bidenomics cleanup",
            "government spending 23% gdp","congress recess august","government funding september",
            "house of cards collapse","doge cuts","immigration return","mega reciprocal tariff",
            "trump lowering rate","disinflationary path","weak usd intentional","gdp 0.2%",
            "fed atlanta negative","trump pahlawan","base hancur improvement","trump ga cebokkin",
            "trump bobrokin biden","1982 collapse pattern","dow 776 1982","bull market 1982 2000",
            "volcker reagan combo","defisit explode","reagan tax cut","supply side economics"],
        invalidation_keywords=["trump_reverses_policy","congress_blocks","funding_passed_smoothly",
            "economy_recovers_without_reset","tariff_cancelled"],
        beneficiaries={"us":["TLT","GLD","VIX"],"ihsg":["BBCA.JK","TLKM.JK","UNVR.JK"],
            "safe_haven":["USD_cash","IDR_cash"]},
        fades={"us":["SPY","QQQ","IWM","high_beta"],"ihsg":["property","consumer_discretionary"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=52,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["trump_tariff_executed","doge_cuts_announced","congress_recess_aug4",
            "funding_deadline_sep","treasury_yield_spike","gdp_negative_q1","unemployment_rises",
            "detox_period_confirmed"],
    ),

    # ── ARTICLE 17: Trump Tariff Good or Bad ──────────────────────────────────
    NarrativeTemplate(
        name="Trump Tariff — Good or Bad? Debt, Weak USD & Negotiation Tactic",
        description="""Ricky2212 tariff analysis framework:
IMMEDIATE REACTION:
- Stock market sell off
- US Bond market diburu, yield jatuh dalam
- Dollar jatuh melemah dalam
- Commodities jatuh dalam
- Big boyz: "this is bad, this is insane, Trump make a stupid decision"
- Nasdaq hampir kena HALT
US DEBT REALITY:
- US debt: $36 Trillion
- Interest payment: ~$1 Trillion/year
- Deficit: ~$1 Trillion/year
- Total annual deficit potential: $2T+/year
- "4 tahun kemarin tuh ekonomi amrik di dorong oleh genjotam fiskal yang luar biasa"
- "Negara harus merelakan fiskalnya jebol buat memompa ekonomi"
- "Fiskal dijebolin, mereka harus terus gali hutang"
- "FFR ga bisa turun karena mereka harus menggali hutang lewat UST dalam jumlah besar"
- "Cost bunga gede? makin jebol tuh hutang mereka"
TARIFF AS TOOL:
- "Tariff yang dilucurkan oleh Trump itu adalah sebuah tools buat menambah pemasukkan negara"
- "More Tariff means more income buat negara. More income, balance sheet terbantu."
- Fairness argument: "Amrik aja masukkin barang ke negara lo pada dikenain tariff yang lebih tinggi dari lo pada masukkin barang ke kita"
- "Fair bukan? itu kata amrik begitu"
TRUMP'S HIDDEN AGENDA:
1. Force Fed to CUT:
    - "Tariff mempercepat pelemahan ekonomi terjadi dan itu yang memamg Trump mau"
    - "Dengan pelemaham ekonomi yang terjadi maka Bank sentral harus melakukan sesuatu"
    - "Many times Trump minta sama Fed buat turunin bunga and Fed insist"
    - "Trump mau patokan refinancing nya UST 10 years notes"
    - "Trump memaksa Fed juga menurunkan FFR nya dengan menekan ekonomi Amrik jatuh"
    - $8-10T debt refinancing due mid-2025
2. Weak USD:
    - "We need Weak Dollar" — Trump repeated
    - Lutnick: "if Dollar is Cheaper, it will be easier to export"
    - Weak USD = US products look cheap internationally
    - "Trump and US butuh weak USD"
    - Post-tariff: DXY keok, EUR +2%
3. Shift to Private Sector:
    - "Trump mau memindahkan ekonomi yang tadinya dari Govt spending zaman biden ke private spending"
    - "Dengan banyak melibatkan swasta, manufaktur akan berjalan kembali"
    - "Pabrik bakal banyak dibangun dan tenaga kerja akan terserap banyak kembali"
4. Negotiation Tactic:
    - "Trump adalah negoisator ulung dan Tariff itu adalah salah satu cara dia untuk membuka negoisasi"
    - "Trump CAPER pake tariff agar negara lain mau duduk bareng bicara"
Ricky's view: "Saya bukan Trump Fans yah, saya hanya coba menarik apa yang Trump pikirkan"
"Trump bilang dengan santai bahwa stock market will BOOM"
Key data: Tariff = short-term pain for long-term structural fix + negotiation leverage.""",
        category="geopolitical",
        catalyst_types=["trump_tariff_analysis","us_debt_crisis","weak_usd_strategy","fed_forced_cut",
            "negotiation_tactic","fiscal_restructuring","private_sector_shift"],
        activation_keywords=["trump tariff good or bad","trump tariff analysis","us debt 36 trillion",
            "bunga hutang 1 trilyun","fiskal jebol","tariff tools","tariff income","fairness tariff",
            "trump force fed cut","trump weak dollar","lutnick dollar cheaper","dxy keok","eur menguat",
            "private spending shift","manufacturing revival","trump negotiator","tariff negotiation",
            "capper tariff","stock market will boom","ust refinancing 8 trilyun","ust 10 years",
            "bessent refinancing","trump hidden agenda tariff","tariff short term pain","long term structural fix"],
        invalidation_keywords=["tariff_reversed","fed_holds_rates","usd_strengthens_post_tariff",
            "negotiation_fails","debt_default"],
        beneficiaries={"us":["TLT","GLD","VIX"],"ihsg":["BBCA.JK","TLKM.JK","UNVR.JK"],
            "fx":["EURUSD","USDJPY"],"safe_haven":["USD_cash","IDR_cash"]},
        fades={"us":["SPY","QQQ","IWM","export_oriented"],"ihsg":["auto_sector","export_oriented"],
            "global":["trade_sensitive"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["tariff_revenue_spike","dxy_falls_below_100","fed_signals_cut",
            "negotiation_meetings_scheduled","manufacturing_orders_rise","ust_refinancing_successful"],
    ),

    # ── ARTICLE 18: DxY Hancur Rp Lemah — Inflow Signal & BBRI Ex-Date ────────
    NarrativeTemplate(
        name="DxY Hancur, Rp Lemah — Inflow Signal & BBRI Ex-Date Setup",
        description="""Ricky2212 DXY/IDR framework: "DxY hancur, Rp koq lemah?"
DXY COLLAPSE:
- DXY below 100
- EUR 1.13, JPY 142, CHF 0.84, GBP 1.30
- "Dollar keok se keok keoknya. Thanks to Trump action"
WHY IDR STILL WEAK:
- "Satu dunia sudah tau semua lagi pada mengalami keadaan buruk"
- "Kalo saya sih karena tau satu dunia lagi dihadapkan pada keadaan yang buruk, maka saya kan memilih untuk taro uang ke negara yang punya kekuatan lebih"
- Developed markets (EUR, GBP, CHF, JPY) get inflow first = "pilihan terbaik dari yang terburuk"
- "Dari waktu ke waktu kerasa koq shifting-an nya keluar dari US"
- Indonesia not yet getting massive inflow = "Rupiah jadi mata uang yang lagging"
- "Dengan Lagging nya Rupiah otomatis bursa kita juga masih tersendat2x naiknya"
THE SHIFTING SIGNAL:
- "Chance besar sih bakal ada aksi lanjutan dari Trump"
- "Bond US habis dikerjain sehingga Yield nya sempat naik kembali"
- "Kalo mau terus menekan Fed untuk menurunkan FFR nya, UST yield nya harus juga ditekan lagi"
- "DxY makin keok dari sekarang, Penguatan Rupiah hanya masalah waktu saja"
- "Psikologi pasar akan mengantarkan pada keadaan dimana pokoknya pegang apa saja asal jangan pegang USD"
- IDR target: 16,300-16,400 (initial strengthening)
- "Penguatan Rupiah sedikit saja akibat inflow tentu nantinya akan mendorong indeks saham kita untuk naik"
- "IHSG butuh inflow dan penguatan Rupiah agar dapat tenaga baru"
- "Indeks naik bukan karena ekonomi Indonesia membaik tapi indeks naik karena dapat aliran dana yang kabur dari US"
BBRI EX-DATE SETUP:
- "Hari ini ex date nya BBRI cukup smooth dengan sebuah Set Up dengan balancing saham pak PP"
- "Beberapa hari lalu saham2x satpol PP dibikin jatuh tersungkur parah dulu agar pada waktunya dibutuhkan saham tersebut rally nya dari base bawah"
- "Rally nya dari base bawah maka rallynya bisa dibikin dengan kenaikan yang cukup besar"
- "Sinyal clear ke 2 makin memperlihatkan bahwa ada yang mencoba pertahanin indeks saat big bank melewati masa2x ex date nya"
- BMRI ex-date Monday next = watch for smoothness
Ricky's call: "Every Deep Is a Buying"
"Saya akan berbelanja setiap penurunan dan kalaupun masih jatuh saya akan atur nafas saya sampai titik terburuk -35%"
"Kayu api nya mas @tomhardi kayanya masih on track. Apalagi DxY kaya begini."
Key data: DXY below 100 = first clear signal. IDR lagging = opportunity still open.""",
        category="cycle",
        catalyst_types=["dxy_collapse","idr_lagging","inflow_signal","bbri_ex_date","satpol_pp_balance",
            "developed_market_rotation","trump_continued_pressure"],
        activation_keywords=["dxy hancur","dxy below 100","rp lemah","idr 16800","dxy 98","dxy 99",
            "euro 1.13","jpy 142","chf 0.84","gbp 1.30","shifting keluar us","pilihan terbaik terburuk",
            "rupiah lagging","bursa tersendat","trump aksi lanjutan","ust yield ditekan","idr 16300",
            "idr 16400","inflow indonesia","ihsg naik inflow","bbri ex date smooth","satpol pp jatuh dulu",
            "rally base bawah","bmri ex date","every deep is buying","beli setiap turun","atur nafas",
            "titik terburuk minus 35%","tomhardi kayu api","china balas tarif 125%","it wont go higher"],
        invalidation_keywords=["dxy_reverses_above_100","idr_weakens_above_17000","bbri_ex_date_crash",
            "trump_stops_tariff","inflow_fails"],
        beneficiaries={"ihsg":["BBRI.JK","BMRI.JK","BBCA.JK","BREN.JK","TPIA.JK","PANI.JK"],
            "fx":["USDIDR"],"safe_haven":["IDR_cash"]},
        fades={"ihsg":["property","consumer_discretionary"],"us":["DXY","USD_cash"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["dxy_sustains_below_100","idr_strengthens_to_16400","bbri_ex_date_smooth",
            "bmri_ex_date_smooth","foreign_net_buy_starts","satpol_pp_rebounds","china_tariff_settled"],
    ),

    # ── ARTICLE 19: World Need Another Store of Value ───────────────────────────
    NarrativeTemplate(
        name="World Needs Another Store of Value — BRICS Commodities vs US BTC",
        description="""Ricky2212 Store of Value framework:
BRETTON WOODS COLLAPSE:
- Pre-1971: countries could only print money if backed by gold
- "Negara maju yang dimulai oleh Amrik... mau cetak yang dalam jumlah massive, maka sistem bretton woods runtuh"
- Since then: money printed based on TRUST (ability to pay debts)
- "Setiap lembar uang yang dicetak itu mengandung hutang"
CURRENT DEBT CRISIS:
- Global debt now exceeds pre-Great Depression levels
- US: $36T debt, $1T interest/year, $1T deficit/year = $2T+ annual deficit potential
- EU, England, Japan, Swiss: same super-jumbo debt problem
- "Makin tinggi jumlah hutang nya, makin dipertanyakan kemampuan membayat hutangnya"
- "Level TRUST terhadap FIAT sudah terus menurun terutama USD"
GOLD RALLY EXPLAINED:
- "Bukan harga emas yang naik gila2x an sih tepatnya, tapi nilai mata uang nya yang terus menurun"
- "Dari waktu ke waktu nilai uang terus turun karena terus dicetak secara massive"
- "USD and mata uang negara kuat lainnya perlahan akan tergeser dominasinya"
BRICS STRATEGY:
- "China dan alinsi BRICS sadar akan hal tersebut"
- "Mereka dengan segera bilang bahwa kita akan kembalikan sistem keuangan pada sistem lama Bretton Woods"
- "Uang yang dicetak harus di back up oleh sesuatu yang bernilai"
- Gold: primary backup for BRICS currencies
- "Emas makin kesini makin shortage, karena new investment nya juga rendah sekali"
- Other stores: silver, platinum, rare earth, copper, oil, industrial metals
- "China and BRICS akan bermain di level komoditas sebagai Store of Value mereka"
US STRATEGY:
- "Amrik tau koq dia juga bakal kehilangan nilai mata uang nya secara massive"
- "Amrik harus bikin mainan baru dan ciptakan hegemoni selanjutnya"
- Trump & Bessent: "BTC sebagai Reserve mereka"
- "Amrik akan ambil permainan lain buat Store of Value nya"
- Steps:
    1. Massive crypto regulation
    2. Fiat USD on blockchain
    3. US starts investing in BTC massively
    4. "Dunia akan juga perlahan mengikuti langkah Amrik"
    5. Free tax for US-made coins
    6. "Amrik sudah menciptakan permainan dan hegemoni baru"
BTC AS RESERVE LOGIC:
- "BTC stay anteng2x saja" during massive risk-off = institutional support
- "Harusnya kalo Risk off tingkat tinggi begitu, harga BTC juga free fall"
- "Harusnya mungkin sudah di level $40k an"
- Volatility declining over time:
    * Regulation improving
    * Market cap growing (mature market)
    * If adopted by countries = even less volatile
Ricky's call: "China and BRICS akan memanfaatkan Komoditas sebagai Store of Value mereka"
"Amrik and cs akan memanfaatkan BTC sebagai store of value mereka"
"Komoditas akan naik bukan karena real demand supply, tapi karena dunia butuh Store of Value"
"Salim lapar komoditas? Kayanya Salim tau akan hal ini""",
        category="geopolitical",
        catalyst_types=["store_of_value","brics_commodities","btc_reserve","bretton_woods_2",
            "fiat_distrust","gold_shortage","us_crypto_hegemony","debt_crisis_global"],
        activation_keywords=["world need store of value","bretton woods collapse","brics commodities",
            "btc strategic reserve","fiat distrust","trust terhadap fiat","us debt 36 trillion",
            "global debt great depression","gold shortage","emas shortage","china brics store of value",
            "silver platinum rare earth","copper oil industrial metal","trump btc reserve","bessent btc",
            "us crypto hegemony","fiat usd blockchain","free tax crypto us","coinbase sp500",
            "btc volatility decline","btc mature market","btc institutional","salim komoditas",
            "salim lapar komoditas","emas naik bukan demand supply","store of value demand",
            "usd kehilangan dominasi","mata uang tergeser","trust menurun"],
        invalidation_keywords=["brics_abandons_gold","btc_banned_us","fiat_trust_restored",
            "debt_crisis_resolved","gold_supply_surge"],
        beneficiaries={"global":["GC=F","HG=F","SI=F","PL=F","BTC-USD","ETH-USD"],
            "ihsg":["ANTM.JK","MDKA.JK","BRMS.JK","AMMN.JK","PTBA.JK","MEDC.JK"],
            "us":["NEM","GOLD","AEM","MSTR","COIN","GLD"]},
        fades={"us":["SPY","QQQ","high_beta"],"ihsg":["property","consumer_discretionary"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=52,
        conviction_ceiling=0.85,
        pump_risk=0.15,
        confirmation_signals=["brics_gold_backed_currency","us_btc_reserve_announced","btc_etf_volume_surge",
            "gold_premium_spike","central_bank_gold_buying","crypto_regulation_us_passed"],
    ),

    # ── ARTICLE 20: DxY sudah 98 — Time to Shifting ───────────────────────────
    NarrativeTemplate(
        name="DxY Sudah 98 — Time to Shifting to Risk Assets",
        description="""Ricky2212 DXY 98 framework: "Time to shifting?"
DXY AT 98:
- "DxY hancur memang sesuatu yang dari awal harusnya terjadi"
- "Faktor Trump lewat tariff pingin banget USD nya lemah"
- "Fiat itu about TRUST dan sekarang TRUST terhadap FIAT sudah terus menurun terutama USD"
- "Trump butuh weak USD karena Trump tau bahwa Amrik sudah ga bisa berkompetisi dalam hal cost production"
- "Agar barang mereka bisa tetap berkompetisi dan seakan-akan murah di pasaran, nah tuh USD nya dilemahkan"
SHIFTING CONFIRMATION:
1. CURRENCIES:
    - EUR, CHF, GBP, JPY all strengthened vs USD
    - "Pilihan terbaik dari yang terburuk"
    - "At the end nanti mereka akan GELI buat pegang USD dan akhirnya tuh USD akan melanglang buana"
    - "Nanti juga Rupiah kebagian koq. Rp gerak dikit aja ke 16300 an, tuh IHSG dah kaya apa ngacirnya"
2. COMMODITIES:
    - Gold: "asset ini adalah tempat paling utama buat mengamankan saat penurunan nilai mata uang"
    - "Apakah yang lain akan menyusul? kemungkinan besar IYA"
    - "Semua yang mempunyai nilai akan menyusul"
    - "Komoditas bukan lagi permainan real supply demand, tapi nanti komoditas akan bermain pada level Store of Value"
    - "Saham komoditas terlihat lebih solid, ada pergerakan yang positif"
3. EQUITIES:
    - "Dow mengalami penurunan tajam, bursa saham dunia terlihat ada sedikit perlawanan dan membentuk base yang solid"
    - "IHSG ga jeblok dalam bahkan kadang naik saat Dow malah nyungsep"
    - LATAM ETFs outperform and green vs Dow
    - "Bukankah itu sinyal shifting?"
4. CRYPTO / BTC:
    - "Kejatuhan pasar saham akibat tariff kemarin, harusnya bisa membuat BTC hancur luluh lantah"
    - "Harusnya kalo bener mau dihancurkan, BTC tuh sudah di level $40k an sekarang"
    - "BTC cukup bertahan saat kehancuran kemarin"
    - "BRICS akan bermain komoditas sebagai store of Value, Amrik? mana mau dia kalah"
    - "Trump akan ciptakan permainan ala amrik di risk asset tersebut buat cover penurunan USD nya"
    - "Trump bisa saja menggunakan BTC seakan-akan itu store of value buat mereka"
CRISIS & BLOW OFF TOP:
- "Crisis? belum sih, penurunan kemarin saya bisa bilang itu bukan main show crisisnya"
- "Tapi itu adalah awal perjalanan menuju Main Show nya"
- "Blow off the TOP? kalo pada shifting ke risk asset dan memompa risk asset, apa jadinya?"
- "Apalagi kemungkinan UST akan terus coba dipaksa diturunkan agar nanti narasi CUT bisa akan terus digaungkan"
Ricky's call: "Makanya lagi2x saya setuju nih sama konsep nya mas Tom tentang kayu api nya. Sepertinya keadaan berpihak kesana."
"Paling enak taro dimana? saham yang related sama STORE of VALUE tapi ada tambahannya yaitu narasi konglo Circle 08"
Key data: DXY 98 = shifting point. Risk assets will benefit from USD exodus.""",
        category="cycle",
        catalyst_types=["dxy_98","shifting_risk_assets","commodity_store_of_value","equity_base_forming",
            "btc_resilience","latam_outperform","usd_trust_decline"],
        activation_keywords=["dxy 98","dxy sudah 98","time to shifting","dxy hancur","usd trust decline",
            "fiat trust decline","eur menguat","chf menguat","gbp menguat","jpy menguat","geli pegang usd",
            "usd melanglang buana","rupiah 16300","ihsg ngacir","gold store of value","commodity shifting",
            "saham komoditas solid","dow turun bursa dunia perlawanan","ihsg naik dow turun","latam etf outperform",
            "btc bertahan","btc 40k harusnya","brics commodities","amrik btc store of value","trump btc play",
            "crisis belum main show","blow off top shifting","ust dipaksa turun","narasi cut digaungkan",
            "tomhardi kayu api","konglo circle 08","store of value saham"],
        invalidation_keywords=["dxy_reverses_above_100","risk_assets_fall","commodity_corrects","btc_breaks_50k",
            "usd_strengthens"],
        beneficiaries={"ihsg":["ANTM.JK","MDKA.JK","BRMS.JK","BUMI.JK","BBCA.JK","BBRI.JK","WIFI.JK"],
            "global":["GC=F","HG=F","BTC-USD","ETH-USD","EEM","ILF"],"fx":["EURUSD","USDJPY"]},
        fades={"us":["DXY","USD_cash","TLT"],"ihsg":["property"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=16,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["dxy_sustains_below_98","gold_rally_broadens","copper_breaks_out",
            "btc_holds_above_80k","latam_etf_sustained_outperform","ihsg_decouples_from_dow",
            "idr_strengthens_toward_16300"],
    ),

    # ── ARTICLE 21: Market bakal jatuh dalam — Buying Opportunity ──────────────
    NarrativeTemplate(
        name="Market Bakal Jatuh Dalam — Buying Opportunity & Cash Wins",
        description="""Ricky2212 crash-day buying framework:
THE MINDSET FLIP:
- "yihaaa, horaayyy teriakan2x menghiasi pasar saat bullish" → now silent
- "gimana kalo saya yang berteriak paling keras? Yihhhhaaaaa, horaayyyyyyy, this is the time"
- "Lo akan dapat daging dari segala dagingnya"
- "Imagine di luar sana berserakan perusahaan bagus yang lo bisa beli kapan"
- "Lo ditawarkan dengan harga yang terus berubah lebih rendah tiap hari"
- "Pasar menawarkan harga diskon ke anda tiap hari tanpa henti"
- "Selamat datang di real market"
THE MACRO REALITY:
- "Tenang, ini temporary saja koq. Market lagi minta sesuatu ama Fed"
- "Tinggal nunggu aja Fed kasihnya kapan"
- "Ekonomi tuh memang sudah lemah dan menuju RESESI sebelum Tariff itu datang"
- "Powell benar2x jauh behind the Curve nya"
- "Tariff mempercepat tuh semua prosesnya. Dimajuin semua prosesnya"
- "Ga usah nebak2x kapan CUT nya, CUT akan terjadi dan akan dipaksa terjadi oleh Market"
- "Ga usah nebak2x berapa kali CUT nya, karena butuh dosis yang cukup"
THE STRATEGY:
1. TETAP WARAS:
    - "Bagi anda yang pegang cash sejatinya anda sudah selangkah menang di depan"
    - "Tapi ingat itu baru langkah awal saja"
    - "Langkah selanjutnya yang penting adalah keberanian anda menembakkan uang anda pada waktunya"
    - "Kalo anda ga waras dan ketakutan terus, ga akan pernah tuh nanti anda menembak pelurunya"
2. JANGAN GEGABAH:
    - "Jangan terlalu gegabah berbelanja dengan menembakkan peluru secara langsung dan simultan"
    - "Hari ini murah, besok bisa lebih murah lagi"
    - "Dow and SPX akan dipaksa turun mengejar koreksi bear market nya"
    - "Nasdaq and IWM sudah duluan dihukum koreksi bear market"
    - "Market juga ada potensi terus ditekan untuk menekan central bank melakukan sesuatu dengan cepat"
3. PILIH SAHAM BERCERITA:
    - "Pilih saham yang punya cerita yang bisa menyokong nanti pas come back market"
    - "Dalam kondisi begini akan banyak sekali pilihan di depan anda"
THE ROADMAP:
- "Kemungkinan come back nya nanti luar biasa tapi belum jadi next new cycle"
- "Ini come back buat mengejar peaked market"
- "Narasi CUT akan muncul dan akan digaungkan sebentar lagi"
- "Nanti juga makin massive gaungan CUT nya"
- "CUT fase ini akan mendorong indeks menuju peak, sebelum nanti ada gelombang market minta CUT selanjutnya"
Ricky's call: "Selamat berburu saham pilihan anda"
"Prepare not Predict""",
        category="cycle",
        catalyst_types=["market_crash_buying","cash_is_king","bear_market_correction","fed_forced_cut",
            "dip_buying","fear_opportunity","peaked_market_comeback"],
        activation_keywords=["market bakal jatuh dalam","buying opportunity","crash buying","real market",
            "harga diskon tiap hari","berserakan perusahaan bagus","daging dari segala daging","temporary saja",
            "market minta fed","powell behind the curve","tariff percepat proses","cut dipaksa market",
            "dosis cukup cut","tetap waras","pegang cash menang","keberanian menembakkan uang",
            "jangan gegabah","hari ini murah besok lebih murah","dow spx bear market correction",
            "nasdaq iwm bear market","pilih saham bercerita","come back peaked market",
            "narasi cut muncul","cut fase peak","selamat berburu saham","prepare not predict"],
        invalidation_keywords=["market_recovers_immediately","no_fed_cut","crash_continues",
            "liquidity_crisis"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BUMI.JK","BRMS.JK","TLKM.JK"],
            "us":["SPY","QQQ","IWM"],"safe_haven":["IDR_cash","USD_cash"]},
        fades={"ihsg":["property","high_flyer"],"us":["high_beta","meme_stocks"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["market_sustains_fear","cash_levels_high","fed_signals_emergency_cut",
            "dip_buying_volume_spike","bear_market_technical","vix_above_30","ihsg_rebounds_from_low"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# BATCH 16 — Artikel Ricky2212 (Apr 2026 extraction)
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVES_BATCH16: List[NarrativeTemplate] = [

    # ── ARTICLE 22: Next Conglo Narrative (Narasi 9 Haji) ─────────────────────
    NarrativeTemplate(
        name="Next Conglo Narrative (Narasi 9 Haji) — Tohir, Bakrie, H Isam Circle",
        description="""Ricky2212 conglo rotation framework: "Narasi 9 Haji"
THE SHIFT:
- Old conglo narratives fading:
    * Satpol PP (BREN, TPIA): "narrative konglo dari group satpol PP perlahan sudah mulai memudar"
    * "Beberapa Fund sudah KAPOK dan mulai meninggalkan Group Konglo satpol PP"
    * AMMN: "keliatan banget sudah selesai agendanya"
    * DCII: "mulai ga masuk akal banget, perusahaan dengan laba secuil bisa dihargai Rp 400-500 trilyun"
    * PANI: "pasca dirundung masalah pagar bambu juga perlahan mulai memudar pamor nya"
    * "Yang katanya kuncen nya juga sudah kabur dari permainan"
- "Likuiditas nya juga akan mengikuti pergeseran ke conglo narrative yang baru"
NEW SUPER STARS — 08 CIRCLE:
1. TOHIR:
    - "Keluarga Tohir ga dekat sama keluarga 08. Bahkan tambang ADRO tohir adalah tambang milik adik 08 yang dipaksa diambik saat adik 08 ketiban masalah saat krisis 1998"
    - "Deal bussiness bernilai trilyunan" — AADI spin-off with 08 brother getting cheap shares
    - AADI has IUPK license, benefited from royalty/PNBP changes
    - ADRO/ADMR: "mau masuk bisnis nuklir (masih desas desus)"
    - "Group konglo Tohir jadi salah satu yang dapat jatah bisnisnya"
2. BAKRIE:
    - "Jasa keluarga bakrie sangat besar buat 08. Saat pemilu 2014 dan 08 maju ikut kontestasi, keluarga bakrie jadi salah satu penyokong besar"
    - "08 ga akan melupakan jasa dari keluarga bakrie"
    - Salim collaboration with Bakrie (knowing Bakrie is close to 08)
    - Coal royalty changes benefited Bakrie mines
    - WSKT toll road concession acquisition = first step into economic arena
    - Anin (Bakrie) leads KADIN = "mengkudeta keluarga Arsyad yang dekat dengan si merah"
    - "Jangan kaget nanti akan banyak akusisi dari konglomerasi ini"
3. H ISAM (Haji Andi Syamsudin Arsyad):
    - Banjarmasin/Kalsel coal entrepreneur
    - 2001: learned from Johan Maulana
    - 2003: CV Jhonlin Baratama at PT Arutmin Indonesia (Bakrie's Bumi Resources)
    - Now PT Jhonlin: 400k tons/month coal, Rp 40B/month revenue
    - Diversified: Jhonlin Air Transport (2 Fokker, 2 helis), Jhonlin Marine (16 barges), Jhonlin Agromandiri (palm oil), Jhonlin Agri Raya (biodiesel Rp 2T)
    - Collaboration with Bamsoet (Bambang Soesatyo) in PT Kodeco Timber (HTI + HPH)
    - "Haji Isam jadi salah satu penyokong besar buat kampanye pilpres 08 kemarin"
    - Family in government: Amran Sulaiman (minister)
    - Just acquired TEBE (mining services company)
    - "Kemudahan2x nantinya akan dinikmati oleh Haji Isam dalam berbisnis"
WIFI CONTINUATION:
- "Perhatikan juga gerak gerik adiknya 08. Sepertinya akan banyak WIFI-WiFI baru yang diambil oleh adiknya 08"
- "WIFi sih buat saya belum selesai sampai disini"
- "Kalo sudah diambil, mudah koq ke depannya. Tinggal dibikin perubahan regulasi agar perjalanan usahanya lancar"
Ricky's call: "Conglo yang akan kebagian adalah conglo yang mempunyai kedekatan dengan pusaran 08"
"Saham apa yang punya relasi dengan 3 konglo diatas? nah tinggal rajin2x mencari deh tuh"
"Cari yang belum pernah ada masalah kena FCA atau kena masalah sempritan dari regulator"
"Aliran uang kuat bakal lari kesana dengan kuat"
"No price action question, no perusahaannya apa aja question""",
        category="sector",
        catalyst_types=["conglo_rotation","narasi_9_haji","08_circle","tohir_play","bakrie_play",
            "h_isam_play","regulatory_favor","wifi_new","conglo_super_star"],
        activation_keywords=["next conglo narrative","narasi 9 haji","tohir konglo","bakrie konglo",
            "h isam konglo","08 circle","aadi tohir","adro nuklir","bakrie wskt","anin kadin",
            "jhonlin baratama","tebe acquisition","amran sulaiman","bamsoet kodeco timber",
            "wifi baru adik 08","regulasi lancar","konglo dekat 08","fund kapok satpol pp",
            "ammn selesai","dcii tidak masuk akal","pani pagar bambu","kuncen kabur",
            "likuiditas pergeseran","super star konglo","fcA clean","regulator semprit clean",
            "aliran uang konglo","no price action question"],
        invalidation_keywords=["08_distance_denied","tohir_bakrie_isam_fade","regulatory_crackdown",
            "wifi_fails"],
        beneficiaries={"ihsg":["AADI.JK","ADRO.JK","ADMR.JK","WSKT.JK","TEBE.JK","WIFI.JK","WIRG.JK"],
            "conglo":["BUMI.JK","BRMS.JK","MPIX.JK"]},
        fades={"ihsg":["BREN.JK","TPIA.JK","PANI.JK","DCII.JK","AMMN.JK"]},
        regime_alignment={"Q1":1.50,"Q2":1.30,"Q3":1.10,"Q4":0.90},
        typical_duration_weeks=52,
        conviction_ceiling=0.75,
        pump_risk=0.25,
        confirmation_signals=["aadi_rally","adro_nuclear_news","wskt_toll_acquisition","tebe_takeover_complete",
            "wifi_new_acquisition","regulatory_favor_signal","08_brother_active"],
    ),

    # ── ARTICLE 23: Next rally is not FINDIMINTIL rally ───────────────────────
    NarrativeTemplate(
        name="Next Rally is Not FINDIMINTIL Rally — Inflow Rally to Peaked Market",
        description="""Ricky2212 rally classification framework:
THE EXPERIENCE:
- Apr 4, 2025: Trump "Liberation Day" → market crash
- Fear index hit level 4 (Extremely Fear)
- "Bullish akan dimulai dari fear indeks level ini"
- "Semua hal buruk sedang berada pada puncak nya dan market memfaktorkan nya langsung dengan LEBAY"
- "Sedikit saja berita baik itu muncul... market akan cepat come back"
RALLY TYPE CLASSIFICATION:
- STRUCTURAL BULLISH: "rally yang ditopang oleh keadaan ekonomi yang baik. Jadi antara rally dan real ekonomi berjalan in line"
- FINDIMINTIL RALLY: "Rally yang bersifat structural bullish" — NOT what we're getting
- INFLOW RALLY: "Its not Findimintil Rally, its a inflow Rally. Uang akan mengalir mencari tempat berlabuh yang menguntungkan"
- "Uang sedang mencari Store of Value"
THE NARRATIVE SEQUENCE:
1. "Ternyata masalah Tariff ga seburuk yang dikira koq, Tuh Trump sudah melunak dan coba bernegoisasi sana sini"
2. "Negoisasi nya menemukan titik terang"
3. "Narasi CUT suku bunga digaungkan bahwa dengan suku bunga di CUT ada harapan buat perbaikan di ekonomi"
    - "Seperti narasi CUT Agustus 2024 saat badut inflow bilang CUT bikin ekonomi membaik"
4. "Hingar bingar narrative digaungkan luar biasa, dari sana Euphoria akan menyelimuti market"
    - "Market lupa kalo 4 April kita diterjang badai kuat di pasar"
THE REALITY CHECK:
- "Rally tersebut apakah sudah memperhitungkan masalah penyelesaian ekonomi? not yet bro"
- "CUT nanti walaupun bisa memberi sedikit nafas tapi buat saya rasanya dosis nya belum cukup"
- "Ekonomi yang tadinya sudah sempoyongan harus dihantam tariff, yah harusnya butuh dosis gede CUT nya"
- "Rally tersebut sudah menyelesaikan masalah hutang amrik yang segunung? masih jauh dari selesai bro"
Ricky's strategy: "Saya masih pada strategi yang sama yaitu bermain Konglo Play"
"Its not Findimintil Rally, its not structural rally, ini hanya inflow Rally and manfaatkan rally nya sebaik mungkin"
"Enjoy kalo blow off the top datang"
Key insight: Distinguish structural vs inflow rally. Inflow rally = tradeable but not investable long-term.""",
        category="cycle",
        catalyst_types=["inflow_rally","not_structural","findimintil_rally","peaked_market","cut_euphoria",
            "tariff_negotiation","store_of_value_seek","liquidity_driven"],
        activation_keywords=["next rally not findimintil","inflow rally","findimintil rally","structural bullish",
            "fear index level 4","extremely fear","bullish dari fear","market lebay","berita baik muncul",
            "come back cepat","trump melunak","negoisasi titik terang","narasi cut suku bunga",
            "cut agustus 2024","euphoria menyelimuti","market lupa badai","not yet bro",
            "dosis cut belum cukup","ekonomi sempoyongan","hutang amrik segunung","jauh dari selesai",
            "konglo play strategy","manfaatkan rally","blow off top datang","inflow vs structural"],
        invalidation_keywords=["structural_recovery_confirmed","fundamentals_improve","real_economy_grows",
            "inflow_dries_up"],
        beneficiaries={"ihsg":["BUMI.JK","BRMS.JK","WIFI.JK","MPIX.JK","ELIT.JK","DATA.JK"],
            "us":["QQQ","IWM","BTC-USD"],"safe_haven":["GLD"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK"],"us":["TLT","VIX"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.25,
        confirmation_signals=["fear_index_reverses","tariff_negotiation_progress","fed_cut_narrative_builds",
            "euphoria_index_rises","inflow_surge","structural_data_still_weak"],
    ),

    # ── ARTICLE 24: Market bakal RISK ON pake banget ───────────────────────────
    NarrativeTemplate(
        name="Market Bakal RISK ON Pake Banget — JPY Carry, BTC Spike, Small Cap ATH",
        description="""Ricky2212 extreme risk-on framework:
POST-LIBERATION DAY SETUP:
- Apr 4, 2025: Trump Liberation Day → Fear Greed Index level 4 (Extreme Fear)
- "Bullish Phase dimulai saat itu. Tidak ada lagi ketakutan yang tersisa"
BULLISH CATALYSTS:
1. Extreme fear exhausted: "hanya masalah waktu saja ketakutan itu menghilang secara bertahap"
2. Market justifies: "ehhh, sudah lewat lah masa itu. Market sudah justifikasi semua nya"
3. Tariff negotiation progress: "Negoisasi antar negara akan settled satu per satu"
    - UK deal with US done
    - US-China negotiations opening (Geneva Swiss May 9-12, 2025)
    - "Trump akan menurunan tarif nya buat China"
4. USD weakness → risk asset global shift: "posisi US lewat USD makin berkurang sinar nya. Uang akan bergentayangan ke risk asset ke seluruh dunia"
CURRENCY SHIFT:
- EUR: strengthened significantly post-Liberation Day
- CHF: strengthened despite Swiss deflation (0% inflation)
- JPY: "mother of carry trade currency. pasca liberation day banyak yang balik dan me reverse posisi carry trade nya"
    - JPY pulang kampung buat menutup posisi global Carry trade
    - JPY menguat paling tajam diantara major hard currency
- DXY: longsor below 100
- IDR: "mulai terlihat berani tampil ke panggung. IDR mulai memperlihatkan arah penguatannya"
CARRY TRADE RESTART:
- "JPY mahal, USD murah, Risk asset banyak yang jatuh, perfect condition for Natural Carry Trade"
- Warren Buffett: Berkshire issued JPY bonds = doing Carry Trade
- "JPY dibuang dan terlihat mulai melemah dari 138 an menuju 144" = carry trade release
- "Uang likuid dalam USD sudah siap banget. IT's ALL ABOUT LIQUIDITY DRIVEN"
- "BULLISH MARKET terjadi bukan karena ekonomi membaik tapi karena Likuditas yang ga bisa tersalurkan ke ekonomi"
RISK ON CONFIRMATION:
- IHSG: "naik dari level terendah nya 5800 an dan sempat hampir sedikit lagi menyentuh 7000"
- Small caps outperforming broader market: "Saham2x kapitalisasi kecil outperform broader market"
- "Kalo bukan karena yakin akan ada risk on, mungkin kah saham2x kapitalisasi kecil yang bergerak?"
- BTC: "fucking asset naik luar biasa dalam moment singkat"
- ETH: "ETH dengan kapitalisasi no 2 terbesar... bisa naik bagger dalam hitungan singkat"
- "Gooookkkzzzzz"
- "Aliran uang lagu besar banget ke dunia antah berantah, bahkan inflow nya lebih besar dari inflow ke Gold"
Ricky's call: "I'm in Risk on Mode"
"When the music stops, in terms of liquidity, things will be complicated. But as long as the music is playing, you've got to get up and dance"
"Saya akan berdansa saat music terus dikumandangkan atau likuiditas itu sedang mengalir dan saya akan pulang sebelum music nya selesai"
"Pak mana jack up pak? hehehe hilang semua nanti suara itu dengan sendirinya"
Key data: Liquidity-driven risk-on, not fundamentals-driven. Dance while music plays.""",
        category="cycle",
        catalyst_types=["extreme_risk_on","jpy_carry_restart","btc_spike","eth_spike","small_cap_outperform",
            "liquidity_driven","usd_weakness_risk_on","currency_shift"],
        activation_keywords=["risk on pake banget","fucking risk on","extreme risk on","liberation day setup",
            "fear greed index 4","bullish phase dimulai","tariff negotiation settled","uk deal us",
            "us china negoisasi","geneva swiss may 9-12","trump turun tarif china","usd berkurang sinar",
            "uang gentayangan risk asset","eur menguat","chf menguat","jpy menguat tajam",
            "jpy carry trade restart","jpy pulang kampung","natural carry trade","buffett jpy bond",
            "jpy melemah 138 ke 144","liquidity driven","bullish bukan ekonomi","ihsg 5800 ke 7000",
            "small cap outperform","btc spike","eth bagger","dunia antah berantah inflow",
            "im in risk on mode","music playing dance","pulang sebelum music selesai","jack up hilang sendiri"],
        invalidation_keywords=["risk_on_fails","jpy_carry_unwinds","btc_corrects_30pct","liquidity_dries",
            "fed_hawkish_surprise"],
        beneficiaries={"ihsg":["WIFI.JK","MPIX.JK","ELIT.JK","DATA.JK","DOOH.JK","INET.JK","BUMI.JK","BRMS.JK"],
            "us":["IWM","QQQ","BTC-USD","ETH-USD","MSTR","COIN"],"fx":["USDJPY","EURUSD"]},
        fades={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK"],"us":["TLT","GLD","VIX"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":1.20,"Q1":0.90},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.30,
        confirmation_signals=["fear_greed_reverses_from_extreme","jpy_carry_trade_volume","btc_breaks_ath",
            "eth_surges","small_cap_index_outperform","ihsg_approaches_7000","idr_strengthens_toward_16000",
            "liquidity_injection_confirmed"],
    ),

    # ── ARTICLE 25: Trump doing a great job ────────────────────────────────────
    NarrativeTemplate(
        name="Trump Doing a Great Job — Bidenomics Cleanup & Recession Base",
        description="""Ricky2212 Trump policy assessment framework:
BIDENOMICS DAMAGE:
- "Biden itu kaya nampar muka sendiri" — mocked Trump but left catastrophic economy
- COVID: $9T spent ("bukan keadaan yang mengharuskan Amrik keluar $9T")
- Post-COVID: Biden/Yellen pumped economy with fiscal spending
- "Ekonomi terlihat bagus tapi Keuangan Amrik parah banget"
- "Total hutang yang dibikin zaman Biden, Yellen itu mungkin 60-70% total hutang Amrik yang sekarang sebesar $37 Trilyun"
- "Mau berapa lagi hutang amrik?"
- Interest on $36T = $1T/year. Refinancing 2025 starting June.
- "Fiskal jebol dan itu harus ditambal. Nambalnya pake apa? pakai hutang"
- "US harus menambal fiskal sekitar another $1.5 - $2 trilyun"
- Annual deficit potential: $2.5T+ = "massive catastrophic"
- "Kalo sudah begitu berarti harus kasih extra yield lagi agar mau kasih hutang ke US"
- "Makin tinggi bunga yang diberikan, makin tinggi defisit. Makin tinggi defisit maka makin banyak cetak uang"
- "Ujungnya? Default and Hyperinflation"
TRUMP'S TEAM:
- Elon Musk: DOGE — efficiency in bloated government
- Scott Bessent: Treasury — economic recovery program. "Otak Bessent itu Hedge Fund yang jenius banget" (Quantum Capital with Soros/Druckenmiller)
TRUMP'S FOCUS:
1. Efficiency: "Elon Musk ditugasin buat merancang efisensi di tubuh pemerintahan Amrik yang tambun di zaman Biden"
2. Shift to Private Spending: "memindahkan ekonomi dari Government spending ke Private Spending"
3. Fix Financial Structure: "memperbaiki struktur keuangan US"
TARIFF:
- "Fairness dalam perdagangan dunia"
- "US itu dagang nya tekor mulu dengan partner dagangnya"
- Bessent's hidden mission: negotiate lower rates, weaken USD for exports, prepare for "The One, Big, Beautiful Tax Bill"
TAX BILL:
- "THE ONE, BIG, BEAUTIFUL BILL" passed House
- "MASSIVE Tax CUTS, No Tax on Tips, No Tax on Overtime, Tax Deductions for American Made Vehicle"
- "Strong Border Security, Pay Raises for ICE, Funding for Golden Dome, TRUMP Savings Accounts for newborn babies"
- Purpose: shift from Govt spending to private spending
    * Consumers: extra money from no tax on tips/overtime → spending up
    * Business: tax cuts → liquidity → expansion → hiring
    * "Rekrut karyawan ga tuh pengusaha? rekrut karyawan pasti lah yah"
    * GDP rises → tax revenue rises even at lower rate
- Tariff fills gap until tax cut effects materialize
INFLATION CONTROL:
- "Trump akan lakukan dan mengambil apapun kebijakan nya untuk terus menjaga inflasi"
- Green energy abandoned ("mahal, bikin inflasi") → back to fossil
- "Drill baby Drill" — massive oil supply to keep prices down
- OPEC raising production despite low prices = "salah satu cara jaga inflasi"
- Trump: "dia akan membuat harga obat turun" — another inflation component
- "Mr too late masih parno saja sama masalah INFLASI. How come?"
THE BASE CASE:
- "Semua hal diatas akan sangat terlihat bagus hasilnya kalau ekonomi Amrik bikin Base baru dulu di bawah"
- "Ekonomi dilemahkan dibikin low. Inflasi turun ke level bawah. Suku bunga harus diturunkan ke level bawah. Pasar saham harus dijatuhkan ke level bawah"
- "Semua itu tanda apa? itu syarat untuk sebuah QE dilakukan dan itu adalah RESESI"
- "Makanya itu juga salah satu tujuan Trump and Bessent bikin Tariff. Mereka sudah siapin sampai kesini perjalanannya."
Ricky's call: "Prepare not Predict"
"Crash? kita lihat saja nanti, setiap ada masalah hutang maka penyelesaian nya adalah Crisis"
"Tapi tenang, semua yang dilakukan Trump itu sebuah Fondasi ekonomi yang baik buat nanti setelah ekonomi bikin low base""",
        category="geopolitical",
        catalyst_types=["trump_great_job","bidenomics_cleanup","tax_bill","tariff_tool","inflation_control",
            "fossil_revival","recession_base","qe_setup","debt_crisis_resolution"],
        activation_keywords=["trump doing great job","bidenomics damage","biden nampar muka sendiri",
            "hutang 37 trilyun","biden yellen 60-70% hutang","fiskal jebol","default hyperinflation",
            "elon musk doge","scott bessent treasury","quantum capital bessent","efficiency pemerintahan",
            "government spending ke private spending","the one big beautiful bill","massive tax cuts",
            "no tax on tips","no tax on overtime","american made vehicle tax","trump savings account",
            "golden dome","border security funding","tax bill purpose","tariff fills gap",
            "inflation control trump","green energy abandoned","drill baby drill","opec raise production",
            "harga obat turun","mr too late parno","base baru ekonomi","ekonomi low base",
            "syarat qe","resesi syarat","trump bessent siapin perjalanan","crash penyelesaian hutang",
            "crisis penyelesaian hutang","fondasi ekonomi baik","prepare not predict trump"],
        invalidation_keywords=["trump_impeached","tax_bill_fails","tariff_war_escalates","inflation_spikes",
            "recession_deeper_than_expected"],
        beneficiaries={"us":["XLE","OIH","CVX","XOM","TLT"],"ihsg":["BBCA.JK","TLKM.JK","UNVR.JK"],
            "crypto":["BTC-USD","MSTR","COIN"]},
        fades={"us":["SPY","QQQ","high_beta"],"ihsg":["property","consumer_discretionary"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=52,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["tax_bill_passes_senate","tariff_revenue_spikes","doge_cuts_executed",
            "inflation_stays_low","oil_supply_increases","gdp_base_formed","unemployment_rises_to_reset"],
    ),

    # ── ARTICLE 26: Blow off the top skenario ─────────────────────────────────
    NarrativeTemplate(
        name="Blow Off The Top Skenario — UST Spike Trap & CUT FOMO",
        description="""Ricky2212 blow-off-top execution framework:
UST SPIKE TRAP:
- "UST yang bergerak konyooooll. Ga ada alasan UST harus spike segitu tingginya"
- "Semua data mengarah pada disinflation. PCE indeks sudah berada di 2.1%"
- "Data inflasi 2.1% sementara UST yield rata2x sudah diatas 4%"
- "Market sampai meminta premium diatas 2.5% buat bond yang dikeluarkan US?"
- "Bukan bro, itu narasi yang sengaja diciptakan oleh Amrik sendiri"
- "Waktu mereka semakin pendek buat refinancing hutang mereka yang jumbo yang jatuh tempo di Juni ini"
- "Perfect scenario banget permainan mereka"
THE TRAP MECHANICS:
- USD jatuh parah → USD keliatan murah → "Para pengelola dana pasti kepancing buat masuk ke pasar US"
- Yield UST dibikin menarik → "memancing para pemegang dana membeli Bond USD"
- "Amrik buat absorb dana dalam jumlah super jumbo buat mengamankan hutang2x yang jatuh temp tersebut"
- "Damn mereka sukses tuh di permainan awal hutang jatuh tempo nya. Mereka bisa bernafas lega sesaat"
THE FOMO SEQUENCE:
- Post-debt-settled: "nyambung ke part yang bikin nanti ter FOMO FOMO"
- "Mereka menyimpan skenario ini buat next level jack up nya. Perlu narasi lanjutan buat blow off puncak nanti"
- Market come back with negotiation stories: "satu per satu bisa settled saat negoisasi terus berjalan"
- Store of Value running well
- "Next apa yang terjadi pasca US sudah men settled kan hutang nya?"
- "Dia punya banyak alasan koq buat menaikkan narasi CUT nya ke publik"
CUT NARRATIVE BUILD:
- GDP US kontraksi negatif
- Inflasi 2.1%
- Home seller listings spike
- CEO confidence jatuh luar biasa
- Daya beli konsumen menukik tajam
- "Masih belum cukup kah?"
- "atau butuh data tenaga kerja nyungsep dulu agar semua bsia dijalankan?"
- "Amrik bilang mau CUT soon"
- "Gilaa ga tuh seluruh dunia juga bakal ikutin CUT dengab pace yang cukup cepat"
- "Narasi CUT terjadi ke seluruh antero dunia dan USD bakal jadi pihak mata uang yang lemah"
- "Store of value makin menjadi-jadi dan tak tertahankan lagi"
COMMODITY FOMO:
- "Liat pergerakan komoditas semalam saat Dxy Ambruk lagi dibawah level 99"
- "Mulai dari emas, copper, natural gas even sampai oil pun juga diajak naik"
- "Dunia akan ter FOMO - FOMO ga karuan"
THE SKEPTICS:
- "Sampai saat ini masih cukup banyak Fund yang masih di pinggir lapangan. Mereka masih skeptis"
PEAK CONFIRMATION:
- "Semua ga akan tersadar nanti, semua jatuh dalam ke euphoria an"
- "Semua dimabuk oleh bullish nya market and itu salah satu syarat terjadinya Crisis"
- "Crisis terjadi saat orang tidak ada yang menduga-duga, Crisis terjadi saat banyak yang tidak siap"
Ricky's call: "Prepare not Predict, semoga anda semua tetap bersiap terhadap semua keadaan yang mungkin terjadi"
"Kita semua sudah berjalan sejauh ini dan semua tetap pada jalur nya"
Key data: UST spike = trap to absorb foreign capital for refinancing. Post-refinancing = CUT FOMO = blow off top.""",
        category="cycle",
        catalyst_types=["ust_spike_trap","blow_off_top","cut_fomo","debt_refinancing","foreign_bond_trap",
            "commodity_fomo","euphoria_peak","crisis_setup"],
        activation_keywords=["blow off the top skenario","ust spike trap","konyol ust","pce 2.1%","ust yield 4%",
            "premium bond 2.5%","narasi sengaja diciptakan amrik","refinancing hutang jumbo","juni jatuh tempo",
            "perfect scenario amrik","usd murah kepancing","yield menarik memancing","absorb dana super jumbo",
            "bernapas lega sesaat","fomo sequence","negoisasi settled","store of value running",
            "cut narrative build","gdp kontraksi negatif","home seller spike","ceo confidence jatuh",
            "daya beli menukik","cut soon","seluruh dunia ikut cut","usd lemah massive",
            "komoditas fomo","dxy ambruk 99","emas copper gas oil naik","fund skeptis pinggir lapangan",
            "euphoria peak","crisis tidak siap","prepare not predict blow off"],
        invalidation_keywords=["ust_spike_fundamental","fed_holds_no_cut","refinancing_fails",
            "market_peaks_without_fomo"],
        beneficiaries={"us":["SPY","QQQ","IWM","TLT"],"global":["GC=F","HG=F","CL=F","NG=F"],
            "crypto":["BTC-USD","ETH-USD"]},
        fades={"us":["SQQQ","VIX"],"ihsg":["property"]},
        regime_alignment={"Q3":1.70,"Q4":1.50,"Q2":1.20,"Q1":0.90},
        typical_duration_weeks=16,
        conviction_ceiling=0.85,
        pump_risk=0.25,
        confirmation_signals=["ust_yield_spike_unjustified","foreign_bond_buying_bludak","pce_confirms_disinflation",
            "refinancing_completed","cut_narrative_massive","commodity_rally_broadens","fund_still_skeptical",
            "euphoria_index_spike"],
    ),

    # ── ARTICLE 27: Sun Tzu Art of War — Iran-Israel Conflict as Market Driver ──
    NarrativeTemplate(
        name="Sun Tzu Art of War — Iran-Israel Conflict as Market Theme",
        description="""Ricky2212 war-as-market-theme framework:
THE GOD FATHER'S WAR:
- "Percaya ga percaya, market dunia tuh seakan-akan ada yang gerakkin. Dibutuhkan sebuah tema buat mereka agar bisa menggerakkkan financial market"
- "War, God Father Art in financial market"
- "So untuk beberapa waktu ke depan Tema market adalah WAR"
THEME LIFECYCLE:
- Tariff theme (Liberation Day): "Naik turun nya market sangat dipengaruhi naik turunnya negoisasi masalah tarif tersebut"
- "Belakangan tema tersebut mulai BASI. Efek nya mulai tidak begitu kerasa"
- Trump-Elon conflict: "Tema Colongan yang diluncurkan ke market"
- Iran-Israel war: "Tema nya digaungkan dengan kencang sebagai awal mula WW3"
- "Seketika financial market Shock saat tema tersebut diluncurkan"
- "Ini akan jadi tema yang akan dipakai untuk mendrive and menggerakkan market"
IRAN NUCLEAR HISTORY:
- 1950s: Shah + US "Atom for Peace" program
- 1979 Revolution: Khomeini halted program as "tidak Islami"
- 1980-1988 Iran-Iraq War: "Serangan Irak yang didukung AS... memaksa Iran mencari keamanan"
- "Pengalaman traumatis ini mendorong keinginan untuk melakukan pencegah strategis"
- A.Q. Khan network supplied enrichment technology
- 2002: Natanz + Arak facilities revealed
- 2015: JCPOA deal (Obama + Rouhani)
- 2018: Trump withdrew from JCPOA, "maximum pressure" sanctions
- Oct 7, 2023: Hamas attack on Israel
- "Iran menyatakan dukungan moral untuk Hamas tetapi menyangkal keterlibatan langsung"
- "Hubungan panjang dan dukungan Iran membuat Israel and AS menuduh Iran sebagai dalang"
HORMUZ THREAT:
- 21% world energy (21M barrels/day) from countries bordering conflict zone
- Hormuz bordering countries: Iran (3M), UAE (3.5M), Oman (1M)
- Non-bordering but dependent: Saudi (9-9.5M), Iraq (4M), Kuwait (3.3M), Qatar (700k)
- "Iran akan menutup selat Hormuz"
- "Kalau sampai ini kejadian ditutup, tambah parah lah pasokan energi dunia"
- "Sedikit saja perang tersebut meluas, efek nya akan merembet kemana-mana"
MARKET IMPACT:
- Oil prices spike instantly on war news
- "Perang + Store of Value + Narasi konglo 9 haji + CA + EBT adalah kombinasi narasi yang sempurna"
- "Ini bukan FINDIMINTIL play. Yang akan main adalah Liquidity Drive"
- "Yang akan bermain adalah Narrative dan uang akan deras masuk ke saham yang punya narrative sangat kuat"
FED IMPLICATION:
- "Bank sentral dunia sudah banyak yang melakukan CUT, hanya US saja yang masih coba bertahan belum CUT"
- "Fed masih bersikeras kalo mereka masih khawatir kalo inflasi US akan terus membandel"
- "Perang ini bisa juga jadi alasan ketidak pastian sehingga FED tinggal bilang Perang akan bikin ketidak pastian terhadap inflasi"
- "Cut hanya masalah waktu saja"
- "Ga pernah tuh spread antara inflasi dan suku bunga sampai sejauh sekarang"
    * Fed rate 4.5-4.75%, inflation ~2.4% = 2.25% spread (historical ~1%)
- "Fed meeting Juni ini sepertinya Fed akan tetap menahan"
- "Buat saya selama masih ada tema berjalan (kaya perang) yang masih bisa menggerakkan market, biar lah CUT nya nanti saja"
NEXT THEME:
- "Habis tema perang dan jadi BASI an, saya melihat tema CUT adalah tema selanjutnya yang akan menggerakkan market"
- "CUT akan bikin jack up, jerk up, jack off sampe ter FOMO FOMO"
Ricky's call: "no nanya saham apa yang paling baik, no nanya pilihin saham A atau B, no nanya semua yang berhubungan dengan price action""",
        category="geopolitical",
        catalyst_types=["iran_israel_war","hormuz_threat","oil_spike","ww3_theme","market_theme_rotation",
            "fed_uncertainty_war","cut_next_theme"],
        activation_keywords=["sun tzu art of war","god father war","market theme war","tema market war",
            "iran israel conflict","iran sirewel","iran nuclear program","hormuz threat","selat hormuz",
            "21% energi dunia","21 juta barrel per hari","hormuz ditutup","oil spike war","ww3 theme",
            "tema tariff basi","tema colongan trump elon","hamas attack oct 7","jcpoa 2015","trump maximum pressure",
            "fed cut uncertainty war","inflasi membandel","spread inflasi suku bunga 2.25%","fed meeting juni",
            "tema cut selanjutnya","jack up jerk up jack off","fomo cut","liquidity drive narrative",
            "findimintil play no","komoditas store of value war","oil pick and shovel","energy substitution",
            "no price action question war"],
        invalidation_keywords=["peace_agreement","hormuz_stays_open","oil_supply_unaffected",
            "war_theme_fades_quickly"],
        beneficiaries={"global":["CL=F","NG=F","GC=F","USO","UNG"],"ihsg":["MEDC.JK","PTBA.JK","ANTM.JK","MDKA.JK"],
            "us":["XLE","OIH","CVX","XOM"]},
        fades={"us":["SPY","QQQ","high_beta"],"ihsg":["property","consumer_discretionary"]},
        regime_alignment={"Q3":1.50,"Q4":1.30,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["iran_missile_launched","israel_retaliates","hormuz_closure_threat",
            "oil_spike_10pct","vix_spike","defense_stocks_rally","fed_cites_war_uncertainty"],
    ),

    # ── ARTICLE 28: Get Ready TFF — OJK Changes & Liquidity Flood Indonesia ───
    NarrativeTemplate(
        name="Get Ready TFF — OJK Changes, Lot Shrink & Tax Amnesty Liquidity Flood",
        description="""Ricky2212 Indonesia liquidity preparation framework: "Ter FOMO FOMO"
THE TFF JOKE:
- "Mas beneran nih bakal TFF. Saya bingung apa itu TFF"
- "Ter FOMO FOMO" / "Ter Fuck Fuck" / "Ter Frayogo Fangestu"
- "Makin kesini makin terlihat set up game nya mengarah kesana"
GLOBAL CUT RACE:
- "Bank sentral dunia terus memotong suku bunga nya secara simultan"
- BOE, ECB, BoC, RBA, RBNZ, SNB (cut to 0, even negative rates possible)
- "Tinggal siapa yang belum? US melalui Fed nya belum action"
- "CUT adalah keniscayaan buat FFR"
- "Biarkan sementara market memainkan semua drama and narrative nya sebelum nantinya CUT akan datang"
INDONESIA PREPARATION (5 POINTS):
1. TRADING HOURS EXTENSION:
    - "Jam perdagangan bursa kita akan ditambah masing2x 1 jam sebelum pembukaan dan 1 jam setelah penutupan"
    - "Seumur2x saya di bursa, baru kali ini ada wacana penyesuaian dengan penambahan jam perdagangan bursa"
    - "Bursa Indonesia mau menampung lebih banyak lagi likuiditas dari luar sana"
    - "Bursa akan semakin ramai secara value transaksi perdagangan"
2. LOT SHRINK:
    - Current: 1 lot = 100 shares
    - Proposed: 1 lot = 10 shares
    - Example ITMG: 2.3M/lot → 230k/lot
    - "Makin terjangkau bukan?"
    - "harapan nya dengan hal ini akan makin ramai transaksi di bursa kita"
    - "Bayangkan orang yang tadinya judi ga jelas pake judi selot, perputaran uang nya yang sangat besar bisa pindah ke bursa saham"
    - "Partisipan yang dibawah, harapan nya sampai pada lapisan bawah bisa berpartisipasi di bursa saham"
    - Last lot change: ~2004 (BEJ changed from 500 to 100 shares/lot)
3. SECURITIES CONSOLIDATION:
    - "Sekuritas akan ditertibkan secara MKBD dan permodalan nya"
    - "Sekuritas akan banyak di merge dan sisa yang kuat2x dan tertib administrasi saja yang masih akan terus ada"
4. JUDOL MONEY REPATRIATION:
    - "Masih ingat judol yang marak kemarin? masih ingat uang nya dibawa kabur kemana?"
    - "Konon katanya uang nya di parkir di negara lain dan salah satu nya di kamboja"
    - "Sepertinya akan ditarik pulkam kesini lewat bursa dan itu jumlah nya cukup mumpuni"
    - "Sekuritas ditertibkan tuh MKBD nya supaya bisa menampung uang2x tersebut"
    - "Mencegah terjadinya settlement failure"
5. TAX AMNESTY:
    - "Beberapa taipan akan dikasih karpet merah buat uang nya masuk ke Indo lewat TA atau Tax Amnesty"
    - "2018 salah satu group kertas lakukan hal tersebut dan lihat saja tuh saham kertasnya saat itu"
    - "Ekonomi seret banget secara likuiditas nya, so dengan adanya Tax Amnesty maka likuiditas deres bisa masuk ke indo"
    - "Sebagian akan digunakan taipan buat aksi korporasinya"
    - "Indo butuh nambal fiskal sehingga Tax Amnesty bisa jadi jalan buat kumpulin fiskal nya"
Ricky's call: "Indonesia ready ga tuh? ready dan get ready buat TFF alias Ter FOMO FOMO menampung banyak likuiditas nantinya"
"Minggu depan saya sambung lagi yah skenario tema narrative global yang akan berjalan versi saya"
Key data: Indonesia is preparing infrastructure to absorb massive liquidity inflow. TFF = liquidity-driven euphoria.""",
        category="geopolitical",
        catalyst_types=["ojk_reform","lot_shrink","trading_hours_extension","securities_consolidation",
            "judol_money_repatriation","tax_amnesty","liquidity_flood_indonesia","tff_setup"],
        activation_keywords=["get ready tff","ter fomo fomo","ter fuck fuck","ojk changes","ojk reform",
            "jam perdagangan ditambah","trading hours extension","lot shrink","1 lot 10 lembar",
            "itmg 230 ribu per lot","sekuritas merge","mkbd sekuritas","judol money repatriation",
            "uang judol kamboja","tarik pulkam bursa","settlement failure prevention","tax amnesty",
            "taipan karpet merah","tax amnesty 2018 kertas","likuiditas deres masuk","indonesia ready tff",
            "bank sentral dunia cut simultan","snb negative rates","cut keniscayaan ffr","indonesia menampung likuiditas",
            "tff liquidity flood","ramai transaksi bursa"],
        invalidation_keywords=["ojk_reform_blocked","lot_shrink_cancelled","tax_amnesty_fails",
            "liquidity_doesnt_arrive"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","UNVR.JK","BUMI.JK","WIFI.JK"],
            "broker":[" securities_sector"],"safe_haven":["IDR_cash"]},
        fades={"ihsg":["property"]},
        regime_alignment={"Q1":1.60,"Q2":1.40,"Q3":1.20,"Q4":1.00},
        typical_duration_weeks=26,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["ojk_announces_hours_extension","lot_shrink_approved","securities_merge_starts",
            "tax_amnesty_program_launched","judol_money_returns","foreign_inflow_surge_indonesia",
            "idr_strengthens_toward_16000"],
    ),

    # ── ARTICLE 29: BER BER BER curse ──────────────────────────────────────────
    NarrativeTemplate(
        name="BER BER BER Curse — Sep-Oct Crash Pattern & FOMC Cut Timing",
        description="""Ricky2212 seasonal crash pattern framework: "The Curse"
HISTORICAL BER BER BER (Sep-Oct):
- 2022: Market drop from aggressive rate hikes
- 2008: Global Financial Crisis
- 1987: Black Monday
- 1927-1928: Great Depression buildup
- "Ber Ber Ber brrrrrrr, memang benar adanya kejadian2x buruk pasar banyak terjadi di periode tersebut"
THE BEHAVIOR EXPLANATION:
- "Sell in May and Go Away" → funds exit for summer vacation (happens in BER BER BER period)
- "Puncak kenaikan market tuh terjadi di bulan Juli atau Agustus berbarengan dengan keluarnya laporan kinerja tengah tahunan"
- "Kalo sudah keluar dari pasar berarti? butuh masuk lagi kan ke pasar?"
- "Pasar butuh dibikin RUSUH dulu di ber ber ber agar mereka para fund dapat karpet merah buat masuk kembali ke pasar"
2025 PATTERN:
- 2022: Rate hike crash in BER BER BER
- 2023: First HALT in BER BER BER
- 2024: First CUT in BER BER BER
- "Kebetulan kah semua itu? koq bisa yah pas begitu"
- 2025 BER BER BER: "odds tertinggi pemotongan suku bunga terjadi di periode BER BER BER"
- "Chance besar Bulan meeting FOMC buat CUT akan terjadi di periode bulan BER BER BER tersebut"
- "Odds nya sudah sampai menyentuh 80% untuk CUT di periode bulan tersebut"
THE MECHANICS:
- "Kalo mau potong suku bunga maka? dibutuhkan reason agar FED punya urgency untuk memotong suku bunga nya"
- "Makanya jangan kaget nanti misalkan di dekat2x sana kalo ada sedikit guncangan pasar"
- "Yah turun2x pasar jadi hal yang wajar lah. Tapi ga usah terlalu jadi parno sendiri nantinya"
- "Santai aja menghadapinya karena nanti dari sana tercipta TFF"
THEME TIMING:
- Tariff theme: April launch → lasted ~2 months → now BASI
- War theme: June launch → "tema perang akan bisa bertahan sampai bulan agustus"
- "Kebetulan kah? tema perang nantinya akan bertahan sampai Agustus yang dekat banget sama bulan BER BER BER"
- "Trump bakal kasih liat Fed tuh, kalo kebijakan tarif kemarin aja ga ada inflasi yang menakutkan yang datang"
- "Begitu juga efek dari perang, ga ada inflasi yang datang"
- "Tidak ada lagi alasan yang tersisa buat tidak melakukan CUT"
- Trump: "harusnya suku bunga US sudah 2% atau bahkan 1%"
CUT PREDICTIONS:
- Morgan Stanley: "2026 akan ada 7 rate CUT x 0.25"
- Julius Baer: "5x CUT yang akan Fed lakukan"
- Ricky's prediction: 2-phase CUT
    * Phase 1: 2.75%-3.25% target. TFF, jerk up, jack up. "CUT to CUT yang membuat market peaked" (13 key point)
    * Phase 2: Market realizes CUT not enough → disappointment → "ULTIMATE CUT" (13 key point)
Ricky's call: "BER BER BER Brrrrrrr, ga usah parno sendiri. Kita akan melihat pasar TFF nantinya"
"The cursenya akan menuntun kita buat CUT yang massive yang berujung pada keluarnya dana2x mengendap sehingga berujung pada TFF"
"Berasa? sekarang aja sudah berasa auranya tuh, market di US aja terus merengsek dari ATH ke ATH"
Key data: BER BER BER = seasonal crash window that creates entry for funds + forces Fed action.""",
        category="cycle",
        catalyst_types=["ber_ber_ber_curse","sep_oct_crash","fomc_cut_timing","seasonal_pattern",
            "sell_in_may","fund_reentry","tff_peak","cut_phase_1","cut_phase_2"],
        activation_keywords=["ber ber ber curse","ber ber ber brrrrr","sep oct crash","seasonal crash",
            "sell in may","fund summer vacation","fund reentry","pasar rusuh ber ber ber","karpet merah fund",
            "2022 rate hike ber","2023 halt ber","2024 cut ber","2025 ber ber ber","odds cut 80%",
            "fomc meeting ber ber ber","guncangan pasar dekat","turun pasar wajar","tff dari ber ber ber",
            "tema tariff 2 bulan","tema perang juni agustus","trump kasih liat fed","tariff ga ada inflasi",
            "perang ga ada inflasi","tidak ada alasan tidak cut","suku bunga 2%","suku bunga 1%",
            "morgan stanley 7 cut 2026","julius baer 5 cut","ricky 2 phase cut","cut to cut peaked",
            "ultimate cut 13 key point","market merengsek ath ke ath","aura tff berasa"],
        invalidation_keywords=["ber_ber_ber_fails_2025","fed_holds_through_sep","no_crash_occurs",
            "cut_comes_early"],
        beneficiaries={"us":["SPY","QQQ","IWM","TLT"],"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BUMI.JK","WIFI.JK"],
            "safe_haven":["IDR_cash","USD_cash"]},
        fades={"us":["SQQQ","VIX"],"ihsg":["property","high_flyer"]},
        regime_alignment={"Q3":1.60,"Q4":1.40,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=8,
        conviction_ceiling=0.80,
        pump_risk=0.20,
        confirmation_signals=["sep_oct_volatility_spike","vix_above_25","fund_cash_levels_peak",
            "fomc_meeting_in_sep_oct","cut_odds_above_80%","market_drops_5pct","tff_signals_emerge"],
    ),

    # ── ARTICLE 30: TFF part 3 — Puncak Kegilaan Trump (BTC Strategic Reserve) ─
    NarrativeTemplate(
        name="TFF Part 3 — Puncak Kegilaan Trump (BTC Strategic Reserve & US Debt Payoff)",
        description="""Ricky2212 ultimate Trump crypto hegemony framework:
THE DESSERT CYCLE:
- "Masih ingat Artikel tentang Dessert penutup Cycle? ada 2 menu dessert: saham Bxxx dan Digital Gold BTx"
- "Kalo keduanya berjalan rally mbledug, yah jangan lupa untuk bersiap"
THE SETUP:
1. Bessent = hedge fund brain (Quantum Capital with Soros/Druckenmiller)
2. USD collapsing → needs Store of Value
3. BTC = US Store of Value (China loses on BTC setup)
4. US wants to reduce $36T debt
TRUMP'S CRYPTO JOURNEY:
- Campaign: Trump crypto-friendly. "US akan jadi center utama Crypto"
- "Kalo kita ga mulai dari sekarang, maka China akan memulai nya"
- "China tuh sejauh ini belum crypto friendly karena mereka masih banned asset tsb"
- Game plan: crypto in US tax-free for US-based projects
THE EXECUTION:
1. Crypto tax exemption for US-based projects
2. Replace anti-crypto SEC chair (Biden era) with crypto-friendly one
    - "Ketua SEC zaman biden tersebut terkenal sangat anti Crypto"
    - "XRP tidak bisa beroperasi penuh di Amrik"
    - New SEC chair → XRP and all crypto projects liberated
3. USD on blockchain: "US akan meluncurkan koin USD di dunia Crypto sebagai penambah jangkauan USD"
4. GENIUS Act stablecoin bill: "dollar dalam crypto dalam menjalanan ekonominya"
5. Real world ↔ Crypto HUB: "likuiditas akan bertambah. Likuiditas di pasar crypto itu terus membesar"
    - "Trump akan membuat HUB antara dunia crypto dengan real world"
    - "Disana bisa beli surat hutang UST lewat Crypto"
6. Coinbase in S&P 500: "Trump mau menunjukkan ke dunia agar dunia makin yakin kalo US benar2x serius di Crypto"
7. Coinbase stablecoin for consumer payments
8. XRP as primary US payment system: "koin XRP yang tadinya susah beroperasi juga akan jadi payment system utama"
9. US banks opening to crypto: "Beberapa Bank di US juga sudah mulai membuka diri untuk memfasilitasi transaksi Crypto"
    - Swiss bank adopts Ripple (XRP) network
    - Freddie Mac & Fannie Mae: crypto as payment tool
    - Jamie Dimon (JPM): "Ga suka sama Crypto, tapi narasi nya kuat sekali dan Trump support narasi tersebut"
    - JPM ready to be primary crypto custody → other banks follow
THE CLIMAX:
- "Kalo semua set up HEGEMONI sudah makin membesar, Trump akan umumkan: US akan menjadikan BTC sebagai Strategic Reserve"
- "Gilaaaa? yap, gila dan kalo sampe US lakukan itu maka lo tau kan BTC akan gimana?"
- "Satu dunia juga akan ter FOMO FOMO tuh makan BTC ngekor US"
- "Harga spike ga karuan, Govt of US sebagai salah satu pemegang BTC terbesar tinggal bayar hutang2x nya tuh pake kenaikan nilai BTC nya"
BTC VOLATILITY ARGUMENT:
- "BTC itu volatilitas nya tinggi karena: marcap masih rendah, regulasi belum ketat, pemegang belum super global"
- "Makin besar nilai suatu Asset pastinya nanti membuat volatilitas menurun"
- "Sama seperti BTC nantinya, saat makin mature dan makin diregulasi juga bakal less volatile"
- "Kalo saham big cap kaya AMZN, MSFT, GOOG satu dunia jadi pemegang saham... jadi less volatile"
- "ETF BTC mulai diperkenalkan = satu cara supaya BTC diregulasi dengan baik"
- "Cycle ini adalah cycle terakhir crypto yang masih ada volatile nya"
Ricky's call: "US akan ciptakan permainan store of value ala mereka sendiri"
"Pesan utama: kalo thesis DESSERT nya akan berjalan dengan baik. Puncak Peaked market akan terlihat dari permainan yang diciptakan Trump ini"
"Ini khayalan liar saya saja yah. Jangan ditelan mentah2x"
"NB: anda akan melihat sebuah design dimana dunia koin akan dibikin HUB ke dunia real finance"
"Satu kegilaan and manipulasi yang diciptakan oleh likuiditas""",
        category="geopolitical",
        catalyst_types=["btc_strategic_reserve","us_crypto_hegemony","trump_crypto_climax","debt_payoff_btc",
            "xrp_liberation","coinbase_sp500","stablecoin_hub","crypto_regulation_us","dessert_cycle"],
        activation_keywords=["tff part 3","puncak kegilaan trump","btc strategic reserve","us debt payoff btc",
            "bessent hedge fund brain","quantum capital","usd collapsing store of value","china loses btc",
            "trump crypto friendly","us center crypto","crypto tax exemption us","sec chair replaced",
            "xrp liberated","usd blockchain","genius act stablecoin","real world crypto hub",
            "ust via crypto","coinbase sp500","coinbase stablecoin payment","xrp payment system us",
            "us banks crypto","swiss bank ripple","freddie mac fannie mae crypto","jamie dimon crypto",
            "jpm custody crypto","hegemoni crypto","fomo btc strategic reserve","govt us bayar hutang btc",
            "btc volatility decline","btc marcap besar","btc etf regulation","cycle terakhir crypto volatile",
            "dessert cycle bxxx btx","puncak peaked market","design koin hub real finance",
            "kegilaan manipulasi likuiditas"],
        invalidation_keywords=["btc_reserve_denied","crypto_regulation_fails","xrp_still_blocked",
            "coinbase_removed_sp500","trump_abandons_crypto"],
        beneficiaries={"us":["BTC-USD","ETH-USD","MSTR","COIN","XRP-USD"],"global":["GLD","TLT"],
            "ihsg":["BBCA.JK","TLKM.JK"]},
        fades={"us":["SQQQ","VIX"],"ihsg":["property"]},
        regime_alignment={"Q3":1.80,"Q4":1.70,"Q2":1.40,"Q1":1.00},
        typical_duration_weeks=26,
        conviction_ceiling=0.85,
        pump_risk=0.25,
        confirmation_signals=["trump_announces_btc_reserve","sec_approves_xrp","coinbase_sp500_sustained",
            "genius_act_passed","stablecoin_volume_spike","jpm_crypto_custody_live","ust_crypto_trading_live"],
    ),

    # ── ARTICLE 31: Perfect Classic Game Play — Big Fund Rotation ────────────
    NarrativeTemplate(
        name="Perfect Classic Game Play — Big Fund IDR→Bonds→Equity Rotation",
        description="""Ricky2212 Big Fund rotation framework: "Perputaran Uang Ala Big Fund"
THE COMPLAINTS:
- "Pak, jack up mana pak?"
- "Pak, ini koq market kita merah sendiri?"
- "Pak, kenapa nih market kita koq turun saat global naik?"
- "Pak, kan perang nya sudah titik terang tapi kenapa belum disambut market?"
- "Seharian saya terima DM yang isinya pertanyaan seperti itu. Ga hanya 1 atau 2 orang, tapi puluhan"
THE PSYCHOLOGY:
- "Selalu berharap market naik dan sesuai harapan yah? sekali nya tidak sesuai harapan jadi kaya terganggu psikologinya"
- "Teman2x disini sih harusnya sudah paham semua pola nya yah"
THE CLASSIC GAME PLAY (May 9, 2023 article reference):
1. BUY IDR FIRST:
    - "Fund memborong dulu mata uang Rp sebagai persiapan untuk masuk ke paper asset di suatu negara"
    - "Rp nya sudah menguat lebih dari 200 point dan kembali ke bawah 16300"
    - IDR strengthening = fund positioning
2. BUY BONDS NEXT:
    - "Fund akan memborong dulu surat Hutang nya"
    - "Surat hutang kita, pasti pergerakannya arahnya menguat"
    - Bond rally = second phase of fund positioning
3. PRESSURE EQUITY FOR ENTRY:
    - "Kalo sudah kenyang memborong surat hutang, tinggal apa? yap tinggal bersiap buat masuk equity lah yah"
    - "Mereka pasti bikin skenario agar mereka bisa masuk ke equity dengan harga yang menguntungkan"
    - "Karpet merah harus disiapkan, makanya market seakan-akan ditekan dulu dan menimbulkan kecemasan"
    - "WEAK HAND yang penuh ketakutan dan kecemasan pasti akan termakan oleh market"
    - "Padahal kondisinya adalah set up yang diciptakan oleh Fund"
THE TIMING QUESTION:
- "Berapa lama kira2x pasar saham akan dapat impact nya?"
- "Buat saya jangan pernah bertanya tentang waktu, kapan, tepat nya karena di pasar saham tidak ada yang bisa memastikan waktunya"
- "Prepare jauh lebih baik daripada predict"
- "Yang jelas classic game play nya tuh terlihat koq"
- "Selama kita tau game play nya, yah sudah tinggal action aja sesuai dengan risk profile masing2x"
RISK ON SIGNALS:
- "Bellwether asset tuh terus memperlihatkan sinyal RISK ON"
- "Semua lagi mengarah pada keadaan TFF terFoMo FoMo and Ter Fuck Fuck"
- "Selama tidak ada gejolak luar biasa lagi sih harusnya bisa berjalan dengan baik"
- "Paling kalau ada sedikit riak2x yah dimaklumkan saja lah"
- "Ini mah koreksi biasa aja, lebih parah koreksi APRIL kemarin kan?"
Ricky's call: "Classic game play, Seperti biasa Fund memborong dulu mata uang Rp..."
"Prepare not Predict"
Key data: Big Fund classic 3-step: IDR → Bonds → Equity. Current phase = equity pressure before entry.""",
        category="cycle",
        catalyst_types=["big_fund_rotation","classic_gameplay","idr_positioning","bond_positioning",
            "equity_pressure","weak_hand_shakeout","fund_entry_setup"],
        activation_keywords=["perfect classic game play","perputaran uang big fund","big fund rotation",
            "idr memborong dulu","rp menguat 200 point","rp bawah 16300","surat hutang memborong",
            "bond rally indonesia","equity pressure","karpet merah equity","market ditekan dulu",
            "weak hand shakeout","ketakutan kecemasan termakan","set up diciptakan fund",
            "jangan tanya waktu","prepare better than predict","classic game play terlihat",
            "action sesuai risk profile","bellwether risk on","tff terfomo fomo","ter fuck fuck",
            "gejolak biasa","riak2x dimaklumkan","koreksi biasa","koreksi april lebih parah",
            "fund 3 step","idr bonds equity","fund entry indonesia"],
        invalidation_keywords=["idr_reverses_weak","bonds_sell_off","fund_exodus","gameplay_broken"],
        beneficiaries={"ihsg":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","TLKM.JK","UNVR.JK","BUMI.JK","WIFI.JK"],
            "safe_haven":["IDR_cash"],"bonds":["SBN","INDO_GOV_BONDS"]},
        fades={"ihsg":["property","high_flyer","weak_hand_stocks"]},
        regime_alignment={"Q3":1.40,"Q4":1.20,"Q2":1.00,"Q1":0.80},
        typical_duration_weeks=8,
        conviction_ceiling=0.80,
        pump_risk=0.15,
        confirmation_signals=["idr_strengthens_sustained","bond_yields_fall","foreign_bond_buying_surge",
            "equity_pressure_intensifies","weak_hand_selling_spike","fund_cash_deployed","ihsg_rebounds_post_pressure"],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# MERGE ALL BATCHES INTO MASTER REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVES: List[NarrativeTemplate] = []
_NARRATIVES.extend(_NARRATIVES_BATCH14)
_NARRATIVES.extend(_NARRATIVES_BATCH15)
_NARRATIVES.extend(_NARRATIVES_BATCH16)

NARRATIVE_BY_NAME: Dict[str, NarrativeTemplate] = {n.name: n for n in _NARRATIVES}

NARRATIVES_BY_CATEGORY: Dict[str, List[NarrativeTemplate]] = {}
for _n in _NARRATIVES:
    NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)

# Convenience exports
__all__ = [
    "NarrativeTemplate",
    "_NARRATIVES",
    "NARRATIVE_BY_NAME",
    "NARRATIVES_BY_CATEGORY",
    "_NARRATIVES_BATCH14",
    "_NARRATIVES_BATCH15",
    "_NARRATIVES_BATCH16",
]
