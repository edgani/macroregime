"""engines/narrative_engine_ricky_patch.py

PATCH INSTRUCTIONS for engines/narrative_engine.py

This file shows exactly WHAT to add to narrative_engine.py to complete Ricky's framework.
Apply these changes by adding to the NARRATIVES dict and the reactive_ignition() method.

CHANGES:
  1. Add 5 missing Ricky narratives to NARRATIVES dict
  2. Connect config.narrative_universe (TICKER_NARRATIVES + NARRATIVE_QUAD_BIAS)
  3. Use narrative_universe in reactive_ignition() to boost signals from known Ricky tickers
"""

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 1: ADD THESE 5 ENTRIES TO THE NARRATIVES DICT
# In narrative_engine.py, find:
#     "bond_duration_bull": {...},
# Add AFTER that entry:
# ══════════════════════════════════════════════════════════════════════════════

MISSING_RICKY_NARRATIVES = {

    # ── RICKY #1: Bakrie/Konglo Cycle ─────────────────────────────────────────
    # Ricky's most consistent IHSG thesis — konglomerasi end-of-cycle play
    # Articles: Bakrie King is Back Part 1/2/3, Bocil Indicator, Bakrie coal
    # Triggers: Quad Q2, global liquidity flowing to EM, Bakrie group moves
    "konglo_bakrie_cycle": {
        "sectors": ["coal", "oil_gas", "indonesia_mining", "energy_infra", "dry_bulk_shipping"],
        "keywords": [
            "Bakrie", "konglomerat", "BUMI", "DEWA", "BRMS", "BNBR", "ENRG", "ELTY",
            "bocil indicator", "B-indicator", "anak perusahaan naik dulu",
            "kong lo", "konglo cycle", "siklus konglomerat", "aliran uang deras",
            "legend market maker", "store of value", "global liquidity EM",
        ],
        "quad_boost": {"Q1": 0.60, "Q2": 0.90, "Q3": 0.45, "Q4": 0.25},
        "markets": ["ihsg"],
        "ricky_note": "Bakrie cycle = konglomerasi terbesar IHSG. Bocil indicator: anak dulu (DEWA/BRMS/ENRG), baru induk (BUMI/BNBR). End-of-cycle play. Satu tangan di pintu keluar.",
        "tickers": ["BUMI.JK","DEWA.JK","BRMS.JK","BNBR.JK","ENRG.JK","ELTY.JK","LOGI.JK","SHIP.JK"],
        "invalidators": ["Quad Q3/Q4", "USD rally", "global risk-off", "Bakrie debt news"],
    },

    # ── RICKY #2: RKAB Coal Quota Cycle ──────────────────────────────────────
    # Indonesian coal production quota restriction = supply bottleneck
    # Ricky: RKAB revisi terbuka tapi pemerintah hati-hati → harga terjaga
    # Tickers: ITMG, ADRO, PTBA, AADI, HRUM, BUMI
    "rkab_coal_quota_cycle": {
        "sectors": ["coal", "indonesia_mining"],
        "keywords": [
            "RKAB", "coal quota", "revisi RKAB", "produksi batubara", "Dirjen Minerba",
            "kuota batubara", "coal production limit", "RKAB dibuka", "coal war",
            "war premium", "geopolitics coal", "energy security",
        ],
        "quad_boost": {"Q1": 0.55, "Q2": 0.85, "Q3": 0.65, "Q4": 0.35},
        "markets": ["ihsg", "commodity"],
        "ricky_note": "RKAB revisi terbuka tapi pemerintah hati-hati → supply terkontrol = harga terjaga. War premium on top. ITMG, AADI, ADRO beneficiary.",
        "tickers": ["ITMG.JK","AADI.JK","ADRO.JK","PTBA.JK","HRUM.JK","BUMI.JK"],
        "invalidators": ["China coal demand collapse", "coal price sub-$100", "RKAB dikasih bebas"],
    },

    # ── RICKY #3: Indonesia Offshore Drilling Ramp ────────────────────────────
    # Prabowo's 1 juta BPD 2030 target = decade-long OSV/offshore demand
    # Separate from commodity supercycle — this is STRUCTURAL capex
    # Ricky: OBMD monopoly, SHIP FSO monopoly, LEAD OSV no.2
    "indonesia_offshore_drilling_ramp": {
        "sectors": ["osv_hulu", "oil_services", "oil_distribution"],
        "keywords": [
            "1 juta BPD", "satu juta barel", "SKK Migas", "KKKS drilling",
            "offshore Indonesia", "hulu migas", "IPA convention", "investasi migas",
            "Prabowo energy target", "pertamina offshore", "blok migas", "wilayah kerja",
            "day rates OSV", "FSO FPSO Indonesia", "anti-slip drilling",
        ],
        "quad_boost": {"Q1": 0.65, "Q2": 0.85, "Q3": 0.70, "Q4": 0.45},
        "markets": ["ihsg"],
        "ricky_note": "Target 1 juta BPD = pipeline proyek drilling decade. OBMD: satu-satunya kimia anti-slip (monopoly). SHIP: satu-satunya FSO/FPSO listed. LEAD: OSV no.2 recovery. Foreign entry = signal.",
        "tickers": ["OBMD.JK","SHIP.JK","LEAD.JK","WINS.JK","MEDC.JK","AKRA.JK"],
        "invalidators": ["Oil price <$50", "pemerintah kurangi target drilling", "IKN capex redirect"],
    },

    # ── RICKY #4: Rating Agencies Geopolitical Pressure ──────────────────────
    # Ricky's thesis: Moodys/Fitch/S&P as geopolitical weapon against Indonesia
    # Operasi Penurunan Indonesia — nickel processing, Danantara, fiscal
    # Creates buying opportunities when downgrade causes panic selling
    "rating_agencies_geopolitical_pressure": {
        "sectors": ["nickel", "indonesia_mining", "banking"],
        "keywords": [
            "Moodys downgrade", "Fitch downgrade", "S&P", "rating agencies",
            "operasi penurunan", "nickel processing ban", "Danantara", "fiscal",
            "Indonesia sovereign", "APBN", "geopolitical downgrade", "credit outlook",
            "foreign debt", "capital flight narrative", "rating pressure",
        ],
        "quad_boost": {"Q1": 0.40, "Q2": 0.50, "Q3": 0.75, "Q4": 0.70},
        "markets": ["ihsg", "forex"],
        "ricky_note": "Downgrade bisa jadi senjata geopolitik. Moodys/Fitch bergerak saat Indonesia tegas soal nikel. Panic selling = BUY opportunity untuk yang paham. ANTM, INCO, HRUM beneficiary dari narasi perlawanan.",
        "tickers": ["ANTM.JK","INCO.JK","HRUM.JK","NCKL.JK","MDKA.JK"],
        "invalidators": ["Actual fiscal deterioration", "current account crisis", "IDR freefall >17000"],
    },

    # ── RICKY #5: Ricky Sesi Recovery Framework ───────────────────────────────
    # Ricky's 3-stage market recovery cycle for IHSG
    # Sesi 1: Pain/bottom (nobody believes, foreign exit done)
    # Sesi 2: Banking/consumer recovery (BBCA, BBRI stabilize)
    # Sesi 3: King is Back (coal/OSV/commodity re-ignite, B-indicator fires)
    # Signal: BDI + ITMG foreign flow + OSV day rates = Sesi 3 confirmation
    "ihsg_sesi_recovery_cycle": {
        "sectors": ["banking_ihsg", "coal", "osv_hulu", "dry_bulk_shipping"],
        "keywords": [
            "CKPN selesai", "stage 3 NPL", "BBRI net buy", "foreign net buy banking",
            "BDI naik", "OSV day rates", "ITMG foreign flow", "coal foreign buy",
            "sesi recovery", "king is back", "B indicator", "bocil indicator coal",
            "disbelieve rally", "pain is over", "IHSG bottom", "banking NPL peak",
            "ultra mikro done", "mikro selesai",
        ],
        "quad_boost": {"Q1": 0.85, "Q2": 0.80, "Q3": 0.45, "Q4": 0.35},
        "markets": ["ihsg"],
        "ricky_note": "Sesi 1=Pain done. Sesi 2=Banking stabilize (BBCA/BBRI foreign net buy 2+ days). Sesi 3=King is Back (BDI up, ITMG foreign buy, OSV day rates rise). Q4→Q1 = maximum Sesi 3 probability.",
        "tickers": ["BBCA.JK","BBRI.JK","BMRI.JK","ITMG.JK","ADRO.JK","SHIP.JK","LEAD.JK","PSSI.JK"],
        "invalidators": ["CKPN stage 3 not complete", "foreign net sell 3+ days", "BDI <1200"],
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 2: NARRATIVE SPILLOVER ADDITIONS
# Add to NARRATIVE_SPILLOVER dict in narrative_engine.py:
# ══════════════════════════════════════════════════════════════════════════════

MISSING_RICKY_SPILLOVER = {
    "konglo_bakrie_cycle": [
        ("rkab_coal_quota_cycle", 0.70),          # Bakrie = BUMI = coal = RKAB
        ("indonesia_commodity_supercycle", 0.60),   # broader commodity bid
        ("indonesia_offshore_drilling_ramp", 0.40), # Bakrie has SHIP exposure
    ],
    "rkab_coal_quota_cycle": [
        ("konglo_bakrie_cycle", 0.65),
        ("indonesia_commodity_supercycle", 0.55),
        ("china_reopening_commodity", 0.45),
    ],
    "indonesia_offshore_drilling_ramp": [
        ("indonesia_commodity_supercycle", 0.55),
        ("shipping_supply_crisis", 0.60),           # OSV = shipping sector
        ("energy_transition", 0.30),
    ],
    "rating_agencies_geopolitical_pressure": [
        ("dxy_bearish_em_recovery", 0.50),           # downgrade → IDR pressure → recovery play
        ("indonesia_commodity_supercycle", 0.40),    # nickel/mineral focus
        ("indonesia_banking_recovery", 0.45),        # banking affected by sovereign rating
    ],
    "ihsg_sesi_recovery_cycle": [
        ("indonesia_banking_recovery", 0.80),         # Sesi 2 = banking
        ("indonesia_commodity_supercycle", 0.70),     # Sesi 3 = commodity
        ("konglo_bakrie_cycle", 0.60),               # Sesi 3 = konglo
        ("shipping_supply_crisis", 0.55),            # OSV/BDI = Sesi 3 signal
        ("dxy_bearish_em_recovery", 0.65),           # foreign flow = EM recovery
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 3: NARRATIVE UNIVERSE CONNECTOR
# Add this function to NarrativeEngine class in narrative_engine.py
# Call it from reactive_ignition() to boost scores for Ricky-mapped tickers
# ══════════════════════════════════════════════════════════════════════════════

NARRATIVE_UNIVERSE_CONNECTOR_CODE = '''
    def _boost_from_ricky_universe(
        self,
        ignition_scores: dict,
        prices: dict,
    ) -> dict:
        """
        Cross-reference reactive ignition with Ricky's narrative_universe.py.
        If tickers mapped to a Ricky narrative are moving, boost that narrative score.
        
        This connects config/narrative_universe.TICKER_NARRATIVES to live scores.
        """
        try:
            from config.narrative_universe import TICKER_NARRATIVES, NARRATIVE_QUAD_BIAS
        except ImportError:
            return ignition_scores
        
        # For each Ricky article, check if its tickers are moving
        article_signals = {}
        for ticker, articles in TICKER_NARRATIVES.items():
            s = prices.get(ticker)
            if s is None: continue
            s = pd.to_numeric(s, errors="coerce").dropna()
            if len(s) < 22: continue
            ret_1m = float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0.0
            ret_5d = float(s.iloc[-1]/s.iloc[-6]-1) if len(s)>=6 else 0.0
            # Signal: short-term momentum on Ricky-mapped tickers
            if abs(ret_5d) > 0.03 or abs(ret_1m) > 0.08:
                for article in articles:
                    article_signals[article] = article_signals.get(article, 0) + abs(ret_5d)*2 + abs(ret_1m)
        
        # Map article signals back to engine narrative names
        article_to_narrative = {
            # Bakrie articles → konglo_bakrie_cycle
            "bakrie___the_king_is_back": "konglo_bakrie_cycle",
            "bakrie___the_king_is_back__part_2": "konglo_bakrie_cycle",
            "bakrie___the_king_is_back__part_3___bocil_indicato": "konglo_bakrie_cycle",
            "all_eyes_on_bumi_now": "konglo_bakrie_cycle",
            "bumi___pemanasan_sebelum_ada___ledakan": "konglo_bakrie_cycle",
            # RKAB articles → rkab_coal_quota_cycle
            "rkab_coal_journey": "rkab_coal_quota_cycle",
            "coal_war_cycle_2026": "rkab_coal_quota_cycle",
            "energy_store_of_value_2026": "indonesia_commodity_supercycle",
            # Rating agencies
            "operasi_penurunan_rating_agencies": "rating_agencies_geopolitical_pressure",
            # OSV/offshore
            "logindo___the_desset_of_oil_narrative": "indonesia_offshore_drilling_ramp",
            "soci___sekoci_terakhir_menuju_hilir": "indonesia_offshore_drilling_ramp",
            # Banking/recovery
            "dari_denial_ke_panik_fed": "ihsg_sesi_recovery_cycle",
            "ath_20_bottom_behaviour": "ihsg_sesi_recovery_cycle",
            "disbelieve_psychology": "ihsg_sesi_recovery_cycle",
        }
        
        for article, strength in article_signals.items():
            narr_name = article_to_narrative.get(article)
            if narr_name and narr_name in ignition_scores:
                # Boost existing score
                ignition_scores[narr_name] = min(
                    1.0,
                    ignition_scores[narr_name] + float(np.tanh(strength * 2)) * 0.20
                )
        
        return ignition_scores
'''

# ══════════════════════════════════════════════════════════════════════════════
# HOW TO APPLY THIS PATCH TO narrative_engine.py:
#
# STEP 1: Add MISSING_RICKY_NARRATIVES entries to the NARRATIVES dict
#   Find: "bond_duration_bull": {...},
#   After that, add all entries from MISSING_RICKY_NARRATIVES
#
# STEP 2: Add MISSING_RICKY_SPILLOVER entries to NARRATIVE_SPILLOVER dict
#   Find: "bond_duration_bull": [...],
#   After that, add all entries from MISSING_RICKY_SPILLOVER
#
# STEP 3: Add _boost_from_ricky_universe() method to NarrativeEngine class
#   Copy the method from NARRATIVE_UNIVERSE_CONNECTOR_CODE
#
# STEP 4: In reactive_ignition() method, before returning, add:
#   scores = self._boost_from_ricky_universe(scores, prices)
#   (where scores is the dict of narrative → strength values)
#
# STEP 5: Do the same for narrative_engine_v3.py (same changes, same location)
# ══════════════════════════════════════════════════════════════════════════════

print("Ricky narrative patch ready.")
print("Add 5 narratives: konglo_bakrie_cycle, rkab_coal_quota_cycle,")
print("  indonesia_offshore_drilling_ramp, rating_agencies_geopolitical_pressure,")
print("  ihsg_sesi_recovery_cycle")
print("Connect narrative_universe.py via _boost_from_ricky_universe()")
