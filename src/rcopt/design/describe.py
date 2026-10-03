"""Human-readable, JSON-serialisable description of a design with its ground-truth evaluation (UI drawer / API)."""
from __future__ import annotations

import numpy as np

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.design.constraints import evaluate_from_demands
from rcopt.design.variables import DesignSpace, default_space
from rcopt.fe.runner import fe_demands


def _f(x):
    return None if x is None else float(x)


def describe_genome(genome, space: DesignSpace | None = None) -> dict:
    """Sections, reinforcement, grades, quantities, cost/carbon breakdown and true utilisations of one genome."""
    space = space or default_space()
    design = space.decode(genome)
    out: dict = {
        "genome": [int(x) for x in genome],
        "concrete": design.concrete, "steel": design.steel,
        "beams": [{"group": g, "b_mm": b.b_mm, "D_mm": b.D_mm, "bottom": f"{b.bot_n}-{b.bot_dia_mm} mm",
                   "top": f"{b.top_n}-{b.top_dia_mm} mm", "stirrups": f"{config.design_space().beam.stirrup_legs}-L "
                   f"{config.design_space().beam.stirrup_dia_mm} mm"} for g, b in enumerate(design.beams)],
        "columns": [{"group": g, "b_mm": c.b_mm, "D_mm": c.D_mm, "bars": f"{c.n}-{c.dia_mm} mm",
                     "pt_percent": 100.0 * c.n * dt.bar_area_mm2(c.dia_mm) / (c.b_mm * c.D_mm)}
                    for g, c in enumerate(design.columns)],
    }
    dem, _, _ = fe_demands(design)
    ev = evaluate_from_demands(design, dem.beam, dem.col_all, dem.defl_max_over_L)
    out["status"] = ev.status
    if ev.status != "OK":
        out["geometry_reasons"] = ev.geom_reasons
        return out
    q = ev.quantities
    out.update({
        "quantities": {"concrete_m3": q.concrete_m3, "steel_kg": q.steel_kg, "formwork_m2": q.formwork_m2,
                       "beam_concrete_m3": q.beam_concrete_m3, "column_concrete_m3": q.column_concrete_m3,
                       "beam_steel_kg": q.beam_steel_kg, "column_steel_kg": q.column_steel_kg},
        "cost_inr": {k: float(v) for k, v in ev.cost_parts.items()},
        "carbon_kgco2e": {k: float(v) for k, v in ev.carbon_parts.items()},
        "utilisation": {"flexure_by_beam_group": [float(x) for x in ev.U_flex_g], "shear_by_beam_group": [float(x) for x in ev.U_shear_g],
                        "column_by_group": [float(x) for x in ev.U_col_g], "U_flex_max": float(ev.U_flex),
                        "U_shear_max": float(ev.U_shear), "U_col_max": float(ev.U_col), "deflection_ratio": float(ev.defl_ratio),
                        "deflection_mm": float(dem.defl_mm)},
        "stirrup_spacing_mm": [float(x) for x in ev.sv_mm],
        "demands": {"beam_Msag_Mhog_Vu": np.round(dem.beam, 2).tolist()},
        "feasible": bool(ev.feasible),
        "violations": {n: float(v) for n, v in zip(("defl", "flex", "shear", "col", "beam_steel", "col_pt", "geom"), ev.g, strict=True)
                       if v > 1e-9},
    })
    return out
