"""P1 gate: discrete-aware LHS, biased stratum, seed reproducibility, no physically impossible rows."""
import numpy as np
import pytest

from rcopt.design.variables import default_space
from rcopt.sampling.biased_sampler import precheck
from rcopt.sampling.discrete_lhs import discrete_lhs
from rcopt.sampling.matrix import build_design_matrix, sanity_check


def test_lhs_is_stratified_per_gene():
    sp = default_space()
    n = 3500
    g = discrete_lhs(sp, n, seed=1)
    assert g.shape == (n, sp.n_genes)
    for j, k in enumerate(sp.n_options):
        counts = np.bincount(g[:, j], minlength=k)
        # equal-probability bins: every option gets n/k points up to +/- 2 (LHS strata straddle bin edges)
        assert np.all(np.abs(counts - n / k) <= 2.0), (sp.gene_names[j], counts)


def test_lhs_seed_reproducible_and_seed_sensitive():
    sp = default_space()
    assert np.array_equal(discrete_lhs(sp, 200, 7), discrete_lhs(sp, 200, 7))
    assert not np.array_equal(discrete_lhs(sp, 200, 7), discrete_lhs(sp, 200, 8))


def _design(sp, **over):
    base = dict(B0_b=2, B0_D=4, B0_bd=1, B0_bn=3, B0_td=1, B0_tn=3, B1_b=2, B1_D=4, B1_bd=1, B1_bn=3, B1_td=1,
                B1_tn=3, C0_b=5, C0_D=5, C0_dia=2, C0_n=3, C1_b=5, C1_D=5, C1_dia=2, C1_n=3, fck=2, fy=1)
    base.update(over)
    return sp.decode([base[n] for n in sp.gene_names], repair=False)


def test_precheck_accepts_reasonable_and_rejects_undersized():
    sp = default_space()
    assert precheck(_design(sp)) is None
    assert precheck(_design(sp, B0_b=0, B0_D=0, B0_bd=0, B0_bn=0, B0_td=0, B0_tn=0)) is not None   # 230 x 300 beam, 2-12 bars
    assert precheck(_design(sp, C0_b=0, C0_D=0, C0_dia=0, C0_n=0, C1_b=0, C1_D=0, C1_dia=0, C1_n=0)) is not None


@pytest.mark.slow
def test_design_matrix_gate():
    df, rep = build_design_matrix()
    sp = default_space()
    assert len(df) == 5000 and set(df.sample_stratum) == {"lhs", "biased"}
    assert rep["physically_impossible_rows"] == 0 and rep["genes_in_range"]
    assert df["id"].is_unique
    cols = [c for c in df if c.startswith("g_")]
    assert not df.duplicated(subset=cols).any()
    assert rep["lhs_raw_geometry_infeasible_fraction"] > 0.5                              # the reported raw fraction
    assert sanity_check(sp, df)["physically_impossible_rows"] == 0
    df2, _ = build_design_matrix()
    assert df.equals(df2)                                                                  # same seed => identical matrix
