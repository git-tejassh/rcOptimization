"""FE sanity (project.md 7.4): closed-form beams, end-to-end sign conventions, equilibrium, cache invariance."""
import numpy as np
import pytest

from rcopt.design.variables import default_space
from rcopt.fe import analysis as an
from rcopt.fe.opensees_model import ElementProps, rect_props, solve_cases
from rcopt.fe.runner import evaluate_genome
from rcopt.geometry.frame_spec import FrameSpec, Member

L, W = 5.0, 20.0


def _q(shape):
    return np.full((1, an.N_GRID), W) if shape == "udl" else None


def test_fixed_end_udl():
    va, vb, ma, mb = an.fixed_end(_q("udl"), np.array([L]))
    assert va[0] == pytest.approx(W * L / 2, rel=1e-3) and vb[0] == pytest.approx(W * L / 2, rel=1e-3)
    assert ma[0] == pytest.approx(W * L**2 / 12, rel=1e-3) and mb[0] == pytest.approx(W * L**2 / 12, rel=1e-3)


def test_fixed_end_triangle_yield_line():
    # triangular load, peak q0 = w L/2 at mid-span (square panel of side L): FEM = 5 q0 L^2 / 96, total = q0 L / 2
    w = 4.75
    x = np.array([[L * s for s in an.XI]])
    q = an.slab_q(x[0], L, L, w)[None, :]
    va, vb, ma, mb = an.fixed_end(q, np.array([L]))
    q0 = w * L / 2
    assert va[0] + vb[0] == pytest.approx(q0 * L / 2, rel=1e-4)
    assert ma[0] == pytest.approx(5 * q0 * L**2 / 96, rel=2e-3)
    assert ma[0] == pytest.approx(mb[0], rel=1e-9)


def test_trapezoid_total_load():
    x = np.linspace(0, 8.0, an.N_GRID)
    q = an.slab_q(x, 8.0, 5.0, 4.0)                    # long side of a 5 x 8 panel
    assert np.trapezoid(q, x) == pytest.approx(4.0 * (8.0 - 5.0 / 2) * 5.0 / 2, rel=1e-4)


def test_diagrams_and_deflection_fixed_fixed_and_simply_supported():
    EI = 3e7 * 0.3 * 0.45**3 / 12
    Lv = np.array([L])
    q = _q("udl")
    # fixed-fixed: Fa = wL/2, ma (CCW on element) = +wL^2/12
    x, Ms, Vs = an.beam_diagrams(Lv, q, np.array([W * L / 2]), np.array([W * L**2 / 12]))
    assert Ms[0, 0] == pytest.approx(-W * L**2 / 12, rel=1e-4)
    assert Ms[0, 100] == pytest.approx(W * L**2 / 24, rel=1e-4)
    assert Vs[0, 0] == pytest.approx(W * L / 2, rel=1e-6) and Vs[0, -1] == pytest.approx(-W * L / 2, rel=1e-4)
    v, dev = an.beam_chord_deflection(x, Ms, np.array([EI]), np.zeros(1), np.zeros(1), np.zeros(1))
    assert -dev.min() == pytest.approx(W * L**4 / (384 * EI), rel=2e-3)
    assert abs(v[0, -1]) < 1e-3 * W * L**4 / (384 * EI)               # ends are consistent (v(L) = 0)
    # simply supported: Ms(x) = w x (L - x) / 2, left-end rotation clockwise = -wL^3/(24 EI)
    x, Ms, _ = an.beam_diagrams(Lv, q, np.array([W * L / 2]), np.zeros(1))
    assert Ms[0, 100] == pytest.approx(W * L**2 / 8, rel=1e-4)
    v, dev = an.beam_chord_deflection(x, Ms, np.array([EI]), np.zeros(1), np.zeros(1),
                                      np.array([-W * L**3 / (24 * EI)]))
    assert -dev.min() == pytest.approx(5 * W * L**4 / (384 * EI), rel=2e-3)
    assert abs(v[0, -1]) < 5e-3 * 5 * W * L**4 / (384 * EI)


def _beam_between_rigid_columns():
    fs = FrameSpec([0.0, L], [0.0], [0.0], 1.0, [])
    fs.nodes = {1: (0, 0, 0), 2: (L, 0, 0), 3: (0, -1.0, 0), 4: (L, -1.0, 0)}
    fs.members = [Member(1, "bx", 1, 2, 0, 0, L, False, 0, 0), Member(2, "stub", 3, 1, 0, 0, 1.0, False, 0, 0),
                  Member(3, "stub", 4, 2, 0, 0, 1.0, False, 0, 0)]
    return fs


def test_opensees_end_to_end_fixed_fixed_beam():
    """UDL via equivalent nodal loads on a beam between (almost) rigid stubs: end moments wL^2/12, mid wL^2/24."""
    fs = _beam_between_rigid_columns()
    E = 3e7
    beam = rect_props(0.3, 0.45, E, 0.17, 1.0)
    rigid = ElementProps(A=1e3, Iy=1e5, Iz=1e5, J=1e5, E=E, G=E / 2.34)
    q = _q("udl")
    va, vb, ma, mb = an.fixed_end(q, np.array([L]))
    h = np.array([0.0, 0.0, 1.0])                                   # e x u for e = +X
    loads = {n: np.zeros(6) for n in fs.nodes}
    loads[1][1], loads[2][1] = -va[0], -vb[0]
    loads[1][3:6] -= ma[0] * h
    loads[2][3:6] += mb[0] * h
    sol = solve_cases(fs, {1: beam, 2: rigid, 3: rigid}, {"DL": loads})["DL"]
    e = sol.ef[1].copy()
    e[1] += va[0]
    e[7] += vb[0]
    e[3:6] += ma[0] * h
    e[9:12] -= mb[0] * h
    x, Ms, Vs = an.beam_diagrams(np.array([L]), q, np.array([e[1]]), np.array([e[3:6] @ h]))
    assert Ms[0, 0] == pytest.approx(-W * L**2 / 12, rel=2e-3)
    assert Ms[0, -1] == pytest.approx(-W * L**2 / 12, rel=2e-3)
    assert Ms[0, 100] == pytest.approx(W * L**2 / 24, rel=3e-3)
    assert sol.reaction_sum[1] == pytest.approx(W * L, rel=1e-6)         # equilibrium
    assert e[1] + e[7] == pytest.approx(W * L, rel=1e-6)


def test_opensees_end_to_end_shear_deformation_flag_runs():
    fs = _beam_between_rigid_columns()
    p = rect_props(0.3, 0.45, 3e7, 0.17, 1.0)
    loads = {n: np.zeros(6) for n in fs.nodes}
    loads[2][1] = -10.0
    a = solve_cases(fs, {1: p, 2: p, 3: p}, {"c": loads})["c"].disp[2][1]
    b = solve_cases(fs, {1: p, 2: p, 3: p}, {"c": loads}, shear_deformation=True)["c"].disp[2][1]
    assert b < a < 0 and abs(b - a) / abs(a) < 0.1                   # shear deformation adds flexibility


def test_frame_equilibrium_and_beam_statics():
    d = an.analyze(an.FEInput(((300, 450), (300, 450)), ((450, 450), (450, 450)), 30.0))
    assert d.ok and d.equilibrium_err < 1e-9 and d.beam_equil_err < 1e-6


def test_dead_load_total_matches_independent_hand_total_in_benchmark_mode():
    """Hand total of the STAAD model's dead load = 17,580 kN (docs/BENCHMARK.md)."""
    d = an.analyze(an.FEInput(((300, 450),) * 2, ((450, 450),) * 2, 30.0), st=an.FESettings.benchmark(),
                   keep_raw=True)
    assert -sum(f[1] for f in d.raw["nodal"]["DL"].values()) == pytest.approx(17580.9, abs=0.5)
    assert -sum(f[1] for f in d.raw["nodal"]["LL"].values()) == pytest.approx(2850.0, abs=0.01)


def test_symmetry_of_a_symmetric_frame():
    d = an.analyze(an.FEInput(((300, 450), (300, 450)), ((450, 450), (450, 450)), 30.0),
                   st=an.FESettings.design(), keep_raw=True)
    # design mode has no wall torque -> reactions symmetric about the plan centre
    fs = an.default_frame()
    r = d.raw["sols"]["DL"].reactions
    for iz in range(fs.nz):
        for ix in range(fs.nx):
            a = r[fs.base_node(ix, iz)][1]
            b = r[fs.base_node(fs.nx - 1 - ix, fs.nz - 1 - iz)][1]
            assert a == pytest.approx(b, rel=1e-6)


def _genome(sp, **over):
    base = dict(B0_b=2, B0_D=3, B0_bd=1, B0_bn=2, B0_td=1, B0_tn=2, B1_b=2, B1_D=3, B1_bd=1, B1_bn=2, B1_td=1,
                B1_tn=2, C0_b=5, C0_D=5, C0_dia=2, C0_n=2, C1_b=5, C1_D=5, C1_dia=2, C1_n=2, fck=2, fy=1, cement=1)
    base.update(over)
    return np.array([base[n] for n in sp.gene_names])


def test_fe_demands_do_not_depend_on_reinforcement_or_steel_grade():
    sp = default_space()
    r1 = evaluate_genome(_genome(sp), sp)
    r2 = evaluate_genome(_genome(sp, B0_bn=4, B1_tn=3, C0_n=3, fy=0), sp)
    for k in ("B0_Msag", "B0_Mhog", "B1_Vu", "T1_1_0_Pu", "defl_L_B0", "defl_mm"):
        assert r1[k] == pytest.approx(r2[k], rel=1e-12)
    assert r1["U_flex_max"] != r2["U_flex_max"]


def test_bigger_members_reduce_utilisation_and_raise_cost():
    sp = default_space()
    small = evaluate_genome(_genome(sp, C0_b=3, C0_D=3, C1_b=3, C1_D=3), sp)
    big = evaluate_genome(_genome(sp, C0_b=6, C0_D=6, C1_b=6, C1_D=6, C0_n=4, C1_n=4), sp)
    assert big["U_col_max"] < small["U_col_max"] and big["cost"] > small["cost"]


def test_status_and_row_contract():
    sp = default_space()
    row = evaluate_genome(_genome(sp), sp)
    assert row["status"] == "OK" and row["fe_time_s"] >= 0
    for k in ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max", "cost", "carbon", "feasible",
              "B0_Msag", "T4_2_1_MD", "concrete_m3", "steel_kg"):
        assert k in row


def test_repair_makes_random_genomes_buildable():
    sp = default_space()
    from rcopt.design.geometric_feasibility import check_geometry
    rng = np.random.default_rng(5)
    raw_bad = 0
    for g in sp.random_genomes(300, rng):
        raw_bad += not check_geometry(sp.decode(g, repair=False)).ok
        rep = sp.repair(g)
        assert check_geometry(sp.decode(rep, repair=False)).ok
        assert np.array_equal(sp.repair(rep), rep)                 # idempotent
    assert raw_bad > 200                                           # raw uniform draws are mostly unbuildable
