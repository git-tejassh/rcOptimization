"""Genome repair: snap a genome to the nearest *buildable* discrete design (decision D-012).

Rules (each maps an infeasible choice to an IS-standard option; nothing is ever interpolated):

1. column groups: ``(b, D) -> (min, max)`` so that D >= b;
2. column bars ``(dia, count)``: if the face spacing rules fail for that size, pick the feasible
   ``(dia, count)`` pair closest in option-index space (L1), ties to the smaller steel area;
3. beam width: clamp to the largest option <= the narrowest column width it frames into;
4. beam bars: if more than ``max_layers`` layers would be needed, reduce the count until the bars fit.

``repair_genome`` is idempotent and leaves every already-feasible genome unchanged.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.design.geometric_feasibility import tie_dia_mm
from rcopt.design.variables import DesignSpace


@lru_cache(maxsize=None)
def _col_feasible(b: int, D: int, dia: int, n: int) -> bool:
    cfg = config.design_space()
    d = cfg.detailing
    tie = tie_dia_mm(dia, cfg.column.tie_dia_min_mm)
    sb, sD = dt.column_clear_spacings_mm(b, D, dia, n, cfg.cover_mm.column, tie)
    smin = dt.min_clear_spacing_mm(dia, d.aggregate_size_mm, d.min_clear_spacing_mm)
    return min(sb, sD) >= smin and max(sb, sD) <= d.column_clear_spacing_max_mm


@lru_cache(maxsize=None)
def _beam_fits(b: int, n: int, dia: int) -> bool:
    cfg = config.design_space()
    d = cfg.detailing
    return dt.beam_bar_layers(b, n, dia, cfg.cover_mm.beam, cfg.beam.stirrup_dia_mm, d.aggregate_size_mm,
                              d.min_clear_spacing_mm, d.min_clear_vertical_mm, cfg.beam.max_layers) is not None


def repair_genome(space: DesignSpace, genome) -> np.ndarray:
    """Return the repaired genome (new array of indices)."""
    g = np.array([int(x) for x in genome], dtype=int)
    idx = space.gene_index
    cs, bs = space.cfg.column, space.cfg.beam

    for c in range(space.n_cg):
        ib, iD = idx(f"C{c}_b"), idx(f"C{c}_D")
        lo, hi = sorted((g[ib], g[iD]))
        g[ib], g[iD] = lo, hi                        # option lists for b and D are identical by construction
        b, D = cs.b_mm[g[ib]], cs.D_mm[g[iD]]
        idia, in_ = idx(f"C{c}_dia"), idx(f"C{c}_n")
        if not _col_feasible(b, D, cs.bar_dia_mm[g[idia]], cs.bar_count[g[in_]]):
            best = None
            for kd, dia in enumerate(cs.bar_dia_mm):
                for kn, n in enumerate(cs.bar_count):
                    if _col_feasible(b, D, dia, n):
                        key = (abs(kd - g[idia]) + abs(kn - g[in_]), dia * dia * n)
                        if best is None or key < best[0]:
                            best = (key, kd, kn)
            if best is not None:
                g[idia], g[in_] = best[1], best[2]

    col_of_storey = {s: gi for gi, grp in enumerate(space.geom.column_groups) for s in grp}
    n_storeys = len(space.geom.storey_heights_m)
    for bgi, grp in enumerate(space.geom.beam_groups):
        cols = {col_of_storey[s] for lv in grp for s in (lv - 1, lv) if 0 <= s < n_storeys}
        if space.cfg.detailing.beam_b_le_column_b:
            limit = min(cs.b_mm[g[idx(f"C{c}_b")]] for c in cols)
            ib = idx(f"B{bgi}_b")
            while bs.b_mm[g[ib]] > limit and g[ib] > 0:
                g[ib] -= 1
        b = bs.b_mm[g[idx(f"B{bgi}_b")]]
        for dia_gene, n_gene, dias in ((f"B{bgi}_bd", f"B{bgi}_bn", bs.bottom_bar_dia_mm),
                                       (f"B{bgi}_td", f"B{bgi}_tn", bs.top_bar_dia_mm)):
            while g[idx(n_gene)] > 0 and not _beam_fits(b, bs.bar_count[g[idx(n_gene)]], dias[g[idx(dia_gene)]]):
                g[idx(n_gene)] -= 1
    return g
