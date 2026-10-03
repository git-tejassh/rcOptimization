"""Ground-truth evaluation of designs and parallel batch data generation (project.md 8.2).

Every genome yields exactly one row, whatever happens: ``OK`` or one of the status codes
``GEOM_INFEASIBLE`` (pre-FE), ``FE_SINGULAR``, ``FE_ERROR``, ``CHECK_ERROR``, ``EQUILIBRIUM_FAIL``. Nothing is dropped.
The elastic FE response depends only on sizes + concrete grade, so FE results are cached per size key inside each
process; ``fe_time_s`` is the wall time of a real FE solve (0 and ``fe_cached = 1`` on a cache hit).
"""
from __future__ import annotations

import time
from functools import lru_cache

import numpy as np

from rcopt import config
from rcopt.codes import column as col_code
from rcopt.design.constraints import evaluate_from_demands, geometry_violation
from rcopt.design.geometric_feasibility import check_geometry
from rcopt.design.variables import Design, DesignSpace, default_space
from rcopt.fe.analysis import FEDemands, FEInput, analyze

STATUSES = ("OK", "GEOM_INFEASIBLE", "FE_SINGULAR", "FE_ERROR", "CHECK_ERROR", "EQUILIBRIUM_FAIL")
TRIPLE_FIELDS = ("Pu", "MD", "Mb", "l")


def demand_columns(n_bg: int, n_cg: int) -> list[str]:
    """Names of the flattened demand columns (the inputs/targets of Surrogate B)."""
    cols = []
    for g in range(n_bg):
        cols += [f"B{g}_Msag", f"B{g}_Mhog", f"B{g}_Vu"]
    for g in range(n_cg):
        cols += [f"C{g}_T{k}_{f}" for k in range(4) for f in TRIPLE_FIELDS]
    cols += [f"defl_L_B{g}" for g in range(n_bg)]
    return cols


def demands_to_row(d: FEDemands) -> dict[str, float]:
    row: dict[str, float] = {}
    for g in range(d.beam.shape[0]):
        row[f"B{g}_Msag"], row[f"B{g}_Mhog"], row[f"B{g}_Vu"] = (float(x) for x in d.beam[g])
    for g in range(d.col_triples.shape[0]):
        for k in range(4):
            for f, v in zip(TRIPLE_FIELDS, d.col_triples[g, k], strict=True):
                row[f"C{g}_T{k}_{f}"] = float(v)
    for g, v in enumerate(d.defl_over_L):
        row[f"defl_L_B{g}"] = float(v)
    return row


def row_to_demands(row, n_bg: int, n_cg: int) -> tuple[np.ndarray, list[np.ndarray], float]:
    """(beam_dem (n_bg,3), per-group (4,4) column triples, max defl/L) from a flattened row / mapping."""
    beam = np.array([[row[f"B{g}_Msag"], row[f"B{g}_Mhog"], row[f"B{g}_Vu"]] for g in range(n_bg)], dtype=float)
    cols = [np.array([[row[f"C{g}_T{k}_{f}"] for f in TRIPLE_FIELDS] for k in range(4)], dtype=float)
            for g in range(n_cg)]
    return beam, cols, float(max(row[f"defl_L_B{g}"] for g in range(n_bg)))


@lru_cache(maxsize=50_000)
def _fe_cached(key: tuple):
    fe_in = FEInput(*key)
    t0 = time.perf_counter()
    d = analyze(fe_in)
    return d, time.perf_counter() - t0


def fe_demands(design: Design) -> tuple[FEDemands, float, bool]:
    """FE demands for the design's sizes: (demands, solve time s, cache hit)."""
    key = FEInput.from_design(design).key()
    hit = _fe_cached.cache_info().hits
    d, t = _fe_cached(key)
    return d, t, _fe_cached.cache_info().hits > hit


def evaluate_genome(genome, space: DesignSpace | None = None) -> dict:
    """Ground-truth evaluation of one genome -> flat dict (see module docstring for statuses)."""
    space = space or default_space()
    solver = config.load_dict("solver")["checks"]
    design = space.decode(genome)
    row: dict = {f"g_{n}": int(v) for n, v in zip(space.gene_names, genome, strict=True)}
    row.update(status="OK", reason="", fe_time_s=0.0, fe_cached=0)
    row["geom_violation"] = geometry_violation(design)
    gr = check_geometry(design)
    if not gr.ok:
        row.update(status="GEOM_INFEASIBLE", reason=gr.code)
        return row
    try:
        dem, t, hit = fe_demands(design)
    except Exception as exc:  # OpenSees raises RuntimeError/ValueError on a singular system
        row.update(status="FE_ERROR", reason=f"{type(exc).__name__}: {exc}"[:200])
        return row
    row.update(fe_time_s=0.0 if hit else t, fe_cached=int(hit))
    row.update(demands_to_row(dem))
    row["defl_mm"] = dem.defl_mm
    row["equilibrium_err"] = dem.equilibrium_err
    if not dem.ok or not np.isfinite(dem.beam).all():
        row.update(status="FE_SINGULAR", reason="analysis did not converge / non-finite demands")
        return row
    if dem.equilibrium_err > config.load_dict("solver")["fe"]["equilibrium_tol"]:
        row.update(status="EQUILIBRIUM_FAIL", reason=f"reaction/load mismatch {dem.equilibrium_err:.2e}")
    try:
        ev = evaluate_from_demands(design, dem.beam, dem.col_all, dem.defl_max_over_L)
        triple_u = []
        for g, sec in enumerate(design.columns):
            u = 0.0
            for Pu, MD, Mb, l_mm in dem.col_triples[g]:
                u = max(u, col_code.check_column(sec, design.concrete, design.steel, Pu, MD, Mb, l_mm,
                                                 k_eff=solver["column_k_eff"],
                                                 emin_simultaneous=solver["emin_simultaneous"],
                                                 cap=solver["util_cap"],
                                                 max_slenderness=solver["max_slenderness_le_D"]).U)
            triple_u.append(u)
    except Exception as exc:
        row.update(status="CHECK_ERROR", reason=f"{type(exc).__name__}: {exc}"[:200])
        return row
    for g, v in enumerate(ev.U_flex_g):
        row[f"U_flex_B{g}"] = v
    for g, v in enumerate(ev.U_shear_g):
        row[f"U_shear_B{g}"] = v
    for g, v in enumerate(ev.U_col_g):
        row[f"U_col_C{g}"] = v
    for g, v in enumerate(triple_u):
        row[f"U_col_triple_C{g}"] = v
    for g, v in enumerate(ev.sv_mm):
        row[f"sv_B{g}"] = v
    q = ev.quantities
    row.update(
        U_flex_max=ev.U_flex, U_shear_max=ev.U_shear, U_col_max=ev.U_col, defl_ratio_max=ev.defl_ratio,
        U_col_triple_max=max(triple_u), g_beam_steel=ev.g_beam_steel, g_col_pt=ev.g_col_pt, cost=ev.cost,
        carbon=ev.carbon, concrete_m3=q.concrete_m3, steel_kg=q.steel_kg, formwork_m2=q.formwork_m2,
        feasible=int(ev.feasible and row["status"] == "OK"),
    )
    row["max_g"] = float(np.max(ev.g))
    return row


def evaluate_chunk(genomes: np.ndarray, ids: np.ndarray, strata: list[str]) -> list[dict]:
    """Worker entry point: evaluate a chunk (each worker process owns its OpenSees state and caches)."""
    space = default_space()
    out = []
    for gid, g, s in zip(ids, genomes, strata, strict=True):
        r = evaluate_genome(g, space)
        r["id"] = int(gid)
        r["sample_stratum"] = s
        out.append(r)
    return out


def default_n_jobs() -> int:
    import os
    cfg = config.load_dict("solver")["fe"]["n_jobs"]
    # OpenSees workers scale poorly past ~8 processes on this class of machine (measured: 1->51 s, 8->20 s, 15->25 s per 1200 designs)
    return max(1, min((os.cpu_count() or 2) - 1, 8)) if cfg == "auto" else int(cfg)
