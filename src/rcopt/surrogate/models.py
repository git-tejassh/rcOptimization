"""Surrogate A (direct utilisation regression, brief-faithful) and Surrogate B (demand surrogate + analytic IS 456).

* **A**: inputs = all genes + derived features; outputs = ``U_flex_max, U_shear_max, U_col_max, defl_ratio_max``
  (continuous, log-transformed) plus the stirrup spacings ``sv_B{g}`` (needed by the cost model, decision D-008).
  Each output is a bootstrap ensemble of XGBoost regressors (mean = prediction, std = uncertainty).
* **B**: inputs = sizes + fck (the only things the elastic FE depends on); outputs = FE demands (beam Msag/Mhog/Vu per
  group, critical column triples Pu/MD/Mb per group, delta/L per group); utilisations then come from the *exact*
  analytic IS 456 module via ``evaluate_from_demands``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

from rcopt import config
from rcopt.design.constraints import (
    analytic_constraints,
    analytic_objectives,
    evaluate_from_demands,
    geometry_violation,
)
from rcopt.design.variables import DesignSpace, default_space
from rcopt.fe.runner import TRIPLE_FIELDS, demand_columns, row_to_demands
from rcopt.surrogate.features import FeatureBuilder

TARGETS_A = ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max")
LOG_FLOOR = 1e-3


def aux_targets(n_bg: int) -> tuple[str, ...]:
    return tuple(f"sv_B{g}" for g in range(n_bg))


def _xgb(params: dict, seed: int) -> xgb.XGBRegressor:
    return xgb.XGBRegressor(tree_method="hist", random_state=seed, n_jobs=4, verbosity=0, **params)


def _to_log(y: np.ndarray) -> np.ndarray:
    return np.log(np.maximum(y, LOG_FLOOR))


class SurrogateA:
    """Bootstrap ensembles of gradient-boosted trees on the full genome features."""

    def __init__(self, params: dict | None = None, n_ensemble: int | None = None, seed: int = 42,
                 space: DesignSpace | None = None):
        sc = config.load_dict("surrogate")
        self.params = dict(params or sc["xgboost"])
        self.n_ensemble = n_ensemble or sc["n_ensemble"]
        self.seed = seed
        self.space = space or default_space()
        self.fb = FeatureBuilder(self.space)
        self.models: dict[str, list[xgb.XGBRegressor]] = {}
        self.feature_names: list[str] = []

    def targets(self) -> tuple[str, ...]:
        return TARGETS_A + aux_targets(self.space.n_bg)

    def fit(self, G: np.ndarray, df: pd.DataFrame) -> SurrogateA:
        X = self.fb.features_a(G)
        self.feature_names = list(X.columns)
        rng = np.random.default_rng(self.seed)
        n = len(X)
        self.models = {}
        for t in self.targets():
            y = df[t].to_numpy(float)
            y = _to_log(y) if t in TARGETS_A else y
            members = []
            for k in range(self.n_ensemble):
                idx = np.arange(n) if k == 0 else rng.integers(0, n, n)        # member 0 = full data, others bootstrap
                m = _xgb(self.params, self.seed + k)
                m.fit(X.iloc[idx], y[idx])
                members.append(m)
            self.models[t] = members
        return self

    def predict(self, G: np.ndarray, with_std: bool = False):
        """dict target -> prediction in original units (U ratios, sv in mm); optionally the log-space std."""
        X = self.fb.features_a(G)[self.feature_names]
        out, std = {}, {}
        for t, members in self.models.items():
            P = np.column_stack([m.predict(X) for m in members])
            mean, sd = P.mean(axis=1), P.std(axis=1)
            out[t] = np.exp(mean) if t in TARGETS_A else mean
            std[t] = sd
        return (out, std) if with_std else out

    def predict_eval(self, G: np.ndarray, margin: float = 0.0) -> dict:
        """Objectives and constraint matrix for genomes ``G`` (n, n_genes): cost, carbon, g (n, 7).

        Constraints: [defl - 1 + m, U_flex - 1 + m, U_shear - 1 + m, U_col - 1 + m] from the surrogate with
        safety margin ``m``; [g_beam_steel, g_col_pt, geom_violation] exactly analytic.
        """
        pred = self.predict(G)
        return _assemble(self.space, G, pred, margin)

    def importances(self, target: str) -> pd.Series:
        imp = np.mean([m.feature_importances_ for m in self.models[target]], axis=0)
        return pd.Series(imp, index=self.feature_names).sort_values(ascending=False)


def _assemble(space: DesignSpace, G: np.ndarray, pred: dict, margin: float) -> dict:
    n = len(G)
    cost, carbon = np.empty(n), np.empty(n)
    g = np.empty((n, 7))
    for i in range(n):
        d = space.decode(G[i])
        sv = tuple(float(max(pred[f"sv_B{k}"][i], 75.0)) for k in range(space.n_bg))
        cost[i], carbon[i], _ = analytic_objectives(d, sv)
        gb, gc = analytic_constraints(d)
        g[i] = [pred["defl_ratio_max"][i] - 1 + margin, pred["U_flex_max"][i] - 1 + margin,
                pred["U_shear_max"][i] - 1 + margin, pred["U_col_max"][i] - 1 + margin, gb, gc,
                geometry_violation(d)]
    return {"cost": cost, "carbon": carbon, "g": g}


def column_group_lengths_mm(design, geom: config.GeometryCfg | None = None) -> list[float]:
    """Storey clear length per column group (h - D of the beam group at the top of the storey), mm."""
    geom = geom or config.geometry()
    bg_of_level = {lv: gi for gi, grp in enumerate(geom.beam_groups) for lv in grp}
    out = []
    for grp in geom.column_groups:
        s = max(grp)
        out.append((geom.storey_heights_m[s] * 1000.0) - design.beams[bg_of_level[s + 1]].D_mm)
    return out


class SurrogateB:
    """Demand surrogate: sizes + fck -> FE demands; utilisations by the analytic IS 456 checks."""

    def __init__(self, params: dict | None = None, seed: int = 42, space: DesignSpace | None = None):
        sc = config.load_dict("surrogate")
        self.params = dict(params or sc["xgboost"])
        self.seed = seed
        self.space = space or default_space()
        self.fb = FeatureBuilder(self.space)
        self.models: dict[str, xgb.XGBRegressor] = {}
        self.feature_names: list[str] = []

    def target_columns(self) -> list[str]:
        """Predicted demand columns (the unsupported-length ``l`` entries are analytic, not learned)."""
        return [c for c in demand_columns(self.space.n_bg, self.space.n_cg) if not c.endswith("_l")]

    def fit(self, G: np.ndarray, df: pd.DataFrame) -> SurrogateB:
        X = self.fb.features_b(G)
        self.feature_names = list(X.columns)
        self.models = {}
        for c in self.target_columns():
            m = _xgb(self.params, self.seed)
            m.fit(X, df[c].to_numpy(float))
            self.models[c] = m
        return self

    def predict_demands(self, G: np.ndarray) -> pd.DataFrame:
        X = self.fb.features_b(G)[self.feature_names]
        return pd.DataFrame({c: np.maximum(m.predict(X), 0.0) for c, m in self.models.items()})

    def _rows(self, G: np.ndarray, D: pd.DataFrame):
        for i in range(len(G)):
            design = self.space.decode(G[i])
            lens = column_group_lengths_mm(design)
            row = D.iloc[i].to_dict()
            for g in range(self.space.n_cg):
                for k in range(4):
                    row[f"C{g}_T{k}_l"] = lens[g]
            yield design, *row_to_demands(row, self.space.n_bg, self.space.n_cg)

    def predict_eval(self, G: np.ndarray, margin: float = 0.0) -> dict:
        """Objectives and constraints; also returns the four utilisation outputs for metric comparison."""
        D = self.predict_demands(G)
        n = len(G)
        cost, carbon = np.empty(n), np.empty(n)
        g = np.empty((n, 7))
        util = np.empty((n, 4))
        for i, (design, beam, cols, defl) in enumerate(self._rows(G, D)):
            ev = evaluate_from_demands(design, beam, cols, defl)
            util[i] = [ev.U_flex, ev.U_shear, ev.U_col, ev.defl_ratio]
            cost[i], carbon[i] = ev.cost, ev.carbon
            gb, gc = analytic_constraints(design)
            g[i] = [ev.defl_ratio - 1 + margin, ev.U_flex - 1 + margin, ev.U_shear - 1 + margin,
                    ev.U_col - 1 + margin, gb, gc, geometry_violation(design)]
        return {"cost": cost, "carbon": carbon, "g": g,
                "U_flex_max": util[:, 0], "U_shear_max": util[:, 1], "U_col_max": util[:, 2],
                "defl_ratio_max": util[:, 3]}

    def importances(self, target: str) -> pd.Series:
        return pd.Series(self.models[target].feature_importances_, index=self.feature_names).sort_values(
            ascending=False)


__all__ = ["SurrogateA", "SurrogateB", "TARGETS_A", "aux_targets", "column_group_lengths_mm", "TRIPLE_FIELDS"]
