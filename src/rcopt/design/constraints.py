"""Constraint evaluation: demands + reinforcement -> utilisations, constraint vector g, cost and carbon.

``evaluate_from_demands`` is the single place where IS 456 checks, quantities, cost and carbon are combined; it is
used for ground truth (FE demands), for Surrogate B (predicted demands) and by the verifier / API.
Constraint vector (pymoo convention, feasible when every entry <= 0)::

    g = [defl_ratio - 1, U_flex - 1, U_shear - 1, U_col - 1, g_beam_steel, g_col_pt, geom_violation]
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from rcopt import config
from rcopt.codes import beam as beam_code
from rcopt.codes import column as col_code
from rcopt.codes import detailing as dt
from rcopt.cost_carbon.carbon import carbon_kgco2e
from rcopt.cost_carbon.cost import cost_inr
from rcopt.cost_carbon.quantities import Quantities, compute_quantities
from rcopt.design.geometric_feasibility import beam_layers, check_geometry, tie_dia_mm
from rcopt.design.variables import Design

G_NAMES = ("defl", "flex", "shear", "col", "beam_steel", "col_pt", "geom")


def geometry_violation(design: Design, geom: config.GeometryCfg | None = None,
                       cfg: config.DesignSpaceCfg | None = None) -> float:
    """Continuous (>= 0) measure of how badly the design violates the geometric rules (0 = buildable)."""
    cfg = cfg or config.design_space()
    geom = geom or config.geometry()
    d = cfg.detailing
    v = 0.0
    for bs in design.beams:
        for top in (False, True):
            lay = beam_layers(bs, cfg, top)
            if lay is None:
                n = bs.top_n if top else bs.bot_n
                dia = bs.top_dia_mm if top else bs.bot_dia_mm
                s = dt.min_clear_spacing_mm(dia, d.aggregate_size_mm, d.min_clear_spacing_mm)
                n1 = max(int((bs.b_mm - 2 * (cfg.cover_mm.beam + cfg.beam.stirrup_dia_mm) + s) // (dia + s)), 1)
                v += max(n - n1 * cfg.beam.max_layers, 1) / n
    for cs in design.columns:
        v += max(cs.b_mm - cs.D_mm, 0) / cs.b_mm
        tie = tie_dia_mm(cs.dia_mm, cfg.column.tie_dia_min_mm)
        sb, sD = dt.column_clear_spacings_mm(cs.b_mm, cs.D_mm, cs.dia_mm, cs.n, cfg.cover_mm.column, tie)
        smin = dt.min_clear_spacing_mm(cs.dia_mm, d.aggregate_size_mm, d.min_clear_spacing_mm)
        v += max(smin - min(sb, sD), 0.0) / smin + max(max(sb, sD) - d.column_clear_spacing_max_mm, 0.0) / \
            d.column_clear_spacing_max_mm
        pt = 100.0 * cs.n * dt.bar_area_mm2(cs.dia_mm) / (cs.b_mm * cs.D_mm)
        v += max(pt - d.column_pt_abs_max_percent, 0.0) / d.column_pt_abs_max_percent
    if d.beam_b_le_column_b:
        n_storeys = len(geom.storey_heights_m)
        col_of_storey = {s: g for g, grp in enumerate(geom.column_groups) for s in grp}
        for g, grp in enumerate(geom.beam_groups):
            cols = {col_of_storey[s] for lv in grp for s in (lv - 1, lv) if 0 <= s < n_storeys}
            cb = min(design.columns[c].b_mm for c in cols)
            v += max(design.beams[g].b_mm - cb, 0) / design.beams[g].b_mm
    return v


@dataclass
class Evaluation:
    """Complete evaluation of one design against a set of demands."""

    status: str
    geom_reasons: str
    geom_violation: float
    U_flex_g: tuple[float, ...] = ()
    U_shear_g: tuple[float, ...] = ()
    U_col_g: tuple[float, ...] = ()
    U_flex: float = 0.0
    U_shear: float = 0.0
    U_col: float = 0.0
    defl_ratio: float = 0.0
    g_beam_steel: float = 0.0
    g_col_pt: float = 0.0
    sv_mm: tuple[float, ...] = ()
    cost: float = 0.0
    carbon: float = 0.0
    cost_parts: dict = field(default_factory=dict)
    carbon_parts: dict = field(default_factory=dict)
    quantities: Quantities | None = None
    beam_checks: list = field(default_factory=list)

    @property
    def g(self) -> np.ndarray:
        return np.array([self.defl_ratio - 1.0, self.U_flex - 1.0, self.U_shear - 1.0, self.U_col - 1.0,
                         self.g_beam_steel, self.g_col_pt, self.geom_violation])

    @property
    def feasible(self) -> bool:
        return bool(np.all(self.g <= 1e-9)) and self.status == "OK"


def evaluate_from_demands(design: Design, beam_dem: np.ndarray, col_sets: list[np.ndarray],
                          defl_over_L: float, cap: float | None = None) -> Evaluation:
    """IS 456 checks + quantities + cost + carbon.

    ``beam_dem``: (n_bg, 3) Msag_kNm, Mhog_kNm, Vu_kN (strength level); ``col_sets``: per column group an
    (m, 4) array of (Pu_kN, MD_kNm, Mb_kNm, l_mm) triples to check (all columns or the critical ones);
    ``defl_over_L``: max service delta/L (dimensionless).
    """
    cfg = config.design_space()
    solver = config.load_dict("solver")["checks"]
    cap = cap or solver["util_cap"]
    gr = check_geometry(design)
    gv = geometry_violation(design)
    if not gr.ok:
        return Evaluation("GEOM_INFEASIBLE", gr.code, gv)

    bchecks = [beam_code.check_beam_group(sec, design.concrete, design.steel, *beam_dem[g], cfg=cfg, cap=cap)
               for g, sec in enumerate(design.beams)]
    ucol_g, gpt = [], -np.inf
    for g, sec in enumerate(design.columns):
        u = 0.0
        for Pu, MD, Mb, l_mm in col_sets[g]:
            ck = col_code.check_column(sec, design.concrete, design.steel, Pu, MD, Mb, l_mm, cfg,
                                       k_eff=solver["column_k_eff"], emin_simultaneous=solver["emin_simultaneous"],
                                       cap=cap, max_slenderness=solver["max_slenderness_le_D"])
            u = max(u, ck.U)
            gpt = max(gpt, ck.g_pt)
        ucol_g.append(u)
    sv = tuple(b.sv_mm for b in bchecks)
    q = compute_quantities(design, sv)
    cp = cost_inr(q, design.concrete, design.steel)
    cb = carbon_kgco2e(q, design.concrete, design.steel)
    return Evaluation(
        "OK", "", 0.0,
        U_flex_g=tuple(b.U_flex for b in bchecks), U_shear_g=tuple(b.U_shear for b in bchecks),
        U_col_g=tuple(ucol_g), U_flex=max(b.U_flex for b in bchecks), U_shear=max(b.U_shear for b in bchecks),
        U_col=max(ucol_g), defl_ratio=defl_over_L * solver["deflection_limit_ratio"],
        g_beam_steel=max(b.g_steel for b in bchecks), g_col_pt=float(gpt), sv_mm=sv,
        cost=cp["total"], carbon=cb["total"], cost_parts=cp, carbon_parts=cb, quantities=q, beam_checks=bchecks,
    )


def analytic_objectives(design: Design, sv_mm: tuple[float, ...]) -> tuple[float, float, Quantities]:
    """(cost, carbon, quantities) for given stirrup spacings (used by the surrogate-driven optimizer)."""
    q = compute_quantities(design, sv_mm)
    return cost_inr(q, design.concrete, design.steel)["total"], carbon_kgco2e(
        q, design.concrete, design.steel)["total"], q


def analytic_constraints(design: Design) -> tuple[float, float]:
    """Reinforcement-only constraints that need no FE: (g_beam_steel, g_col_pt)."""
    cfg = config.design_space()
    fy = float(config.load_dict("is456_tables")["steel"]["fy_MPa"][design.steel])
    g_b = -np.inf
    for sec in design.beams:
        bot, top = beam_layers(sec, cfg, False), beam_layers(sec, cfg, True)
        if bot is None or top is None:
            continue
        b, D = float(sec.b_mm), float(sec.D_mm)
        a_b, a_t = sec.bot_n * dt.bar_area_mm2(sec.bot_dia_mm), sec.top_n * dt.bar_area_mm2(sec.top_dia_mm)
        amax = cfg.detailing.beam_pt_max_percent / 100.0 * b * D
        g_b = max(g_b, 0.85 * b * (D - bot.y_centroid_mm) / fy / a_b - 1, 0.85 * b * (D - top.y_centroid_mm) / fy / a_t - 1,
                  a_b / amax - 1, a_t / amax - 1)
    g_c = -np.inf
    for cs in design.columns:
        pt = 100.0 * cs.n * dt.bar_area_mm2(cs.dia_mm) / (cs.b_mm * cs.D_mm)
        g_c = max(g_c, cfg.detailing.column_pt_min_percent / pt - 1, pt / cfg.detailing.column_pt_max_percent - 1)
    return float(g_b), float(g_c)
