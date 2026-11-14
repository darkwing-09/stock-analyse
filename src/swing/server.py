# -*- coding: utf-8 -*-
"""Dashboard API + static host: ``python swing.py serve``.

Reads the JSON files the engine writes under ``data/swing`` and the latest
India market review under ``reports/``. Read-only: it never places orders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATE_DIR = Path("data/swing")
REPORTS_DIR = Path("reports")
DIST_DIR = Path(__file__).resolve().parents[2] / "apps" / "swing-dashboard" / "dist"


def _read(name: str) -> Optional[Dict[str, Any]]:
    path = STATE_DIR / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def latest_market_review(reports_dir: Path = REPORTS_DIR) -> Optional[Dict[str, str]]:
    files = sorted(reports_dir.glob("market_review_*.md"))
    if not files:
        return None
    text = files[-1].read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("[dsa-market-region]")]
    return {"date": files[-1].stem.replace("market_review_", ""), "markdown": "\n".join(lines).strip()}


def create_app() -> FastAPI:
    app = FastAPI(title="Stock Analyse dashboard", docs_url=None, redoc_url=None)

    def payload(data):
        return JSONResponse({"available": data is not None, "data": data})

    @app.get("/api/portfolio")
    def portfolio():
        return payload(_read("paper_status.json"))

    @app.get("/api/signals")
    def signals():
        return payload(_read("latest_rank.json"))

    @app.get("/api/backtest")
    def backtest():
        return payload(_read("backtest.json"))

    @app.get("/api/market")
    def market():
        return payload(latest_market_review())

    if DIST_DIR.exists():
        app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            candidate = DIST_DIR / path
            if path and candidate.is_file() and DIST_DIR in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(DIST_DIR / "index.html")

    return app
