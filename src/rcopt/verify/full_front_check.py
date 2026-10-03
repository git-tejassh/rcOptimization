"""Extra finding (D4): cheap re-evaluation of the ENTIRE pooled front of every configuration."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from rcopt.config import ROOT
from rcopt.optimize.metrics import Normaliser, non_dominated

RESULTS = ROOT / "data" / "results"
FILES = {"A": "pareto_surrogate_A", "A_margin": "pareto_surrogate_A_margin", "B": "pareto_surrogate_B",
         "B_margin": "pareto_surrogate_B_margin", "direct": "pareto_direct"}


def run_full_front_check() -> dict:
    fronts = {k: pd.read_parquet(RESULTS / f"{v}.parquet") for k, v in FILES.items()}
    cmp_ = json.loads((RESULTS / "compute_comparison.json").read_text())
    norm = Normaliser.__new__(Normaliser)
    norm.ideal, norm.nadir = np.array(cmp_["norm"]["ideal"]), np.array(cmp_["norm"]["nadir"])
    norm.range, norm.ref = np.maximum(norm.nadir - norm.ideal, 1e-12), np.full(2, 1.05)
    out = {}
    for k, d in fronts.items():
        ok = (d.true_status == "OK") & (d.true_feasible == 1)
        pred = d[["pred_cost", "pred_carbon"]].to_numpy()
        true = d.loc[ok, ["true_cost", "true_carbon"]].to_numpy()
        true_nd = true[non_dominated(true)] if len(true) else true
        out[k] = {
            "front_size": int(len(d)), "truly_feasible": int(ok.sum()), "truly_feasible_fraction": float(ok.mean()),
            "hv_predicted_front": norm.hv(pred), "hv_true_front_of_truly_feasible": norm.hv(true_nd),
            "hv_gap_relative": float((norm.hv(pred) - norm.hv(true_nd)) / max(norm.hv(pred), 1e-12)),
            "cost_rel_err_mean": float(np.mean(np.abs(d.pred_cost - d.true_cost) / d.true_cost)),
            "carbon_rel_err_mean": float(np.mean(np.abs(d.pred_carbon - d.true_carbon) / d.true_carbon)),
            "max_true_utilisation_violation": float(np.max(np.maximum(d[[f"true_{t}" for t in
                ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max")]].max(axis=1) - 1.0, 0.0))),
        }
    (RESULTS / "full_front_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out
