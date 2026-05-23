"""engines/bottleneck_kb_v2.py — MASSIVE Bottleneck Knowledge Base v36

Encodes thought process from ALL accounts in bottleneck_reference.json:
  • aleabitoreddit (Photonics/AI optics specialist)
  • citrini (Thematic bottleneck scanner)
  • ParadisLabs (L6 Space + Quantum)
  • zephyr_z9 (Japan precision manufacturing)
  • jukan05 (Materials + helium plays)
  • HyperTechInvest (Diversified AI infra)
  • PhotonCap (Photonics fund)

For each ticker: account, layer, role, thesis, mechanism, causation chain.

This REPLACES the smaller embedded KB in alpha_layer_v35.py. The alpha layer
will IMPORT from this file at runtime — single source of truth.

Reference: bottleneck_reference.json (Edward's curated list)
"""
from __future__ import annotations
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════
# ACCOUNT THOUGHT PROCESS — Full set with lens + thesis
# ═══════════════════════════════════════════════════════════════════════

ACCOUNT_THOUGHT_PROCESS_V36 = {
    "aleabitoreddit": {
        "lens": "AI optics + photonics + advanced packaging specialist",
        "preferred_layers": ["L2a_Optical", "L1_Compute", "L3_Materials"],
        "thesis_summary": (
            "Deep specialist on AI optical interconnect bottlenecks. Focuses on monopoly suppliers "
            "(AXTI InP substrates, LITE 200G EML, SIVE CW lasers, RPI OpenClaw). High conviction "
            "early positioning before broader market awareness."
        ),
        "win_examples": [
            "ARM ~$32 → $82.56 (+158%)",
            "RPI early call → +44.76% single day",
            "AAOI ~$84 large position",
        ],
        "execution_style": "Early-stage specialist, ride to monopoly pricing recognition",
    },
    "citrini": {
        "lens": "Thematic bottleneck scanner — Citrini Research methodology",
        "preferred_layers": ["All layers", "L1-L7 thematic"],
        "thesis_summary": (
            "Citrindex methodology — narratives drive markets, factor purity >80%. "
            "Identifies mega-trends 3-10 year horizon. Owns scarce link at each cycle."
        ),
        "win_examples": [
            "GLP-1 thematic (LLY, NVO 2023+)",
            "Energy transition uranium (CCJ, URA 2022+)",
            "AI Infrastructure full stack (NVDA → HBM → optical → power)",
        ],
        "execution_style": "Thematic primer publish → scale up position → cascade to next layer",
    },
    "ParadisLabs": {
        "lens": "AI infrastructure + advanced manufacturing + space/quantum",
        "preferred_layers": ["L1_Compute", "L2a_Optical", "L4_Memory", "L6_Space"],
        "thesis_summary": (
            "Speculative tech with multi-quarter conviction. Quantum compute (IONQ, RGTI), "
            "space infra (ASTS, PL), advanced optics (POET), hydrogen fuel cells (PLUG)."
        ),
        "win_examples": ["ASTS multi-bag", "IONQ early"],
        "execution_style": "Long-dated speculative — 6-18 month horizon",
    },
    "zephyr_z9": {
        "lens": "Japanese precision manufacturing + robotics + PCB substrates",
        "preferred_layers": ["L5_Robotics", "L2b_PCB", "L3_Machines"],
        "thesis_summary": (
            "Hidden Japan-listed bottleneck plays. Harmonic Drive (servo monopoly), "
            "Nabtesco (harmonic reducer), THK (linear motion), Yaskawa/Fanuc (servo). "
            "AMEC China etching tools long-term hold."
        ),
        "win_examples": ["Nabtesco multi-year hold", "Fujibo PCB breakout"],
        "execution_style": "Long-term Japan equities (5-10 year hold)",
    },
    "jukan05": {
        "lens": "Materials cycle + helium + industrial gas",
        "preferred_layers": ["L1_Memory", "L3_Materials"],
        "thesis_summary": (
            "Materials cycle plays. WDC HDD (20-30% price hike thesis), Air Products + Linde "
            "(rerouted industrial gas contracts), helium exploration (Pulsar, Helium One — speculative)."
        ),
        "win_examples": ["WDC HDD recovery"],
        "execution_style": "Mid-cycle materials, 6-12 month",
    },
    "HyperTechInvest": {
        "lens": "Diversified AI infra — power + compute + semis",
        "preferred_layers": ["L1_Compute", "L3_Power", "L3_Machines"],
        "thesis_summary": (
            "AI infrastructure broad-based: HUT (Bitcoin → AI pivot), ASML (EUV monopoly), "
            "BESI (advanced packaging). Long-term core holds."
        ),
        "win_examples": ["ASML structural hold"],
        "execution_style": "Buy-and-hold blue chip AI infra",
    },
    "PhotonCap": {
        "lens": "Photonics fund — top positions LITE + FORM",
        "preferred_layers": ["L2a_Optical"],
        "thesis_summary": (
            "Pure photonics specialist. LITE +85.7% (top 5), FORM largest position."
        ),
        "win_examples": ["LITE +85.7%", "FORM largest"],
        "execution_style": "Concentrated photonics portfolio",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# MEGA BOTTLENECK KNOWLEDGE BASE — All tickers with deep thesis
# ═══════════════════════════════════════════════════════════════════════
#
# Each entry encodes:
#   - mechanism: WHY this is a bottleneck
#   - causation_chain: HOW it propagates
#   - first/second/third order beneficiaries
#   - cascade_to: next bottleneck downstream
#   - horizon: time to play out
#   - estimated_impact_pct: revenue/margin lift potential
#   - citation: account or research source
#   - thought_process: deep explanation in Citrini/Leopold voice
#

BOTTLENECK_KB_V36 = {

    # ═══════════════════════════════════════════════════════════════
    # L1_COMPUTE — GPU + AI ACCELERATORS
    # ═══════════════════════════════════════════════════════════════

    "ai_compute_gpu_nvda": {
        "layer": "L1_Compute",
        "accounts": ["citrini", "HyperTechInvest", "ParadisLabs"],
        "mechanism": (
            "NVDA monopoly on AI training accelerators. CUDA software moat (10+ years lead). "
            "Mellanox networking (acquired 2020) = vertical integration. "
            "Gross margin 75%+ vs historic 60% — pure monopoly pricing."
        ),
        "causation_chain": [
            "AI training compute doubles every 6 months (Epoch AI)",
            "Each frontier model ($Claude, GPT-5) needs 10K-100K H100/H200/B100 GPUs",
            "Single H100 cluster $40K-$60K capex, $1B+ total per model",
            "AMD MI300 4-6 quarters behind, lower software ecosystem",
            "Intel Gaudi 3 ~12+ quarters behind",
            "NVDA pricing power: GB200 priced 30%+ above H200 spec uplift",
        ],
        "first_order": ["NVDA"],
        "second_order": ["AMD", "AVGO", "MRVL"],
        "third_order": ["ARM", "ANET", "ALAB"],
        "cascade_to": "ai_memory_hbm_micron",
        "horizon": "Q3 2024 - Q4 2026 (8 quarters)",
        "estimated_impact_pct": 0.50,
        "citation": "Leopold Situational Awareness 2024, Citrini AI Infra primer, HyperTechInvest",
        "thought_process": (
            "Leopold thesis: AGI by 2027 requires 100× compute scaling. Bottleneck shifts "
            "UP the stack each year. Citrini methodology: own scarce link at each cycle. "
            "NVDA captures value at compute layer 2024-2026, then cascades to HBM (MU/HYNIX), "
            "then power (VST/CEG), then networking (ANET). Don't chase what's already moved — "
            "front-run the cascade."
        ),
    },

    "ai_compute_amd": {
        "layer": "L1_Compute",
        "accounts": ["HyperTechInvest", "citrini"],
        "mechanism": (
            "AMD MI300/MI325 catching up to NVDA — 2nd source in AI accelerator duopoly. "
            "Custom silicon for hyperscalers (XILINX integration). Stars=2 per bottleneck_ref."
        ),
        "causation_chain": [
            "Hyperscalers desperate for 2nd source (anti-NVDA monopoly risk)",
            "Microsoft MAIA, Google TPU, AWS Trainium → AMD CXL/Infinity fabric advantage",
            "MI300 software ecosystem maturing (ROCm)",
            "Custom silicon: AMD acquired Xilinx (FPGA + adaptive compute)",
            "TAM: $2T potential per HyperTechInvest (10× from $200B current)",
        ],
        "first_order": ["AMD"],
        "second_order": ["MRVL", "ARM"],
        "third_order": ["MU"],
        "cascade_to": "ai_memory_hbm_micron",
        "horizon": "Q2 2025 - Q4 2027",
        "estimated_impact_pct": 0.35,
        "citation": "HyperTechInvest, citrini (stars=2)",
        "thought_process": (
            "HyperTechInvest thesis: AMD 2T potential — 10× from current. Custom silicon "
            "wave (hyperscaler chips) needs AMD's open architecture vs NVDA's closed stack. "
            "MI300 NOT a winner-takes-all play vs NVDA — it's the necessary 2nd source."
        ),
    },

    "ai_compute_arm": {
        "layer": "L1_Compute",
        "accounts": ["aleabitoreddit"],
        "mechanism": (
            "ARM CPU architecture for AI inference + edge. 5× revenue growth thesis per aleabit. "
            "RPI/Picoclaw/OpenClaw plays adjacent."
        ),
        "causation_chain": [
            "AI inference moves to edge devices (phones, cars, IoT)",
            "ARM dominant in mobile/embedded — extending to data center via NVDA Grace",
            "Royalty model = massive operating leverage",
            "NVDA Grace+Hopper uses ARM cores — vertical adoption",
        ],
        "first_order": ["ARM"],
        "second_order": ["RPI"],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Q1 2025 - Q4 2027",
        "estimated_impact_pct": 0.30,
        "citation": "aleabitoreddit (early ARM $32 → $82.56 +158%)",
        "thought_process": (
            "aleabit early call on ARM ~$32, exited near $82 for +158%. Thesis: ARM royalty "
            "model has 90%+ gross margin, AI inference shift to edge multiplies device count. "
            "RPI (Raspberry Pi parent OpenClaw/Picoclaw) similar edge AI play, fwd P/E 19."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L2a_OPTICAL — AI Interconnect Layer (Photonics)
    # ═══════════════════════════════════════════════════════════════

    "ai_optical_lite_200g_eml": {
        "layer": "L2a_Optical",
        "accounts": ["aleabitoreddit", "PhotonCap", "citrini"],
        "mechanism": (
            "LITE = 200G EML laser monopoly. Sold out through 2028. "
            "NVDA $2B capacity lock-in playbook (same as last year for EML)."
        ),
        "causation_chain": [
            "Cluster size >10K GPUs requires inter-rack optical (>10m runs)",
            "800G optical modules dominant 2025+, 1.6T 2026",
            "200G EML lasers = LITE near-monopoly (DFB/EML)",
            "NVDA pre-paid $2B to LITE (locked capacity through 2028)",
            "Pricing: $25/200G EML, sold out → premium pricing",
        ],
        "first_order": ["LITE"],
        "second_order": ["COHR", "CIEN"],
        "third_order": ["VIAV", "JEN"],
        "cascade_to": "ai_optical_axti_inp",
        "horizon": "Q1 2025 - Q4 2028 (sold out)",
        "estimated_impact_pct": 0.85,
        "citation": "aleabitoreddit, PhotonCap (LITE +85.7%), Citrini",
        "thought_process": (
            "aleabit: LITE 200G EML monopoly is THE forgotten bottleneck. NVDA locked $2B "
            "capacity (same playbook as COHR/MRVL last year). Sold out through 2028 = pricing "
            "power persistent multi-year. PhotonCap holds as top 5 with +85.7% gain confirming."
        ),
    },

    "ai_optical_axti_inp": {
        "layer": "L2a_Optical",
        "accounts": ["aleabitoreddit"],
        "mechanism": (
            "AXTI = Indium Phosphide (InP) substrate near-monopoly. InP required for DFB/EML "
            "lasers in optical modules. $10B+ TAM potential per aleabit. Tiny company, "
            "structural shortage."
        ),
        "causation_chain": [
            "All optical lasers (DFB, EML, CW) need InP substrates",
            "AXTI dominant supplier (2-3 players globally)",
            "200G EML demand (LITE) → InP wafer demand 5×",
            "Capacity expansion 18-24 months lead time",
            "Price elasticity HIGH — substrate cost <5% of laser cost",
        ],
        "first_order": ["AXTI"],
        "second_order": ["LITE", "COHR"],
        "third_order": ["IIVI"],
        "cascade_to": "ai_optical_sive_cw_laser",
        "horizon": "Q2 2025 - Q4 2028 (multi-year shortage)",
        "estimated_impact_pct": 0.90,
        "citation": "aleabitoreddit (HIGH priority, $10B+ potential)",
        "thought_process": (
            "aleabit pure-play call on AXTI as InP substrate monopoly. Citrini-style: "
            "InP cost is <5% of finished laser cost, but supply is 1/100th of demand. "
            "Pricing power asymmetric — even 10× substrate price = <50% finished laser price. "
            "TINY market cap, $10B+ TAM = massive multibagger if supply stays tight."
        ),
    },

    "ai_optical_sive_cw_laser": {
        "layer": "L2a_Optical",
        "accounts": ["aleabitoreddit"],
        "mechanism": (
            "SIVE = CW (Continuous Wave) laser light source for CPO (Co-Packaged Optics). "
            "$1B revenue by 2029 target. Early stage but pure-play CPO winner."
        ),
        "causation_chain": [
            "CPO (Co-Packaged Optics) replaces pluggable transceivers in 1.6T+ systems",
            "CPO needs external CW laser source",
            "SIVE = small market cap (~$290M), one of 2-3 CW laser specialists",
            "Adoption inflection 2026-2028 as CPO becomes standard",
        ],
        "first_order": ["SIVE"],
        "second_order": ["POET", "AYAR"],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Q4 2026 - Q4 2029 (CPO adoption curve)",
        "estimated_impact_pct": 1.50,
        "citation": "aleabitoreddit (HIGH conviction, $1B rev by 2029)",
        "thought_process": (
            "aleabit early-stage call. Same playbook as $2B NVDA capacity lock-in but for CW "
            "lasers (CPO adoption). High volatility (small cap) but $290M mcap → $1B rev by "
            "2029 = potential 5-10× multibagger if CPO adoption hits."
        ),
    },

    "ai_optical_cohr": {
        "layer": "L2a_Optical",
        "accounts": ["citrini", "PhotonCap"],
        "mechanism": (
            "COHR (II-VI Coherent) = DFB laser leader, NVDA $2B optical components lock-in. "
            "Stars=2 priority HIGH."
        ),
        "causation_chain": [
            "COHR/II-VI dominant in DFB lasers + optical components",
            "NVDA $2B capacity lock-in (announced playbook)",
            "Acquired Coherent (laser tools) → diversified DFB + industrial laser",
            "OFC market (optical fiber components) duopoly with LITE",
        ],
        "first_order": ["COHR"],
        "second_order": ["LITE", "CIEN"],
        "third_order": [],
        "cascade_to": "ai_optical_axti_inp",
        "horizon": "Q1 2025 - Q4 2028",
        "estimated_impact_pct": 0.45,
        "citation": "citrini, PhotonCap",
        "thought_process": (
            "Citrini: COHR is the 'safer' optical bottleneck play vs LITE (more diversified, "
            "larger cap). NVDA's $2B capacity lock-in is the playbook signal — same pattern "
            "as last year securing EML capacity."
        ),
    },

    "ai_optical_himx_cpo": {
        "layer": "L2a_Optical",
        "accounts": ["citrini"],
        "mechanism": (
            "HIMX = CPO / Display Driver play. CPO adoption upside as co-packaged optics scales."
        ),
        "causation_chain": [
            "HIMX has display driver IC monopoly position",
            "Adjacency to CPO (Co-Packaged Optics) for AI clusters",
            "AR/VR adoption tailwind (Apple Vision Pro etc)",
        ],
        "first_order": ["HIMX"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Q3 2025 - Q4 2027",
        "estimated_impact_pct": 0.25,
        "citation": "citrini",
        "thought_process": (
            "Citrini lateral: HIMX is CPO + AR/VR double-tailwind. Lower conviction (priority LOW) "
            "but small cap with upside on CPO adoption inflection."
        ),
    },

    "ai_optical_glw_substrates": {
        "layer": "L2a_Optical",
        "accounts": ["aleabitoreddit"],
        "mechanism": (
            "GLW (Corning) = Glass substrates near-monopoly for optical fiber + advanced display."
        ),
        "causation_chain": [
            "Optical fiber demand surging (AI clusters need fiber backbones)",
            "GLW dominant in pure silica fiber + Gorilla Glass + Vialux LCD substrates",
            "Near-monopoly position in specialty glass",
        ],
        "first_order": ["GLW"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Multi-year structural",
        "estimated_impact_pct": 0.20,
        "citation": "aleabitoreddit",
        "thought_process": (
            "aleabit: GLW is large cap defensive optics play. Near-monopoly in specialty glass. "
            "Lower upside (large cap) but tail risk lower. Hold for multi-year."
        ),
    },

    "ai_optical_lwlg_tfln": {
        "layer": "L2a_Optical",
        "accounts": ["aleabitoreddit"],
        "mechanism": (
            "LWLG = TFLN (Thin Film Lithium Niobate) electro-optic modulator pioneer. "
            "Early stage, high vol."
        ),
        "causation_chain": [
            "TFLN replaces traditional LiNbO3 for high-speed modulators",
            "Enables 1.6T+ optical with lower power",
            "LWLG holds key IP, early commercialization",
        ],
        "first_order": ["LWLG"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Speculative — 2-5 years",
        "estimated_impact_pct": 1.00,
        "citation": "aleabitoreddit (LOW priority, early stage)",
        "thought_process": (
            "aleabit speculative — small cap with patent IP in TFLN modulators. "
            "Could be 10× if commercialization hits, 0 if competition catches up. "
            "Position size: <0.5% portfolio."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L1_MEMORY / L4_MEMORY — HBM + NAND
    # ═══════════════════════════════════════════════════════════════

    "ai_memory_hbm_micron": {
        "layer": "L4_Memory",
        "accounts": ["citrini"],
        "mechanism": (
            "Each H100/H200 uses 80GB+ HBM (High Bandwidth Memory). Production single-bottlenecked "
            "on TSMC CoWoS advanced packaging (3 fabs globally). HBM3e pricing 4-5× DDR5 = pure margin."
        ),
        "causation_chain": [
            "HBM is stacked DRAM with 8-12 dies on silicon interposer",
            "Requires TSMC CoWoS-S or CoWoS-L packaging (only TSMC has scale)",
            "CoWoS capacity ~50K wafers/quarter (Apple/AMD/NVDA all compete)",
            "SK Hynix has 50%+ HBM3e market share, Samsung ramping, MU late entry",
            "Pricing: $25K+ per 80GB HBM3 stack (vs ~$3K DDR5 equivalent)",
        ],
        "first_order": ["MU"],
        "second_order": ["AMAT", "LRCX", "KLAC"],
        "third_order": ["AMKR", "ASX", "TROX"],
        "cascade_to": "ai_optical_lite_200g_eml",
        "horizon": "Q4 2024 - Q2 2027 (10 quarters)",
        "estimated_impact_pct": 0.40,
        "citation": "Citrini Research bottleneck scanner Layer 4",
        "thought_process": (
            "Citrini: when demand river meets capacity dam, value shifts to scarce link. "
            "HBM is THE scarce link 2024-2026. Even MU (3rd place) sees 40%+ margin lift "
            "as ALL capacity sold out. SK Hynix listed Korea (KS:000660) for direct exposure."
        ),
    },

    "memory_nand_wdc_jukan": {
        "layer": "L1_Memory",
        "accounts": ["jukan05"],
        "mechanism": (
            "WDC = HDD storage 20-30% price hike thesis per jukan05. AI inference workload "
            "drives massive enterprise storage demand. Capex cuts during oversupply 2022-23 "
            "now creates undersupply 2025+."
        ),
        "causation_chain": [
            "NAND prices crashed 70% peak-to-trough 2022-2023",
            "Major suppliers cut capex 30-50%, idle fabs",
            "AI inference workloads consume massive storage (LLM serving)",
            "Enterprise SSD/HDD demand +40% YoY for AI clusters",
            "HDD pricing power restored — 20-30% hike per jukan05",
        ],
        "first_order": ["WDC", "STX", "SNDK"],
        "second_order": ["MU"],
        "third_order": [],
        "cascade_to": "ai_compute_gpu_nvda",
        "horizon": "Q1 2025 - Q4 2026 (cyclical 4-6 quarters)",
        "estimated_impact_pct": 0.35,
        "citation": "jukan05 (HDD price hike thesis)",
        "thought_process": (
            "jukan05: WDC + HDD pricing recovery is the 'forgotten' AI storage play. "
            "Storage requirement scales 100× with model size (inference cluster needs petabytes). "
            "SNDK (SanDisk spinoff from WDC) + STX undervalued vs MU which gets all attention. "
            "Catalyst: capex cuts → supply tight 2025+."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L3_POWER — AI Power Grid
    # ═══════════════════════════════════════════════════════════════

    "ai_power_lng_natural_gas": {
        "layer": "L3_Power",
        "accounts": ["HyperTechInvest", "citrini"],
        "mechanism": (
            "LNG (Cheniere Energy) = US natural gas exporter benefiting from 'Power Struggle' "
            "thesis. Stars=2. Behind-the-meter gas turbines for AI data centers."
        ),
        "causation_chain": [
            "Single 100K-GPU cluster draws 150 MW (city of 100K people)",
            "US grid interconnect queue 4-6 years",
            "Hyperscalers contracting behind-the-meter gas turbines",
            "LNG export demand surge (Europe + Asia)",
            "Permian basin gas → LNG cycle increasing capacity",
        ],
        "first_order": ["LNG"],
        "second_order": ["VST", "CEG"],
        "third_order": ["ETN", "VRT"],
        "cascade_to": "ai_water_cooling_vrt",
        "horizon": "Q1 2025 - Q4 2030",
        "estimated_impact_pct": 0.40,
        "citation": "HyperTechInvest, citrini",
        "thought_process": (
            "Citrini Power Struggle thesis: AI bottleneck is NOT silicon anymore — it's electrons. "
            "LNG benefits from US gas exports + behind-the-meter data center deals. "
            "Front-runner play before utilities (VST/CEG) get fully repriced."
        ),
    },

    "ai_power_hut_pivot": {
        "layer": "L3_Power",
        "accounts": ["HyperTechInvest"],
        "mechanism": (
            "HUT (Hut 8) = Bitcoin miner pivoting to AI hosting. Pre-connected power infra = "
            "AI hosting goldmine (Yves narrative frame)."
        ),
        "causation_chain": [
            "BTC miners have years-of-permit power infrastructure",
            "AI hosting demand = $millions/MW vs BTC mining = $thousands/MW",
            "HUT pivoting business model — multi-MW data center contracts",
            "Stranded power assets converted to AI compute hosting",
        ],
        "first_order": ["HUT"],
        "second_order": ["CORZ", "IREN", "APLD", "CIFR"],
        "third_order": ["MARA", "RIOT"],
        "cascade_to": None,
        "horizon": "Q3 2025 - Q4 2027",
        "estimated_impact_pct": 0.60,
        "citation": "HyperTechInvest",
        "thought_process": (
            "HyperTechInvest pivot thesis. Yves narrative frame: crowd says 'BTC miners doomed' "
            "but smart money sees stranded power assets as AI hosting goldmine. CORZ/IREN already "
            "moved, HUT lagging = catch-up trade."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L3_MACHINES — Semi Equipment
    # ═══════════════════════════════════════════════════════════════

    "ai_machines_asml_euv": {
        "layer": "L3_Machines",
        "accounts": ["HyperTechInvest"],
        "mechanism": (
            "ASML = EUV (Extreme UV) lithography monopoly. Every leading-edge chip needs EUV. "
            "Long-term structural hold."
        ),
        "causation_chain": [
            "EUV machines $200M+ each, 18-month lead time",
            "ASML only supplier globally",
            "TSMC + Intel + Samsung all need EUV for 3nm/2nm nodes",
            "High-NA EUV next gen (1A nodes) — even more monopoly",
        ],
        "first_order": ["ASML"],
        "second_order": ["BESI", "ASMI"],
        "third_order": ["AMAT", "LRCX", "KLAC"],
        "cascade_to": "ai_memory_hbm_micron",
        "horizon": "Multi-year structural (5-10 years)",
        "estimated_impact_pct": 0.30,
        "citation": "HyperTechInvest",
        "thought_process": (
            "HyperTechInvest core hold. ASML EUV monopoly = literal AAA-rated bottleneck. "
            "Lower upside (large cap, well-known) but lowest downside risk. Hold through cycles."
        ),
    },

    "ai_machines_amec_china": {
        "layer": "L3_Machines",
        "accounts": ["zephyr_z9"],
        "mechanism": (
            "AMEC = China etching tools — domestic semi self-sufficiency play."
        ),
        "causation_chain": [
            "US chip export restrictions → China builds domestic semi industry",
            "AMEC = domestic alternative to AMAT/LRCX etching",
            "Government subsidies + mandate",
            "10+ year structural growth path",
        ],
        "first_order": ["AMEC"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Long-term (5-10 years)",
        "estimated_impact_pct": 0.50,
        "citation": "zephyr_z9 (LOW priority — long-term China play)",
        "thought_process": (
            "zephyr_z9: AMEC = China etching tools structural growth. US-China decoupling "
            "creates domestic semi monopoly opportunity. Patient capital required."
        ),
    },

    "ai_machines_besi_packaging": {
        "layer": "L3_Machines",
        "accounts": ["HyperTechInvest"],
        "mechanism": (
            "BESI = advanced packaging equipment (hybrid bonding for HBM)."
        ),
        "causation_chain": [
            "Advanced packaging (CoWoS, hybrid bonding) = next bottleneck after wafer",
            "BESI hybrid bonders critical for HBM3e + chiplet integration",
            "TSMC CoWoS expansion → BESI demand follows",
        ],
        "first_order": ["BESI"],
        "second_order": ["AMAT", "KLAC"],
        "third_order": [],
        "cascade_to": "ai_memory_hbm_micron",
        "horizon": "Q2 2025 - Q4 2028",
        "estimated_impact_pct": 0.40,
        "citation": "HyperTechInvest",
        "thought_process": (
            "HyperTechInvest: BESI is the hidden bottleneck for HBM expansion. "
            "Hybrid bonding tools = next gen packaging mandatory for HBM3e/HBM4."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L3_MATERIALS — Rare Earths, Industrial Gas, Helium
    # ═══════════════════════════════════════════════════════════════

    "materials_mp_rare_earths": {
        "layer": "L3_Materials",
        "accounts": ["aleabitoreddit", "citrini"],
        "mechanism": (
            "MP Materials = US rare earth mining + magnet production. China dominance → "
            "policy-driven onshoring."
        ),
        "causation_chain": [
            "Rare earths critical for EV motors, wind turbines, defense (F-35)",
            "China controls 70%+ of supply + 90% of processing",
            "US policy: IRA subsidies + Defense funding for domestic supply",
            "MP only integrated US producer (mine to magnet)",
        ],
        "first_order": ["MP"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Q1 2025 - Q4 2030 (decade structural)",
        "estimated_impact_pct": 0.55,
        "citation": "aleabitoreddit + citrini (stars=2)",
        "thought_process": (
            "Citrini policy-driven thesis: MP is the ONLY US rare earth play with integrated "
            "value chain. Government de-risking via DoD contracts + IRA. Defense angle = "
            "secular demand."
        ),
    },

    "materials_jukan_helium": {
        "layer": "L3_Materials",
        "accounts": ["jukan05"],
        "mechanism": (
            "Helium exploration plays — Pulsar Helium, Helium One. Speculative supply-side."
        ),
        "causation_chain": [
            "Helium critical for semi manufacturing + MRI + quantum computing",
            "Global helium shortage cycles (2018, 2022)",
            "Pulsar + Helium One = new exploration projects",
        ],
        "first_order": ["Pulsar Helium", "Helium One"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Speculative — 2-5 years",
        "estimated_impact_pct": 1.00,
        "citation": "jukan05 (LOW priority — speculative)",
        "thought_process": (
            "jukan05 speculative: helium exploration plays. Asymmetric — low probability "
            "high payoff. Position <0.5% each."
        ),
    },

    "materials_jukan_industrial_gas": {
        "layer": "L3_Materials",
        "accounts": ["jukan05"],
        "mechanism": (
            "Air Products + Linde = industrial gas duopoly. Rerouted contracts (China/Russia "
            "ban) → margin expansion."
        ),
        "causation_chain": [
            "Industrial gas (N2, O2, He, H2) critical for semi + steel + chemical",
            "China export restrictions reroute global supply",
            "Air Products + Linde = US-based duopoly",
        ],
        "first_order": ["Air Products", "Linde"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Q3 2025 - Q4 2027",
        "estimated_impact_pct": 0.25,
        "citation": "jukan05",
        "thought_process": (
            "jukan05: Air Products + Linde duopoly benefits from supply chain reorganization. "
            "Lower upside (large cap) but stable income."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L5_ROBOTICS — Japanese Precision Manufacturing
    # ═══════════════════════════════════════════════════════════════

    "robotics_nabtesco_harmonic_reducer": {
        "layer": "L5_Robotics",
        "accounts": ["zephyr_z9"],
        "mechanism": (
            "Nabtesco = harmonic reducer (precision gear) near-monopoly. "
            "Robot bottleneck per zephyr_z9."
        ),
        "causation_chain": [
            "Industrial robots all need precision reducers",
            "Nabtesco dominant in cycloidal reducers (60%+ market share)",
            "Humanoid robotics (Tesla Optimus, Figure AI) → 10× TAM expansion",
            "Each humanoid robot needs 20+ precision reducers",
        ],
        "first_order": ["Nabtesco"],
        "second_order": ["Harmonic Drive"],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Long-term (5-15 years)",
        "estimated_impact_pct": 0.45,
        "citation": "zephyr_z9 (HIGH priority — robot bottleneck)",
        "thought_process": (
            "zephyr_z9 Japan precision play: Nabtesco = harmonic reducer monopoly. "
            "Humanoid robotics (Optimus, Figure) inflection = 10× TAM. "
            "Each robot needs 20+ Nabtesco gears. Multi-decade hold."
        ),
    },

    "robotics_japan_basket": {
        "layer": "L5_Robotics",
        "accounts": ["zephyr_z9"],
        "mechanism": (
            "Japan robotics basket — Yaskawa (servo motors), Fanuc (servo + robots), "
            "THK (linear motion), SMC (pneumatic), Harmonic Drive (reducer)."
        ),
        "causation_chain": [
            "Industrial automation + humanoid robotics inflection",
            "Japan dominant in precision motion components",
            "Yaskawa + Fanuc = global servo motor duopoly",
            "Long-term hold basket strategy",
        ],
        "first_order": ["Yaskawa", "Fanuc"],
        "second_order": ["THK", "SMC", "Harmonic Drive"],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Long-term (10+ years)",
        "estimated_impact_pct": 0.35,
        "citation": "zephyr_z9 (MEDIUM priority basket)",
        "thought_process": (
            "zephyr_z9 basket approach: own ALL Japanese precision motion. "
            "Long-term structural growth. Diversified within the bottleneck theme."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L6_SPACE — Quantum + Space Infrastructure
    # ═══════════════════════════════════════════════════════════════

    "space_asts_d2d": {
        "layer": "L6_Space",
        "accounts": ["ParadisLabs"],
        "mechanism": (
            "ASTS = Satellite direct-to-phone connectivity. Mid-cap long-term per ParadisLabs."
        ),
        "causation_chain": [
            "Cell coverage gaps in 80%+ of Earth surface",
            "ASTS BlueBird constellation = direct-to-cell-phone (no special device)",
            "AT&T + Verizon + Vodafone partnerships",
            "Each launched bird = revenue commitment",
        ],
        "first_order": ["ASTS"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "2-5 years",
        "estimated_impact_pct": 1.20,
        "citation": "ParadisLabs (MEDIUM priority, mid-cap long-term)",
        "thought_process": (
            "ParadisLabs: ASTS unique D2D (direct-to-device) satellite play. "
            "Mid-cap with TAM = all 8B people on Earth needing connectivity. "
            "Bird launches = revenue activation."
        ),
    },

    "space_quantum_ionq_rgti": {
        "layer": "L6_Space",
        "accounts": ["ParadisLabs"],
        "mechanism": (
            "Quantum computing pure-plays — IONQ + RGTI. Speculative."
        ),
        "causation_chain": [
            "Quantum supremacy era 2025-2030",
            "IONQ = trapped ion technology",
            "RGTI = superconducting",
            "Government contracts + cloud quantum services emerging",
        ],
        "first_order": ["IONQ", "RGTI"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "5-10 years speculative",
        "estimated_impact_pct": 2.00,
        "citation": "ParadisLabs (LOW priority — speculative)",
        "thought_process": (
            "ParadisLabs speculative — quantum computing pure-plays. "
            "Binary outcome: 10×+ if quantum supremacy + commercial, 0 if competition wins. "
            "Position <0.5% each."
        ),
    },

    "space_poet_photonics": {
        "layer": "L6_Space",
        "accounts": ["ParadisLabs"],
        "mechanism": (
            "POET = Photonics integration small-cap."
        ),
        "causation_chain": [
            "Photonic integration platforms for AI clusters + space comms",
            "Small-cap with optical IP",
            "Adjacency to CPO + space laser comms",
        ],
        "first_order": ["POET"],
        "second_order": [],
        "third_order": [],
        "cascade_to": None,
        "horizon": "Speculative",
        "estimated_impact_pct": 0.80,
        "citation": "ParadisLabs (LOW priority)",
        "thought_process": (
            "ParadisLabs speculative small-cap photonics. "
            "Adjacent to broader CPO thesis."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # L7_HEALTHCARE — GLP-1
    # ═══════════════════════════════════════════════════════════════

    "healthcare_glp1_lly_citrini": {
        "layer": "L7_Healthcare",
        "accounts": ["citrini"],
        "mechanism": (
            "GLP-1 (Ozempic, Mounjaro, Zepbound) addressable market 100M+ US adults. "
            "Supply constrained — peptide synthesis + injection device manufacturing."
        ),
        "causation_chain": [
            "NVO (Ozempic) + LLY (Mounjaro/Zepbound) duopoly — peptide moat",
            "Manufacturing capacity 4-quarter lead time, expanding 2025+",
            "Generic semaglutide 2026 (compounded), pure GLP-1 patents 2031+",
            "Spillover: weight loss → obesity-related conditions",
        ],
        "first_order": ["LLY", "NVO"],
        "second_order": ["VKTX", "AMGN", "PFE"],
        "third_order": ["WW", "PLNT", "HIMS"],
        "cascade_to": None,
        "horizon": "Q3 2024 - Q4 2027",
        "estimated_impact_pct": 0.45,
        "citation": "citrini GLP-1 thematic primer (2023+)",
        "thought_process": (
            "Citrini: GLP-1 is the most undervalued mega-trend. Manufacturing supply limits "
            "dominant — LLY/NVO can't print Zepbound/Wegovy fast enough. Pricing power held "
            "through 2028 minimum."
        ),
    },

    # ═══════════════════════════════════════════════════════════════
    # ENERGY TRANSITION — Uranium
    # ═══════════════════════════════════════════════════════════════

    "energy_uranium_ccj": {
        "layer": "L3_Power",
        "accounts": ["citrini"],
        "mechanism": (
            "Nuclear renaissance — AI power demand + climate policy + Russia ban "
            "creates structural uranium shortage. Spot price 2× since 2022."
        ),
        "causation_chain": [
            "Kazakhstan (40% supply) production constrained",
            "Russia ban on enriched uranium (US Aug 2024)",
            "China + India adding 50+ reactors by 2030",
            "SMR/Small modular reactors approved 2025-26",
            "Uranium ETF supply absorbed (Sprott URNM)",
        ],
        "first_order": ["CCJ", "URA"],
        "second_order": ["NXE", "DNN", "UEC", "LEU"],
        "third_order": ["UUUU", "URG", "PALAF"],
        "cascade_to": "ai_power_lng_natural_gas",
        "horizon": "Q1 2024 - Q4 2030 (decade structural)",
        "estimated_impact_pct": 0.50,
        "citation": "citrini Uranium primer + Sprott Physical Uranium Trust",
        "thought_process": (
            "Citrini structural thesis: uranium sympathetic with AI power story. "
            "Doubled clean energy demand + Russia geopolitical = supply squeeze visible 2026+. "
            "CCJ best-in-class, URA passive exposure, LEU enrichment angle."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def lookup_ticker_in_kb(ticker: str) -> Optional[Dict]:
    """Find a ticker in the bottleneck KB. Returns the bottleneck data."""
    ticker_upper = ticker.upper()
    for btk_id, btk_data in BOTTLENECK_KB_V36.items():
        all_tiers = (btk_data.get("first_order", []) +
                    btk_data.get("second_order", []) +
                    btk_data.get("third_order", []))
        all_tiers_upper = [t.upper() for t in all_tiers]
        if ticker_upper in all_tiers_upper:
            tier = "first_order" if ticker_upper in [t.upper() for t in btk_data["first_order"]] else \
                   "second_order" if ticker_upper in [t.upper() for t in btk_data["second_order"]] else \
                   "third_order"
            return {
                "bottleneck_id": btk_id,
                "tier": tier,
                **btk_data,
            }
    return None


def get_accounts_tracking_ticker(ticker: str) -> List[str]:
    """Get list of accounts tracking this ticker."""
    btk = lookup_ticker_in_kb(ticker)
    if btk:
        return btk.get("accounts", [])
    return []


def get_account_lens(account: str) -> Optional[Dict]:
    """Get the thought process lens for an account."""
    return ACCOUNT_THOUGHT_PROCESS_V36.get(account)


def list_tickers_by_layer(layer: str) -> List[str]:
    """Get all tickers tracked under a specific layer."""
    out = []
    for btk_data in BOTTLENECK_KB_V36.values():
        if btk_data.get("layer") == layer:
            out.extend(btk_data.get("first_order", []))
            out.extend(btk_data.get("second_order", []))
            out.extend(btk_data.get("third_order", []))
    return list(dict.fromkeys(out))


def list_tickers_by_account(account: str) -> List[str]:
    """Get all tickers an account tracks."""
    out = []
    for btk_data in BOTTLENECK_KB_V36.values():
        if account in (btk_data.get("accounts", [])):
            out.extend(btk_data.get("first_order", []))
            out.extend(btk_data.get("second_order", []))
            out.extend(btk_data.get("third_order", []))
    return list(dict.fromkeys(out))


__all__ = [
    "BOTTLENECK_KB_V36",
    "ACCOUNT_THOUGHT_PROCESS_V36",
    "lookup_ticker_in_kb",
    "get_accounts_tracking_ticker",
    "get_account_lens",
    "list_tickers_by_layer",
    "list_tickers_by_account",
]
