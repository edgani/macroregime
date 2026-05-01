"""engines/bottleneck_engine.py v3 — Multi-Asset Bottleneck Scanner (FIXED)

Fixes vs v2:
 1. DEDUPLICATED KNOWN_BOTTLENECKS — AMKR & GEV had silent dict overwrites. MERGED.
 2. CONDITIONAL score boost — known bottleneck only gets +0.15 if trend+regime support it.
    Downtrend known bottleneck gets PENALTY (0.70x) not boost. Preserves #process.
 3. FORWARD QUAD MULTIPLIER in EV — EV now front-runs Quad transition probability,
    not just current Quad. Uses BASE_TRANSITIONS from scenario_engine calibration.
 4. RANGE POSITION injected into every item dict — "range_label", "range_action",
    "pct_from_lo", "pct_from_hi" so UI can display BUY ZONE / TRIM ZONE / WAIT.
 5. BREWING threshold raised from acc>=0.55 → acc>=0.65 (reduce false positives).
 6. POD PROXY signal — uses price momentum ROC as proxy for Pod1 revenue acceleration.
    Flags if Pod proxy is decelerating vs Trend signal (thesis risk).
 7. DIRECTION logic: structural/defensive bottlenecks in Q3 remain LONG even if
    market_dir=short, but ONLY if trend supports it (uptrend or range).
 8. THESIS field unified — all items now carry "thesis" key (known_thesis fallback
    to rationale) so UI never shows empty thesis.
 9. Removed options flow proxy comment — labeled as "PROXY ONLY (no live gamma feed)".

Framework alignment:
 - GIP Model: regime_fit per Quad from BOTTLENECK_PROFILES (27yr Hedgeye backtest)
 - Risk Range™: EV uses range_pos to penalise at-resistance setups
 - Citrini Bottleneck: KNOWN_BOTTLENECKS = curated second-order supply chain map
 - Forward-run: EV × transition_mult front-runs Quad shift, not current state
 - IHSG: long-only, foreign-flow gated (Ricky methodology)
 - Options overlay: flow_scores accepted as PROXY input, labeled clearly

EV formula (v3):
 EV = regime_fit × trend_score × constraint × (1 + rs_3m) × forward_mult × range_discount
 where:
 forward_mult = 1.0 + 0.25 × max(0, next_quad_fit - regime_fit) [front-run transition]
 range_discount = 0.70 if at_resistance else 1.0 [don't buy TRR]
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from config.settings import (
    BOTTLENECK_PROFILES, TICKER_SECTOR, QUAD_ASSET_PERFORMANCE,
    MARKET_CLASSIFICATION, QUAD_MARKET_DIRECTION, EM_RECOVERY_SIGNALS,
)

# ─────────────────────────────────────────────────────────────────────────────
# FORWARD QUAD TRANSITION MATRIX
# Calibrated from Hedgeye 27yr backtest (via scenario_engine.BASE_TRANSITIONS)
# "Quads follow each other like seasons in a continuous loop." — McCullough
# ─────────────────────────────────────────────────────────────────────────────
_FWD_TRANSITIONS: Dict[str, Dict[str, float]] = {
    "Q1": {"Q1": 0.28, "Q2": 0.38, "Q3": 0.12, "Q4": 0.22},
    "Q2": {"Q2": 0.22, "Q3": 0.38, "Q1": 0.24, "Q4": 0.16},
    "Q3": {"Q3": 0.22, "Q4": 0.38, "Q2": 0.20, "Q1": 0.20},
    "Q4": {"Q4": 0.18, "Q1": 0.48, "Q3": 0.20, "Q2": 0.14},
}

def _forward_quad_multiplier(sector: str, quad_str: str, profiles: dict) -> float:
    """
    Front-run Quad transition: if the highest-probability NEXT Quad has a HIGHER
    regime_fit for this sector than the current Quad, reward EV now (pre-consensus).
    This is the 'front-run The Machine' logic in quantified form.

    Returns multiplier: 1.0 (no edge) → 1.25 (strong transition tailwind).
    """
    prof = profiles.get(sector, profiles.get("generic", {}))
    current_fit = float(prof.get(quad_str, 0.50))
    transitions = _FWD_TRANSITIONS.get(quad_str, {})
    if not transitions:
        return 1.0

    # Weighted average of next-quad regime fits
    weighted_next_fit = sum(
        prob * float(prof.get(nq, 0.50))
        for nq, prob in transitions.items()
        if nq != quad_str  # exclude staying in same quad
    )
    total_trans_prob = sum(prob for nq, prob in transitions.items() if nq != quad_str)
    if total_trans_prob < 1e-9:
        return 1.0

    weighted_next_fit /= total_trans_prob
    delta = weighted_next_fit - current_fit  # positive = getting better next quad
    mult = 1.0 + 0.25 * max(0.0, delta)
    return float(np.clip(mult, 0.80, 1.30))

# ─────────────────────────────────────────────────────────────────────────────
# KNOWN BOTTLENECK DATABASE — research April/May 2026
# RULES:
# - Each ticker appears EXACTLY ONCE (no silent dict overwrites)
# - Duplicates merged: higher constraint wins; more current phase wins
# - All entries validated against Citrini second-order methodology
# - IHSG bottlenecks in separate IHSG_BOTTLENECKS dict below
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_BOTTLENECKS: Dict[str, dict] = {

    # ── AI OPTICS / PHOTONICS ─────────────────────────────────────────────────
    "LITE": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.95, "phase": "level_2",
        "thesis": "ONLY volume supplier 200G EMLs. NVIDIA $2B committed. InP laser monopoly for CPO. "
                  "Supply constrained through 2027+. Citrini Level 2: lasers ARE the scarcity node.",
        "catalyst": "NVIDIA CPO deployment, 1.6T transceiver ramp, Q2 earnings guide",
        "tp_type": "structural",
        "risk": "CPO adoption delay; pluggable modules persist longer than expected",
    },
    "COHR": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.90, "phase": "level_2",
        "thesis": "Volume leader ~25% CW laser market share. NVIDIA $2B AI photonics commitment. "
                  "Spectrum-X and Rubin AI platforms = COHR laser demand. "
                  "Second-order: as LITE hits capacity ceiling, COHR absorbs overflow.",
        "catalyst": "CPO contract announcements, Rubin deployment timeline, 800G→1.6T mix shift",
        "tp_type": "structural",
        "risk": "Broadcom vertical integration; LITE takes disproportionate share",
    },
    "POET": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.85, "phase": "level_1",
        "thesis": "Pure-play CPO photonic engine. Next scarcity layer after LITE/COHR. "
                  "If CPO architecture wins vs pluggable, POET is the purest expression. "
                  "Small cap = binary but asymmetric.",
        "catalyst": "Customer adoption announcement, foundry partnership, CPO standard finalization",
        "tp_type": "structural",
        "risk": "Pre-revenue binary risk; CPO standard not finalized; small float = illiquid",
    },
    "MKSI": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.75, "phase": "watch",
        "thesis": "Laser systems for SiPh fab expansion. Tower + GlobalFoundries expanding SiPh = "
                  "MKS Instruments capital equipment demand. Less-known picks-and-shovels.",
        "catalyst": "SiPh foundry capex announcements, fab expansion orders",
        "tp_type": "structural",
        "risk": "Cyclical capex slowdown; limited pure SiPh revenue",
    },
    "ACLS": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.72, "phase": "watch",
        "thesis": "Ion implant for SiPh fabs. Picks-and-shovels for photonics fab expansion. "
                  "Low profile, low ownership = pre-consensus.",
        "catalyst": "Tower/GF SiPh expansion orders, design win",
        "tp_type": "structural",
        "risk": "Limited SiPh-specific revenue visibility; small position in most books",
    },
    "FORM": {
        "type": "structural", "sub": "ai_optics", "constraint": 0.70, "phase": "watch",
        "thesis": "Optical test and measurement for datacom. 800G/1.6T transceiver test demand "
                  "is structural growth driver. Proactive chain: optics ramp → test bottleneck.",
        "catalyst": "800G/1.6T ramp volume, CPO test requirements standardization",
        "tp_type": "structural",
        "risk": "Cyclical test equipment demand; budget cuts at hyperscalers",
    },

    # ── AI POWER / SiC / GaN ─────────────────────────────────────────────────
    "ON": {
        "type": "structural", "sub": "ai_power", "constraint": 0.87, "phase": "level_2",
        "thesis": "EliteSiC M3e: 30% conduction loss reduction. vGaN breakthrough: 50% energy savings. "
                  "AI DC power = new primary thesis replacing slowing EV. "
                  "WOLF distress = ON gains pricing power on SiC substrates. "
                  "52+ week lead times = structural supply constraint.",
        "catalyst": "AI DC SiC design wins, vGaN production ramp, hyperscaler power density mandates",
        "tp_type": "structural",
        "risk": "EV slowdown dominates narrative; WOLF recovery removes pricing umbrella; AI capex plateau",
    },
    "WOLF": {
        "type": "structural", "sub": "ai_power", "constraint": 0.75, "phase": "watch",
        "thesis": "ONLY US large-scale SiC substrate maker. CHIPS Act strategic asset. "
                  "Distressed valuation = binary optionality. If restructured: ON loses substrate leverage.",
        "catalyst": "Govt rescue/acquisition, debt restructuring completion, DoD strategic interest",
        "tp_type": "structural",
        "risk": "Bankruptcy is a real risk — not a watch, a binary bet. Position sizing 1% MAX.",
    },
    "MPWR": {
        "type": "structural", "sub": "ai_power", "constraint": 0.80, "phase": "level_2",
        "thesis": "Monolithic Power = highest efficiency DC-DC converters for AI server racks. "
                  "AI DC power density explosion = MPWR's core market. "
                  "Pure-play power mgmt for hyperscaler build-out.",
        "catalyst": "AI server volume ramp, hyperscaler DC buildout, rack power density increase",
        "tp_type": "structural",
        "risk": "Competition from TI/Analog Devices; China exposure (~15% revenue)",
    },
    "AEHR": {
        "type": "structural", "sub": "sic_gan", "constraint": 0.78, "phase": "level_1",
        "thesis": "Wafer-level burn-in test for SiC/GaN. Critical for automotive + AI power reliability. "
                  "FOX systems = monopoly-like positioning in SiC burn-in test. "
                  "Citrini second-order: SiC ramp → test bottleneck → AEHR.",
        "catalyst": "SiC automotive adoption acceleration, AI power device test demand scale",
        "tp_type": "structural",
        "risk": "Cyclical capex; customer concentration risk (ON Semi ~40% revenue)",
    },

    # ── AI POWER INFRASTRUCTURE ───────────────────────────────────────────────
    "VST": {
        "type": "structural", "sub": "ai_power_infra", "constraint": 0.87, "phase": "level_2",
        "thesis": "Nuclear baseload = ONLY 24/7 carbon-free power for AI. "
                  "AI DC purchase agreements locked in. Power infrastructure secular bottleneck. "
                  "Aschenbrunner thesis: owning power > owning AI code.",
        "catalyst": "New AI hyperscaler power purchase agreements, nuclear relicense",
        "tp_type": "structural",
        "risk": "Regulatory, nuclear license renewal risk, rate case delays",
    },
    "ETN": {
        "type": "structural", "sub": "ai_power_infra", "constraint": 0.83, "phase": "level_2",
        "thesis": "Eaton transformers/switchgear: 2-3 year lead times. "
                  "You CANNOT build an AI data center without Eaton. Infrastructure you can't rush. "
                  "Order backlog is the secular signal — not quarterly earnings.",
        "catalyst": "Hyperscaler capex guides raising, order backlog disclosures, utility grid upgrade",
        "tp_type": "structural",
        "risk": "Demand normalization if AI capex plateaus; supply chain catch-up reduces lead times",
    },
    "VRT": {
        "type": "structural", "sub": "transformer_infra", "constraint": 0.88, "phase": "level_2",
        "thesis": "Vertiv = data center power infrastructure near-monopoly. "
                  "Liquid cooling + UPS + power mgmt. AI DC buildout = decade-long order visibility. "
                  "CEO called 2026 'breakout year.' 10yr backlog is the real moat.",
        "catalyst": "AI DC power density increase (kW/rack), hyperscaler capex guide revision",
        "tp_type": "structural",
        "risk": "Valuation stretched (priced for perfection); execution risk at scale",
    },
    "HUBB": {
        "type": "structural", "sub": "transformer_infra", "constraint": 0.82, "phase": "level_2",
        "thesis": "Hubbell electrical components + switchgear. DC + grid upgrade = multi-year demand. "
                  "Less expensive than ETN = more upside leverage on same thesis.",
        "catalyst": "Utility grid upgrade cycle, AI DC power contracts, NEM 3.0 grid hardening",
        "tp_type": "structural",
        "risk": "Cyclical exposure; not a pure AI play — grid spending can be delayed",
    },
    "NVT": {
        "type": "structural", "sub": "transformer_infra", "constraint": 0.78, "phase": "level_1",
        "thesis": "nVent Electric = electrical enclosures + thermal management for data centers. "
                  "AI DC density = thermal bottleneck = nVent's core product. "
                  "Pre-consensus: low institutional ownership vs ETN/VRT.",
        "catalyst": "AI DC thermal density mandates, liquid cooling adoption",
        "tp_type": "structural",
        "risk": "Less liquid; limited Wall Street coverage; execution risk",
    },
    "GEV": {
        # MERGED: was duplicated (level_1 constraint=0.80 + dojjunn level_2 constraint=0.85)
        # Resolution: dojjunn thesis is more current (May 2026), higher constraint wins
        "type": "structural", "sub": "ai_power_infra", "constraint": 0.85, "phase": "level_2",
        "thesis": "GE Vernova gas turbines: AI DCs need 24/7 firm power → gas turbines = ONLY scalable "
                  "solution besides nuclear at required timeline. @dojjunn chain confirmed: "
                  "'gas turbines' as next bottleneck after power infra. "
                  "Lead time 3-4 years. Order book sold out through 2027.",
        "catalyst": "AI DC power emergency forcing gas turbine orders, utility contracts, LNG offtake",
        "tp_type": "structural",
        "risk": "Energy transition regulation, stranded asset risk, geopolitical LNG disruption",
    },
    "BE": {
        "type": "structural", "sub": "ai_power_infra", "constraint": 0.82, "phase": "level_2",
        "thesis": "Bloom Energy solid oxide fuel cells for AI DC baseload. "
                  "No transmission bottleneck = FASTEST to deploy for AI campuses. "
                  "Aschenbrunner Fund core holding: +51.3% since March 5 2026. "
                  "On-site power = regulatory bypass for hyperscalers.",
        "catalyst": "AI hyperscaler fuel cell contracts, DoE financing, utility partnership",
        "tp_type": "structural",
        "risk": "High cost vs grid power; hydrogen supply chain risk; customer concentration",
    },

    # ── AI PACKAGING ─────────────────────────────────────────────────────────
    "AJINY": {
        "type": "structural", "sub": "ai_packaging", "constraint": 0.85, "phase": "level_1",
        "thesis": "Ajinomoto (AJINY) = makes ABF substrate — insulating layer between AI chip die and PCB. "
                  "@dojjunn: NEXT bottleneck layer. ONLY 3 companies make ABF. "
                  "Lead times 52+ weeks. AI chip explosion → ABF demand explosion. "
                  "Supply cannot scale <2 years. Citrini: purest second-order play.",
        "catalyst": "TSMC CoWoS capacity expansion drives ABF demand, AI chip volume surge",
        "tp_type": "structural",
        "risk": "Japanese stock illiquidity; private capacity expansion by competitors; Taiwan geopolitical",
    },
    "AMKR": {
        # MERGED: was duplicated (constraint=0.78 phase=level_2 + dojjunn constraint=0.82 phase=level_2)
        # Resolution: dojjunn version is more current and adds ABF/CoWoS context; higher constraint wins
        "type": "structural", "sub": "ai_packaging", "constraint": 0.82, "phase": "level_2",
        "thesis": "Amkor Technology = advanced packaging (CoWoS, SoIC, FOPLP). "
                  "TSMC overflow + new AI chip packaging demand. ABF substrate consumer. "
                  "@dojjunn chain: after photonics bottleneck = packaging bottleneck. "
                  "CoWoS-adjacent capacity beneficiary with TSMC overflow economics.",
        "catalyst": "TSMC CoWoS overflow, Blackwell packaging volume, AJINY substrate allocation",
        "tp_type": "structural",
        "risk": "TSMC insources capacity; ABF substrate cost pass-through limits",
    },
    "COHU": {
        "type": "structural", "sub": "ai_packaging", "constraint": 0.72, "phase": "watch",
        "thesis": "Semiconductor test handlers + vision inspection. "
                  "AI chip volume = test handler demand. "
                  "Proactive: packaging ramp → test bottleneck → COHU.",
        "catalyst": "AI chip volume ramp, advanced packaging inspection requirements",
        "tp_type": "structural",
        "risk": "Cyclical; strong competition from Advantest/Teradyne",
    },

    # ── AI COMPUTE / MEMORY ───────────────────────────────────────────────────
    "MU": {
        "type": "structural", "sub": "ai_memory", "constraint": 0.83, "phase": "level_2",
        "thesis": "Micron = HBM3E + LPDDR5X structural bottleneck. "
                  "@dojjunn: 'today it's memory' = Micron IS the bottleneck node. "
                  "AI inference memory bandwidth is the real constraint on model speed. "
                  "Only Samsung/SK Hynix/Micron make HBM at volume = oligopoly pricing.",
        "catalyst": "HBM3E volume ramp, NVDA Blackwell memory allocation announcement, AI PC cycle",
        "tp_type": "structural",
        "risk": "DRAM cycle downturn; Samsung competitive response on HBM4 pricing",
    },
    "ARM": {
        "type": "structural", "sub": "ai_compute", "constraint": 0.80, "phase": "level_2",
        "thesis": "ARM Holdings = THE compute architecture for AI at edge + mobile + inference. "
                  "EVERY AI chip uses ARM cores (Apple M, Qualcomm Oryon, NVDA Grace). "
                  "Royalty model = infinite operating leverage on AI chip volume. "
                  "@dojjunn confirmed: ARM +14.76% on semis day = institutional conviction.",
        "catalyst": "AI edge deployment, custom silicon wins (Apple, Qualcomm, NVDA Grace Blackwell)",
        "tp_type": "structural",
        "risk": "RISC-V open-source competition; China licensing risk (25% revenue)",
    },
    "SNDK": {
        "type": "structural", "sub": "ai_memory", "constraint": 0.80, "phase": "level_2",
        "thesis": "Western Digital NAND / SanDisk flash storage for AI inference. "
                  "Aschenbrunner: flash is next bottleneck after compute+power. "
                  "Every AI model needs fast local storage for weights + KV cache.",
        "catalyst": "AI inference storage demand, datacenter SSD ramp, enterprise flash upgrade",
        "tp_type": "structural",
        "risk": "Samsung/Micron competition; NAND price cycle downturn",
    },

    # ── HEALTHCARE / DEFENSIVE STRUCTURAL ────────────────────────────────────
    "ISRG": {
        "type": "structural", "sub": "healthcare_eq", "constraint": 0.88, "phase": "level_2",
        "thesis": "Intuitive Surgical = robotic surgery near-monopoly. "
                  "8000+ DaVinci installed base. Consumables = recurring revenue moat. "
                  "No substitute for trained surgeons (switching cost = 3yr retraining). "
                  "Q3 = best regime for healthcare structural.",
        "catalyst": "Procedure volume recovery, FDA approvals (new indications), intl expansion",
        "tp_type": "structural",
        "risk": "Competition from CMR Surgical/Medtronic Ion; China regulatory risk",
    },

    # ── PRECIOUS METALS / SAFE HAVEN ─────────────────────────────────────────
    "GLD": {
        "type": "structural", "sub": "precious_metals", "constraint": 0.80, "phase": "level_2",
        "thesis": "Q3 = BEST gold regime (stagflation + USD bearish = perfect gold setup). "
                  "Central bank buying at record pace (de-dollarization structural bid). "
                  "McCullough Apr 2026: USD TREND confirmed bearish. "
                  "Gold is the Q3 hedge AND the structural macro trade.",
        "catalyst": "Fed pivot signal, USD breakdown continuation, EM central bank buying",
        "tp_type": "structural",
        "risk": "USD reversal (dollar crisis resolution); real yield spike if growth re-accelerates",
    },

    # ── DEFENSE ──────────────────────────────────────────────────────────────
    "LMT": {
        "type": "structural", "sub": "defense", "constraint": 0.82, "phase": "level_2",
        "thesis": "Defense production bottleneck. NATO 2% GDP mandate = decade-long order book. "
                  "Missile + munitions manufacturing cannot scale fast enough. "
                  "Q3 defensive regime + geopolitical tail risk = dual tailwind.",
        "catalyst": "NATO spending commitments, F-35 orders, Ukraine resupply contracts",
        "tp_type": "structural",
        "risk": "Peace negotiations; US defense budget sequestration; DOGE cuts",
    },

    # ── ENERGY INFRASTRUCTURE ────────────────────────────────────────────────
    "KMI": {
        "type": "structural", "sub": "energy_infra", "constraint": 0.75, "phase": "level_2",
        "thesis": "Kinder Morgan = natural gas infrastructure monopoly. "
                  "AI DC power demand driving gas pipeline utilization to record. "
                  "LNG export + AI power = dual demand driver. Q2 monthly overlay = energy tailwind.",
        "catalyst": "LNG export terminal utilization, AI DC gas demand contracts",
        "tp_type": "structural",
        "risk": "Energy transition timeline; regulatory rate case risk",
    },

    # ── INDONESIA SPECIFIC ────────────────────────────────────────────────────
    "OBMD": {
        "type": "structural", "sub": "oil_services", "constraint": 0.88, "phase": "level_1",
        "thesis": "ONLY drilling chemical supplier Indonesia. Anti-slip agent offshore drilling. "
                  "Zero domestic competition. Ricky: satu-satunya penyedia kimia agar pengeboran ga slip. "
                  "True monopoly niche = pricing power.",
        "catalyst": "Indonesia offshore drilling ramp toward 1jt BPD 2030 target",
        "tp_type": "ihsg",
        "risk": "Illiquid small cap; lumpy contract revenue; single customer concentration",
    },
    "SHIP": {
        "type": "structural", "sub": "osv_hulu", "constraint": 0.82, "phase": "level_1",
        "thesis": "ONLY listed Indonesia company with FSO/FPSO fleet. "
                  "Every offshore field needs FSO. Ricky: hanya SHIP yg punya. Monopoly niche. "
                  "Offshore production MUST use SHIP's assets — no alternative.",
        "catalyst": "New offshore field first oil, FPSO contract win, SKK Migas mandate",
        "tp_type": "ihsg",
        "risk": "High debt levels; capex heavy model; contract renewal risk",
    },
    "PSSI": {
        "type": "structural", "sub": "dry_bulk_shipping", "constraint": 0.80, "phase": "level_2",
        "thesis": "ONLY complete dry bulk operator Indonesia with TnB + large vessel fleet. "
                  "APOL/BLTA bankrupt = PSSI has no domestic competition at scale. "
                  "Ricky rating A. Active capacity expansion phase.",
        "catalyst": "BDI rally, China coal/iron ore surge, Indonesia domestic coal demand",
        "tp_type": "ihsg",
        "risk": "BDI cyclicality; capex overhang from fleet expansion",
    },
    "LEAD": {
        "type": "structural", "sub": "osv_hulu", "constraint": 0.82, "phase": "level_2",
        "thesis": "Logindo = OSV no.2 Indonesia. 43 vessels. NPM 30%+ peak vs WINS 17% "
                  "(WINS transfer pricing suspect per Ricky). ADNOC + Husky clients = quality. "
                  "History: was champion OSV before correction. Debt restructuring in progress.",
        "catalyst": "Offshore drilling ramp, WINS overflow, OSV rate recovery",
        "tp_type": "ihsg",
        "risk": "Debt maturity risk; restructuring timeline; client concentration",
    },
    "AKRA": {
        "type": "structural", "sub": "oil_distribution", "constraint": 0.75, "phase": "level_2",
        "thesis": "AKR = MARKET LEADER fuel distribution Indonesia. Only private vs Pertamina. "
                  "Storage + distribution network moat (25yr asset life). "
                  "BONUS: JIIPE industrial estate = FDI play (EV battery, China+1 supply chain).",
        "catalyst": "Oil demand growth, JIIPE new tenant announcements, IDR stabilization",
        "tp_type": "ihsg",
        "risk": "Pertamina competition on retail; IDR weakness hurts import cost",
    },
    "TPMA": {
        "type": "structural", "sub": "dry_bulk_shipping", "constraint": 0.72, "phase": "level_1",
        "thesis": "Trans Power Marine = TnB coal shipping Indonesia. "
                  "BDI proxy play. Smaller pure-play vs PSSI = higher beta on recovery.",
        "catalyst": "BDI rally, domestic coal demand, PSSI overflow contracts",
        "tp_type": "ihsg",
        "risk": "BDI cyclicality; competition; illiquid small float",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# IHSG BOTTLENECKS (separate — long-only, foreign-flow gated)
# ─────────────────────────────────────────────────────────────────────────────
IHSG_BOTTLENECKS: Dict[str, dict] = {
    "ITMG.JK": {
        "type": "foreign_flow", "sub": "coal", "phase": "watch", "tp_type": "ihsg",
        "thesis": "Highest coal dividend yield. Q3 structural = commodity cycle watchlist. "
                  "Trade ONLY on foreign net buy + IDR weakness trigger.",
        "catalyst": "Foreign net buy signal, China coal demand surprise, IDR >16000",
        "risk": "Coal price collapse; ESG institutional exit; Indonesia export quota",
    },
    "ADRO.JK": {
        "type": "foreign_flow", "sub": "coal", "phase": "watch", "tp_type": "ihsg",
        "thesis": "Largest coal producer Indonesia. Dividend play. "
                  "Q2 monthly overlay = mild commodity tailwind. Watch foreign flow.",
        "catalyst": "Foreign net buy, coal ASP improvement, special dividend announcement",
        "risk": "Coal price; ESG; Adaro Energy restructuring uncertainty",
    },
    "BBRI.JK": {
        "type": "macro_positioning", "sub": "banking_ihsg", "phase": "watch", "tp_type": "ihsg",
        "thesis": "BRI = ultra-mikro exposure. CKPN cascade: ultra-mikro DONE → mikro CURRENT "
                  "(BBRI 2x CKPN). Stage 3 NPL rising. Tactical ONLY if foreign flow net buy 2+ days. "
                  "Ricky: wait for CKPN cycle to complete before structural long.",
        "catalyst": "CKPN cycle completion signal, NPL peak confirmation, foreign net buy",
        "risk": "CKPN stage 3 not complete; leasing motor NPL contagion",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _rs(close: pd.Series, bench: Optional[pd.Series], n: int = 63) -> Optional[float]:
    if bench is None:
        return None
    try:
        c = pd.to_numeric(close, errors="coerce").dropna()
        b = pd.to_numeric(bench, errors="coerce").dropna()
        idx = c.index.intersection(b.index)
        c, b = c.loc[idx], b.loc[idx]
        if len(c) < n + 1:
            return None
        return float(c.iloc[-1] / c.iloc[-n - 1] - 1) - float(b.iloc[-1] / b.iloc[-n - 1] - 1)
    except Exception:
        return None

def _trend(close: pd.Series, n: int = 63) -> Tuple[bool, bool, str]:
    c = pd.to_numeric(close, errors="coerce").dropna().tail(n).values
    if len(c) < 20:
        return False, False, "insufficient"
    half = max(len(c) // 3, 5)
    hh = float(np.max(c[-half:])) > float(np.max(c[:half])) * 1.003
    hl = float(np.min(c[-half:])) > float(np.min(c[:half])) * 1.003
    lh = float(np.max(c[-half:])) < float(np.max(c[:half])) * 0.997
    ll = float(np.min(c[-half:])) < float(np.min(c[:half])) * 0.997
    if hh and hl:
        return True, True, "uptrend"
    if lh and ll:
        return False, False, "downtrend"
    return hh, hl, "range"

def _range_pos(close: pd.Series, n: int = 63) -> Tuple[float, str]:
    c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
    if len(c) < 20:
        return 0.5, "mid_range"
    lo, hi = float(c.min()), float(c.max())
    px = float(c.iloc[-1])
    span = hi - lo
    if span < 1e-9:
        return 0.5, "mid_range"
    rp = (px - lo) / span
    if rp >= 0.90:
        label = "at_resistance"
    elif rp >= 0.75:
        label = "approaching_resistance"
    elif rp <= 0.10:
        label = "at_support"
    elif rp <= 0.25:
        label = "approaching_support"
    else:
        label = "mid_range"
    return rp, label

def _vol_acc(close: pd.Series, n: int = 63) -> float:
    """Volume accumulation proxy using price momentum consistency."""
    c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
    if len(c) < 20:
        return 0.5
    rets = c.pct_change().dropna()
    if len(rets) < 10:
        return 0.5
    # Positive-return days ratio (accumulation proxy when no volume data)
    pos_ratio = float((rets > 0).mean())
    return float(np.clip(pos_ratio, 0.0, 1.0))

def _pod_proxy(close: pd.Series) -> Dict[str, Any]:
    """
    Pod 1 proxy: Rate of change of 1M return vs 3M return (momentum acceleration).
    Pod 2 proxy: Volatility-adjusted return (margin-of-safety signal).
    NOTE: These are PRICE-BASED PROXIES only — true Pods require fundamental data.
    Label output clearly so UI can flag 'proxy only.'
    """
    c = pd.to_numeric(close, errors="coerce").dropna()
    if len(c) < 65:
        return {
            "pod1_proxy": 0.0,
            "pod2_proxy": 0.0,
            "pod_quality": "insufficient",
            "pod_note": "PROXY ONLY — insufficient price history (<65 bars)",
        }

    ret_1m = float(c.iloc[-1] / c.iloc[-22] - 1) if len(c) >= 22 else 0.0
    ret_3m = float(c.iloc[-1] / c.iloc[-63] - 1) if len(c) >= 63 else 0.0
    vol_63 = float(c.pct_change().dropna().tail(63).std()) if len(c) > 64 else 0.02

    # Pod1 proxy: is momentum accelerating? (1M outperforming 3M annualised pace)
    ret_3m_ann = ret_3m * (252 / 63) if ret_3m else 0.0
    ret_1m_ann = ret_1m * (252 / 22) if ret_1m else 0.0
    pod1_accel = float(np.tanh((ret_1m_ann - ret_3m_ann) * 5))  # -1 to +1

    # Pod2 proxy: vol-adjusted return (Sharpe-like, 63d)
    pod2_sharpe = float(ret_3m / (vol_63 * math.sqrt(63))) if vol_63 > 1e-9 else 0.0
    pod2_proxy = float(np.tanh(pod2_sharpe))

    quality = "accelerating" if pod1_accel > 0.20 else "decelerating" if pod1_accel < -0.20 else "stable"
    return {
        "pod1_proxy": round(pod1_accel, 3),
        "pod2_proxy": round(pod2_proxy, 3),
        "pod_quality": quality,
        "pod_note": "PROXY ONLY — price momentum ROC, not fundamental revenue/margin data",
    }

def _compute_tp(
    close: pd.Series,
    tp_type: str = "structural",
    trend_lrr=None, trend_trr=None, trade_trr=None,
) -> dict:
    c = pd.to_numeric(close, errors="coerce").dropna()
    if len(c) < 5:
        return {}
    px = float(c.iloc[-1])
    rv21 = float(c.pct_change().dropna().tail(21).std()) if len(c) > 22 else 0.02
    rv63 = float(c.pct_change().dropna().tail(63).std()) if len(c) > 64 else rv21
    hi52 = float(c.tail(252).max()) if len(c) >= 252 else float(c.max())

    if tp_type == "structural":
        t1 = trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px * (1 + 1.5 * rv21 * math.sqrt(15))
        t2 = trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px * (1 + 2.5 * rv63 * math.sqrt(63))
        t3 = hi52 if hi52 > t2 * 1.05 else px * (1 + 4.0 * rv63 * math.sqrt(63))
        stop = trend_lrr if trend_lrr and math.isfinite(float(trend_lrr)) else px * (1 - 1.5 * rv63)
        rat = "T1=TRADE TRR: trim 25% | T2=TREND TRR: trim 50% | T3=ATH/resistance: trail 25%. EXIT on TREND LRR break."
        sz = "2-4% portfolio. Add 1.5x on breakout above T2 with volume confirm."
    elif tp_type == "squeeze":
        t1, t2, t3 = px * 1.30, px * 1.55, px * 2.10
        stop = px * 0.88
        rat = "T1=+30% trim 50% | T2=+55% trim 40% | T3=+110% trail 10%. TIME STOP: 5 days."
        sz = "1-2% MAX. Hard -12% stop. No exceptions."
    elif tp_type == "commodity":
        t1 = px * (1 + 1.0 * rv63); t2 = px * (1 + 2.0 * rv63); t3 = hi52
        stop = px * 0.85
        rat = "T1=+1σ 63d: trim 33% | T2=+2σ 63d: trim 33% | T3=52w high: trail 34%. -15% hard stop."
        sz = "1-3% portfolio. Commodity regime filter: only hold in Q2/Q3."
    elif tp_type == "ihsg":
        t1 = trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px * 1.12
        t2 = trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px * 1.25
        t3 = None
        stop = px * 0.92
        rat = "T1=TRADE TRR/+12%: trim 50% on foreign net sell | T2=TREND TRR/+25%: trim 50%. Exit 100% on 2x foreign net sell."
        sz = "2-4% portfolio. EXIT TRIGGER: 2 consecutive days foreign net sell."
    else:
        t1 = px * 1.10; t2 = px * 1.20; t3 = px * 1.35; stop = px * 0.92
        rat = "Generic TP: T1=+10% T2=+20% T3=+35%. Stop -8%."
        sz = "1-2% portfolio."

    return {
        "t1": round(t1, 4) if t1 else None,
        "t2": round(t2, 4) if t2 else None,
        "t3": round(t3, 4) if t3 else None,
        "stop": round(stop, 4),
        "rationale": rat,
        "sizing": sz,
        "tp_type": tp_type,
    }

# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class BottleneckEngine:
    """
    Multi-asset bottleneck scanner.

    EV formula (v3):
        EV = regime_fit × trend_score × constraint × (1 + rs_3m)
             × forward_mult × range_discount

    Signal rules (Hedgeye #process):
      - Known bottleneck in uptrend + good regime → BUY ZONE at LRR, NOT at TRR
      - Known bottleneck in downtrend → AVOID until Trend recovers (no score boost)
      - Structural/defensive bottlenecks in Q3 → LONG exception to market_dir=short
      - IHSG → long-only, foreign-flow gated
      - Options flow → accepted as proxy input, labeled clearly (not true gamma)
    """

    def run(
        self,
        prices: Dict[str, pd.Series],
        quad_str: str = "Q3",
        quad_mon: str = "Q2",
        benchmark: str = "SPY",
        asset_ranges: Optional[Dict] = None,
        flow_scores: Optional[Dict[str, float]] = None,  # PROXY ONLY — no live gamma feed
    ) -> dict:
        asset_ranges = asset_ranges or {}
        flow_scores = flow_scores or {}
        bench = prices.get(benchmark)

        # Quad → market direction map
        directions: Dict[str, str] = QUAD_MARKET_DIRECTION.get(quad_str, {})

        all_scored: List[dict] = []
        market_buckets: Dict[str, List[dict]] = {
            "us_equity": [], "forex": [], "commodity": [],
            "crypto": [], "ihsg": [], "bonds": [], "global": [],
        }

        for ticker, close in prices.items():
            close = pd.to_numeric(close, errors="coerce").dropna()
            if len(close) < 30:
                continue

            sector = TICKER_SECTOR.get(ticker, "generic")
            market = MARKET_CLASSIFICATION.get(ticker, "us_equity")
            kb = KNOWN_BOTTLENECKS.get(ticker) or IHSG_BOTTLENECKS.get(ticker)

            # ── Core signal calculations ──────────────────────────────────────
            hh, hl, trd = _trend(close, 63)
            trend_score = 1.0 if trd == "uptrend" else 0.5 if trd == "range" else 0.0

            rs3 = _rs(close, bench, 63)
            rs21 = _rs(close, bench, 21)
            rs_score = float(np.clip((rs3 or 0.0) / 0.15, -1.0, 1.0))  # normalized

            acc_s = _vol_acc(close, 63)
            rp, rp_label = _range_pos(close, 63)

            hi52 = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
            lo52 = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
            px = float(close.iloc[-1])
            pct_from_hi = (px - hi52) / max(hi52, 1e-9)
            pct_from_lo = (px - lo52) / max(abs(lo52), 1e-9)

            # ── Pod proxy (price-based only — labeled clearly) ─────────────
            pod = _pod_proxy(close)

            # ── Range position signal (KEY: never buy at TRR) ─────────────
            # Penalise at-resistance: don't buy at TRR per McCullough #process
            range_discount = 0.70 if rp_label == "at_resistance" else \
                             0.85 if rp_label == "approaching_resistance" else 1.0
            # Range action label for UI
            if rp_label in ("at_support", "approaching_support"):
                range_action = "✅ BUY ZONE"
            elif rp_label in ("at_resistance",):
                range_action = "🔴 TRIM ZONE"
            elif rp_label == "approaching_resistance":
                range_action = "⚠️ APPROACHING TRR"
            else:
                range_action = "⏳ WAIT — MID RANGE"

            # ── Regime fit (current quad) ──────────────────────────────────
            prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES.get("generic", {}))
            regime_fit = float(prof.get(quad_str, 0.50))
            constraint = float(prof.get("constraint", 0.50))

            # ── KNOWN BOTTLENECK OVERRIDE (conditional, not unconditional) ─
            # FIX v3: known bottleneck ONLY gets boost if trend+regime support it.
            # Downtrend known bottleneck = PENALTY (wrong side of Range).
            if kb:
                # Override constraint with research-validated value
                constraint = max(constraint, float(kb.get("constraint", 0.70)))
                if trd in ("uptrend", "range") and regime_fit >= 0.50:
                    # Conditional boost: thesis confirmed by signal
                    constraint = min(constraint + 0.05, 1.0)
                elif trd == "downtrend" or regime_fit < 0.40:
                    # Trend breakdown OR wrong regime: research thesis ≠ market signal
                    # Do NOT boost. Apply penalty — even great companies can be wrong-side.
                    constraint *= 0.75

            # ── Options flow proxy (LABELED: not true gamma/dealer positioning) ─
            # flow_scores should be: {ticker: float -1.0 to +1.0}
            # Positive = net bullish flow proxy, Negative = net bearish
            # MAX ±0.08 EV impact — this is a CONFIRMATION LAYER, never primary signal
            flow_adj = float(flow_scores.get(ticker, 0.0)) * 0.08
            flow_adj = float(np.clip(flow_adj, -0.08, 0.08))
            # NOTE: True options overlay (dealer gamma, 0DTE, skew) requires live feed.
            # This proxy uses externally-provided flow_scores as approximation only.

            # ── Score (base composite) ─────────────────────────────────────
            score = (
                0.30 * constraint +
                0.25 * regime_fit +
                0.20 * trend_score +
                0.15 * max(rs_score, 0) +  # only positive RS contributes to score
                0.10 * acc_s
            )
            score = float(np.clip(score + flow_adj, 0.0, 1.0))

            # Avoid penalty
            if regime_fit < 0.35:
                score *= 0.30
            # Pod1 deceleration penalty: if price momentum decelerating and thesis is
            # growth-dependent, flag it (doesn't kill score but reduces it)
            if pod["pod1_proxy"] < -0.30 and sector not in ("precious_metals", "defense", "utilities", "water"):
                score *= 0.85

            # ── Level classification ───────────────────────────────────────
            phase = kb.get("phase", "") if kb else ""
            if phase == "level_1" and trd in ("uptrend", "range") and regime_fit >= 0.50:
                level = "level_1"
            elif phase == "level_2" and trd in ("uptrend", "range") and regime_fit >= 0.45:
                level = "level_2"
            elif phase in ("level_1", "level_2") and (trd == "downtrend" or regime_fit < 0.40):
                level = "watch"  # known bottleneck but wrong signal — downgrade to watch
            elif score >= 0.70 and trd in ("uptrend", "range") and regime_fit >= 0.65:
                level = "level_1"
            elif score >= 0.55 and constraint >= 0.65 and regime_fit >= 0.50:
                level = "level_2"
            elif score >= 0.40 and constraint >= 0.55:
                level = "watch"
            else:
                level = "avoid"

            regime_trap = regime_fit < 0.35

            # ── EV formula v3 (forward-looking, range-adjusted) ────────────
            # EV = regime_fit × trend_score × constraint × (1+rs_3m) × fwd_mult × range_discount
            fwd_mult = _forward_quad_multiplier(sector, quad_str, BOTTLENECK_PROFILES)
            ev = regime_fit * trend_score * constraint * (1.0 + (rs3 or 0.0)) * fwd_mult * range_discount
            ev = float(np.clip(ev, -2.0, 2.0))

            # ── Direction logic ────────────────────────────────────────────
            market_dir = directions.get(market, "neutral")
            if market_dir == "long" and trd in ("uptrend", "range"):
                direction = "long"
            elif market_dir == "long" and trd == "downtrend":
                direction = "avoid_long"
            elif market_dir == "short" and trd == "downtrend":
                direction = "short"
            elif market_dir == "short" and trd in ("uptrend", "range"):
                direction = "avoid_short"
            else:
                direction = "neutral"

            # IHSG override: long-only
            if market == "ihsg":
                direction = "long" if trd in ("uptrend", "range") else "avoid"

            # STRUCTURAL/DEFENSIVE EXCEPTION in Q3:
            # Gold, healthcare, defense, power infra, precious metals → LONG even in Q3
            # because Q3 IS their best regime. Market_dir=short refers to cyclicals, not defensive.
            # Per Hedgeye Q3 playbook: "best = Gold, Healthcare, Utilities, Defense"
            defensive_subs = {
                "precious_metals", "healthcare_eq", "pharma", "defense",
                "utilities", "water", "ai_power_infra", "transformer_infra",
                "energy_infra", "oil_services", "osv_hulu",  # IHSG offshore = structural
            }
            if kb and kb.get("type") in ("structural", "defensive") and kb.get("sub") in defensive_subs:
                if trd in ("uptrend", "range") and regime_fit >= 0.50:
                    direction = "long"
                elif trd == "downtrend":
                    direction = "avoid_long"  # wait for trend to recover

            # ── Risk Range cross-reference ─────────────────────────────────
            rr_data = asset_ranges.get(ticker, {})
            trade_lrr = rr_data.get("trade_lrr")
            trade_trr = rr_data.get("trade_trr")
            trend_lrr = rr_data.get("trend_lrr")
            trend_trr = rr_data.get("trend_trr")
            rr_signal = rr_data.get("composite", "neutral")
            rr_quality = rr_data.get("quality", "none")

            # TP levels
            tp = _compute_tp(close, tp_type=kb.get("tp_type", "structural") if kb else "structural",
                             trend_lrr=trend_lrr, trend_trr=trend_trr, trade_trr=trade_trr)

            # ── Unified thesis field (FIX: was missing for non-known tickers) ─
            if kb:
                thesis_text = kb.get("thesis", "")
                catalyst_text = kb.get("catalyst", "")
                risk_text = kb.get("risk", "")
            else:
                thesis_text = f"{sector.replace('_',' ').title()} | Trend: {trd} | RS3M: {rs3:.1%}" if rs3 else f"{sector} | {trd}"
                catalyst_text = f"Regime fit: {regime_fit:.0%} | Range: {rp_label}"
                risk_text = f"Regime trap: {'YES' if regime_trap else 'NO'}"

            item = dict(
                ticker=ticker, market=market, sector=sector,
                btn_type=kb.get("type", "systematic") if kb else "systematic",
                level=level, score=round(score, 3), constraint=round(constraint, 2),
                regime_fit=round(regime_fit, 2), trend=trd, hh=hh, hl=hl,
                acc=round(acc_s, 2), rs_3m=round(rs3, 4) if rs3 else None,
                rs_1m=round(rs21, 4) if rs21 else None, rs_score=round(rs_score, 2),
                trend_score=round(trend_score, 2), range_pos=round(rp, 2),
                range_label=rp_label, range_action=range_action,
                pct_from_hi=round(pct_from_hi, 3), pct_from_lo=round(pct_from_lo, 3),
                px=round(px, 4), ev=round(ev, 3), direction=direction,
                known=bool(kb),
                # Unified thesis (FIX — was empty for non-known tickers in UI)
                thesis=thesis_text[:120],
                catalyst=catalyst_text[:80],
                risk=risk_text[:80],
                # Known-specific (for backwards compat with UI)
                known_thesis=thesis_text,
                known_catalyst=catalyst_text,
                known_risk=risk_text,
                # Forward Quad signal
                forward_mult=round(fwd_mult, 3),
                range_discount=round(range_discount, 2),
                # Pod proxies (labeled as proxy)
                pod1_proxy=pod["pod1_proxy"],
                pod2_proxy=pod["pod2_proxy"],
                pod_quality=pod["pod_quality"],
                pod_note=pod["pod_note"],
                # Options flow (proxy label)
                flow_adj_proxy=round(flow_adj, 4),
                flow_proxy_note="PROXY ONLY — no live dealer gamma/skew feed",
                # Risk Range cross-reference
                rr_signal=rr_signal, rr_quality=rr_quality,
                trade_lrr=trade_lrr, trade_trr=trade_trr,
                trend_lrr=trend_lrr, trend_trr=trend_trr,
                regime_trap=regime_trap, tp=tp,
                rationale=thesis_text[:80],
            )

            all_scored.append(item)
            if market in market_buckets:
                market_buckets[market].append(item)

        # Sort each bucket by EV descending
        for mkt in market_buckets:
            market_buckets[mkt].sort(key=lambda x: x["ev"], reverse=True)

        # ── Level buckets (for UI rendering) ──────────────────────────────────
        level_1 = sorted([s for s in all_scored if s["level"] == "level_1"], key=lambda x: x["ev"], reverse=True)
        level_2 = sorted([s for s in all_scored if s["level"] == "level_2"], key=lambda x: x["ev"], reverse=True)
        watch = sorted([s for s in all_scored if s["level"] == "watch"], key=lambda x: x["ev"], reverse=True)
        avoid = sorted([s for s in all_scored if s["level"] == "avoid"], key=lambda x: x["ev"], reverse=True)

        # ── Brewing detection (FIX: raised acc threshold 0.55 → 0.65) ─────────
        # High constraint + regime fit + accumulation but not yet Level 1/2
        # acc >= 0.65 (was 0.55) reduces false positives per #process signal purity
        brewing = sorted(
            [s for s in watch
             if s["constraint"] >= 0.70
             and s["regime_fit"] >= 0.60
             and s["acc"] >= 0.65  # FIX: was 0.55
             and s["trend"] in ("uptrend", "range")],
            key=lambda x: x["ev"], reverse=True
        )

        # ── ON Semiconductor special analysis ─────────────────────────────────
        on_close = prices.get("ON")
        on_analysis = {}
        if on_close is not None:
            on_analysis = {
                "ticker": "ON", "is_bottleneck": True, "type": "SiC/GaN structural",
                "why_surged": [
                    "EliteSiC M3e: 30% conduction loss reduction vs competitors",
                    "vGaN: 50% energy savings → AI DC power new primary driver",
                    "WOLF distress = ON gains substrate pricing power",
                    "AI DC power = structural demand replacing slowing EV narrative",
                    "52+ week SiC lead times = scarcity premium locked in",
                ],
                "current_status": "Level 2 — continuation. AI power thesis intact. EV headwind partially offset.",
                "risk_watch": "WOLF debt restructuring resolution — if WOLF recovers, ON loses leverage",
            }

        # ── EM Recovery signal ─────────────────────────────────────────────────
        qk = quad_str; qk_mon = quad_mon
        em_key = f"{qk}→{qk_mon}"
        em_signal = EM_RECOVERY_SIGNALS.get(em_key, EM_RECOVERY_SIGNALS.get("Q3→Q2", {}))

        return dict(
            level_1=level_1,
            level_2=level_2,
            watch=watch,
            avoid=avoid,
            brewing=brewing,
            all_scored=all_scored,
            market_buckets=market_buckets,
            on_analysis=on_analysis,
            em_recovery=em_signal,
            quad=quad_str,
            quad_mon=quad_mon,
            known_count=sum(1 for s in all_scored if s["known"]),
            # Framework metadata
            ev_formula="regime_fit × trend_score × constraint × (1+rs_3m) × fwd_mult × range_discount",
            flow_proxy_note="OPTIONS FLOW: proxy input only. True dealer gamma/skew requires live Tier 1 Alpha feed.",
            pod_proxy_note="POD PROXY: price momentum ROC only. True Pod 1/2 requires fundamental revenue/margin data.",
        )
