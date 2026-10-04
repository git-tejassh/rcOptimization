"""Embodied carbon (kgCO2e, A1-A4) of a design from quantities and ``config/carbon_factors.yaml`` (all provisional).

Concrete per m3 = cement content x cement factor + other constituents; A4 transport = mass x distance x factor.
Reinforcement = mass x factor (+ A4). Formwork carbon is excluded (flagged).
"""
from __future__ import annotations

from rcopt import config
from rcopt.cost_carbon import scenario
from rcopt.cost_carbon.quantities import Quantities


def concrete_factor_kgco2e_m3(grade: str, overrides: dict | None = None, cement: str | None = None) -> float:
    """A1-A3 factor of one m3 of concrete of ``grade`` (kgCO2e/m3)."""
    c = config.load_dict("carbon_factors")
    ov = overrides if overrides is not None else scenario.active()
    cem = c["cement"][cement or c["cement"]["default"]]["value"] * ov.get("cement_carbon_scale", 1.0)
    return c["cement_content_kg_m3"][grade]["value"] * cem + c["concrete_other_kgCO2e_m3"]["value"]


def carbon_kgco2e(q: Quantities, concrete: str, steel: str, overrides: dict | None = None,
                  cement: str | None = None) -> dict[str, float]:
    """Carbon breakdown: concrete, steel, transport A4 (concrete + steel), total."""
    c = config.load_dict("carbon_factors")
    ov = overrides if overrides is not None else scenario.active()
    conc = q.concrete_m3 * concrete_factor_kgco2e_m3(concrete, ov, cement)
    stl = q.steel_kg * c["steel"][steel]["value"] * ov.get("steel_carbon_scale", 1.0)
    tc, ts = c["transport_A4"]["concrete"], c["transport_A4"]["steel"]
    a4_conc = q.concrete_m3 * c["concrete_density_kg_m3"] / 1000.0 * tc["distance_km"] * tc["factor_kgCO2e_per_t_km"]
    a4_steel = q.steel_kg / 1000.0 * ts["distance_km"] * ts["factor_kgCO2e_per_t_km"]
    return {"concrete": conc, "steel": stl, "transport": a4_conc + a4_steel, "total": conc + stl + a4_conc + a4_steel}


def recompute_dataset_objectives(df, space=None):
    """(cost, carbon) arrays for dataset rows from their stored quantities under the CURRENT config (no FE needed)."""
    import numpy as np

    from rcopt.cost_carbon.cost import cost_inr
    from rcopt.design.variables import default_space

    space = space or default_space()
    grades = space.options[space.gene_index("fck")]
    steels = space.options[space.gene_index("fy")]
    cost, carb = np.empty(len(df)), np.empty(len(df))
    z = 0.0
    cements = space.options[space.gene_index("cement")]
    for i, (cm, sk, fw, gi, si, ci) in enumerate(
            zip(df.concrete_m3, df.steel_kg, df.formwork_m2, df.g_fck, df.g_fy, df.g_cement, strict=True)):
        q = Quantities(cm, sk, fw, z, z, z, z, z, z, z, z, z, z)
        cost[i] = cost_inr(q, grades[int(gi)], steels[int(si)], cement=cements[int(ci)])["total"]
        carb[i] = carbon_kgco2e(q, grades[int(gi)], steels[int(si)], cement=cements[int(ci)])["total"]
    return cost, carb
