"""Phase 2: FE batch data generation. Every design-matrix row becomes a dataset row (status flag, never dropped)."""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.variables import DesignSpace, default_space
from rcopt.fe.runner import default_n_jobs, evaluate_chunk

DATASET_PATH = ROOT / "data" / "processed" / "fe_dataset.parquet"
META_PATH = ROOT / "data" / "processed" / "fe_dataset.meta.json"
FAILURE_TABLE = ROOT / "data" / "results" / "failure_table.csv"
RUNTIME_PATH = ROOT / "data" / "results" / "fe_runtime.json"
RESULT_COLS = ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max")


def genome_columns(space: DesignSpace) -> list[str]:
    return [f"g_{n}" for n in space.gene_names]


def run_rows(genomes: np.ndarray, ids: np.ndarray, strata: list[str], n_jobs: int | None = None,
             chunk: int = 100) -> tuple[pd.DataFrame, dict]:
    """Evaluate genomes in parallel (each worker process owns its OpenSees state). Returns (rows, timing)."""
    n_jobs = n_jobs or default_n_jobs()
    t0 = time.perf_counter()
    parts = [(genomes[i:i + chunk], ids[i:i + chunk], strata[i:i + chunk]) for i in range(0, len(genomes), chunk)]
    out = Parallel(n_jobs=n_jobs, backend="loky")(delayed(evaluate_chunk)(*p) for p in parts)
    rows = [r for chunk_rows in out for r in chunk_rows]
    wall = time.perf_counter() - t0
    df = pd.DataFrame(rows).sort_values("id").reset_index(drop=True)
    fe = df.loc[(df.get("fe_cached", 0) == 0) & (df["fe_time_s"] > 0), "fe_time_s"]
    timing = {"wall_s": wall, "n_jobs": n_jobs, "n_rows": len(df), "n_fe_solves": int(len(fe)),
              "mean_fe_time_s": float(fe.mean()) if len(fe) else float("nan"),
              "median_fe_time_s": float(fe.median()) if len(fe) else float("nan"),
              "wall_s_per_row_parallel": wall / max(len(df), 1)}
    return df, timing


def failure_table(df: pd.DataFrame) -> pd.DataFrame:
    """Counts by status and reason code (every non-OK row is listed; OK rows are split feasible / infeasible)."""
    ok = df[df.status == "OK"]
    rows = [{"status": "OK", "reason": "feasible (all IS 456 + deflection checks pass)", "count": int(ok.feasible.sum())},
            {"status": "OK", "reason": "infeasible (>= 1 check fails, valid data)", "count": int((ok.feasible == 0).sum())}]
    bad = df[df.status != "OK"]
    for (st, reason), g in bad.groupby(["status", "reason"]):
        rows.append({"status": st, "reason": reason, "count": len(g)})
    if bad.empty:
        rows.append({"status": "FAILED_RUNS", "reason": "none", "count": 0})
    return pd.DataFrame(rows)


def run_phase2(force: bool = False, n_jobs: int | None = None) -> dict:
    """Run FE + checks for the design matrix (skipped if inputs unchanged). Returns the runtime record."""
    space = default_space()
    matrix = pd.read_parquet(ROOT / "data" / "processed" / "design_matrix.parquet")
    chash = config.config_hash()
    inputs = {"config_hash": chash, "n_matrix": len(matrix)}
    if DATASET_PATH.exists() and META_PATH.exists() and not force:
        meta = json.loads(META_PATH.read_text())
        if meta.get("inputs") == inputs:
            return meta["runtime"]
    gcols = genome_columns(space)
    df, timing = run_rows(matrix[gcols].to_numpy(), matrix["id"].to_numpy(), matrix["sample_stratum"].tolist(), n_jobs)
    extra = matrix[["id", "raw_geom_infeasible", "repaired"]]
    df = df.merge(extra, on="id", how="left")
    df.to_parquet(DATASET_PATH, index=False)
    ft = failure_table(df)
    FAILURE_TABLE.parent.mkdir(parents=True, exist_ok=True)
    ft.to_csv(FAILURE_TABLE, index=False)
    ok = df[df.status == "OK"]
    band = config.load_dict("surrogate")["boundary_band"]
    near = np.zeros(len(ok), dtype=bool)
    for c in RESULT_COLS:
        near |= ((ok[c] >= band[0]) & (ok[c] <= band[1])).to_numpy()
    timing.update({
        "status_counts": df.status.value_counts().to_dict(), "feasible": int(ok.feasible.sum()),
        "feasible_fraction_of_ok": float(ok.feasible.mean()), "near_boundary_rows": int(near.sum()),
        "dataset_rows": len(df), "config_hash": chash,
    })
    META_PATH.write_text(json.dumps({"inputs": inputs, "runtime": timing}, indent=1), encoding="utf-8")
    (ROOT / "data" / "results").mkdir(parents=True, exist_ok=True)
    RUNTIME_PATH.write_text(json.dumps(timing, indent=1), encoding="utf-8")
    return timing
