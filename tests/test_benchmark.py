"""STAAD benchmark gate (project.md 7.5) and parser/config consistency."""
import pytest

from rcopt import config
from rcopt.fe import benchmark as bm
from rcopt.fe import staad_reference as sr
from rcopt.geometry.frame_spec import build_frame
from rcopt.geometry.staad_parser import parse_staad, staad_grid

pytestmark = pytest.mark.skipif(not (sr.STD_DIR / f"{sr.STEM}.rea").exists(), reason="STAAD result files absent")


def test_staad_parse_matches_config_geometry():
    sm = parse_staad(bm.STAAD_FILE)
    xs, ys, zs = staad_grid(sm)
    g = config.geometry()
    fs = build_frame(g)
    assert xs == fs.xs and zs == fs.zs
    assert ys == sorted([-g.stub_height_m] + fs.ys)
    assert len(sm.joints) == len(fs.nodes) and len(sm.members) == len(fs.members)
    assert set(sm.supports) == set(range(101, 121))
    assert sm.section_m[1] == (0.45, 0.30) and sm.section_m[81] == (0.45, 0.45)


def test_staad_loads_match_config_loads():
    sm = parse_staad(bm.STAAD_FILE)
    lc = config.loads()
    floor = lc.unit_weight_rc_kNm3 * lc.slab.thickness_mm / 1000 + lc.slab.finish_kNm2
    roof = lc.unit_weight_rc_kNm3 * lc.slab.thickness_mm / 1000 + lc.slab.roof_finish_kNm2
    dl = {d["YRANGE"]: -d["w"] for d in sm.floor_loads[5]}
    assert dl[(0.0, 9.0)] == pytest.approx(floor) and dl[(12.0, 12.0)] == pytest.approx(roof)
    ll = {d["YRANGE"]: -d["w"] for d in sm.floor_loads[6]}
    assert ll[(0.0, 9.0)] == lc.live.floor_kNm2 and ll[(12.0, 12.0)] == lc.live.roof_kNm2
    walls = {len(m["members"]): -m["w"] for m in sm.member_loads[5]}
    assert walls[70] == lc.wall.fixed_perimeter_kNm and walls[85] == lc.wall.fixed_interior_kNm
    # the depth-following wall formula reproduces STAAD's wall loads for the 450 mm beam
    assert lc.wall.perimeter_thickness_m * (3.0 - 0.45) * lc.wall.unit_weight_kNm3 == pytest.approx(11.73, abs=0.01)
    assert lc.wall.interior_thickness_m * (3.0 - 0.45) * lc.wall.unit_weight_kNm3 == pytest.approx(5.87, abs=0.01)


def test_benchmark_tolerances():
    r = bm.run_benchmark()
    assert r["reactions_Fy"]["DL"]["sum_opensees_kN"] == pytest.approx(r["reactions_Fy"]["DL"]["sum_staad_kN"], rel=1e-5)
    for name in ("DL", "LL", "COMB11"):
        assert r["reactions_Fy"][name]["max_rel"] < 0.005
        assert r["displacements_dy_mm"][name]["max_rel"] < 0.01
        assert r["displacements_dx_dz_mm"][name]["max_abs_diff_mm"] < 0.05
    assert r["columns_Pu"]["max_rel"] < 0.005 and r["columns_Pu"]["members_compared"] >= 70
    assert r["columns_Mz_ge20kNm"]["max_rel"] < 0.02 and r["columns_My_ge20kNm"]["max_rel"] < 0.02
    assert r["columns_Mz_all"]["max_rel"] < 0.5 and r["columns_My_all"]["max_rel"] < 0.5   # abs diff, kN.m


def test_anl_parse_column_81():
    c = sr.parse_anl_columns()[81]
    assert c["guiding_case"] == 11 and c["Pu_kN"] == 775.79 and c["IR"] == 0.39
    assert c["Muz1_kNm"] == 150.87 and c["Puz_kN"] == 2901.43
