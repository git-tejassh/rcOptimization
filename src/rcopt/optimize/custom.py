"""Re-optimise with the user's own unit prices (the "change prices, then optimise" workflow of the dashboard and CLI).

One NSGA-II run (surrogate + safety margin by default, so a run takes seconds to a few minutes) is started AFTER the prices are
applied; its near-Pareto designs are then re-evaluated with the exact FE + IS 456 check under the same prices and only truly
feasible designs are reported. Quality of the quick run is lower than the 5-seed study of ``rcopt phase4`` (one seed, fewer
generations): the result says so.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize

from rcopt import config
from rcopt.config import ROOT
from rcopt.cost_carbon import prices as price_mod
from rcopt.cost_carbon import scenario
from rcopt.design.describe import describe_genome
from rcopt.design.variables import default_space
from rcopt.optimize.metrics import non_dominated
from rcopt.optimize.phase4 import pooled_front
from rcopt.optimize.problem import GenomeRepair, RCProblem
from rcopt.optimize.run import HistoryCallback, make_evaluator

MODES = {"quick": {"pop": 100, "gen": 60}, "standard": {"pop": 200, "gen": 150}}
ENGINES = ("B_margin", "B", "A_margin", "A", "direct")


class _Progress(HistoryCallback):
    """HistoryCallback that also reports progress to a JSON file (polled by the API)."""

    def __init__(self, path: Path | None, n_gen: int, t0: float):
        super().__init__()
        self.path, self.n_gen, self.t0 = path, n_gen, t0

    def notify(self, algorithm):
        super().notify(algorithm)
        if self.path is not None:
            write_progress(self.path, "optimising", gen=int(algorithm.n_gen), n_gen=self.n_gen, feasible=self.n_feasible[-1],
                           elapsed_s=round(time.perf_counter() - self.t0, 1))


def write_progress(path: Path | None, stage: str, **kw) -> None:
    if path is not None:
        Path(path).write_text(json.dumps({"stage": stage, **kw}), encoding="utf-8")


def _design_record(i: int, g: np.ndarray, pred: tuple[float, float], sp) -> dict:
    d = describe_genome(g, sp)
    ok = d.get("status") == "OK"
    rec = {"id": i, "genome": [int(x) for x in g], "concrete": d["concrete"], "steel": d["steel"], "cement": d["cement"], "beams": d["beams"],
           "columns": d["columns"], "pred_cost": float(pred[0]), "pred_carbon": float(pred[1]),
           "true_cost": float(d["cost_inr"]["total"]) if ok else None,
           "true_carbon": float(d["carbon_kgco2e"]["total"]) if ok else None,
           "feasible_true": bool(d.get("feasible", False)), "status": d["status"]}
    for k in ("quantities", "cost_inr", "carbon_kgco2e", "utilisation", "stirrup_spacing_mm"):
        if k in d:
            rec[k] = d[k]
    rec["verification"] = {"verified": True, "passed": rec["feasible_true"], "boundary_pick": False,
                           "reasons": [] if rec["feasible_true"] else ["exact FE + IS 456 check: not feasible"]}
    return rec


def _baseline_repriced(sp) -> dict:
    """The designs that were optimal under the placeholder prices, priced with the new prices (shows what the price change does)."""
    import pandas as pd

    path = ROOT / "data" / "results" / "pareto_surrogate_B_margin.parquet"
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    df = df[df.true_status == "OK"] if "true_status" in df else df
    out = {}
    for name, col in (("lowest_cost", "true_cost"), ("lowest_carbon", "true_carbon")):
        row = df.sort_values(col).iloc[0]
        g = np.array([int(row[f"g_{n}"]) for n in sp.gene_names])
        d = describe_genome(g, sp)
        if d.get("status") == "OK":
            out[name] = {"cost_old_prices": float(row["true_cost"]), "cost_new_prices": float(d["cost_inr"]["total"]),
                         "carbon": float(d["carbon_kgco2e"]["total"]), "concrete": d["concrete"], "steel": d["steel"], "cement": d["cement"]}
    return out


def reoptimize(price_values: dict | None = None, mode: str = "quick", engine: str = "B_margin", seed: int = 1,
               progress_path: Path | None = None, target: int = 40) -> dict:
    """Run the price-driven optimisation and return a JSON-serialisable result (see module docstring)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {tuple(MODES)}")
    if engine not in ENGINES:
        raise ValueError(f"engine must be one of {ENGINES}")
    vals = price_mod.validate(price_values or {})
    defaults = price_mod.defaults()
    full = {**defaults, **vals}
    changed = {k: v for k, v in full.items() if abs(v - defaults[k]) > 1e-12}
    pop_size, n_gen = MODES[mode]["pop"], MODES[mode]["gen"]
    sp = default_space()
    t0 = time.perf_counter()
    scenario.set_scenario(full)
    try:
        write_progress(progress_path, "loading", gen=0, n_gen=n_gen)
        ev = make_evaluator(engine)
        cb = _Progress(progress_path, n_gen, t0)
        algo = NSGA2(pop_size=pop_size, sampling=IntegerRandomSampling(),
                     crossover=SBX(prob=0.9, eta=15, vtype=float, repair=RoundingRepair()),
                     mutation=PM(eta=20, vtype=float, repair=RoundingRepair()), repair=GenomeRepair(), eliminate_duplicates=True)
        res = minimize(RCProblem(ev), algo, ("n_gen", n_gen), seed=seed, callback=cb, verbose=False)
        wall_opt = time.perf_counter() - t0
        pop = res.pop
        run = {"X": pop.get("X").astype(int), "F": pop.get("F"), "CV": pop.get("CV")[:, 0]}
        X, F = pooled_front([run], target=target)
        write_progress(progress_path, "verifying", gen=n_gen, n_gen=n_gen, n_candidates=int(len(X)), elapsed_s=round(wall_opt, 1))
        designs = [_design_record(i, X[i], (F[i, 0], F[i, 1]), sp) for i in range(len(X))]
        good = [d for d in designs if d["feasible_true"]]
        if good:
            nd = non_dominated(np.array([[d["true_cost"], d["true_carbon"]] for d in good]))
            for j, d in enumerate(good):
                d["pareto_true"] = bool(j in set(int(x) for x in nd))
        baseline = _baseline_repriced(sp)
        result = {
            "prices": full, "defaults": defaults, "changed": changed, "mode": mode, "engine": engine, "seed": seed,
            "pop_size": pop_size, "n_gen": n_gen, "evaluations": int(ev.stats()["evaluations_requested"]),
            "wall_s": round(time.perf_counter() - t0, 1), "n_candidates": len(designs), "n_feasible_true": len(good),
            "designs": good, "rejected": len(designs) - len(good), "baseline_repriced": baseline,
            "note": ("Quick single-seed run (surrogate"
                     + (" + safety margin" if engine.endswith("_margin") else "")
                     + ", then every reported design re-checked with the exact finite-element model and IS 456 under the SAME prices). "
                     "Prices that are placeholders stay placeholders: absolute INR values are indicative. Gravity loads only."),
            "provisional": True, "config_hash": config.config_hash(),
        }
        write_progress(progress_path, "done", gen=n_gen, n_gen=n_gen, elapsed_s=result["wall_s"])
        return result
    finally:
        scenario.set_scenario(None)
