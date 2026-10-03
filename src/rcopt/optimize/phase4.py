"""Phase 4 orchestration: run all configurations x seeds, pool fronts, re-evaluate them with ground truth, compare compute."""
from __future__ import annotations

import json
import time

import joblib
import numpy as np
import pandas as pd

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.variables import default_space
from rcopt.fe.runner import evaluate_genome
from rcopt.optimize.metrics import Normaliser, non_dominated, objective_correlation, spacing
from rcopt.optimize.run import CONFIGS, OUT_DIR, run_all

RESULTS = ROOT / "data" / "results"
TRUE_COLS = ("cost", "carbon", "U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max", "feasible", "status",
             "concrete_m3", "steel_kg", "formwork_m2", "g_beam_steel", "g_col_pt")


def load_runs(configs=CONFIGS) -> dict[str, list[dict]]:
    oc = config.load_dict("optimize")
    return {c: [joblib.load(OUT_DIR / f"{c}_seed{s}.joblib") for s in oc["seeds"]] for c in configs}


def pooled_front(runs: list[dict], target: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Near-Pareto set: feasible (as the algorithm saw it) final-population members of all seeds, unique, taken rank by rank
    (non-dominated sorting) until ``target`` designs are collected. Rank 1 is the pooled Pareto front proper; with these
    objectives it is tiny (cost and carbon are aligned), so deeper ranks give the verification / full-front checks
    something to test. Returns (genomes, F) sorted by (rank, cost); ``last_ranks`` holds the rank of each row."""
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

    X = np.vstack([r["X"][r["CV"] <= 0] for r in runs])
    F = np.vstack([r["F"][r["CV"] <= 0] for r in runs])
    if len(X) == 0:
        pooled_front.last_ranks = np.array([], dtype=int)
        return X, F
    _, first = np.unique(X, axis=0, return_index=True)
    X, F = X[first], F[first]
    order: list[int] = []
    ranks: list[int] = []
    for rk, front in enumerate(NonDominatedSorting().do(F), start=1):
        front = np.array(front)[np.argsort(F[front, 0])]
        order += front.tolist()
        ranks += [rk] * len(front)
        if len(order) >= target:
            break
    pooled_front.last_ranks = np.array(ranks, dtype=int)
    return X[order], F[order]


pooled_front.last_ranks = np.array([], dtype=int)


def reevaluate(X: np.ndarray) -> pd.DataFrame:
    """Ground-truth FE + IS 456 evaluation of genomes (used for every reported front)."""
    sp = default_space()
    rows = [evaluate_genome(g, sp) for g in X]
    df = pd.DataFrame(rows)
    keep = [c for c in TRUE_COLS if c in df]
    out = df[[c for c in df if c.startswith("g_") and c not in ("g_beam_steel", "g_col_pt")] + keep].copy()
    return out.rename(columns={c: f"true_{c}" for c in keep})


def measure_fe_time(n: int = 150, seed: int = 11) -> float:
    """Mean wall time (s) of one cold OpenSees FE solve in a quiet single process."""
    from rcopt.fe import runner as fr

    sp = default_space()
    G = sp.random_genomes(n, np.random.default_rng(seed))
    fr._fe_cached.cache_clear()
    times = []
    for g in G:
        r = evaluate_genome(g, sp)
        if r.get("fe_cached", 1) == 0:
            times.append(r["fe_time_s"])
    fr._fe_cached.cache_clear()
    return float(np.mean(times))


def run_phase4(force: bool = False, n_jobs: int = 8) -> dict:
    t0 = time.time()
    summaries = run_all(force=force, n_jobs=n_jobs)
    runs = load_runs()
    pooled, rank1 = {}, {}
    for c in CONFIGS:
        pooled[c] = pooled_front(runs[c])
        rank1[c] = int((pooled_front.last_ranks == 1).sum())
        pooled_front.ranks_by_cfg = getattr(pooled_front, 'ranks_by_cfg', {})
        pooled_front.ranks_by_cfg[c] = pooled_front.last_ranks.copy()
    reeval = {c: reevaluate(pooled[c][0]) for c in CONFIGS}
    # truly feasible, non-dominated true fronts per config (true objectives)
    true_fronts: dict[str, np.ndarray] = {}
    true_all: dict[str, np.ndarray] = {}
    for c in CONFIGS:
        d = reeval[c]
        ok = (d["true_status"] == "OK") & (d["true_feasible"] == 1)
        F = d.loc[ok, ["true_cost", "true_carbon"]].to_numpy()
        true_all[c] = F
        true_fronts[c] = F[non_dominated(F)] if len(F) else F
    allF = np.vstack([pooled[c][1] for c in CONFIGS] + [f for f in true_fronts.values() if len(f)])
    norm = Normaliser(allF)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_cfg: dict = {}
    for c in CONFIGS:
        X, F = pooled[c]
        df = pd.DataFrame(X, columns=[f"g_{n}" for n in default_space().gene_names])
        df["pred_cost"], df["pred_carbon"] = F[:, 0], F[:, 1]
        df["pred_rank"] = pooled_front.ranks_by_cfg[c]
        df = pd.concat([df.reset_index(drop=True), reeval[c].drop(columns=[x for x in reeval[c] if x.startswith("g_")]
                                                                  ).reset_index(drop=True)], axis=1)
        name = "pareto_direct.parquet" if c == "direct" else f"pareto_surrogate_{c}.parquet"
        df.to_parquet(RESULTS / name, index=False)
        if c == "A":
            df.to_parquet(RESULTS / "pareto_surrogate.parquet", index=False)
        # convergence: mean HV (predicted/own objectives) vs evaluations, over seeds
        hv_curves = []
        for r in runs[c]:
            hv_curves.append([norm.hv(f) for f in r["fronts"]])
        ev = np.array(runs[c][0]["n_eval"])
        hv_arr = np.array(hv_curves)
        per_seed_final = hv_arr[:, -1]
        Ft = true_fronts[c]
        out_cfg[c] = {
            "seeds": len(runs[c]), "pop_size": runs[c][0]["pop_size"], "n_gen": runs[c][0]["n_gen"],
            "pooled_front_size": int(len(X)), "rank1_front_size": rank1[c], "pooled_front_truly_feasible": int(((df.true_status == "OK") & (df.true_feasible == 1)).sum()),
            "true_front_size": int(len(Ft)),
            "best_true_cost": float(true_all[c][:, 0].min()) if len(true_all[c]) else None,
            "best_true_carbon": float(true_all[c][:, 1].min()) if len(true_all[c]) else None,
            "n_truly_feasible_in_set": int(len(true_all[c])), "hv_final_per_seed": per_seed_final.tolist(),
            "hv_final_mean": float(per_seed_final.mean()), "hv_final_std": float(per_seed_final.std()),
            "hv_pooled_front_as_seen": norm.hv(F), "hv_pooled_front_true": norm.hv(Ft),
            "spacing_true_front": spacing(norm(Ft)) if len(Ft) else float("nan"),
            "cost_carbon_correlation_pooled": objective_correlation(F) if len(F) > 2 else float("nan"),
            "cost_range_true": [float(Ft[:, 0].min()), float(Ft[:, 0].max())] if len(Ft) else None,
            "carbon_range_true": [float(Ft[:, 1].min()), float(Ft[:, 1].max())] if len(Ft) else None,
            "convergence": {"n_eval": ev.tolist(), "hv_mean": hv_arr.mean(axis=0).tolist(), "hv_std": hv_arr.std(axis=0).tolist()},
            "run_summaries": [r["summary"] for r in runs[c]],
        }
    fe_time = measure_fe_time()
    meta = json.loads((ROOT / "data" / "processed" / "fe_dataset.meta.json").read_text())["runtime"]
    sm = json.loads((RESULTS / "surrogate_metrics.json").read_text())
    al = sm["active_learning"]["timing"]
    n_fe_data = meta["n_fe_solves"] + al["n_fe_solves"]
    datagen_serial_s = n_fe_data * fe_time
    train_s = sm["runtime_s"] - al["wall_s"]
    cmp_: dict = {"mean_fe_solve_time_s_single_process": fe_time, "norm": {"ideal": norm.ideal.tolist(), "nadir": norm.nadir.tolist()},
                  "data_generation": {"fe_solves": n_fe_data, "serial_equivalent_s": datagen_serial_s,
                                      "parallel_wall_s": meta["wall_s"] + al["wall_s"]},
                  "surrogate_training_s": train_s, "configs": {}}
    for c in CONFIGS:
        s = out_cfg[c]["run_summaries"]
        cmp_["configs"][c] = {
            "evaluations_requested_per_seed": float(np.mean([x["evaluations_requested"] for x in s])),
            "unique_evaluations_per_seed": float(np.mean([x["unique_evaluations"] for x in s])),
            "unique_fe_solves_per_seed": float(np.mean([x["unique_fe_solves"] for x in s])),
            "wall_s_per_seed": float(np.mean([x["wall_s"] for x in s])), "wall_s_total_seeds": float(np.sum([x["wall_s"] for x in s])),
            "hv_final_mean": out_cfg[c]["hv_final_mean"], "hv_pooled_front_true": out_cfg[c]["hv_pooled_front_true"],
        }
    direct_total = cmp_["configs"]["direct"]["wall_s_total_seeds"]
    for c in ("A", "B", "A_margin", "B_margin"):
        sur_total = cmp_["configs"][c]["wall_s_total_seeds"] + datagen_serial_s + train_s
        cmp_["configs"][c]["speedup_vs_direct_incl_datagen_and_training"] = direct_total / sur_total
        cmp_["configs"][c]["speedup_optimisation_only"] = direct_total / max(cmp_["configs"][c]["wall_s_total_seeds"], 1e-9)
        cmp_["configs"][c]["hv_ratio_true_vs_direct"] = out_cfg[c]["hv_pooled_front_true"] / max(out_cfg["direct"]["hv_pooled_front_true"], 1e-12)
    (RESULTS / "optimization_summary.json").write_text(json.dumps(out_cfg, indent=1, default=float), encoding="utf-8")
    (RESULTS / "compute_comparison.json").write_text(json.dumps(cmp_, indent=1, default=float), encoding="utf-8")
    cmp_["phase4_wall_s"] = time.time() - t0
    return {"optimization": out_cfg, "compute": cmp_, "summaries": summaries}
