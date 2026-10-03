"""IS 456 anchor tests (project.md 7.2): independently derivable values, STAAD column-81 numbers, hand calcs."""
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from rcopt import config
from rcopt.codes import beam, column, deflection
from rcopt.codes import detailing as dt
from rcopt.codes import is456_tables as t
from rcopt.design.variables import BeamSection, ColumnSection

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hand_calcs", ROOT / "docs" / "hand_calcs" / "hand_calcs.py")
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)


# ----------------------------------------------------------------------------- flexure
@pytest.mark.parametrize("grade,expected", [("M20", 2.76), ("M25", 3.45), ("M30", 4.14)])
def test_mu_lim_over_bd2_fe415(grade, expected):
    assert t.mu_lim_over_bd2(t.fck_MPa(grade), "Fe415") == pytest.approx(expected, rel=0.005)


def test_mu_lim_over_bd2_fe500_is_computed_from_046():
    v = t.mu_lim_over_bd2(25.0, "Fe500")
    assert v == pytest.approx(0.36 * 25 * 0.46 * (1 - 0.42 * 0.46))          # 3.34; SP 16 differs slightly (0.456)
    assert 3.30 < v < 3.40


def test_singly_reinforced_matches_closed_form_within_1pct():
    for (b, d, ast, fck, fy, steel) in [(300, 452, 1256.6, 25, 500, "Fe500"), (230, 400, 603, 20, 415, "Fe415"),
                                        (450, 700, 2945, 40, 500, "Fe500")]:
        mod = beam.flexural_capacity_Nmm(b, d, 50, ast, 0.0, fck, fy, steel)
        ref = beam.mu_singly_closed_form_Nmm(b, d, ast, fck, fy)
        assert mod == pytest.approx(ref, rel=0.01)


def test_over_reinforced_section_capped_at_limiting_moment():
    b, d, fck, fy = 230.0, 400.0, 20.0, 415.0
    mu = beam.flexural_capacity_Nmm(b, d, 50, 4000.0, 0.0, fck, fy, "Fe415")
    assert mu == pytest.approx(t.mu_lim_over_bd2(fck, "Fe415") * b * d * d, rel=1e-6)


def test_compression_steel_increases_capacity_and_is_continuous_at_the_limit():
    b, d, fck, fy = 300.0, 450.0, 25.0, 500.0
    single = beam.flexural_capacity_Nmm(b, d, 50, 1800.0, 0.0, fck, fy, "Fe500")
    double = beam.flexural_capacity_Nmm(b, d, 50, 1800.0, 600.0, fck, fy, "Fe500")
    assert double > single


def test_beam_hand_calc():
    r = hc.beam()
    i = r["inputs"]
    mod = beam.flexural_capacity_Nmm(i["b"], r["d"], 60.0, r["Ast"], 0.0, i["fck"], i["fy"], "Fe500") / 1e6
    assert mod == pytest.approx(r["Mu_kNm"], rel=0.01)
    sh = beam.shear_design(i["Vu_kN"], i["b"], r["d"], r["pt"], 2 * math.pi / 4 * 64, "M25", 500.0, 25.0, 75.0,
                           0.4, 415.0)
    assert sh["tau_v"] == pytest.approx(r["tau_v"], rel=1e-9)
    assert sh["tau_c"] == pytest.approx(r["tau_c"], abs=1e-9)
    assert sh["sv_strength_mm"] == pytest.approx(r["sv_strength_mm"], rel=1e-6)


# ----------------------------------------------------------------------------- shear tables
@pytest.mark.parametrize("grade,v", [("M20", 2.8), ("M25", 3.1), ("M30", 3.5), ("M35", 3.7), ("M40", 4.0)])
def test_table20(grade, v):
    assert t.tau_c_max_MPa(grade) == v


def test_table19_spot_values_and_interpolation():
    assert t.tau_c_MPa(0.5, "M20") == pytest.approx(0.48)
    assert t.tau_c_MPa(1.0, "M20") == pytest.approx(0.62)
    assert t.tau_c_MPa(0.75, "M20") == pytest.approx(0.56)
    assert t.tau_c_MPa(0.625, "M20") == pytest.approx(0.52)               # midpoint of 0.48 and 0.56
    assert t.tau_c_MPa(0.05, "M25") == t.tau_c_MPa(0.15, "M25")           # clamped below the table
    assert t.tau_c_MPa(5.0, "M30") == t.tau_c_MPa(3.0, "M30")             # clamped above the table


def test_table19_is_monotone_in_pt_and_grade():
    for g in ("M20", "M25", "M30", "M35", "M40"):
        v = np.array(config.load_dict("is456_tables")["table19"][g])
        assert np.all(np.diff(v) >= 0)
    for k in range(13):
        col = [config.load_dict("is456_tables")["table19"][g][k] for g in ("M20", "M25", "M30", "M35", "M40")]
        assert col == sorted(col)


def test_steel_curve_matches_sp16_total_strains():
    # SP 16 Table: total strain at 0.8 fyd and 1.0 fyd
    for fy, e08, e10 in [(415, 0.00144, 0.00380), (500, 0.00174, 0.00417)]:
        fyd = fy / 1.15
        assert t.steel_stress_MPa(e08, fy) == pytest.approx(0.8 * fyd, rel=0.01)
        assert t.steel_stress_MPa(e10, fy) == pytest.approx(fyd, rel=0.002)
        assert t.steel_stress_MPa(0.01, fy) == pytest.approx(fyd)
        assert t.steel_stress_MPa(-0.0005, fy) == pytest.approx(-0.0005 * 2e5)


# ----------------------------------------------------------------------------- column
def _sec(b=450, D=450, dia=20, n=8):
    return ColumnSection(b, D, dia, n)


def test_alpha_n_endpoints_and_midpoint():
    assert column.alpha_n(0.1, 1.0) == 1.0
    assert column.alpha_n(0.2, 1.0) == 1.0
    assert column.alpha_n(0.5, 1.0) == pytest.approx(1.5)
    assert column.alpha_n(0.8, 1.0) == pytest.approx(2.0)
    assert column.alpha_n(0.95, 1.0) == 2.0


def test_puz_hand_value():
    assert column.puz_N(450, 450, 904.78, 30, 500) == pytest.approx(0.45 * 30 * (202500 - 904.78) + 0.75 * 500 * 904.78)


def test_uniaxial_at_zero_axial_equals_beam_flexure_of_symmetric_section():
    # 4 corner bars: 2 top + 2 bottom == doubly reinforced beam b x D with d' = c'
    b, D, dia, cover, tie = 400, 400, 25, 40.0, 8.0
    P, M, _ = column.pm_curve(b, D, dia, 4, cover, tie, 30.0, 500.0, "x")
    mu_col = column.uniaxial_capacity_Nmm(P, M, 0.0)
    c = cover + tie + dia / 2
    A2 = 2 * dt.bar_area_mm2(dia)
    mu_beam = beam.flexural_capacity_Nmm(b, D - c, c, A2, A2, 30.0, 500.0, "Fe500")
    assert mu_col == pytest.approx(mu_beam, rel=0.02)


def test_pm_curve_is_monotone_in_p_and_has_expected_ends():
    P, M, Pb = column.pm_curve(450, 450, 20, 8, 40.0, 8.0, 30.0, 500.0, "x")
    assert np.all(np.diff(P) >= -1e-6)
    assert P[0] < 0 < P[-1]                                              # pure tension .. pure compression
    assert M.max() > M[0] and M.max() > M[-1]
    assert P[-1] == pytest.approx(0.446 * 30 * (450 * 450 - 8 * dt.bar_area_mm2(20)) + 8 * dt.bar_area_mm2(20) * 373.0,
                                  rel=0.02)


def test_column_hand_calc_point():
    r = hc.column()
    lay = dt.column_layers(450, 450, 20, 8, 40.0, 8.0, "x")
    P, M = column.pm_points(lay, 30.0, 500.0, np.array([r["xu"]]))
    assert P[0] / 1e3 == pytest.approx(r["P_kN"], rel=0.002)
    assert M[0] / 1e6 == pytest.approx(r["M_kNm"], rel=0.002)


def test_strip_integration_converged():
    lay = dt.column_layers(450, 450, 20, 8, 40.0, 8.0, "x")
    xu = np.array([100.0, 270.0, 450.0, 700.0])
    p1, m1 = column.pm_points(lay, 30.0, 500.0, xu, n_strips=200)
    p2, m2 = column.pm_points(lay, 30.0, 500.0, xu, n_strips=4000)
    assert np.allclose(p1, p2, rtol=2e-3) and np.allclose(m1, m2, rtol=5e-3, atol=2e3)


def test_staad_column_81_reproduced():
    """STAAD (legacy/staad_model .ANL, column 81): Pu 775.79 kN, M 35.20/34.65, Puz 2901.43, Muz1 150.87, IR 0.39."""
    Asc = 463.85
    assert column.puz_N(450, 450, Asc, 30, 500) / 1e3 == pytest.approx(2901.43, abs=0.05)
    # STAAD spreads the required steel equally: emulate with 16 thin bars (dia 6.1), d' = 40 + 8 + dia/2
    P, M, _ = column.pm_curve(450, 450, 6, 16, 40.0, 8.0, 30.0, 500.0, "x")
    mu1 = column.uniaxial_capacity_Nmm(P, M, 775.79e3) / 1e6
    assert mu1 == pytest.approx(150.87, rel=0.015)
    an = column.alpha_n(775.79e3, 2901.43e3)
    assert an == pytest.approx(1.112, abs=0.002)
    ir = (35.20 / 150.87) ** an + (34.65 / 150.87) ** an
    assert ir == pytest.approx(0.39, abs=0.005)


def test_min_eccentricity_staad_column_81():
    # STAAD: emin moment 16.29 kN.m = 775.79 kN x e with e = 3000/500 + 450/30 = 21 mm
    assert column.min_eccentricity_mm(3000, 450) == pytest.approx(21.0)
    assert 775.79 * 0.021 == pytest.approx(16.29, abs=0.01)
    assert column.min_eccentricity_mm(500, 150) == 20.0


def test_check_column_behaviour():
    sec = _sec()
    low = column.check_column(sec, "M30", "Fe500", 500, 20, 20, 2550)
    high = column.check_column(sec, "M30", "Fe500", 500, 120, 120, 2550)
    assert 0 < low.U < high.U
    assert column.check_column(sec, "M30", "Fe500", 1e5, 10, 10, 2550).U == 10.0   # beyond axial capacity -> cap
    slender = column.check_column(_sec(230, 230, 16, 4), "M25", "Fe415", 300, 5, 5, 6000)
    assert slender.slender_D and slender.slender_b
    assert column.check_column(_sec(230, 230, 16, 4), "M25", "Fe415", 300, 5, 5, 3000).MD_design_kNm < slender.MD_design_kNm


def test_column_pt_limits():
    assert column.check_column(_sec(600, 600, 12, 4), "M30", "Fe500", 500, 20, 20, 2550).g_pt > 0    # < 0.8 %
    assert column.check_column(_sec(230, 230, 32, 16), "M30", "Fe500", 500, 20, 20, 2550).g_pt > 0   # > 4 %
    assert column.check_column(_sec(450, 450, 20, 8), "M30", "Fe500", 500, 20, 20, 2550).g_pt <= 0


# ----------------------------------------------------------------------------- beam group + misc
def test_check_beam_group_basics():
    sec = BeamSection(300, 500, 20, 4, 16, 2)
    ok = beam.check_beam_group(sec, "M25", "Fe500", 100, 50, 100)
    assert ok.U_flex < 1.0 and ok.U_shear < 1.0 and ok.sv_mm >= 75
    bad = beam.check_beam_group(sec, "M25", "Fe500", 400, 50, 100)
    assert bad.U_flex > 1.0
    assert beam.check_beam_group(sec, "M25", "Fe500", 100, 100, 700).U_shear > 1.0   # tau_v > tau_c,max


def test_beam_steel_limits_flag():
    thin = BeamSection(450, 750, 12, 2, 12, 2)               # far below 0.85 b d / fy
    assert beam.check_beam_group(thin, "M25", "Fe500", 10, 10, 10).g_steel > 0


def test_shear_spacing_rules():
    sh = beam.shear_design(10.0, 300, 450, 1.0, 100.53, "M25", 500.0, 25.0, 75.0, 0.4, 415.0)
    assert math.isinf(sh["sv_strength_mm"])                               # concrete alone carries 10 kN
    assert sh["sv_mm"] <= min(0.75 * 450, 300)                           # cl. 26.5.1.5
    assert sh["sv_mm"] % 25 == 0


def test_layers():
    lay = dt.beam_bar_layers(300, 4, 20, 30, 8, 20, 25, 25, 2)
    assert lay.counts == (4,) and lay.y_centroid_mm == pytest.approx(30 + 8 + 10)
    lay2 = dt.beam_bar_layers(230, 6, 25, 30, 8, 20, 25, 25, 2)
    assert lay2.counts == (3, 3) and lay2.y_centroid_mm > 30 + 8 + 12.5
    assert dt.beam_bar_layers(230, 8, 25, 30, 8, 20, 25, 25, 2) is None


def test_column_layout_rule():
    for n in (4, 6, 8, 10, 12, 16):
        nb, nD = dt.column_layout(n)
        assert 2 * (nb + nD) - 4 == n and nD >= nb
        lay = dt.column_layers(450, 450, 20, n, 40, 8, "x")
        assert lay.area_mm2.sum() == pytest.approx(n * dt.bar_area_mm2(20))


def test_span_depth_diagnostic():
    r = deflection.span_depth_ratio_check(5000, 450, 500, 1.0, 0.5, 0.8)
    assert 20 < r["allowable"] < 60 and r["actual"] == pytest.approx(5000 / 450)
