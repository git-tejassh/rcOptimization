"""Pre-FE geometric / detailing feasibility of a decoded design (project.md 5.3).

A design that fails here is *not* analysed; it is stored with status ``GEOM_INFEASIBLE`` and the reason codes.
Code-bound limits (reinforcement percentages, capacities) are NOT geometric: they are soft constraints in
``rcopt.design.constraints``.
"""
from __future__ import annotations

from dataclasses import dataclass

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.design.variables import Design


@dataclass(frozen=True)
class GeomResult:
    ok: bool
    reasons: tuple[str, ...]

    @property
    def code(self) -> str:
        return ";".join(self.reasons)


def tie_dia_mm(bar_dia_mm: float, tie_dia_min_mm: float) -> float:
    """IS 456 cl. 26.5.3.2 (c): tie dia >= max(bar dia / 4, 6 mm); project minimum from config; even mm."""
    need = max(bar_dia_mm / 4.0, tie_dia_min_mm)
    return float(2 * int(-(-need // 2)))


def beam_layers(section, cfg: config.DesignSpaceCfg, top: bool) -> dt.BeamLayer | None:
    d = cfg.detailing
    dia, n = (section.top_dia_mm, section.top_n) if top else (section.bot_dia_mm, section.bot_n)
    return dt.beam_bar_layers(
        section.b_mm, n, dia, cfg.cover_mm.beam, cfg.beam.stirrup_dia_mm, d.aggregate_size_mm,
        d.min_clear_spacing_mm, d.min_clear_vertical_mm, cfg.beam.max_layers,
    )


def check_geometry(design: Design, geom: config.GeometryCfg | None = None,
                   cfg: config.DesignSpaceCfg | None = None) -> GeomResult:
    """Return all geometric infeasibility reasons (empty tuple => buildable)."""
    cfg = cfg or config.design_space()
    geom = geom or config.geometry()
    d = cfg.detailing
    reasons: list[str] = []

    for g, bs in enumerate(design.beams):
        for top in (False, True):
            lay = beam_layers(bs, cfg, top)
            if lay is None:
                reasons.append(f"B{g}_{'TOP' if top else 'BOT'}_NOFIT")
            elif bs.D_mm - lay.y_centroid_mm <= 0:
                reasons.append(f"B{g}_{'TOP' if top else 'BOT'}_NEG_D")

    for g, cs in enumerate(design.columns):
        if cs.D_mm < cs.b_mm:
            reasons.append(f"C{g}_D_LT_B")
        tie = tie_dia_mm(cs.dia_mm, cfg.column.tie_dia_min_mm)
        sb, sD = dt.column_clear_spacings_mm(cs.b_mm, cs.D_mm, cs.dia_mm, cs.n, cfg.cover_mm.column, tie)
        smin = dt.min_clear_spacing_mm(cs.dia_mm, d.aggregate_size_mm, d.min_clear_spacing_mm)
        if min(sb, sD) < smin:
            reasons.append(f"C{g}_SPACING_MIN")
        if max(sb, sD) > d.column_clear_spacing_max_mm:
            reasons.append(f"C{g}_SPACING_MAX")
        if 100.0 * cs.n * dt.bar_area_mm2(cs.dia_mm) / (cs.b_mm * cs.D_mm) > d.column_pt_abs_max_percent:
            reasons.append(f"C{g}_PT_GT_ABS_MAX")

    if d.beam_b_le_column_b:
        n_storeys = len(geom.storey_heights_m)
        col_of_storey = {s: g for g, grp in enumerate(geom.column_groups) for s in grp}
        for g, grp in enumerate(geom.beam_groups):
            cols = {col_of_storey[s] for lv in grp for s in (lv - 1, lv) if 0 <= s < n_storeys}
            if design.beams[g].b_mm > min(design.columns[c].b_mm for c in cols):
                reasons.append(f"B{g}_B_GT_COLUMN_B")
    return GeomResult(not reasons, tuple(reasons))
