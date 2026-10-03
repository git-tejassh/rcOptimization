"""IS 456:2000 column checks: P-M interaction by strain compatibility (cl. 38.1, SP 16), biaxial bending
(cl. 39.6), minimum eccentricity (cl. 25.4), slenderness (cl. 25.1.2, 39.7) and steel limits (cl. 26.5.3).

Units: N, mm, MPa; demands in kN / kN.m. ``MD`` is the moment in the plane across the depth D (strain varies
over D, i.e. moment about the axis parallel to b); ``Mb`` is the moment across the width b.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.codes import is456_tables as t
from rcopt.design.geometric_feasibility import tie_dia_mm
from rcopt.design.variables import ColumnSection

N_STRIPS = 200
XU_GRID_FACTORS = np.concatenate(([1e-4], np.geomspace(0.02, 100.0, 140), [1e4]))   # xu / H


def pm_points(layers: dt.ColumnLayers, fck: float, fy: float, xu: np.ndarray, n_strips: int = N_STRIPS):
    """Axial force (N, compression +) and moment about the section centroid (N.mm) for neutral-axis depths ``xu``.

    Strain profile: eps_cu = 0.0035 at the compression face for xu <= H; for xu > H the strain is 0.002 at
    3H/7 from the compression face (cl. 38.1 pivot). Steel force is net of the displaced concrete.
    """
    H, W = layers.H_mm, layers.W_mm
    xu = np.asarray(xu, dtype=float)[:, None]
    dy = H / n_strips
    ys = (np.arange(n_strips) + 0.5) * dy

    def strain(y):
        return np.where(xu <= H, t.EPS_CU * (xu - y) / xu, t.EPS_C0 * (xu - y) / (xu - 3.0 * H / 7.0))

    fc = t.concrete_stress_MPa(strain(ys[None, :]), fck) * W * dy
    P = fc.sum(axis=1)
    M = (fc * (H / 2.0 - ys[None, :])).sum(axis=1)
    eps_s = strain(layers.y_mm[None, :])
    fs = (t.steel_stress_MPa(eps_s, fy) - t.concrete_stress_MPa(eps_s, fck)) * layers.area_mm2[None, :]
    P = P + fs.sum(axis=1)
    M = M + (fs * (H / 2.0 - layers.y_mm[None, :])).sum(axis=1)
    return P, M


@lru_cache(maxsize=60_000)
def pm_curve(b: int, D: int, dia: int, n: int, cover: float, tie: float, fck: float, fy: float, about: str):
    """(P_N ascending, M_Nmm) interaction curve and Pb (balanced axial force, N) for one axis."""
    lay = dt.column_layers(b, D, dia, n, cover, tie, about)
    xu = XU_GRID_FACTORS * lay.H_mm
    P, M = pm_points(lay, fck, fy, xu)
    order = np.argsort(P)
    P, M = P[order], M[order]
    k_bal = _balanced_ratio(fy)
    d_ext = float(lay.y_mm[-1])
    Pb = float(pm_points(lay, fck, fy, np.array([k_bal * d_ext]))[0][0])
    return P, np.maximum(M, 0.0), Pb


def _balanced_ratio(fy: float) -> float:
    grade = "Fe415" if abs(fy - 415) < abs(fy - 500) else "Fe500"
    return t.xu_max_ratio(grade)


def uniaxial_capacity_Nmm(P: np.ndarray, M: np.ndarray, Pu_N: float) -> float:
    """Moment capacity Mu1 at axial load ``Pu`` read off the interaction curve (0 if Pu exceeds the curve)."""
    if Pu_N > P[-1]:
        return 0.0
    return float(np.interp(Pu_N, P, M))


def alpha_n(Pu_N: float, Puz_N: float) -> float:
    """cl. 39.6: 1.0 for Pu/Puz <= 0.2, 2.0 for >= 0.8, linear between."""
    r = Pu_N / Puz_N
    return float(np.clip(1.0 + (r - 0.2) / 0.6, 1.0, 2.0))


def puz_N(b: float, D: float, Asc: float, fck: float, fy: float) -> float:
    """Axial capacity 0.45 fck Ac + 0.75 fy Asc, cl. 39.6 (Ac = concrete area net of steel, as STAAD's)."""
    return 0.45 * fck * (b * D - Asc) + 0.75 * fy * Asc


def min_eccentricity_mm(l_mm: float, dim_mm: float) -> float:
    """cl. 25.4: e_min = max(l/500 + D/30, 20 mm)."""
    return max(l_mm / 500.0 + dim_mm / 30.0, 20.0)


@dataclass(frozen=True)
class ColumnCheck:
    U: float
    Pu_kN: float
    MD_design_kNm: float
    Mb_design_kNm: float
    MuD1_kNm: float
    Mub1_kNm: float
    alpha_n: float
    Puz_kN: float
    pt_percent: float
    slender_D: bool
    slender_b: bool
    g_pt: float          # >0 = violation of 0.8 % <= pt <= 4 %


def check_column(sec: ColumnSection, concrete: str, steel: str, Pu_kN: float, MD_kNm: float, Mb_kNm: float,
                 l_mm: float, cfg: config.DesignSpaceCfg | None = None, k_eff: float = 1.2,
                 emin_simultaneous: bool = True, cap: float = 10.0,
                 max_slenderness: float = 60.0) -> ColumnCheck:
    """Biaxial check of one column section for one (Pu, MD, Mb) triple at unsupported length ``l_mm``."""
    cfg = cfg or config.design_space()
    fck, fy = t.fck_MPa(concrete), t.fy_MPa(steel)
    b, D = float(sec.b_mm), float(sec.D_mm)
    tie = tie_dia_mm(sec.dia_mm, cfg.column.tie_dia_min_mm)
    Asc = sec.n * dt.bar_area_mm2(sec.dia_mm)
    pt = 100.0 * Asc / (b * D)
    g_pt = max(cfg.detailing.column_pt_min_percent / pt - 1.0, pt / cfg.detailing.column_pt_max_percent - 1.0)
    Pu = max(Pu_kN, 0.0) * 1e3
    Puz = puz_N(b, D, Asc, fck, fy)

    PD, MD_curve, PbD = pm_curve(sec.b_mm, sec.D_mm, sec.dia_mm, sec.n, cfg.cover_mm.column, tie, fck, fy, "x")
    Pbb_curve, Mb_curve, Pbb = pm_curve(sec.b_mm, sec.D_mm, sec.dia_mm, sec.n, cfg.cover_mm.column, tie, fck, fy, "y")

    le = k_eff * l_mm
    sD, sb = le / D, le / b
    slender_D, slender_b = sD > 12.0, sb > 12.0
    eD = min_eccentricity_mm(l_mm, D)
    eb = min_eccentricity_mm(l_mm, b)
    if emin_simultaneous:
        MD_d = max(abs(MD_kNm) * 1e6, Pu * eD)
        Mb_d = max(abs(Mb_kNm) * 1e6, Pu * eb)
    else:                                   # cl. 25.4: need not apply in both directions simultaneously
        MD_d, Mb_d = abs(MD_kNm) * 1e6, abs(Mb_kNm) * 1e6
        if Pu * eD >= Pu * eb:
            MD_d = max(MD_d, Pu * eD)
        else:
            Mb_d = max(Mb_d, Pu * eb)
    if slender_D:                           # cl. 39.7.1: Ma = Pu D (le/D)^2 / 2000, reduced by k (39.7.1.1)
        kD = min(1.0, (Puz - Pu) / (Puz - PbD)) if Puz > PbD else 1.0
        MD_d += Pu * D / 2000.0 * sD**2 * max(kD, 0.0)
    if slender_b:
        kb = min(1.0, (Puz - Pu) / (Puz - Pbb)) if Puz > Pbb else 1.0
        Mb_d += Pu * b / 2000.0 * sb**2 * max(kb, 0.0)

    MuD1 = uniaxial_capacity_Nmm(PD, MD_curve, Pu)
    Mub1 = uniaxial_capacity_Nmm(Pbb_curve, Mb_curve, Pu)
    an = alpha_n(Pu, Puz)
    if max(sD, sb) > max_slenderness or MuD1 <= 0 or Mub1 <= 0 or Pu >= Puz:
        U = cap
    else:
        U = min((MD_d / MuD1) ** an + (Mb_d / Mub1) ** an, cap)
    return ColumnCheck(U, Pu / 1e3, MD_d / 1e6, Mb_d / 1e6, MuD1 / 1e6, Mub1 / 1e6, an, Puz / 1e3, pt,
                       slender_D, slender_b, g_pt)



__all__ = ["pm_curve", "check_column", "alpha_n", "puz_N", "min_eccentricity_mm", "ColumnCheck"]
