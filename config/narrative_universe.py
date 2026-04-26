"""config/narrative_universe.py — BATCH 14
Artikel baru Ricky2212 (Apr 2026 extraction):
1.  Gold ATH — historical parallels (1979-80 Iran +300%, 2007-11 GFC $650→$1900, 2019-20 COVID $1500→$2075) + Trump uncertainty + physical hoarding
2.  Bullish or Bullish-it — banking collapse (BBRI/BMRI/BBNI/BBCA), CKPN cycle, structural vs fake bullish
3.  Banjir M2 — M2 money supply vs market cap ratio, bubble indicator, QE→M2→speculation framework
4.  How deep the correction — IHSG 7910→6500 (-17.8%), ATH-20%=6300, pyramid buying, JPY entry, banking/konglo accumulation
5.  Kalau ini jadi blow off — AI narrative, China tech/DeepSeek, Copper rally, Gold monster rally, USD ease, crypto, konglo tech (WIFI/DATA/DOOH/INET/ELIT), BUMI/BRMS/ADII
6.  Sovereign Wealth Fund — Danantara, INA, global SWF comparison, $900B AUM, 7 BUMN consolidated
7.  Bursa saham sudah melewati bear market — IHSG -21%, entry at 6500/6324, banking rebound, MSCI rebalancing, Morgan downgrade→upgrade
8.  Market Come Back + 3 faktor jack up — +3.97% banking-led, 6324/6500 defense, DXY weakness, JPY carry restart, local fund skeptics with cash
9.  It's not the main show — Trump tariff shock therapy (Mexico/Canada 25%, China 10%), 2016-2020 deja vu, flush before main show

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

    # ── ARTICLE 5: Blow Off Top Setup — AI + DeepSeek + Copper + Crypto + Konglo Tech ─
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
# MERGE INSTRUCTIONS — copy-paste ke bawah narrative_universe.py yang sudah ada:
# ═══════════════════════════════════════════════════════════════════════════════
# _NARRATIVES.extend(_NARRATIVES_BATCH14)
# NARRATIVE_BY_NAME.update({n.name: n for n in _NARRATIVES_BATCH14})
# for _n in _NARRATIVES_BATCH14:
#     NARRATIVES_BY_CATEGORY.setdefault(_n.category, []).append(_n)
