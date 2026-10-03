"""+/-20 % sensitivity of the headline front to steel cost, cement carbon and steel carbon (project.md 9.5).

For each scenario the headline optimisation (surrogate A) is re-run for the first two seeds with the scaled factor, the
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


def _true_front(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[(df.true_status == "OK") & (df.true_feasible == 1)].reset_index(drop=True)
    if ok.empty:
        return ok
    nd = non_dominated(ok[["true_cost", "true_carbon"]].to_numpy())
    return ok.iloc[nd].sort_values("true_cost").reset_index(drop=True)


def run_sensitivity(force: bool = False, n_jobs: int = 8) -> dict:
    oc = config.load_dict("optimize")
    seeds = oc["seeds"][:N_SEEDS]
    tasks = [("A", s, oc["pop_size"], oc["n_gen"], force, sc, name) for name, sc in SCENARIOS.items() if name != "baseline"
             for s in seeds]
    Parallel(n_jobs=n_jobs, backend="loky")(delayed(run_one)(*t) for t in tasks)

    fronts: dict[str, pd.DataFrame] = {}
    for name, sc in SCENARIOS.items():
        tag = "A" if name == "baseline" else name
        runs = [joblib.load(OUT_DIR / f"{tag}_seed{s}.joblib") for s in seeds]
        X, _ = pooled_front(runs)
        with scenario(**sc):
            fronts[name] = _true_front(reevaluate(X))
    base = fronts["baseline"]
    gcols = [c for c in base.columns if c.startswith("g_")]
    out = []
    for name, sc in SCENARIOS.items():
        f = fronts[name]
        with scenario(**sc):                                  # baseline designs re-priced under this scenario
            rep = reevaluate(base[gcols].to_numpy())
        rep = rep[(rep.true_status == "OK")].reset_index(drop=True)
        union = np.vstack([f[["true_cost", "true_carbon"]].to_numpy(), rep[["true_cost", "true_carbon"]].to_numpy()])
        nd = set(non_dominated(union).tolist())
        survive = [i in nd for i in range(len(f), len(union))]
        sp_c = spearmanr(base.true_cost, rep.true_cost)[0] if len(rep) > 2 else float("nan")
        sp_k = spearmanr(base.true_carbon, rep.true_carbon)[0] if len(rep) > 2 else float("nan")
        norm = Normaliser(union)
        knee_i = int(np.argmin(np.linalg.norm(norm(f[["true_cost", "true_carbon"]].to_numpy()), axis=1)))
        base_knee = int(np.argmin(np.linalg.norm(norm(base[["true_cost", "true_carbon"]].to_numpy()), axis=1)))
        k = f.iloc[knee_i]
        same = bool(k["g_fck"] == base["g_fck"].iloc[base_knee] and k["g_fy"] == base["g_fy"].iloc[base_knee])
        out.append({
            "name": name, "label": LABELS[name], "front_size": int(len(f)),
            "hv": norm.hv(f[["true_cost", "true_carbon"]].to_numpy()),
            "cost_range": [float(f.true_cost.min()), float(f.true_cost.max())],
            "carbon_range": [float(f.true_carbon.min()), float(f.true_carbon.max())],
            "baseline_survival_fraction": float(np.mean(survive)) if survive else float("nan"),
            "cost_rank_spearman": float(sp_c), "carbon_rank_spearman": float(sp_k),
            "knee": {"cost": float(k.true_cost), "carbon": float(k.true_carbon), "g_fck": int(k["g_fck"]),
                     "g_fy": int(k["g_fy"]), "same_grades_as_baseline_knee": same},
            "front": [{"cost": float(a), "carbon": float(b)} for a, b in f[["true_cost", "true_carbon"]].to_numpy()],
        })
    worst_surv = min(s["baseline_survival_fraction"] for s in out)
    worst_rho = min(min(s["cost_rank_spearman"], s["carbon_rank_spearman"]) for s in out)
    verdict = (f"Under +/-20 % changes of steel cost, cement carbon and steel carbon, at least {100 * worst_surv:.0f} % of the "
               f"baseline-front designs remain non-dominated and the worst rank correlation of cost/carbon along the baseline front is "
               f"{worst_rho:.3f}. ")
    verdict += ("The shape and ordering of the front are robust to these perturbations." if worst_surv >= 0.8 and worst_rho >= 0.95
                else "The front is NOT fully robust to these perturbations: see the scenario table.")
    res = {"scenarios": out, "verdict": verdict, "seeds_used": seeds,
           "note": "all rates and factors are provisional, so absolute levels are indicative only"}
    (RESULTS / "sensitivity.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res
