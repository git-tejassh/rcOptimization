"""Phase 5: re-verify Pareto designs with ground truth (project.md 8.5).

Selection (fixed rule, executed once, never revisited after seeing results): ``n_designs`` designs per front, chosen
along the cost axis in equal-quantile bins (the design closest to each bin median) plus the ``n_boundary`` designs
with the smallest *predicted* constraint slack (where surrogates are weakest). Pass = truly feasible AND the predicted
utilisations / deflection agree with the truth within the configured tolerances. Failures are listed with reasons.
"""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.variables import default_space
from rcopt.fe.runner import evaluate_genome
from rcopt.surrogate.models import TARGETS_A

RESULTS = ROOT / "data" / "results"
UTIL = ("U_flex_max", "U_shear_max", "U_col_max")


def predict_front(model_name: str, G: np.ndarray) -> dict:
    model = joblib.load(ROOT / "models" / f"surrogate_{model_name}.joblib")
    if model_name == "A":
        p = model.predict(G)
        r = model.predict_eval(G)
        p["cost"], p["carbon"], p["g"] = r["cost"], r["carbon"], r["g"]
        return p
    return model.predict_eval(G)


def select_designs(cost: np.ndarray, slack: np.ndarray, n_designs: int, n_boundary: int) -> np.ndarray:
    """Indices: (n_designs - n_boundary) cost-quantile picks + n_boundary smallest predicted slack (distinct)."""
    n = len(cost)
    n_q = max(min(n_designs - n_boundary, n), 0)
    order = np.argsort(cost)
    picks: list[int] = []
    if n_q:
        for chunk in np.array_split(order, n_q):
            if len(chunk):
                picks.append(int(chunk[len(chunk) // 2]))
    rest = [i for i in np.argsort(slack) if i not in set(picks)]
    picks += rest[:min(n_boundary, len(rest))]
    return np.array(sorted(set(picks)), dtype=int)


def verify_front(variant: str, front: pd.DataFrame, vc: dict, tol: dict) -> dict:
    sp = default_space()
    gcols = [f"g_{n}" for n in sp.gene_names]
    G = front[gcols].to_numpy().astype(int)
    model = "A" if variant.startswith("A") else "B"
    pred = predict_front(model, G)
    slack = -np.max(pred["g"][:, :4], axis=1)                   # >0 = predicted feasible with room
    sel = select_designs(front["pred_cost"].to_numpy(), np.abs(slack), vc["n_designs"], vc["n_boundary"])
    boundary_idx = set(np.argsort(np.abs(slack))[:vc["n_boundary"]].tolist())
    rows, fails = [], []
    for i in sel:
        r = evaluate_genome(G[i], sp)
        rec = {"index": int(i), "pred_cost": float(front["pred_cost"].iloc[i]), "pred_carbon": float(front["pred_carbon"].iloc[i]),
               "boundary_pick": bool(i in boundary_idx), "status": r["status"]}
        reasons = []
        if r["status"] != "OK":
            reasons.append(f"FE_STATUS:{r['status']}")
        else:
            rec.update(true_cost=r["cost"], true_carbon=r["carbon"], feasible_true=bool(r["feasible"]))
            for t in TARGETS_A:
                rec[f"pred_{t}"], rec[f"true_{t}"] = float(pred[t][i]), float(r[t])
            for t in UTIL:
                err = abs(rec[f"pred_{t}"] - rec[f"true_{t}"])
                rec[f"err_{t}"] = err
                if err > tol["util_abs"]:
                    reasons.append(f"TOLERANCE:{t} |err|={err:.3f} > {tol['util_abs']}")
            rel = abs(rec["pred_defl_ratio_max"] - rec["true_defl_ratio_max"]) / max(rec["true_defl_ratio_max"], 1e-9)
            rec["err_defl_rel"] = rel
            if rel > tol["defl_rel"]:
                reasons.append(f"TOLERANCE:defl_ratio_max rel err {rel:.3f} > {tol['defl_rel']}")
            if not rec["feasible_true"]:
                over = {t: rec[f"true_{t}"] for t in TARGETS_A if rec[f"true_{t}"] > 1.0}
                if r["g_beam_steel"] > 0 or r["g_col_pt"] > 0:
                    over["steel_limits"] = max(r["g_beam_steel"], r["g_col_pt"]) + 1
                reasons.append("TRULY_INFEASIBLE:" + ",".join(f"{k}={v:.3f}" for k, v in over.items()))
            rec["cost_rel_err"] = abs(rec["pred_cost"] - rec["true_cost"]) / rec["true_cost"]
            rec["carbon_rel_err"] = abs(rec["pred_carbon"] - rec["true_carbon"]) / rec["true_carbon"]
        rec["passed"] = not reasons
        rec["reasons"] = reasons
        rows.append(rec)
        if reasons:
            fails.append({"index": int(i), "boundary_pick": rec["boundary_pick"], "reasons": reasons})
    ok = [r for r in rows if r["status"] == "OK"]
    stats = {t: {"mean_abs_err": float(np.mean([abs(r[f'pred_{t}'] - r[f'true_{t}']) for r in ok])),
                 "max_abs_err": float(np.max([abs(r[f'pred_{t}'] - r[f'true_{t}']) for r in ok]))} for t in TARGETS_A} if ok else {}
    n_pass = sum(r["passed"] for r in rows)
    b_rows = [r for r in rows if r["boundary_pick"]]
    return {
        "variant": variant, "front_size": int(len(front)), "n_verified": len(rows), "n_pass": int(n_pass),
        "pass_rate": n_pass / max(len(rows), 1), "pass_target": vc["pass_target"],
        "target_met": bool(n_pass / max(len(rows), 1) >= vc["pass_target"]),
        "n_truly_feasible": int(sum(bool(r.get("feasible_true")) for r in rows)),
        "n_within_tolerance": int(sum(not any(x.startswith("TOLERANCE") for x in r["reasons"]) for r in rows)),
        "boundary_picks": {"n": len(b_rows), "n_pass": int(sum(r["passed"] for r in b_rows))},
        "failures": fails, "error_stats": stats,
        "cost_rel_err_mean": float(np.mean([r["cost_rel_err"] for r in ok])) if ok else None,
        "carbon_rel_err_mean": float(np.mean([r["carbon_rel_err"] for r in ok])) if ok else None,
        "designs": rows,
    }


def run_phase5() -> dict:
    vc = config.load_dict("verify")
    tol = config.load_dict("solver")["tolerance"]
    out: dict = {"tolerance": tol, "selection": {k: vc[k] for k in ("n_designs", "n_boundary", "pass_target")}, "variants": {}}
    for variant, fname in (("A", "pareto_surrogate_A"), ("A_margin", "pareto_surrogate_A_margin"),
                           ("B", "pareto_surrogate_B"), ("B_margin", "pareto_surrogate_B_margin")):
        front = pd.read_parquet(RESULTS / f"{fname}.parquet")
        out["variants"][variant] = verify_front(variant, front, vc, tol)
    out["headline"] = out["variants"]["A"]
    (RESULTS / "verification.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out
