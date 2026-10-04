"""Vectorised feature construction from genome index arrays (no per-design Python loops).

``physical`` maps indices to physical option values; ``features_a`` adds the derived geometry (areas, effective depths,
reinforcement ratios, stiffness proxies) used by Surrogate A; ``features_b`` is the size-only subset (+ fck) that
the elastic FE response depends on (Surrogate B).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from rcopt import config
from rcopt.design.variables import DesignSpace, default_space


class FeatureBuilder:
    def __init__(self, space: DesignSpace | None = None):
        self.space = space or default_space()
        sp = self.space
        self._values = []
        for name, opts in zip(sp.gene_names, sp.options, strict=True):
            if name == "fck":
                self._values.append(np.array([sp.fck_of[o] for o in opts], dtype=float))
            elif name == "fy":
                self._values.append(np.array([sp.fy_of[o] for o in opts], dtype=float))
            elif name == "cement":
                self._values.append(np.arange(len(opts), dtype=float))      # categorical: option index
            else:
                self._values.append(np.array(opts, dtype=float))
        self.cfg = config.design_space()
        self.n_bg, self.n_cg = sp.n_bg, sp.n_cg

    # ------------------------------------------------------------------ raw physical values
    def physical(self, G: np.ndarray) -> pd.DataFrame:
        G = np.atleast_2d(G)
        cols = {n: self._values[i][G[:, i]] for i, n in enumerate(self.space.gene_names)}
        return pd.DataFrame(cols)

    # ------------------------------------------------------------------ vectorised detailing helpers
    def _beam_yc(self, b, n, dia):
        """Centroid distance of ``n`` bars of ``dia`` in a beam of width ``b`` (vectorised ``beam_bar_layers``)."""
        d = self.cfg.detailing
        s = np.maximum(np.maximum(dia, d.aggregate_size_mm + 5.0), d.min_clear_spacing_mm)
        avail = b - 2.0 * (self.cfg.cover_mm.beam + self.cfg.beam.stirrup_dia_mm)
        n1 = np.maximum(np.floor((avail + s) / (dia + s)), 1.0)
        c1 = np.minimum(n, n1)
        c2 = n - c1
        y1 = self.cfg.cover_mm.beam + self.cfg.beam.stirrup_dia_mm + dia / 2.0
        pitch = dia + np.maximum(dia, d.min_clear_vertical_mm)
        return (c1 * y1 + c2 * (y1 + pitch)) / n

    @staticmethod
    def _area(dia, n):
        return n * np.pi / 4.0 * dia**2

    # ------------------------------------------------------------------ features
    def features_a(self, G: np.ndarray) -> pd.DataFrame:
        """All genes (physical) + derived reinforcement / section quantities (Surrogate A inputs)."""
        P = self.physical(G)
        out = P.drop(columns=["cement"])         # cement type changes cost / carbon only, never U or deflection
        fy, fck = P["fy"].to_numpy(), P["fck"].to_numpy()
        for g in range(self.n_bg):
            b, D = P[f"B{g}_b"].to_numpy(), P[f"B{g}_D"].to_numpy()
            ab, at = self._area(P[f"B{g}_bd"], P[f"B{g}_bn"]).to_numpy(), self._area(P[f"B{g}_td"], P[f"B{g}_tn"]).to_numpy()
            db = D - self._beam_yc(b, P[f"B{g}_bn"].to_numpy(), P[f"B{g}_bd"].to_numpy())
            dt_ = D - self._beam_yc(b, P[f"B{g}_tn"].to_numpy(), P[f"B{g}_td"].to_numpy())
            out[f"B{g}_Ast_bot"], out[f"B{g}_Ast_top"] = ab, at
            out[f"B{g}_d_bot"], out[f"B{g}_d_top"] = db, dt_
            out[f"B{g}_pt_bot"], out[f"B{g}_pt_top"] = 100 * ab / (b * db), 100 * at / (b * dt_)
            out[f"B{g}_bD"], out[f"B{g}_bD3"] = b * D / 1e5, b * D**3 / 1e9
            out[f"B{g}_Mcap_bot"] = 0.87 * fy * ab * db / 1e6          # lever-arm-free capacity proxy, kN.m scale
            out[f"B{g}_Mcap_top"] = 0.87 * fy * at * dt_ / 1e6
            out[f"B{g}_Mlim"] = 0.138 * fck * b * db**2 / 1e6
        for g in range(self.n_cg):
            b, D = P[f"C{g}_b"].to_numpy(), P[f"C{g}_D"].to_numpy()
            asc = self._area(P[f"C{g}_dia"], P[f"C{g}_n"]).to_numpy()
            out[f"C{g}_Asc"], out[f"C{g}_pt"] = asc, 100 * asc / (b * D)
            out[f"C{g}_bD"], out[f"C{g}_bD3"], out[f"C{g}_D_over_b"] = b * D / 1e5, b * D**3 / 1e9, D / b
            out[f"C{g}_Puz"] = (0.45 * fck * (b * D - asc) + 0.75 * fy * asc) / 1e3
            out[f"C{g}_bD2"] = b * D**2 / 1e6
        return out

    def size_columns(self) -> list[str]:
        cols = []
        for g in range(self.n_bg):
            cols += [f"B{g}_b", f"B{g}_D"]
        for g in range(self.n_cg):
            cols += [f"C{g}_b", f"C{g}_D"]
        return cols + ["fck"]

    def features_b(self, G: np.ndarray) -> pd.DataFrame:
        """Sizes + fck and stiffness proxies: everything the elastic FE response depends on."""
        P = self.physical(G)
        out = P[self.size_columns()].copy()
        for g in range(self.n_bg):
            out[f"B{g}_bD"] = P[f"B{g}_b"] * P[f"B{g}_D"] / 1e5
            out[f"B{g}_I"] = P[f"B{g}_b"] * P[f"B{g}_D"] ** 3 / 1e9
        for g in range(self.n_cg):
            out[f"C{g}_bD"] = P[f"C{g}_b"] * P[f"C{g}_D"] / 1e5
            out[f"C{g}_Imin"] = np.minimum(P[f"C{g}_b"] * P[f"C{g}_D"] ** 3, P[f"C{g}_D"] * P[f"C{g}_b"] ** 3) / 1e9
        for g in range(min(self.n_bg, self.n_cg)):
            out[f"EI_ratio_{g}"] = out[f"B{g}_I"] / out[f"C{g}_Imin"]
        return out
