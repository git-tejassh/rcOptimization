"""Material quantities of a design: concrete (m3), reinforcement (kg), formwork (m2) - project.md 9.1.

Rules (config/quantities.yaml, docs/ASSUMPTIONS.md): beams run clear between column faces (columns take the full
member height incl. the joint, so the joint is counted once); slab concrete/steel excluded; longitudinal bars get
a lap/anchorage allowance; stirrups at the *designed* spacing over the whole span (conservative); column ties at
pitch min(b, 16 dia, 300) without intermediate cross-ties (flagged).

Members are aggregated by (group, direction, framing column group) once, so a call is a handful of arithmetic ops.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.design.geometric_feasibility import tie_dia_mm
from rcopt.design.variables import Design
from rcopt.geometry.frame_spec import FrameSpec, build_frame


@dataclass(frozen=True)
class Quantities:
    concrete_m3: float
    steel_kg: float
    formwork_m2: float
    beam_concrete_m3: float
    column_concrete_m3: float
    beam_steel_kg: float
    column_steel_kg: float
    beam_long_kg: float
    beam_stirrup_kg: float
    column_long_kg: float
    column_tie_kg: float
    beam_formwork_m2: float
    column_formwork_m2: float


def _aggregates(fs: FrameSpec):
    """(beam aggregates, column aggregates, D axis), memoised on the FrameSpec instance."""
    if hasattr(fs, "_qty_agg"):
        return fs._qty_agg
    beams: dict[tuple, list[float]] = defaultdict(lambda: [0, 0.0])
    cols: dict[int, list[float]] = defaultdict(lambda: [0, 0.0])
    for m in fs.members:
        if m.kind in ("bx", "bz"):
            a = beams[(m.group, m.kind, fs.col_group_of_storey[max(m.level - 1, 0)])]
        else:
            a = cols[m.group]
        a[0] += 1
        a[1] += m.length_m
    fs._qty_agg = (dict(beams), dict(cols), fs.column_D_axis)
    return fs._qty_agg


def _hook_mm(dia: float, q: dict) -> float:
    return 2.0 * max(q["hook_dia_multiple"] * dia, q["hook_min_mm"])


@lru_cache(maxsize=1)
def _default_frame() -> FrameSpec:
    return build_frame()


def compute_quantities(design: Design, beam_sv_mm: tuple[float, ...], fs: FrameSpec | None = None) -> Quantities:
    """Quantities for ``design``; ``beam_sv_mm`` = adopted stirrup spacing per beam group (from the beam check)."""
    fs = fs or _default_frame()
    beams, cols, D_axis = _aggregates(fs)
    q = config.load_dict("quantities")
    cfg = config.design_space()
    k_kg = config.load_dict("carbon_factors")["steel_density_kg_m3"] * 1e-6    # kg per (mm2 x m)
    st_dia = cfg.beam.stirrup_dia_mm
    cov_b, cov_c = cfg.cover_mm.beam, cfg.cover_mm.column
    slab = q["slab_thickness_for_formwork_mm"] if q["beam_side_formwork_net_of_slab"] else 0.0

    bc = bf = bl_kg = bs_kg = 0.0
    for (g, kind, cg), (n, sumL) in beams.items():
        s, col = design.beams[g], design.columns[cg]
        along_x = kind == "bx"
        col_dim = (col.D_mm if D_axis == "x" else col.b_mm) if along_x else (col.b_mm if D_axis == "x" else col.D_mm)
        sumLc = max(sumL - n * col_dim / 1000.0, 0.1 * n)
        bc += s.b_mm / 1000.0 * s.D_mm / 1000.0 * sumLc
        a_bot, a_top = s.bot_n * dt.bar_area_mm2(s.bot_dia_mm), s.top_n * dt.bar_area_mm2(s.top_dia_mm)
        bl_kg += (a_bot * (sumL + n * q["beam_lap_dia_multiple"] * s.bot_dia_mm / 1000.0)
                  + a_top * (sumL + n * q["beam_lap_dia_multiple"] * s.top_dia_mm / 1000.0)) * k_kg
        sv = max(beam_sv_mm[g], cfg.beam.stirrup_spacing_min_mm)
        n_st = sumLc * 1000.0 / sv + n
        per = 2.0 * ((s.b_mm - 2 * cov_b) + (s.D_mm - 2 * cov_b)) + _hook_mm(st_dia, q)
        bs_kg += n_st * per / 1000.0 * dt.bar_area_mm2(st_dia) * k_kg
        bf += (s.b_mm + 2.0 * max(s.D_mm - slab, 0.0)) / 1000.0 * sumLc

    cc = cf = cl_kg = ct_kg = 0.0
    for g, (n, sumH) in cols.items():
        s = design.columns[g]
        cc += s.b_mm / 1000.0 * s.D_mm / 1000.0 * sumH
        cf += 2.0 * (s.b_mm + s.D_mm) / 1000.0 * sumH
        a = s.n * dt.bar_area_mm2(s.dia_mm)
        cl_kg += a * (sumH + n * q["column_lap_dia_multiple"] * s.dia_mm / 1000.0) * k_kg
        tie = tie_dia_mm(s.dia_mm, cfg.column.tie_dia_min_mm)
        pitch = min(s.b_mm, 16.0 * s.dia_mm, q["column_tie_pitch_max_mm"])
        n_t = sumH * 1000.0 / pitch + n          # continuous count (floor(h/pitch) + 1 within +/- 1 tie per member)
        per = 2.0 * ((s.b_mm - 2 * cov_c) + (s.D_mm - 2 * cov_c)) + _hook_mm(tie, q)
        ct_kg += n_t * per / 1000.0 * dt.bar_area_mm2(tie) * k_kg
    return Quantities(
        concrete_m3=bc + cc, steel_kg=bl_kg + bs_kg + cl_kg + ct_kg, formwork_m2=bf + cf, beam_concrete_m3=bc,
        column_concrete_m3=cc, beam_steel_kg=bl_kg + bs_kg, column_steel_kg=cl_kg + ct_kg, beam_long_kg=bl_kg,
        beam_stirrup_kg=bs_kg, column_long_kg=cl_kg, column_tie_kg=ct_kg, beam_formwork_m2=bf,
        column_formwork_m2=cf,
    )

