"""engines/narrative_universe_connector.py

Connects config/narrative_universe.py (50 Ricky articles) to live price signals.

HOW IT WORKS:
  1. Reads TICKER_NARRATIVES: {ticker → [article_ids]}
  2. For each ticker, checks 5d and 21d price momentum
  3. If ticker is moving significantly → articles mapped to it get "activated"
  4. Returns: active_articles dict with scores + quad implications

INTEGRATION:
  Called from narrative_engine.py reactive_ignition() to boost article-level signals.
  Article-level → maps to engine-level themes via ARTICLE_TO_THEME mapping.

USAGE:
  connector = NarrativeUniverseConnector()
  result = connector.score(prices, quad_str)
  # result = {
  #   "active_articles": {"bakrie___the_king_is_back": 0.72, ...},
  #   "active_themes": {"konglo_bakrie_cycle": 0.72, "indonesia_commodity_supercycle": 0.55, ...},
  #   "top_signals": [("bakrie___the_king_is_back", 0.72, ["BUMI.JK", "DEWA.JK"]), ...],
  #   "ihsg_cycle_stage": "sesi_2" | "sesi_3" | "sesi_1" | None,
  # }
"""
from __future__ import annotations
import math
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Article → Engine Theme mapping ────────────────────────────────────────────
# Maps Ricky article IDs → narrative_engine.py NARRATIVES dict keys
ARTICLE_TO_THEME: Dict[str, str] = {
    # Bakrie/Konglo cycle
    "bakrie___the_king_is_back":                          "konglo_bakrie_cycle",
    "bakrie___the_king_is_back__part_2":                  "konglo_bakrie_cycle",
    "bakrie___the_king_is_back__part_3___bocil_indicato": "konglo_bakrie_cycle",
    "all_eyes_on_bumi_now":                               "konglo_bakrie_cycle",
    "bumi___pemanasan_sebelum_ada___ledakan":              "konglo_bakrie_cycle",
    "dewa_masuk_terminal_pertama___bumi_baru_saja_panas":  "konglo_bakrie_cycle",
    "menebak_kemana_bumi_berlabuh_di_msci":               "konglo_bakrie_cycle",
    "menjemur_kering_kepemilikan_cic___menguji_thesis_2": "konglo_bakrie_cycle",
    "broksum___putaran_besar_permainan_bandaran":          "konglo_bakrie_cycle",
    # Coal / RKAB
    "coal_war_cycle_2026":         "rkab_coal_quota_cycle",
    "rkab_coal_journey":           "rkab_coal_quota_cycle",
    "energy_store_of_value_2026":  "rkab_coal_quota_cycle",
    # Offshore / OSV
    "logindo___the_desset_of_oil_narrative": "indonesia_offshore_drilling_ramp",
    "soci___sekoci_terakhir_menuju_hilir":   "indonesia_offshore_drilling_ramp",
    "soci_the_beautiful_of_funda___findi_and_narrative": "indonesia_offshore_drilling_ramp",
    # MSCI / Indexing
    "msci___it_s_all_about_push_rank":   "indonesia_commodity_supercycle",
    "msci_freeze_feb2026":               "indonesia_commodity_supercycle",
    "msci_greenlight_trump_tariff":      "indonesia_commodity_supercycle",
    "bukti_uang_mengalir_indexing":      "indonesia_commodity_supercycle",
    "angka_indah_free_float":            "indonesia_commodity_supercycle",
    "high_shareholding_concentration":   "indonesia_commodity_supercycle",
    # Iran / Geopolitics / Energy
    "certain_uncertain_iran_war":  "hard_assets_scarcity",
    "kharg_island_terbakar":       "hard_assets_scarcity",
    "perundingan_iran_gagal":      "hard_assets_scarcity",
    "konspirasi_kekuasaan_uang":   "hard_assets_scarcity",
    "siklus_perang_riskon":        "hard_assets_scarcity",
    "commodity_late_cycle_history":"hard_assets_scarcity",
    # Fed / Macro
    "dari_denial_ke_panik_fed":   "fed_pivot_liquidity",
    "fed_vs_data_reality":        "fed_pivot_liquidity",
    "taco_trump_chickens_out":    "fed_pivot_liquidity",
    "taco_chapter2_fed_rally":    "fed_pivot_liquidity",
    "pola_sama_2025_2026":        "fed_pivot_liquidity",
    # Rating agencies / Indonesia macro
    "operasi_penurunan_rating_agencies": "rating_agencies_geopolitical_pressure",
    "hero_blame_08nomics":               "rating_agencies_geopolitical_pressure",
    "tiga_senjata_08nomics":             "rating_agencies_geopolitical_pressure",
    "berjibaku_market_regulation":       "rating_agencies_geopolitical_pressure",
    # IHSG Recovery cycle
    "ath_20_bottom_behaviour":   "ihsg_sesi_recovery_cycle",
    "disbelieve_psychology":     "ihsg_sesi_recovery_cycle",
    "bottom_anatomy_pain":       "ihsg_sesi_recovery_cycle",
    "crash_itu_terjadi_saat_tak_terduga": "ihsg_sesi_recovery_cycle",
    "terkukung_memikirkan_exit_di_puncak": "ihsg_sesi_recovery_cycle",
    # Psychology (maps to broad shipping/commodity)
    "narrative_play_liat_lk_psikologi_pasar": "shipping_supply_crisis",
    "logindo___the_desset_of_oil_narrative":  "shipping_supply_crisis",
    "pintar_memberikan_anda_privilege":        "shipping_supply_crisis",
    "the_pain_makes_it_all_worth_it":         "ihsg_sesi_recovery_cycle",
    "thesis_investasi_bukan_ramalan_dan_saya_tidak_pern": "ihsg_sesi_recovery_cycle",
    "at_the_end___anda_cukup_menjadi_yang_terbaik_dari":  "ihsg_sesi_recovery_cycle",
    "pak___koq_anda_bodoh_amat_sih___cerita_kekalahan_y": "ihsg_sesi_recovery_cycle",
    "okas_keterbukaan_restrukturisasi": "indonesia_commodity_supercycle",
    "mengapa_narrative_sebagai_narrative": "ihsg_sesi_recovery_cycle",
    "kekuatan_ucapan_menggerakkan_alam_bawah_sadar": "ihsg_sesi_recovery_cycle",
}

# Ricky Sesi detection — which tickers signal each stage
SESI_SIGNALS = {
    "sesi_1": {
        "desc": "Pain/Bottom — nobody believes, foreign exit still happening",
        "tickers": ["^JKSE"],
        "condition": "price_falling_hard",  # IHSG down >15% from ATH
    },
    "sesi_2": {
        "desc": "Banking stabilize — BBCA/BBRI foreign net buy 2+ days",
        "tickers": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
        "condition": "rs_positive",         # banking stocks +RS vs IHSG
    },
    "sesi_3": {
        "desc": "King is Back — BDI up, coal/OSV foreign buy, konglo cycle",
        "tickers": ["ITMG.JK", "ADRO.JK", "SHIP.JK", "LEAD.JK", "PSSI.JK", "BUMI.JK"],
        "condition": "momentum_ignition",   # coal/OSV strong positive RS
    },
}


class NarrativeUniverseConnector:
    """
    Connects Ricky's 50 articles to live price signals.
    Detects which articles are 'active' based on their mapped tickers moving.
    """

    def __init__(self):
        self._loaded = False
        self._ticker_narratives: Dict[str, List[str]] = {}
        self._quad_bias: Dict[str, Optional[str]] = {}
        self._priority: Dict[str, int] = {}
        self._narratives_meta: Dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            from config.narrative_universe import (
                TICKER_NARRATIVES, NARRATIVE_QUAD_BIAS, NARRATIVE_PRIORITY, NARRATIVES
            )
            self._ticker_narratives = TICKER_NARRATIVES
            self._quad_bias         = NARRATIVE_QUAD_BIAS
            self._priority          = NARRATIVE_PRIORITY
            # Extract lightweight meta (no content field — too large)
            for k, v in NARRATIVES.items():
                self._narratives_meta[k] = {
                    "title":    v.get("title", ""),
                    "category": v.get("category", ""),
                    "themes":   v.get("themes", []),
                    "tickers":  v.get("tickers", []),
                    "quad_bias": v.get("quad_bias"),
                    "priority": v.get("priority", 5),
                }
            self._loaded = True
            logger.info(f"NarrativeUniverseConnector: loaded {len(self._ticker_narratives)} tickers, "
                        f"{len(self._narratives_meta)} articles")
        except ImportError as e:
            logger.warning(f"narrative_universe not found: {e}")

    def score(
        self,
        prices: Dict[str, pd.Series],
        quad_str: str = "Q3",
        benchmark: str = "^JKSE",
    ) -> dict:
        """
        Score all 50 Ricky articles by their ticker momentum.
        Returns active articles, theme boosts, and Sesi cycle stage.
        """
        if not self._loaded:
            return {"active_articles": {}, "active_themes": {}, "top_signals": [], "ihsg_cycle_stage": None}

        # Get benchmark return
        bench = prices.get(benchmark) or prices.get("EIDO")
        bench_ret_5d = self._ret(bench, 5) or 0.0
        bench_ret_21d = self._ret(bench, 21) or 0.0

        # Score each article by its ticker movements
        article_scores: Dict[str, float] = {}
        article_driving_tickers: Dict[str, List[str]] = {}

        for ticker, article_ids in self._ticker_narratives.items():
            s = prices.get(ticker)
            if s is None:
                continue
            ret5  = self._ret(s, 5)  or 0.0
            ret21 = self._ret(s, 21) or 0.0
            rs5   = ret5  - bench_ret_5d
            rs21  = ret21 - bench_ret_21d

            # Signal: RS positive AND momentum (both 5d and 21d positive RS)
            signal = 0.0
            if rs5 > 0.02 and rs21 > 0.03:
                # Strong accumulation
                signal = float(np.tanh(rs5 / 0.05) * 0.6 + np.tanh(rs21 / 0.08) * 0.4)
            elif rs5 > 0.01 or rs21 > 0.02:
                # Mild positive RS
                signal = float(np.tanh((rs5 + rs21) / 0.08) * 0.4)
            elif rs5 < -0.03 and rs21 < -0.04:
                # Bearish signal (short thesis active)
                signal = float(np.tanh((rs5 + rs21) / 0.10) * (-0.3))

            if abs(signal) < 0.05:
                continue

            for article_id in article_ids:
                # Weight by article priority
                priority = self._priority.get(article_id, 5)
                priority_mult = 0.6 + 0.4 * (priority / 10.0)

                # Quad compatibility boost
                quad_bias = self._quad_bias.get(article_id)
                quad_match = 1.0
                if quad_bias:
                    if "→" in quad_bias:
                        quads = quad_bias.split("→")
                        quad_match = 1.2 if quad_str in quads else 0.7
                    else:
                        quad_match = 1.3 if quad_bias == quad_str else 0.6

                final_signal = signal * priority_mult * quad_match

                if article_id not in article_scores:
                    article_scores[article_id] = 0.0
                    article_driving_tickers[article_id] = []

                # Accumulate (multiple tickers → stronger signal)
                article_scores[article_id] = float(np.clip(
                    article_scores[article_id] + final_signal * 0.5, -1.0, 1.0
                ))
                if abs(final_signal) > 0.1:
                    article_driving_tickers[article_id].append(ticker)

        # Filter to active only (abs > threshold)
        active_articles = {k: v for k, v in article_scores.items() if abs(v) > 0.15}

        # Map to engine themes
        active_themes: Dict[str, float] = {}
        for article_id, score in active_articles.items():
            theme = ARTICLE_TO_THEME.get(article_id)
            if theme:
                if theme not in active_themes:
                    active_themes[theme] = 0.0
                # Take max (strongest article drives the theme)
                active_themes[theme] = max(active_themes[theme], score)

        # Rank top signals
        top_signals = sorted(
            [(art_id, score, article_driving_tickers.get(art_id, []))
             for art_id, score in active_articles.items() if score > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Detect Ricky Sesi stage
        ihsg_cycle_stage = self._detect_sesi(prices, quad_str)

        return {
            "active_articles":  active_articles,
            "active_themes":    active_themes,
            "top_signals":      top_signals,
            "ihsg_cycle_stage": ihsg_cycle_stage,
            "article_count":    len(active_articles),
            "theme_count":      len(active_themes),
        }

    def _detect_sesi(self, prices: Dict[str, pd.Series], quad_str: str) -> Optional[str]:
        """
        Detect which Ricky IHSG recovery Sesi is active.
        Sesi 1: Pain/bottom
        Sesi 2: Banking stabilize
        Sesi 3: King is Back (coal/OSV/konglo)
        """
        # Sesi 3 check: coal + OSV RS strongly positive
        sesi3_tickers = ["ITMG.JK","ADRO.JK","SHIP.JK","LEAD.JK","BUMI.JK"]
        sesi3_scores = []
        bench = prices.get("^JKSE") or prices.get("EIDO")
        bench21 = self._ret(bench, 21) or 0.0
        for t in sesi3_tickers:
            s = prices.get(t)
            if s is None: continue
            rs = (self._ret(s, 21) or 0.0) - bench21
            sesi3_scores.append(rs)
        if sesi3_scores and np.median(sesi3_scores) > 0.05:
            return "sesi_3"

        # Sesi 2 check: banking RS positive
        sesi2_tickers = ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK"]
        sesi2_scores = []
        for t in sesi2_tickers:
            s = prices.get(t)
            if s is None: continue
            rs = (self._ret(s, 21) or 0.0) - bench21
            sesi2_scores.append(rs)
        if sesi2_scores and np.median(sesi2_scores) > 0.02:
            return "sesi_2"

        # Sesi 1 check: IHSG down hard, all stocks negative
        if bench is not None:
            b = pd.to_numeric(bench, errors="coerce").dropna()
            if len(b) >= 252:
                drawdown = float(b.iloc[-1] / b.tail(252).max() - 1)
                if drawdown < -0.12:
                    return "sesi_1"

        return None

    def _ret(self, s, n: int) -> Optional[float]:
        if s is None: return None
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 1: return None
        b = float(s.iloc[-n-1])
        if abs(b) < 1e-9: return None
        r = float(s.iloc[-1] / b - 1)
        return r if math.isfinite(r) else None

    def get_article_summary(self, article_id: str) -> dict:
        """Return lightweight article metadata (no full content)."""
        return self._narratives_meta.get(article_id, {})

    def get_active_article_titles(self, prices: Dict[str, pd.Series], quad_str: str = "Q3") -> List[Tuple[str, float, str]]:
        """Returns [(article_title, score, category), ...] for UI display."""
        result = self.score(prices, quad_str)
        out = []
        for art_id, score, _ in result.get("top_signals", []):
            meta = self._narratives_meta.get(art_id, {})
            title = meta.get("title", art_id.replace("_", " ").title())
            cat   = meta.get("category", "")
            out.append((title, score, cat))
        return out
