"""config/narrative_universe.py"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class NarrativeTemplate:
    name: str
    description: str
    category: str
    activation_keywords: List[str]
    invalidation_keywords: List[str]
    beneficiaries: Dict[str, List[str]]
    fades: Dict[str, List[str]]
    confirmation_signals: List[str]
    typical_duration_weeks: int
    conviction_ceiling: float
    regime_alignment: Dict[str, float]
    pump_risk: float
    catalyst_types: List[str]


_NARRATIVE_LIBRARY: List[NarrativeTemplate] = [
    NarrativeTemplate(
        name="AI Compute Bottleneck",
        description="GPU/AI accelerator shortage driving datacenter capex arms race. Supply constrained at TSMC CoWoS and HBM level.",
        category="technology",
        activation_keywords=["gpu shortage", "datacenter capex", "ai chip", "nvidia backlog", "tsmc cowos", "hbm supply"],
        invalidation_keywords=["gpu glut", "ai bubble", "capex cut", "inventory correction", "demand slowdown"],
        beneficiaries={
            "us": ["NVDA", "AMD", "AVGO", "TSM", "ASML", "MRVL", "LITE", "CRDO"],
            "ihsg": ["IPCM.JK"],
            "commodities": ["HG=F", "GC=F"],
        },
        fades={"us": ["INTC", "DELL", "HPQ"]},
        confirmation_signals=["NVDA revenue beat", "TSM raises guidance", "Datacenter capex +20% YoY"],
        typical_duration_weeks=16,
        conviction_ceiling=0.92,
        regime_alignment={"Q1": 1.25, "Q2": 1.15, "Q3": 0.75, "Q4": 0.60},
        pump_risk=0.25,
        catalyst_types=["earnings_beat", "product_launch", "partnership"],
    ),
    NarrativeTemplate(
        name="Optics/Photonics Shortage",
        description="AI cluster interconnect demand colliding with telecom underinvestment. CPO and optical interconnect bottleneck emerging.",
        category="technology",
        activation_keywords=["optics shortage", "co-packaged optics", "optical interconnect", "lumentum", "ciena", "ai connectivity"],
        invalidation_keywords=["optics inventory", "telecom capex cut", "fiber glut", "chinese optics"],
        beneficiaries={
            "us": ["LITE", "COHR", "CIEN", "ANET", "MRVL", "CRDO", "NPTN"],
            "commodities": ["GC=F"],
        },
        fades={"us": ["INFN", "COMM"], "commodities": ["SI=F"]},
        confirmation_signals=["LITE guides up", "CIEN backlog expands", "800G deployment accelerates"],
        typical_duration_weeks=20,
        conviction_ceiling=0.88,
        regime_alignment={"Q1": 1.20, "Q2": 1.10, "Q3": 0.80, "Q4": 0.65},
        pump_risk=0.30,
        catalyst_types=["research_breakthrough", "competitor_admission", "earnings_beat"],
    ),
    NarrativeTemplate(
        name="Nuclear Energy Renaissance",
        description="Datacenter power demand + decarb targets driving nuclear restart. SMR and uranium contracting cycle beginning.",
        category="energy",
        activation_keywords=["nuclear renaissance", "smr contract", "uranium spot", "datacenter power", "nuclear restart", "ceg"],
        invalidation_keywords=["nuclear accident", "regulatory block", "uranium price crash", "grid alternative"],
        beneficiaries={
            "us": ["CEG", "NNE", "SMR", "OKLO", "CCJ", "URA", "VST"],
            "commodities": ["URA"],
        },
        fades={"us": ["ENPH", "SEDG", "FSLR"], "commodities": ["NG=F"]},
        confirmation_signals=["CEG signs datacenter PPA", "Uranium spot >$80", "SMR NRC approval"],
        typical_duration_weeks=24,
        conviction_ceiling=0.85,
        regime_alignment={"Q1": 1.10, "Q2": 1.20, "Q3": 1.15, "Q4": 0.90},
        pump_risk=0.35,
        catalyst_types=["government_contract", "regulatory_change", "partnership"],
    ),
    NarrativeTemplate(
        name="Fed Pivot / Rate Cut Cycle",
        description="Fed shifting from hiking to cutting. Duration assets and high-beta beneficiaries.",
        category="policy",
        activation_keywords=["fed pivot", "rate cut", "fed pause", "dovish fed", "terminal rate", "soft landing"],
        invalidation_keywords=["fed hawkish", "rate hike", "inflation reacceleration", "fed higher for longer"],
        beneficiaries={
            "us": ["TLT", "IWM", "XLK", "QQQ", "XLF", "XLRE"],
            "fx": ["EURUSD=X", "AUDUSD=X"],
            "crypto": ["BTC-USD", "ETH-USD"],
        },
        fades={"us": ["UUP", "XLU", "XLP"], "fx": ["USDJPY=X", "USDIDR=X"]},
        confirmation_signals=["Fed dots shift down", "PCE decelerates", "Unemployment ticks up"],
        typical_duration_weeks=12,
        conviction_ceiling=0.80,
        regime_alignment={"Q1": 1.30, "Q2": 0.90, "Q3": 0.70, "Q4": 1.20},
        pump_risk=0.20,
        catalyst_types=["policy_change", "earnings_beat"],
    ),
    NarrativeTemplate(
        name="Indonesia Coal/Nickel Supply",
        description="Indonesia coal and nickel export dynamics. EV battery demand vs domestic policy constraints.",
        category="commodity",
        activation_keywords=["indonesia coal", "nickel price", "adro", "antm", "ev battery nickel", "dmo coal"],
        invalidation_keywords=["coal price crash", "nickel oversupply", "indonesia export ban", "idr collapse"],
        beneficiaries={
            "ihsg": ["ADRO.JK", "ANTM.JK", "PTBA.JK", "ITMG.JK", "INCO.JK"],
            "commodities": ["CL=F", "HG=F"],
        },
        fades={"ihsg": ["BBCA.JK", "BBRI.JK"], "fx": ["IDR=X"]},
        confirmation_signals=["Coal price >$100", "Nickel LME backwardation", "ADRO raises dividend"],
        typical_duration_weeks=14,
        conviction_ceiling=0.82,
        regime_alignment={"Q1": 0.90, "Q2": 1.30, "Q3": 1.20, "Q4": 0.60},
        pump_risk=0.30,
        catalyst_types=["earnings_beat", "regulatory_change"],
    ),
    NarrativeTemplate(
        name="Quantum Computing Inflection",
        description="Quantum advantage approaching for specific workloads. Photonic and superconducting qubit race accelerating.",
        category="technology",
        activation_keywords=["quantum computing", "ionq", "quantum advantage", "photonic qc", "qubit", "google quantum"],
        invalidation_keywords=["quantum winter", "decoherence", "quantum hype", "no commercial use"],
        beneficiaries={
            "us": ["IONQ", "RGTI", "QBTS", "QUBT", "IBM", "GOOGL"],
            "commodities": ["GC=F"],
        },
        fades={"us": ["META", "MSFT"]},
        confirmation_signals=["IONQ beats estimates", "Google quantum paper", "DoD quantum contract"],
        typical_duration_weeks=30,
        conviction_ceiling=0.75,
        regime_alignment={"Q1": 1.20, "Q2": 1.00, "Q3": 0.60, "Q4": 0.50},
        pump_risk=0.55,
        catalyst_types=["research_breakthrough", "government_contract", "competitor_admission"],
    ),
    NarrativeTemplate(
        name="Global Defense Rearmament",
        description="Geopolitical tension driving defense budget expansion across NATO and Indo-Pacific.",
        category="defense",
        activation_keywords=["defense budget", "nato spending", "military aid", "lockheed martin", "rtn", "hypersonic"],
        invalidation_keywords=["peace deal", "defense cut", "budget freeze", "procurement delay"],
        beneficiaries={
            "us": ["LMT", "NOC", "RTX", "GD", "HII", "AVAV"],
            "ihsg": ["PTDI.JK"],
        },
        fades={"us": ["XLY", "XLK"], "ihsg": ["MNCN.JK"]},
        confirmation_signals=["NATO 2%->3% commitment", "Taiwan aid package", "LMT backlog +$10B"],
        typical_duration_weeks=40,
        conviction_ceiling=0.78,
        regime_alignment={"Q1": 0.80, "Q2": 1.10, "Q3": 1.30, "Q4": 0.90},
        pump_risk=0.20,
        catalyst_types=["government_contract", "regulatory_change"],
    ),
    NarrativeTemplate(
        name="Iran-Hormuz Oil Supply Shock",
        description="Middle East escalation threatening Strait of Hormuz transit. Oil shock risk premium.",
        category="geopolitics",
        activation_keywords=["iran", "hormuz", "oil supply", "middle east war", "strait of hormuz", "opec"],
        invalidation_keywords=["ceasefire", "diplomatic breakthrough", "iran deal", "shale surge"],
        beneficiaries={
            "us": ["XLE", "XOM", "CVX", "OXY", "COP"],
            "commodities": ["CL=F", "BZ=F", "GC=F"],
            "fx": ["UUP", "USDJPY=X"],
        },
        fades={"us": ["XLY", "XLK", "IWM"], "ihsg": ["BBCA.JK", "BBRI.JK"]},
        confirmation_signals=["Brent >$90", "Tanker rates spike", "US SPR release"],
        typical_duration_weeks=8,
        conviction_ceiling=0.70,
        regime_alignment={"Q1": 0.70, "Q2": 1.30, "Q3": 1.25, "Q4": 0.80},
        pump_risk=0.40,
        catalyst_types=["regulatory_change", "other"],
    ),
    NarrativeTemplate(
        name="EV Battery Supply Chain Shift",
        description="Solid-state and LFP battery transition disrupting incumbent chemistry. China vs West supply chain bifurcation.",
        category="technology",
        activation_keywords=["solid state battery", "lfp battery", "ev battery", "catl", "tesla battery", "lithium"],
        invalidation_keywords=["ev demand slowdown", "battery fire", "lithium price crash", "hydrogen"],
        beneficiaries={
            "us": ["TSLA", "QS", "SLDP", "ALB", "SQM"],
            "commodities": ["LIT", "COPX"],
        },
        fades={"us": ["F", "GM", "TM"]},
        confirmation_signals=["QS production timeline", "Tesla 4680 ramp", "Lithium contract price"],
        typical_duration_weeks=18,
        conviction_ceiling=0.72,
        regime_alignment={"Q1": 1.15, "Q2": 1.10, "Q3": 0.75, "Q4": 0.60},
        pump_risk=0.45,
        catalyst_types=["product_launch", "partnership", "earnings_beat"],
    ),
    NarrativeTemplate(
        name="Biotech/GLP-1 Revolution",
        description="Obesity drug market expanding beyond diabetes. Healthcare cost and consumer discretionary implications.",
        category="healthcare",
        activation_keywords=["glp-1", "ozempic", "wegovy", "mounjaro", "obesity drug", "novo nordisk"],
        invalidation_keywords=["glp-1 side effects", "fda warning", "competition generic", "demand saturation"],
        beneficiaries={
            "us": ["LLY", "NVO", "VKTX", "MRNA", "ISRG"],
            "ihsg": ["KLBF.JK"],
        },
        fades={"us": ["MCD", "SBUX", "PEP", "KO", "YUM"]},
        confirmation_signals=["LLY raises guidance", "Medicare coverage expansion", "GLP-1 heart data"],
        typical_duration_weeks=28,
        conviction_ceiling=0.80,
        regime_alignment={"Q1": 1.20, "Q2": 0.95, "Q3": 0.85, "Q4": 0.90},
        pump_risk=0.30,
        catalyst_types=["earnings_beat", "regulatory_change", "research_breakthrough"],
    ),
]

NARRATIVE_BY_NAME = {n.name: n for n in _NARRATIVE_LIBRARY}
