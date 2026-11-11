"""Local FastAPI server: live surrogate evaluation and on-demand ground-truth FE (project.md 11.4, CLAUDE.md 8).

Run:  uvicorn api.main:app --reload     (or ``make api``).  Not intended for Vercel: it needs OpenSeesPy and XGBoost.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import uuid
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.schemas import CostCarbonResponse, GenomeIn, OptimizeIn, ReviewIn, SurrogateOut, SurrogateResponse
from rcopt import config
from rcopt.config import ROOT
from rcopt.cost_carbon import prices as price_mod
from rcopt.design.describe import describe_genome
from rcopt.design.variables import default_space
from rcopt.review.frame_review import ReviewError, review_staad

RESULTS = ROOT / "data" / "results"
app = FastAPI(title="RC frame optimisation API", version="0.1.0",
              description="Gravity-only IS 456 evaluation of discrete RC frame designs. Cost / carbon rates are provisional.")
# local tool without credentials: any origin may call it (needed when the dashboard is opened from a file or another port)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
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
    models = {n: (ROOT / "models" / f"surrogate_{n}.joblib").exists() for n in ("A", "B")}
    return {"status": "ok", "service": "rcopt", "surrogates": models, "strength_review": True, "price_optimiser": all(models.values()),
            "results_present": (RESULTS / "verification.json").exists(), "dashboard_built": (ROOT / "web" / "dist" / "index.html").exists(),
            "live_evaluator_ready": all(models.values()), "provisional_data": bool(config.provisional_items())}


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


@app.post("/review/staad")
def review_staad_endpoint(body: ReviewIn) -> dict:
    """Strength review + reinforcement design of a regular RC frame given as STAAD input text (about 0.5 s)."""
    if body.concrete not in config.load_dict("is456_tables")["concrete"]["fck_MPa"] or body.steel not in config.load_dict("is456_tables")["steel"]["fy_MPa"]:
        raise HTTPException(422, "unknown concrete or steel grade")
    try:
        return review_staad(body.text, body.concrete, body.steel, body.cement)
    except ReviewError as exc:
        raise HTTPException(422, str(exc)) from exc


# ----------------------------------------------------------------------------- change prices, then optimise
_JOBS: dict[str, dict] = {}          # job id -> {proc, dir, started, params}; one optimisation at a time (it uses several cores)


def _job_status(jid: str) -> dict:
    job = _JOBS.get(jid)
    if job is None:
        raise HTTPException(404, "unknown job id")
    d: Path = job["dir"]
    prog = {}
    if (d / "progress.json").exists():
        try:
            prog = json.loads((d / "progress.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prog = {}                                  # file caught mid-write: report the next poll
    rc = job["proc"].poll()
    out: dict = {"job_id": jid, "elapsed_s": round(time.time() - job["started"], 1), "params": job["params"], "progress": prog}
    if rc is None:
        out["status"] = "running"
    elif rc == 0 and (d / "result.json").exists():
        out["status"] = "done"
        out["result"] = json.loads((d / "result.json").read_text(encoding="utf-8"))
    else:
        out["status"] = "failed"
        out["error"] = ((d / "log.txt").read_text(encoding="utf-8", errors="replace")[-1500:] if (d / "log.txt").exists() else f"exit code {rc}")
    return out


@app.get("/prices/items")
def prices_items() -> dict:
    """Editable unit prices: key, label, unit, placeholder default, status; plus the CSV template."""
    return {"items": price_mod.items(), "csv_template": price_mod.to_csv_text(), "note": "every default is a placeholder, not a verified rate"}


@app.post("/optimize/prices")
def optimize_prices(body: OptimizeIn) -> dict:
    """Start a price-driven optimisation in a separate process (surrogate + safety margin, then exact FE re-check). Poll GET /optimize/jobs/{id}."""
    from rcopt.optimize.custom import ENGINES, MODES

    if body.mode not in MODES or body.engine not in ENGINES:
        raise HTTPException(422, f"mode must be one of {list(MODES)}, engine one of {list(ENGINES)}")
    if body.prices is not None and body.csv is not None:
        raise HTTPException(422, "give prices OR csv, not both")
    try:
        vals = price_mod.from_csv_text(body.csv) if body.csv is not None else price_mod.validate(body.prices or {})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if body.engine != "direct" and not (ROOT / "models" / f"surrogate_{body.engine[0]}.joblib").exists():
        raise HTTPException(503, f"surrogate {body.engine[0]} is not trained: run `python -m rcopt.cli phase3` or copy models.zip (see docs/DEPLOY.md)")
    if any(j["proc"].poll() is None for j in _JOBS.values()):
        raise HTTPException(409, "another optimisation is still running; wait for it to finish")
    jid = uuid.uuid4().hex[:10]
    d = Path(tempfile.mkdtemp(prefix=f"rcopt_{jid}_"))
    (d / "prices.json").write_text(json.dumps(vals), encoding="utf-8")
    cmd = [sys.executable, "-m", "rcopt.cli", "reoptimize", "--prices-json", str(d / "prices.json"), "--mode", body.mode,
           "--engine", body.engine, "--seed", str(body.seed), "--out", str(d / "result.json"), "--progress", str(d / "progress.json")]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=(d / "log.txt").open("w"), stderr=subprocess.STDOUT)
    _JOBS[jid] = {"proc": proc, "dir": d, "started": time.time(), "params": {"mode": body.mode, "engine": body.engine, "seed": body.seed, "changed": vals}}
    return {"job_id": jid, "status": "running"}


@app.get("/optimize/jobs/{job_id}")
def optimize_job(job_id: str) -> dict:
    return _job_status(job_id)


# the built dashboard is served from the same origin, so `rcopt serve` is a complete local deployment
_DIST = ROOT / "web" / "dist"
if (_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="dashboard")
