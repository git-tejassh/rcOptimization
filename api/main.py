"""Local FastAPI server: live surrogate evaluation and on-demand ground-truth FE (project.md 11.4, CLAUDE.md 8).

Run:  uvicorn api.main:app --reload     (or ``make api``).  Not intended for Vercel: it needs OpenSeesPy and XGBoost.
"""
from __future__ import annotations

import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import CostCarbonResponse, GenomeIn, SurrogateOut, SurrogateResponse
from rcopt import config
from rcopt.config import ROOT
from rcopt.design.describe import describe_genome
from rcopt.design.variables import default_space

RESULTS = ROOT / "data" / "results"
app = FastAPI(title="RC frame optimisation API", version="0.1.0",
              description="Gravity-only IS 456 evaluation of discrete RC frame designs. Cost / carbon rates are provisional.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"],
                   allow_methods=["*"], allow_headers=["*"])
VARIANTS = {"A": "pareto_surrogate_A", "A_margin": "pareto_surrogate_A_margin", "B": "pareto_surrogate_B",
            "B_margin": "pareto_surrogate_B_margin", "direct": "pareto_direct"}


@lru_cache(maxsize=2)
def _model(name: str):
    path = ROOT / "models" / f"surrogate_{name}.joblib"
    if not path.exists():
        raise HTTPException(503, f"surrogate {name} not trained yet (run `make phase3`)")
    return joblib.load(path)


def _genome(body: GenomeIn) -> np.ndarray:
    sp = default_space()
    g = np.array(body.genome)
    if g.shape != (sp.n_genes,):
        raise HTTPException(422, f"genome must have {sp.n_genes} entries")
    if np.any(g < 0) or np.any(g >= sp.n_options):
        raise HTTPException(422, "gene index out of range (see GET /design-space)")
    return sp.repair(g)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "surrogates": {n: (ROOT / "models" / f"surrogate_{n}.joblib").exists() for n in ("A", "B")},
            "provisional_data": bool(config.provisional_items())}


@app.get("/design-space")
def design_space() -> dict:
    p = RESULTS / "design_space.json"
    if not p.exists():
        raise HTTPException(503, "run `make phase0` first")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/pareto/{variant}")
def pareto(variant: str) -> list[dict]:
    if variant not in VARIANTS:
        raise HTTPException(404, f"variant must be one of {sorted(VARIANTS)}")
    p = RESULTS / f"{VARIANTS[variant]}.parquet"
    if not p.exists():
        raise HTTPException(503, "run `make phase4` first")
    return json.loads(pd.read_parquet(p).to_json(orient="records"))


@app.get("/verification")
def verification() -> dict:
    p = RESULTS / "verification.json"
    if not p.exists():
        raise HTTPException(503, "run `make phase5` first")
    return json.loads(p.read_text(encoding="utf-8"))


def _surrogate_out(r: dict, i: int = 0) -> SurrogateOut:
    g = [float(x) for x in r["g"][i]]
    return SurrogateOut(U_flex_max=float(r["U_flex_max"][i]), U_shear_max=float(r["U_shear_max"][i]),
                        U_col_max=float(r["U_col_max"][i]), defl_ratio_max=float(r["defl_ratio_max"][i]),
                        cost=float(r["cost"][i]), carbon=float(r["carbon"][i]), feasible=bool(all(x <= 0 for x in g)), g=g)


@app.post("/evaluate/surrogate", response_model=SurrogateResponse)
def evaluate_surrogate(body: GenomeIn) -> SurrogateResponse:
    g = _genome(body)[None, :]
    a, b = _model("A"), _model("B")
    pa = a.predict(g)
    ra = a.predict_eval(g)
    ra.update({k: pa[k] for k in ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max")})
    rb = b.predict_eval(g)
    return SurrogateResponse(repaired_genome=[int(x) for x in g[0]], A=_surrogate_out(ra), B=_surrogate_out(rb))


@app.post("/evaluate/fe")
def evaluate_fe(body: GenomeIn) -> dict:
    """Ground truth: OpenSeesPy FE + IS 456 checks (about 50 ms)."""
    return describe_genome(_genome(body))


@app.post("/evaluate/cost-carbon", response_model=CostCarbonResponse)
def evaluate_cost_carbon(body: GenomeIn) -> CostCarbonResponse:
    g = _genome(body)
    d = describe_genome(g)
    return CostCarbonResponse(repaired_genome=[int(x) for x in g], status=d["status"], quantities=d.get("quantities"),
                              cost_inr=d.get("cost_inr"), carbon_kgco2e=d.get("carbon_kgco2e"),
                              provisional=bool(config.provisional_items()))
