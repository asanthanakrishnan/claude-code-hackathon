"""
Metric Calculation Engine — REST API

Endpoints:
  POST /calculate          — compute churn for a version + period
  GET  /definitions        — list all versions with summaries
  GET  /definitions/{ver}  — detail for one version
  GET  /health             — liveness check

Run: uvicorn engine.app:app --reload --port 8002
"""

from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator

from .calculator import calculate, load_canonical
from .definitions import REGISTRY, SUMMARIES

app = FastAPI(
    title="Churn Metric Engine",
    description="Versioned SaaS churn calculation API. Every result is tagged with the definition version.",
    version="1.0.0",
)


class CalculateRequest(BaseModel):
    version: str
    period_start: date
    period_end: date

    @field_validator("version")
    @classmethod
    def version_must_exist(cls, v: str) -> str:
        if v not in REGISTRY:
            raise ValueError(f"Unknown version '{v}'. Available: {list(REGISTRY)}")
        return v

    @field_validator("period_end")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("period_start")
        if start and v < start:
            raise ValueError("period_end must be >= period_start")
        return v


@app.get("/health")
def health():
    rows = load_canonical()
    return {"status": "ok", "canonical_rows": len(rows)}


@app.get("/definitions")
def list_definitions():
    return {
        "versions": [
            {"version": v, "summary": s} for v, s in SUMMARIES.items()
        ]
    }


@app.get("/definitions/{version}")
def get_definition(version: str):
    if version not in SUMMARIES:
        raise HTTPException(status_code=404, detail=f"Version '{version}' not found")
    return {"version": version, "summary": SUMMARIES[version]}


@app.post("/calculate")
def calculate_metric(req: CalculateRequest):
    try:
        result = calculate(req.version, req.period_start, req.period_end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/compare")
def compare_all(
    period_start: Annotated[date, Query(description="ISO date, e.g. 2024-06-01")],
    period_end: Annotated[date, Query(description="ISO date, e.g. 2024-06-30")],
):
    """Compute all four versions for the same period — shows the disagreement."""
    rows = load_canonical()
    results = {}
    for version in REGISTRY:
        try:
            results[version] = calculate(version, period_start, period_end, rows)
        except Exception as e:
            results[version] = {"error": str(e)}
    return {"period_start": period_start.isoformat(), "period_end": period_end.isoformat(), "results": results}
