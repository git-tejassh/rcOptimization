"""API smoke tests (project.md 11.4). Surrogate endpoints need models/ (phase 3) and are skipped without them."""
import numpy as np
import pytest
from api.main import app
from fastapi.testclient import TestClient

from rcopt.config import ROOT
from rcopt.design.variables import default_space

client = TestClient(app)
HAVE_MODELS = (ROOT / "models" / "surrogate_A.joblib").exists() and (ROOT / "models" / "surrogate_B.joblib").exists()
GENOME = [int(x) for x in default_space().repair(default_space().random_genomes(1, np.random.default_rng(3))[0])]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["provisional_data"] is True


def test_validation_errors():
    assert client.post("/evaluate/fe", json={"genome": [0, 1]}).status_code == 422
    assert client.post("/evaluate/fe", json={"genome": [999] * 23}).status_code == 422
    assert client.get("/pareto/nonsense").status_code == 404


def test_evaluate_fe_and_cost_carbon():
    r = client.post("/evaluate/fe", json={"genome": GENOME})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "OK" and "utilisation" in d and d["cost_inr"]["total"] > 0
    r2 = client.post("/evaluate/cost-carbon", json={"genome": GENOME})
    assert r2.status_code == 200 and r2.json()["provisional"] is True
    assert r2.json()["carbon_kgco2e"]["total"] == pytest.approx(d["carbon_kgco2e"]["total"])


@pytest.mark.skipif(not HAVE_MODELS, reason="surrogates not trained")
def test_evaluate_surrogate_close_to_ground_truth_cost():
    r = client.post("/evaluate/surrogate", json={"genome": GENOME})
    assert r.status_code == 200
    j = r.json()
    truth = client.post("/evaluate/fe", json={"genome": GENOME}).json()
    assert j["B"]["cost"] == pytest.approx(truth["cost_inr"]["total"], rel=0.05)
    assert set(j) >= {"repaired_genome", "A", "B"}


@pytest.mark.skipif(not (ROOT / "data" / "results" / "verification.json").exists(), reason="phase 5 not run")
def test_results_endpoints():
    assert client.get("/verification").status_code == 200
    assert client.get("/design-space").status_code == 200


def test_review_staad_sample():
    text = (ROOT / "legacy" / "staad_model" / "G+3 RCC FINAL.STD").read_text(encoding="latin-1")
    r = client.post("/review/staad", json={"text": text, "concrete": "M30", "steel": "Fe500", "cement": "PPC"})
    assert r.status_code == 200
    j = r.json()
    assert j["verdict"] == "PASS" and j["frame"]["n_members"] == 255
    assert j["quantities"]["concrete_m3"] == pytest.approx(147.86, rel=1e-3)
    assert all(b["pass"] for b in j["beams"]) and all(c["pass"] for c in j["columns"])


def test_review_rejects_bad_input_and_flags_undersized():
    assert client.post("/review/staad", json={"text": "hello"}).status_code == 422
    text = (ROOT / "legacy" / "staad_model" / "G+3 RCC FINAL.STD").read_text(encoding="latin-1")
    small = text.replace("PRIS YD 0.45 ZD 0.45", "PRIS YD 0.23 ZD 0.23")
    r = client.post("/review/staad", json={"text": small})
    assert r.status_code == 200 and r.json()["verdict"] == "FAIL" and r.json()["failures"]
