"""Run NSGA-II for the five configurations x seeds and persist fronts + convergence histories (project.md 8.4).

Configurations: ``A`` and ``B`` (surrogate-driven, no safety margin), ``A_margin`` and ``B_margin`` (constraints tightened by
the 95th-percentile boundary error of the surrogate), ``direct`` (live OpenSees FE + IS 456, same GA).
"""
from __future__ import annotations

import json
import time

import joblib
import numpy as np
from joblib import Parallel, delayed
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.callback import Callback
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

from rcopt import config
from rcopt.config import ROOT
from rcopt.optimize.problem import DirectFEEvaluator, GenomeRepair, RCProblem, SurrogateEvaluator

OUT_DIR = ROOT / "data" / "processed" / "opt"
CONFIGS = ("A", "A_margin", "B", "B_margin", "direct")


class HistoryCallback(Callback):
    """Per generation: cumulative evaluations and the feasible non-dominated objectives of the population."""

    def __init__(self):
        super().__init__()
        self.n_eval, self.fronts, self.n_feasible = [], [], []

    def notify(self, algorithm):
        pop = algorithm.pop
        F, CV = pop.get("F"), pop.get("CV")[:, 0]
        feas = CV <= 0
        self.n_eval.append(int(algorithm.evaluator.n_eval))
        self.n_feasible.append(int(feas.sum()))
        if feas.any():
            nd = NonDominatedSorting().do(F[feas], only_non_dominated_front=True)
            self.fronts.append(F[feas][nd].copy())
        else:
            self.fronts.append(np.empty((0, 2)))


def _margin(name: str) -> float:
    if not name.endswith("_margin"):
        return 0.0
    m = json.loads((ROOT / "data" / "results" / "surrogate_metrics.json").read_text())["margin_q95"]
    return float(m[name[0]])


def make_evaluator(name: str):
    if name == "direct":
        return DirectFEEvaluator()
    model = joblib.load(ROOT / "models" / f"surrogate_{name[0]}.joblib")
    return SurrogateEvaluator(model, name, margin=_margin(name))


def run_one(name: str, seed: int, pop_size: int, n_gen: int, force: bool = False, scenario: dict | None = None,
            tag: str | None = None) -> dict:
    """One NSGA-II run (fresh process state); returns a small summary and writes ``OUT_DIR/<name>_seed<k>.joblib``."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{tag or name}_seed{seed}.joblib"
    chash = config.config_hash()
    if path.exists() and not force:
        d = joblib.load(path)
        if d["config_hash"] == chash and d["pop_size"] == pop_size and d["n_gen"] == n_gen:
            return d["summary"]
    from rcopt.fe import runner as fe_runner

    fe_runner._fe_cached.cache_clear()                 # unique FE solves must be counted per run
    from rcopt.cost_carbon.scenario import set_scenario

    set_scenario(scenario)                              # +/-20 % sensitivity scenarios (process-local)
    ev = make_evaluator(name)
    problem = RCProblem(ev)
    cb = HistoryCallback()
    algo = NSGA2(pop_size=pop_size, sampling=IntegerRandomSampling(),
                 crossover=SBX(prob=0.9, eta=15, vtype=float, repair=RoundingRepair()),
                 mutation=PM(eta=20, vtype=float, repair=RoundingRepair()), repair=GenomeRepair(),
                 eliminate_duplicates=True)
    t0 = time.perf_counter()
    res = minimize(problem, algo, ("n_gen", n_gen), seed=seed, callback=cb, verbose=False)
    wall = time.perf_counter() - t0
    pop = res.pop
    X, F, CV = pop.get("X").astype(int), pop.get("F"), pop.get("CV")[:, 0]
    feas = CV <= 0
    summary = {"config": tag or name, "seed": seed, "scenario": scenario or {}, "wall_s": wall, "pop_size": pop_size, "n_gen": n_gen,
               "n_feasible_final": int(feas.sum()), **ev.stats(), "margin": getattr(ev, "margin", 0.0)}
    joblib.dump({"X": X, "F": F, "CV": CV, "G": pop.get("G"), "n_eval": cb.n_eval, "fronts": cb.fronts,
                 "n_feasible": cb.n_feasible, "summary": summary, "config_hash": chash, "pop_size": pop_size,
                 "n_gen": n_gen}, path, compress=3)
    set_scenario(None)
    return summary


def run_all(force: bool = False, n_jobs: int = 8, configs=CONFIGS, direct_scale: bool = True) -> list[dict]:
    oc = config.load_dict("optimize")
    tasks = []
    for name in configs:
        pop, gen = (oc["direct_fe"]["pop_size"], oc["direct_fe"]["n_gen"]) if (name == "direct" and direct_scale) else (
            oc["pop_size"], oc["n_gen"])
        for seed in oc["seeds"]:
            tasks.append((name, seed, pop, gen))
    tasks.sort(key=lambda t: t[0] != "direct")        # slowest (direct FE) first for load balance
    return Parallel(n_jobs=n_jobs, backend="loky")(delayed(run_one)(*t, force) for t in tasks)
