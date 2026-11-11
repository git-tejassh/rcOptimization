"""Editable prices: CSV round trip, validation, effect on cost, cache fingerprints, and a tiny price-driven optimisation."""
from __future__ import annotations

import json

import pytest
from api.main import app
from fastapi.testclient import TestClient

from rcopt import config
from rcopt.cost_carbon import prices, scenario
from rcopt.cost_carbon.cost import cost_inr
from rcopt.cost_carbon.quantities import Quantities


def _q() -> Quantities:
    return Quantities(**{f: 10.0 for f in Quantities.__dataclass_fields__})


def test_template_round_trip_and_defaults_are_placeholders():
    assert prices.from_csv_text(prices.to_csv_text()) == prices.defaults()
    assert all(i["status"] == "provisional" for i in prices.items())
    keys = [i["key"] for i in prices.items()]
    assert {"concrete_M25", "steel_Fe500", "formwork_m2", "cement_PSC"} <= set(keys)


def test_csv_validation_messages():
    for bad in ("steel_Fe999,5", "steel_Fe500,abc", "steel_Fe500,-3", "steel_Fe500,0", "item,value\n"):
        with pytest.raises(ValueError):
            prices.from_csv_text(bad)
    assert prices.from_csv_text("# note\nitem,value\nsteel_Fe500, 81.5\n") == {"steel_Fe500": 81.5}


def test_price_override_changes_cost_exactly_and_is_scoped():
    q = _q()
    base = cost_inr(q, "M30", "Fe500", cement="PSC")
    with scenario.scenario(steel_Fe500=100.0, concrete_M30=7000.0, formwork_m2=800.0):
        new = cost_inr(q, "M30", "Fe500", cement="PSC")
    assert new["steel"] == pytest.approx(q.steel_kg * 100.0)
    assert new["formwork"] == pytest.approx(q.formwork_m2 * 800.0)
    assert new["concrete"] - base["concrete"] == pytest.approx(q.concrete_m3 * 1000.0)
    assert cost_inr(q, "M30", "Fe500", cement="PSC") == base                  # scenario restored


def test_cement_price_premium_enters_only_non_baseline_cements():
    q = _q()
    with scenario.scenario(cement_PSC=12.0):
        psc = cost_inr(q, "M30", "Fe500", cement="PSC")["concrete"]
        ppc = cost_inr(q, "M30", "Fe500", cement="PPC")["concrete"]
    with scenario.scenario(cement_PSC=prices.defaults()["cement_PSC"]):
        psc0 = cost_inr(q, "M30", "Fe500", cement="PSC")["concrete"]
    assert psc - psc0 == pytest.approx(q.concrete_m3 * 390 * (12.0 - prices.defaults()["cement_PSC"]))
    assert ppc == cost_inr(q, "M30", "Fe500", cement="PPC")["concrete"]


def test_config_hash_ignores_metadata_and_separates_prices_from_structure():
    assert config.config_hash(config.STRUCTURE) == config.config_hash(config.STRUCTURE)
    assert "cost_rates" not in config.STRUCTURE and "carbon_factors" not in config.STRUCTURE   # editing prices must not retrain
    assert config._strip_meta({"a": {"value": 1, "status": "provisional", "source": "x"}}) == {"a": {"value": 1}}


def test_is456_table_values_match_the_printed_code():
    t = config.load_dict("is456_tables")
    assert t["status"] == "sourced"
    assert t["table20"] == {"M20": 2.8, "M25": 3.1, "M30": 3.5, "M35": 3.7, "M40": 4.0}
    assert t["steel"]["xu_max_over_d"] == {"Fe415": 0.48, "Fe500": 0.46}
    i = t["table19"]["pt"].index(1.0)
    assert [t["table19"][g][i] for g in ("M20", "M25", "M30", "M35", "M40")] == [0.62, 0.64, 0.66, 0.67, 0.68]
    ex = config.design_space().exposure_requirements["moderate"]
    assert (ex["min_grade"], ex["min_cement_kg_m3"], ex["max_water_cement"], ex["cover_beam_mm"]) == ("M25", 300, 0.50, 30)


def test_tiny_price_driven_optimisation_with_direct_fe(monkeypatch):
    from rcopt.optimize import custom

    monkeypatch.setitem(custom.MODES, "tiny", {"pop": 20, "gen": 3})
    res = custom.reoptimize({"cement_PSC": 12.0, "steel_Fe500": 60.0}, mode="tiny", engine="direct", target=10)
    assert res["changed"] == {"cement_PSC": 12.0, "steel_Fe500": 60.0}
    assert res["n_candidates"] > 0 and res["provisional"] is True
    assert all(d["feasible_true"] and d["true_cost"] > 0 for d in res["designs"])
    json.dumps(res)                                                          # serialisable
    assert scenario.active() == {}                                           # no price leaks into the process


def test_api_prices_endpoints_validate_input():
    c = TestClient(app)
    r = c.get("/prices/items")
    assert r.status_code == 200 and len(r.json()["items"]) == 10 and "item,value" in r.json()["csv_template"]
    assert c.post("/optimize/prices", json={"prices": {"steel_Fe999": 5}}).status_code == 422
    assert c.post("/optimize/prices", json={"prices": {"steel_Fe500": 70}, "csv": "item,value\nsteel_Fe500,70"}).status_code == 422
    assert c.post("/optimize/prices", json={"mode": "forever"}).status_code == 422
    assert c.get("/optimize/jobs/doesnotexist").status_code == 404
