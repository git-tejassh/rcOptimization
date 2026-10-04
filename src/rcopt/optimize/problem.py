"""NSGA-II problem definition and the three evaluators (surrogate A, surrogate B, direct FE) - project.md 8.4.

Minimise [cost (INR), carbon (kgCO2e)] over integer-index genomes; constraints g <= 0 (pymoo convention):
``[defl - 1, U_flex - 1, U_shear - 1, U_col - 1, g_beam_steel, g_col_pt, geom_violation]``.
Each evaluator memoises per genome (deterministic functions), counts requests and *unique* evaluations.
"""
from __future__ import annotations

import time

import numpy as np
from pymoo.core.problem import Problem
from pymoo.core.repair import Repair

from rcopt.design.variables import DesignSpace, default_space
from rcopt.fe.runner import evaluate_genome

N_G = 7


class GenomeRepair(Repair):
    """Round / clip to the option ranges, then snap to the nearest buildable design (D-012)."""

    def __init__(self, space: DesignSpace | None = None):
        super().__init__()
        self.space = space or default_space()

    def _do(self, problem, X, **kwargs):
        X = np.clip(np.rint(X), 0, self.space.n_options - 1).astype(int)
        return np.array([self.space.repair(x) for x in X], dtype=float)


class Evaluator:
    """Base class: memoised batch evaluation of genomes -> (F (n, 2), G (n, 7))."""

    name = "base"

    def __init__(self):
        self.n_requested = 0
        self.n_unique = 0
        self.n_fe_solves = 0
        self.fe_time_s = 0.0
        self.wall_s = 0.0
        self._cache: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}

    def _compute(self, G: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def __call__(self, G: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        G = np.asarray(G, dtype=int)
        t0 = time.perf_counter()
        keys = [tuple(g) for g in G]
        self.n_requested += len(keys)
        todo = [i for i, k in enumerate(keys) if k not in self._cache]
        uniq = {keys[i]: i for i in todo}
        if uniq:
            idx = list(uniq.values())
            F, Gm = self._compute(G[idx])
            self.n_unique += len(idx)
            for j, i in enumerate(idx):
                self._cache[keys[i]] = (F[j], Gm[j])
        F = np.array([self._cache[k][0] for k in keys])
        Gm = np.array([self._cache[k][1] for k in keys])
        self.wall_s += time.perf_counter() - t0
        return F, Gm

    def stats(self) -> dict:
        return {"evaluator": self.name, "evaluations_requested": self.n_requested, "unique_evaluations": self.n_unique,
                "unique_fe_solves": self.n_fe_solves, "fe_time_s": self.fe_time_s, "eval_wall_s": self.wall_s}


class SurrogateEvaluator(Evaluator):
    def __init__(self, model, name: str, margin: float = 0.0):
        super().__init__()
        self.model, self.name, self.margin = model, name, margin

    def _compute(self, G):
        r = self.model.predict_eval(G, margin=self.margin)
        return np.column_stack([r["cost"], r["carbon"]]), r["g"]


class DirectFEEvaluator(Evaluator):
    """Ground truth: OpenSees FE + IS 456 checks per genome (FE cached per size key inside the process)."""

    name = "direct_FE"

    def __init__(self, space: DesignSpace | None = None):
        super().__init__()
        self.space = space or default_space()

    def _compute(self, G):
        F = np.full((len(G), 2), 1e12)
        Gm = np.full((len(G), N_G), 1e3)
        for i, g in enumerate(G):
            r = evaluate_genome(g, self.space)
            self.n_fe_solves += 0 if r.get("fe_cached", 1) else 1
            self.fe_time_s += r.get("fe_time_s", 0.0)
            if r["status"] == "OK":
                F[i] = (r["cost"], r["carbon"])
                Gm[i] = (r["defl_ratio_max"] - 1, r["U_flex_max"] - 1, r["U_shear_max"] - 1, r["U_col_max"] - 1,
                         r["g_beam_steel"], r["g_col_pt"], r["geom_violation"])
        return F, Gm


class RCProblem(Problem):
    """Two objectives, seven inequality constraints over the 23 integer genes."""

    def __init__(self, evaluator: Evaluator, space: DesignSpace | None = None):
        space = space or default_space()
        super().__init__(n_var=space.n_genes, n_obj=2, n_ieq_constr=N_G, xl=np.zeros(space.n_genes),
                         xu=(space.n_options - 1).astype(float), vtype=int)
        self.evaluator = evaluator

    def _evaluate(self, X, out, *args, **kwargs):
        F, G = self.evaluator(np.rint(X).astype(int))
        out["F"], out["G"] = F, G
