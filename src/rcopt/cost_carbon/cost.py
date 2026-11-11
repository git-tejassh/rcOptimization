"""Construction cost of a design (INR) from quantities and ``config/cost_rates.yaml`` (all rates provisional)."""
from __future__ import annotations

from rcopt import config
from rcopt.cost_carbon import scenario
from rcopt.cost_carbon.quantities import Quantities


def _active(overrides: dict | None) -> dict:
    return overrides if overrides is not None else scenario.active()


def rates(overrides: dict | None = None) -> dict:
    """Flat rate table. ``overrides`` (default: the active scenario) may hold ``steel_cost_scale`` (+/-20 % study) and
    absolute price overrides by key (``concrete_M25``, ``steel_Fe500``, ``formwork_m2``; see ``cost_carbon.prices``)."""
    r = config.load_dict("cost_rates")
    ov = _active(overrides)
    return {
        "concrete": {g: ov.get(f"concrete_{g}", v["value"]) for g, v in r["concrete_per_m3"].items()},
        "steel": {g: ov.get(f"steel_{g}", v["value"]) * ov.get("steel_cost_scale", 1.0) for g, v in r["steel_per_kg"].items()},
        "formwork": ov.get("formwork_m2", r["formwork_per_m2"]["value"]),
    }


def cement_adjustment_per_m3(concrete: str, cement: str | None, overrides: dict | None = None) -> float:
    """INR per m3 of concrete for using ``cement`` instead of the baseline cement the concrete rates assume."""
    r = config.load_dict("cost_rates")["cement_price_per_kg"]
    if cement is None or cement == r["baseline"]:
        return 0.0
    ov = _active(overrides)
    price = lambda c: ov.get(f"cement_{c}", r[c]["value"])  # noqa: E731
    content = config.load_dict("carbon_factors")["cement_content_kg_m3"][concrete]["value"]
    return content * (price(cement) - price(r["baseline"]))


def cost_inr(q: Quantities, concrete: str, steel: str, overrides: dict | None = None,
             cement: str | None = None) -> dict[str, float]:
    """Cost breakdown (INR): concrete, steel, formwork, total. ``cement`` (OPC / PPC / PSC) adjusts the concrete cost."""
    r = rates(overrides)
    c = q.concrete_m3 * (r["concrete"][concrete] + cement_adjustment_per_m3(concrete, cement, overrides))
    s = q.steel_kg * r["steel"][steel]
    f = q.formwork_m2 * r["formwork"]
    return {"concrete": c, "steel": s, "formwork": f, "total": c + s + f}


def is_provisional() -> bool:
    r = config.load_dict("cost_rates")
    return any(v.get("status") == "provisional" for grp in ("concrete_per_m3", "steel_per_kg") for v in r[grp].values()) \
        or r["formwork_per_m2"].get("status") == "provisional"
