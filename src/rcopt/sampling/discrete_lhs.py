"""Discrete-aware Latin hypercube sampling (project.md 8.1).

A stratified LHS is drawn on the unit cube; each coordinate is mapped to an option *index* with equal-probability
bins (``index = floor(u k)``), so every option of every gene is hit as evenly as N allows (never sample continuous
values and snap afterwards without stratification).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import qmc

from rcopt.design.variables import DesignSpace


def discrete_lhs(space: DesignSpace, n: int, seed: int) -> np.ndarray:
    """(n, n_genes) integer genomes; per gene every option appears floor(n/k) or ceil(n/k) times (+/- LHS jitter)."""
    u = qmc.LatinHypercube(d=space.n_genes, seed=seed, optimization=None).random(n)
    idx = np.floor(u * space.n_options[None, :]).astype(int)
    return np.minimum(idx, space.n_options[None, :] - 1)
