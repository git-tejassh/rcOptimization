"""P0 gate: design space is discrete, IS-standard, round-trips, and geometry checks behave."""
import numpy as np
import pytest

from rcopt import config
from rcopt.design.geometric_feasibility import check_geometry
from rcopt.design.variables import DesignSpace, default_space

IS_BAR_DIAS = {8, 10, 12, 16, 20, 25, 32, 36, 40}          # IS 1786 standard diameters
IS_GRADES_CONCRETE = {"M20", "M25", "M30", "M35", "M40"}   # IS 456 Table 2 (standard grades)
IS_GRADES_STEEL = {"Fe415", "Fe500"}


def test_options_are_standard():
    sp = default_space()
    cfg = sp.cfg
    assert set(cfg.beam.bottom_bar_dia_mm) <= IS_BAR_DIAS
    assert set(cfg.beam.top_bar_dia_mm) <= IS_BAR_DIAS
    assert set(cfg.column.bar_dia_mm) <= IS_BAR_DIAS
    assert set(cfg.global_.concrete_grade) <= IS_GRADES_CONCRETE
    assert set(cfg.global_.steel_grade) <= IS_GRADES_STEEL
    assert min(cfg.column.b_mm) >= 230 and min(cfg.column.D_mm) >= 230  # practice minimum
    assert all(d % 50 == 0 for d in cfg.beam.D_mm)                      # 50 mm increments
    assert all(c % 2 == 0 for c in cfg.column.bar_count)


def test_gene_layout():
    sp = default_space()
    assert sp.n_genes == 6 * 2 + 4 * 2 + 2 == 22
    assert sp.gene_names[0] == "B0_b" and sp.gene_names[-1] == "fy"
    assert sp.total_combinations() > 1e15


def test_roundtrip():
    sp = default_space()
    rng = np.random.default_rng(0)
    for g in sp.random_genomes(200, rng):
        assert np.array_equal(sp.encode(sp.decode(g, repair=False)), g)        # exact without repair
        assert np.array_equal(sp.encode(sp.decode(g)), sp.repair(g))           # canonical genome with repair


def test_decode_rejects_out_of_range():
    sp = default_space()
    g = sp.random_genomes(1, np.random.default_rng(1))[0].copy()
    g[0] = sp.n_options[0]
    with pytest.raises(ValueError):
        sp.decode(g)
    with pytest.raises(ValueError):
        sp.decode(g[:-1])


def test_decoded_values_come_from_option_lists():
    sp = default_space()
    cfg = sp.cfg
    for g in sp.random_genomes(300, np.random.default_rng(2)):
        d = sp.decode(g)
        for b in d.beams:
            assert b.b_mm in cfg.beam.b_mm and b.D_mm in cfg.beam.D_mm
            assert b.bot_dia_mm in cfg.beam.bottom_bar_dia_mm and b.top_n in cfg.beam.bar_count
        for c in d.columns:
            assert c.b_mm in cfg.column.b_mm and c.D_mm in cfg.column.D_mm
            assert c.dia_mm in cfg.column.bar_dia_mm and c.n in cfg.column.bar_count
        assert d.concrete in cfg.global_.concrete_grade and d.steel in cfg.global_.steel_grade


def test_seed_reproducibility():
    sp = default_space()
    a = sp.random_genomes(50, np.random.default_rng(42))
    b = sp.random_genomes(50, np.random.default_rng(42))
    assert np.array_equal(a, b)


def test_size_key_ignores_reinforcement():
    sp = default_space()
    g = sp.random_genomes(1, np.random.default_rng(3))[0].copy()
    g2 = g.copy()
    g2[sp.gene_index("B0_bn")] = (g[sp.gene_index("B0_bn")] + 1) % sp.n_options[sp.gene_index("B0_bn")]
    g2[sp.gene_index("fy")] = 1 - g[sp.gene_index("fy")]
    assert sp.decode(g).size_key() == sp.decode(g2).size_key()


def _design(sp, **over):
    base = dict(B0_b=2, B0_D=3, B0_bd=1, B0_bn=2, B0_td=1, B0_tn=2, B1_b=2, B1_D=3, B1_bd=1, B1_bn=2,
                B1_td=1, B1_tn=2, C0_b=5, C0_D=5, C0_dia=2, C0_n=2, C1_b=5, C1_D=5, C1_dia=2, C1_n=2,
                fck=2, fy=1)
    base.update(over)
    return sp.decode([base[n] for n in sp.gene_names], repair=False)


def test_geometry_reference_design_ok():
    sp = default_space()
    assert check_geometry(_design(sp)).ok


def test_geometry_reasons():
    sp = default_space()
    assert "C0_D_LT_B" in check_geometry(_design(sp, C0_b=7, C0_D=3)).reasons
    # 8 x 25 mm bars in a 230 mm beam need > 2 layers
    r = check_geometry(_design(sp, B0_b=0, B0_bd=3, B0_bn=6, C0_b=5, C0_D=5, C1_b=5, C1_D=5)).reasons
    assert "B0_BOT_NOFIT" in r
    # 4 x 32 mm bars in a 600 mm column: clear spacing along the face exceeds 300 mm
    assert "C0_SPACING_MAX" in check_geometry(_design(sp, C0_b=8, C0_D=8, C0_dia=4, C0_n=0)).reasons
    # beam wider than the column it frames into
    assert "B0_B_GT_COLUMN_B" in check_geometry(_design(sp, B0_b=5, C0_b=1, C0_D=3, C1_b=1, C1_D=3)).reasons


def test_config_hash_stable_and_provisional_listed():
    assert config.config_hash() == config.config_hash()
    prov = config.provisional_items()
    assert any(p.startswith("cost_rates") for p in prov) and any(p.startswith("carbon_factors") for p in prov)


def test_custom_groups_validated():
    g = config.geometry().model_dump()
    g["beam_groups"] = [[0, 1], [3, 4]]
    with pytest.raises(ValueError):
        config.GeometryCfg(**g)
    assert DesignSpace is not None
