"""+/-20 % sensitivity of the headline front to steel cost, cement carbon and steel carbon (project.md 9.5).

For each scenario the best-validated optimisation (surrogate B + safety margin) is re-run for the first two seeds with the scaled factor, the
pooled front is re-evaluated with ground truth under that scenario, and compared with the baseline front.
"""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

from rcopt import config
from rcopt.config import ROOT
from rcopt.cost_carbon.scenario import scenario
from rcopt.optimize.metrics import Normaliser, non_dominated
from rcopt.optimize.phase4 import pooled_front, reevaluate
from rcopt.optimize.run import OUT_DIR, run_one

RESULTS = ROOT / "data" / "results"
SCENARIOS = {
    "baseline": {},
    "steel_cost_-20": {"steel_cost_scale": 0.8}, "steel_cost_+20": {"steel_cost_scale": 1.2},
    "cement_carbon_-20": {"cement_carbon_scale": 0.8}, "cement_carbon_+20": {"cement_carbon_scale": 1.2},
    "steel_carbon_-20": {"steel_carbon_scale": 0.8}, "steel_carbon_+20": {"steel_carbon_scale": 1.2},
}
LABELS = {"baseline": "Baseline", "steel_cost_-20": "Steel INR/kg -20 %", "steel_cost_+20": "Steel INR/kg +20 %",
          "cement_carbon_-20": "Cement carbon -20 %", "cement_carbon_+20": "Cement carbon +20 %",
          "steel_carbon_-20": "Steel carbon -20 %", "steel_carbon_+20": "Steel carbon +20 %"}
N_SEEDS = 2
HEADLINE = "B_margin"   # best validated configuration (97 % verification pass rate); plain A is mostly infeasible in truth


def _true_front(df: pd.DataFrame) -> pd.DataFrame:  # kept for API compatibility
    ok = df[(df.true_status == "OK") & (df.true_feasible == 1)].reset_index(drop=True)
    if ok.empty:
        return ok
    nd = non_dominated(ok[["true_cost", "true_carbon"]].to_numpy())
    return ok.iloc[nd].sort_values("true_cost").reset_index(drop=True)


def _knee(arr: np.ndarray, norm: Normaliser) -> int:
    """Index of the design closest to the ideal point in normalised objective space."""
    return int(np.argmin(np.linalg.norm(norm(arr), axis=1)))


def run_sensitivity(force: bool = False, n_jobs: int = 8) -> dict:
    oc = config.load_dict("optimize")
    seeds = oc["seeds"][:N_SEEDS]
    tasks = [(HEADLINE, s, oc["pop_size"], oc["n_gen"], force, sc, name) for name, sc in SCENARIOS.items() if name != "baseline"
             for s in seeds]
    Parallel(n_jobs=n_jobs, backend="loky")(delayed(run_one)(*t) for t in tasks)

    sets: dict[str, pd.DataFrame] = {}
    for name, sc in SCENARIOS.items():
        tag = HEADLINE if name == "baseline" else name
        runs = [joblib.load(OUT_DIR / f"{tag}_seed{s}.joblib") for s in seeds]
        X, _ = pooled_front(runs)
        with scenario(**sc):
            d = reevaluate(X)
        sets[name] = d[(d.true_status == "OK") & (d.true_feasible == 1)].reset_index(drop=True)
    base = sets["baseline"]
    gcols = [c for c in base.columns if c.startswith("g_")]
    xy = ["true_cost", "true_carbon"]
    out = []
    for name, sc in SCENARIOS.items():
        f = sets[name]
        with scenario(**sc):                                  # baseline designs re-priced under this scenario
            rep = reevaluate(base[gcols].to_numpy())
        rep = rep[rep.true_status == "OK"].reset_index(drop=True)
        union = np.vstack([f[xy].to_numpy(), rep[xy].to_numpy()])
        norm = Normaliser(union)
        # ordering robustness: rank correlation of the baseline designs' cost / carbon before and after re-pricing
        sp_c = float(spearmanr(base.true_cost, rep.true_cost)[0]) if len(rep) > 2 else float("nan")
        sp_k = float(spearmanr(base.true_carbon, rep.true_carbon)[0]) if len(rep) > 2 else float("nan")
        # regret: how much worse is the baseline's best design than the best available under this scenario
        reg_c = float(rep.true_cost.iloc[int(np.argmin(base.true_cost))] / union[:, 0].min() - 1.0)
        reg_k = float(rep.true_carbon.iloc[int(np.argmin(base.true_carbon))] / union[:, 1].min() - 1.0)
        knee_scn = f.iloc[_knee(f[xy].to_numpy(), norm)]
        knee_base_repriced = rep.iloc[_knee(base[xy].to_numpy(), norm)]
        nd_idx = non_dominated(f[xy].to_numpy())
        nd = f.iloc[nd_idx].sort_values("true_cost")
        base_nd = set(non_dominated(base[xy].to_numpy()).tolist())
        rep_nd_idx = set(non_dominated(union).tolist())
        survive = [i in base_nd and (len(f) + i) in rep_nd_idx for i in range(len(rep))]
        out.append({
            "name": name, "label": LABELS[name], "front_size": int(len(nd)), "set_size": int(len(f)),
            "hv": norm.hv(nd[xy].to_numpy()),
            "cost_range": [float(f.true_cost.min()), float(f.true_cost.max())],
            "carbon_range": [float(f.true_carbon.min()), float(f.true_carbon.max())],
            "baseline_survival_fraction": float(np.sum(survive) / max(len(base_nd), 1)),
            "cost_rank_spearman": sp_c, "carbon_rank_spearman": sp_k,
            "regret_baseline_cost_optimum": reg_c, "regret_baseline_carbon_optimum": reg_k,
            "knee": {"cost": float(knee_scn.true_cost), "carbon": float(knee_scn.true_carbon), "g_fck": int(knee_scn["g_fck"]),
                     "g_fy": int(knee_scn["g_fy"]),
                     "same_knee_as_baseline": bool((knee_scn[gcols].to_numpy() == base.iloc[_knee(base[xy].to_numpy(), norm)][gcols].to_numpy()).all()),
                     "baseline_knee_repriced_cost": float(knee_base_repriced.true_cost)},
            "front": [{"cost": float(a_), "carbon": float(b_)} for a_, b_ in f[xy].to_numpy()],
        })
    worst_reg = max(max(s["regret_baseline_cost_optimum"], s["regret_baseline_carbon_optimum"]) for s in out)
    worst_rho = min(min(s["cost_rank_spearman"], s["carbon_rank_spearman"]) for s in out)
    verdict = (f"Under +/-20 % changes of steel cost, cement carbon and steel carbon, the baseline cost/carbon optima lose at most "
               f"{100 * worst_reg:.1f} % against the best design available under each scenario, and the worst rank correlation of cost/carbon "
               f"across the baseline set is {worst_rho:.3f}. ")
    verdict += ("The location of the optimum and the ordering of designs are robust to these perturbations." if worst_reg <= 0.02 and worst_rho >= 0.95
                else "The optimum or the ordering is NOT fully robust to these perturbations: see the scenario table.")
    res = {"scenarios": out, "verdict": verdict, "seeds_used": seeds,
           "note": "all rates and factors are provisional, so absolute levels are indicative only; "
                   "sets are the truly feasible near-Pareto designs (the Pareto front proper is 1-4 points)"}
    (RESULTS / "sensitivity.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res
