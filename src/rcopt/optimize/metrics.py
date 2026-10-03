"""Multi-objective metrics: pooled non-dominated sets, hypervolume against a fixed pooled reference, spacing."""
from __future__ import annotations

import numpy as np
from pymoo.indicators.hv import HV
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting


def non_dominated(F: np.ndarray) -> np.ndarray:
    """Indices of the non-dominated rows of ``F`` (minimisation)."""
    if len(F) == 0:
        return np.array([], dtype=int)
    return NonDominatedSorting().do(F, only_non_dominated_front=True)


class Normaliser:
    """Fixed normalisation: ideal / nadir of the pooled fronts; reference point = nadir + 5 % of the range."""

    def __init__(self, pooled_F: np.ndarray, ref_margin: float = 0.05):
        self.ideal = pooled_F.min(axis=0)
        self.nadir = pooled_F.max(axis=0)
        self.range = np.maximum(self.nadir - self.ideal, 1e-12)
        self.ref = np.full(pooled_F.shape[1], 1.0 + ref_margin)

    def __call__(self, F: np.ndarray) -> np.ndarray:
        return (np.asarray(F) - self.ideal) / self.range

    def hv(self, F: np.ndarray) -> float:
        """Hypervolume of ``F`` in normalised objective space (reference point fixed for all configs)."""
        if len(F) == 0:
            return 0.0
        Fn = self(F)
        Fn = Fn[np.all(Fn < self.ref, axis=1)]
        return float(HV(ref_point=self.ref)(Fn)) if len(Fn) else 0.0


def spacing(F_norm: np.ndarray) -> float:
    """Schott's spacing metric (0 = perfectly even); NaN for < 3 points."""
    n = len(F_norm)
    if n < 3:
        return float("nan")
    d = np.array([np.min(np.sum(np.abs(F_norm[i] - np.delete(F_norm, i, axis=0)), axis=1)) for i in range(n)])
    return float(np.sqrt(np.sum((d.mean() - d) ** 2) / (n - 1)))


def objective_correlation(F: np.ndarray) -> float:
    """Pearson correlation of cost and carbon (the front is narrow if this is close to 1)."""
    return float(np.corrcoef(F[:, 0], F[:, 1])[0, 1]) if len(F) > 2 else float("nan")
