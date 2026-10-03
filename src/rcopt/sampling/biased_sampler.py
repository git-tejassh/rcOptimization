"""Feasibility-biased enrichment stratum (project.md 8.1).

Uniform sampling gives mostly undersized designs, so a second stratum keeps only candidates that pass cheap
analytic pre-checks (no FE): geometry (after repair), reinforcement percentages, and gross capacity versus a *crude*
demand estimate (hand-style tributary formulas, deliberately a bit lenient so the boundary region stays populated).
Every rejection is counted by reason for the sampling report.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

from rcopt import config
from rcopt.codes import beam as beam_code
from rcopt.codes import detailing as dt
from rcopt.codes import is456_tables as t
from rcopt.design.constraints import analytic_constraints
from rcopt.design.variables import Design, DesignSpace

LENIENCY = 0.6          # demand estimates are multiplied by this before comparing with capacity


def crude_demands(design: Design) -> dict:
    """Crude strength-level demands: beam hogging/sagging/shear per group, column Pu per group (kN, kN.m)."""
    lc, geom = config.loads(), config.geometry()
    L = max(max(geom.bays_x_m), max(geom.bays_z_m))
    w_dl_slab = lc.unit_weight_rc_kNm3 * lc.slab.thickness_mm / 1000 + lc.slab.finish_kNm2
    w_slab = (5.0 / 8.0) * (w_dl_slab + lc.live.floor_kNm2) * L        # kN/m, equivalent UDL of two triangles
    h = max(geom.storey_heights_m)
    out = {"beam": [], "col_Pu": []}
    for b in design.beams:
        sw = lc.unit_weight_rc_kNm3 * b.b_mm / 1000 * b.D_mm / 1000
        wall = lc.wall.perimeter_thickness_m * max(h - b.D_mm / 1000, 0) * lc.wall.unit_weight_kNm3
        w = 1.5 * (sw + wall + w_slab)
        out["beam"].append((w * L**2 / 24, w * L**2 / 12, w * L / 2))
    n_levels = len(geom.storey_heights_m) + 1
    trib = L * L
    for g, grp in enumerate(geom.column_groups):
        floors_above = n_levels - min(grp)
        beam_line = np.mean([1.5 * (lc.unit_weight_rc_kNm3 * b.b_mm / 1000 * b.D_mm / 1000 + 8.0) for b in design.beams])
        slab = 1.5 * (w_dl_slab + lc.live.floor_kNm2) * trib
        col_w = lc.unit_weight_rc_kNm3 * design.columns[g].b_mm / 1000 * design.columns[g].D_mm / 1000 * h * 1.5
        out["col_Pu"].append(floors_above * (slab + 2 * L * beam_line + col_w))
    return out


def precheck(design: Design) -> str | None:
    """Return the rejection reason code, or ``None`` if the design passes the cheap pre-checks."""
    cfg = config.design_space()
    g_beam, g_col = analytic_constraints(design)
    if g_beam > 0:
        return "BEAM_STEEL_LIMITS"
    if g_col > 0:
        return "COLUMN_PT_LIMITS"
    dem = crude_demands(design)
    for g, sec in enumerate(design.beams):
        msag, mhog, vu = dem["beam"][g]
        chk = beam_code.check_beam_group(sec, design.concrete, design.steel, LENIENCY * msag, LENIENCY * mhog,
                                         LENIENCY * vu, cfg)
        if chk.U_flex > 1.0:
            return "BEAM_FLEXURE_CRUDE"
        if chk.U_shear > 1.0:
            return "BEAM_SHEAR_CRUDE"
    for g, sec in enumerate(design.columns):
        fck, fy = t.fck_MPa(design.concrete), t.fy_MPa(design.steel)
        asc = sec.n * dt.bar_area_mm2(sec.dia_mm)
        puz = 0.45 * fck * (sec.b_mm * sec.D_mm - asc) + 0.75 * fy * asc
        if LENIENCY * dem["col_Pu"][g] * 1e3 > 0.8 * puz:
            return "COLUMN_AXIAL_CRUDE"
    return None


def biased_sample(space: DesignSpace, n: int, rng: np.random.Generator, max_tries: int = 400_000,
                  exclude: set | None = None) -> tuple[np.ndarray, Counter, int]:
    """Draw repaired uniform genomes until ``n`` unique ones pass ``precheck``.

    Returns (genomes, rejection counter, candidates drawn). Stops early (with fewer rows) after ``max_tries``.
    """
    seen = set(exclude or ())
    keep: list[np.ndarray] = []
    rej: Counter = Counter()
    drawn = 0
    while len(keep) < n and drawn < max_tries:
        batch = space.random_genomes(2000, rng)
        for raw in batch:
            drawn += 1
            g = space.repair(raw)
            key = tuple(g)
            if key in seen:
                rej["DUPLICATE"] += 1
                continue
            reason = precheck(space.decode(g, repair=False))
            if reason:
                rej[reason] += 1
                continue
            seen.add(key)
            keep.append(g)
            if len(keep) == n or drawn >= max_tries:
                break
    return (np.array(keep, dtype=int).reshape(-1, space.n_genes), rej, drawn)

