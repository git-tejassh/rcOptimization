"""Embodied carbon (kgCO2e, A1-A4) of a design from quantities and ``config/carbon_factors.yaml`` (all provisional).

Concrete per m3 = cement content x cement factor + other constituents; A4 transport = mass x distance x factor.
Reinforcement = mass x factor (+ A4). Formwork carbon is excluded (flagged).
"""
from __future__ import annotations

from rcopt import config
from rcopt.cost_carbon.quantities import Quantities


def concrete_factor_kgco2e_m3(grade: str, overrides: dict | None = None) -> float:
    """A1-A3 factor of one m3 of concrete of ``grade`` (kgCO2e/m3)."""
    c = config.load_dict("carbon_factors")
    ov = overrides or {}
    cem = c["cement"][c["cement"]["default"]]["value"] * ov.get("cement_scale", 1.0)
    return c["cement_content_kg_m3"][grade]["value"] * cem + c["concrete_other_kgCO2e_m3"]["value"]


def carbon_kgco2e(q: Quantities, concrete: str, steel: str, overrides: dict | None = None) -> dict[str, float]:
    """Carbon breakdown: concrete, steel, transport A4 (concrete + steel), total."""
    c = config.load_dict("carbon_factors")
    ov = overrides or {}
    conc = q.concrete_m3 * concrete_factor_kgco2e_m3(concrete, ov)
    stl = q.steel_kg * c["steel"][steel]["value"] * ov.get("steel_scale", 1.0)
    tc, ts = c["transport_A4"]["concrete"], c["transport_A4"]["steel"]
    a4_conc = q.concrete_m3 * c["concrete_density_kg_m3"] / 1000.0 * tc["distance_km"] * tc["factor_kgCO2e_per_t_km"]
    a4_steel = q.steel_kg / 1000.0 * ts["distance_km"] * ts["factor_kgCO2e_per_t_km"]
    return {"concrete": conc, "steel": stl, "transport": a4_conc + a4_steel, "total": conc + stl + a4_conc + a4_steel}
