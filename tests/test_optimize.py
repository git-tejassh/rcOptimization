"""P4 building blocks: metrics, memoised evaluators, a tiny direct-FE NSGA-II run, scenarios."""
import numpy as np
import pytest

from rcopt.cost_carbon import scenario as sc
from rcopt.cost_carbon.carbon import carbon_kgco2e
from rcopt.cost_carbon.cost import cost_inr
from rcopt.cost_carbon.quantities import compute_quantities
from rcopt.design.variables import default_space
from rcopt.optimize import run as opt_run
from rcopt.optimize.metrics import Normaliser, non_dominated, spacing
from rcopt.optimize.problem import DirectFEEvaluator, GenomeRepair


def test_non_dominated_and_hypervolume_known_value():
    F = np.array([[0.0, 1.0], [1.0, 0.0], [0.6, 0.6], [1.0, 1.0]])
    assert sorted(non_dominated(F).tolist()) == [0, 1, 2]
    n = Normaliser(np.array([[0.0, 0.0], [1.0, 1.0]]))
    # two corner points + reference 1.05: union area = 2 * (1.05 * 0.05) - 0.05**2
    assert n.hv(np.array([[0.0, 1.0], [1.0, 0.0]])) == pytest.approx(2 * 1.05 * 0.05 - 0.05**2)
    assert n.hv(np.array([[0.0, 0.0]])) == pytest.approx(1.05 * 1.05)
    assert n.hv(np.empty((0, 2))) == 0.0


def test_spacing_zero_for_even_front():
    x = np.linspace(0, 1, 6)
    assert spacing(np.column_stack([x, 1 - x])) == pytest.approx(0.0, abs=1e-12)


def test_genome_repair_operator_is_integer_and_buildable():
    sp = default_space()
    X = sp.random_genomes(20, np.random.default_rng(0)).astype(float) + 0.4
    out = GenomeRepair(sp)._do(None, X)
    assert np.all(out == np.rint(out)) and np.all(out >= 0) and np.all(out <= sp.n_options - 1)


def test_direct_evaluator_memoises_and_counts_fe_solves():
    sp = default_space()
    ev = DirectFEEvaluator(sp)
    G = sp.repair(sp.random_genomes(1, np.random.default_rng(1))[0])[None, :]
    F1, G1 = ev(np.vstack([G, G, G]))
    assert ev.n_requested == 3 and ev.n_unique == 1
    assert np.allclose(F1[0], F1[2]) and F1.shape == (3, 2) and G1.shape == (3, 7)
    F2, _ = ev(G)
    assert ev.n_requested == 4 and ev.n_unique == 1 and np.allclose(F2[0], F1[0])


def test_tiny_direct_nsga2_run(tmp_path, monkeypatch):
    monkeypatch.setattr(opt_run, "OUT_DIR", tmp_path)
    s = opt_run.run_one("direct", 1, 12, 3, force=True)
    assert s["evaluations_requested"] >= 12 and s["unique_fe_solves"] >= 1 and s["wall_s"] > 0
    again = opt_run.run_one("direct", 1, 12, 3)         # cached
    assert again == s


def test_scenarios_scale_cost_and_carbon():
    sp = default_space()
    d = sp.decode(sp.repair(sp.random_genomes(1, np.random.default_rng(2))[0]))
    q = compute_quantities(d, (150.0, 150.0))
    base_c, base_k = cost_inr(q, d.concrete, d.steel), carbon_kgco2e(q, d.concrete, d.steel)
    with sc.scenario(steel_cost_scale=1.2, cement_carbon_scale=0.8, steel_carbon_scale=1.2):
        c, k = cost_inr(q, d.concrete, d.steel), carbon_kgco2e(q, d.concrete, d.steel)
    assert c["steel"] == pytest.approx(1.2 * base_c["steel"]) and c["concrete"] == base_c["concrete"]
    assert k["steel"] == pytest.approx(1.2 * base_k["steel"]) and k["concrete"] < base_k["concrete"]
    assert sc.active() == {}                                # context restored
