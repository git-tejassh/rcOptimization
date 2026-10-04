"""Construction cost of a design (INR) from quantities and ``config/cost_rates.yaml`` (all rates provisional)."""
from __future__ import annotations

from rcopt import config
from rcopt.cost_carbon import scenario
from rcopt.cost_carbon.quantities import Quantities


def rates(overrides: dict | None = None) -> dict:
    """Flat rate table; ``overrides`` (e.g. {'steel_cost_scale': 1.2}; default: the active scenario) supports the +/-20 % sensitivity study."""
    r = config.load_dict("cost_rates")
    ov = overrides if overrides is not None else scenario.active()
    return {
        "concrete": {g: v["value"] for g, v in r["concrete_per_m3"].items()},
        "steel": {g: v["value"] * ov.get("steel_cost_scale", 1.0) for g, v in r["steel_per_kg"].items()},
        "formwork": r["formwork_per_m2"]["value"],
    }


def cement_adjustment_per_m3(concrete: str, cement: str | None) -> float:
    """INR per m3 of concrete for using ``cement`` instead of the baseline cement the concrete rates assume."""
    r = config.load_dict("cost_rates")["cement_price_per_kg"]
    if cement is None or cement == r["baseline"]:
        return 0.0
    content = config.load_dict("carbon_factors")["cement_content_kg_m3"][concrete]["value"]
    return content * (r[cement]["value"] - r[r["baseline"]]["value"])


def cost_inr(q: Quantities, concrete: str, steel: str, overrides: dict | None = None,
             cement: str | None = None) -> dict[str, float]:
    """Cost breakdown (INR): concrete, steel, formwork, total. ``cement`` (OPC / PPC / PSC) adjusts the concrete cost."""
    r = rates(overrides)
    c = q.concrete_m3 * (r["concrete"][concrete] + cement_adjustment_per_m3(concrete, cement))
    s = q.steel_kg * r["steel"][steel]
    f = q.formwork_m2 * r["formwork"]
    return {"concrete": c, "steel": s, "formwork": f, "total": c + s + f}


def is_provisional() -> bool:
    r = config.load_dict("cost_rates")
    return any(v.get("status") == "provisional" for grp in ("concrete_per_m3", "steel_per_kg") for v in r[grp].values()) \
        or r["formwork_per_m2"].get("status") == "provisional"
