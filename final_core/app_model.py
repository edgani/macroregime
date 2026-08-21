from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from final_core.production_entry import run as run_production

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "FINAL_HANDOFF"


def _json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _csv(path: Path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_app_state(run_engine: bool = False):
    if run_engine or not (OUT / "52_CURRENT_PRODUCTION_RUN.json").exists():
        run_production()
    return {
        "run": _json(OUT / "52_CURRENT_PRODUCTION_RUN.json", {}),
        "validation_summary": _json(OUT / "51_MULTI_ENGINE_VALIDATION_SUMMARY.json", {}),
        "strict": _json(OUT / "100_STRICT_ACCEPTANCE_RESULT.json", {}),
        "evidence": _json(OUT / "32_CURRENT_EVIDENCE.json", []),
        "engine_registry": _csv(OUT / "01_ENGINE_REGISTRY.csv"),
        "metric_registry": _csv(OUT / "02_METRIC_MASTER_REGISTRY.csv"),
        "data_coverage": _csv(OUT / "04_FACTUAL_DATA_COVERAGE.csv"),
        "experiment_ledger": _csv(OUT / "06_COMPLETE_EXPERIMENT_LEDGER.csv"),
        "gmis": _csv(OUT / "10_GMIS_FINAL.csv"),
        "rejected": _csv(OUT / "43_REJECTED_OPPORTUNITIES.csv"),
        "qualified": _csv(OUT / "42_CURRENT_QUALIFIED_OPPORTUNITIES.csv"),
    }
