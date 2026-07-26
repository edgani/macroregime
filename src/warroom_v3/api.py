from __future__ import annotations

from pathlib import Path
from typing import Any
import json, os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .runtime import build_asset_snapshot, system_status
from .storage import load_jsonl
from .evaluation import build_evaluation_report


def create_app(root: str | Path | None = None) -> FastAPI:
    base=Path(root or os.environ.get("WARROOM_ROOT") or Path.cwd()).resolve()
    app=FastAPI(title="War Room OS v3",version="3.0.0-ready")
    static=base/"static"
    if static.exists(): app.mount("/static",StaticFiles(directory=static),name="static")

    @app.get("/health")
    def health() -> dict[str,Any]:
        status=system_status(base)
        return {"ok":not status["store_errors"],"mode":status["mode"],"actionable":False,"store_errors":status["store_errors"]}

    @app.get("/api/status")
    def status() -> dict[str,Any]:
        return system_status(base)

    @app.get("/api/assets")
    def assets() -> dict[str,Any]:
        rows=[]
        for asset in ("BTCUSDT","ETHUSDT"):
            path=base/f"runtime/observations/assets/{asset}.json"
            if path.exists(): rows.append(json.loads(path.read_text(encoding="utf-8")))
            else:
                try: rows.append(build_asset_snapshot(base,asset=asset))
                except Exception as exc: rows.append({"asset":asset,"actionable":False,"status":"UNAVAILABLE","reason_codes":[str(exc)]})
        return {"items":rows,"actionable":False,"claim_ceiling":"DESCRIPTIVE_ONLY"}

    @app.get("/api/assets/{asset}")
    def asset(asset: str) -> dict[str,Any]:
        asset=asset.upper()
        if asset not in ("BTCUSDT","ETHUSDT"):
            raise HTTPException(404,"asset not configured")
        try: return build_asset_snapshot(base,asset=asset)
        except Exception as exc:
            raise HTTPException(503,f"asset unavailable: {exc}") from exc

    @app.get("/api/evaluation")
    def evaluation() -> dict[str,Any]:
        return build_evaluation_report(base)

    @app.get("/api/evidence")
    def evidence() -> dict[str,Any]:
        return {
            "prospective_batches":load_jsonl(base/"runtime/prospective/journal.jsonl"),
            "observations":load_jsonl(base/"runtime/observations/journal.jsonl"),
            "outcomes":load_jsonl(base/"runtime/outcomes/journal.jsonl"),
            "claim_ceiling":"EVIDENCE_RECORD_ONLY",
        }

    @app.get("/")
    def index():
        path=base/"static/index.html"
        if not path.exists(): raise HTTPException(404,"dashboard missing")
        return FileResponse(path)

    return app


app=create_app()
