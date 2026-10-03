"""IS 456:2000 material constants, Tables 19/20 and the steel/concrete stress-strain laws.

Every value is read from ``config/is456_tables.yaml`` (status: provisional - owner must verify, see
docs/ASSUMPTIONS.md A1-A5). Units: N, mm, MPa; strains dimensionless; compression positive.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from rcopt import config

EPS_C0 = 0.002      # IS 456 cl. 38.1: strain at the end of the parabola
EPS_CU = 0.0035     # cl. 38.1: ultimate strain in bending
FCC_FACTOR = 0.446  # stress-block plateau = 0.446 fck (0.67 fck / 1.5)
BLOCK_AREA = 0.36   # cl. G-1.1: C = 0.36 fck b xu
BLOCK_ARM = 0.42    # cl. G-1.1: lever arm d - 0.42 xu


@lru_cache(maxsize=1)
def tables() -> dict:
    return config.load_dict("is456_tables")


def fck_MPa(grade: str) -> float:
    return float(tables()["concrete"]["fck_MPa"][grade])


def fy_MPa(grade: str) -> float:
    return float(tables()["steel"]["fy_MPa"][grade])


def Es_MPa() -> float:
    return float(tables()["steel"]["Es_MPa"])


def Ec_MPa(fck: float, factor: float = 5000.0) -> float:
    """Short-term modulus of concrete, cl. 6.2.3.1: Ec = 5000 sqrt(fck)."""
    return factor * math.sqrt(fck)


def fyd_MPa(fy: float) -> float:
    """Design yield stress fy / 1.15 (= 0.87 fy)."""
    return fy / tables()["steel"]["partial_safety"]


def xu_max_ratio(steel_grade: str) -> float:
    """xu,max / d, cl. 38.1 note."""
    return float(tables()["steel"]["xu_max_over_d"][steel_grade])


def mu_lim_over_bd2(fck: float, steel_grade: str) -> float:
    """Limiting moment of resistance / (b d^2), cl. G-1.1 (a): 0.36 fck k (1 - 0.42 k)."""
    k = xu_max_ratio(steel_grade)
    return BLOCK_AREA * fck * k * (1.0 - BLOCK_ARM * k)


@lru_cache(maxsize=None)
def _steel_curve(fy: float) -> tuple[np.ndarray, np.ndarray]:
    """(total strain, stress) breakpoints of the design curve for ``fy`` (Fig. 23 / SP 16)."""
    t = tables()["steel"]
    fyd = fyd_MPa(fy)
    frac = np.array(t["curve_stress_fraction"])
    inel = np.array(t["curve_inelastic_strain"])
    strain = frac * fyd / Es_MPa() + inel
    return np.concatenate([[0.0], strain]), np.concatenate([[0.0], frac * fyd])


def steel_stress_MPa(strain, fy: float):
    """Design stress for total strain (signed; tension negative like compression positive). Vectorised.

    Linear (Es) to 0.8 fyd, then piecewise-linear through the Fig. 23 points, plateau at fyd.
    """
    eps = np.asarray(strain, dtype=float)
    xs, ys = _steel_curve(fy)
    return np.sign(eps) * np.interp(np.abs(eps), xs, ys)


def concrete_stress_MPa(strain, fck: float):
    """Parabola-rectangle stress block (compression positive, zero in tension). Vectorised."""
    eps = np.asarray(strain, dtype=float)
    r = np.clip(eps, 0.0, EPS_C0) / EPS_C0
    s = FCC_FACTOR * fck * (2.0 * r - r * r)
    return np.where(eps <= 0.0, 0.0, np.where(eps >= EPS_C0, FCC_FACTOR * fck, s))


def tau_c_MPa(pt_percent: float, concrete_grade: str) -> float:
    """Design shear strength of concrete, Table 19, linear interpolation in pt (clamped to the table range)."""
    t = tables()["table19"]
    return float(np.interp(pt_percent, t["pt"], t[concrete_grade]))


def tau_c_max_MPa(concrete_grade: str) -> float:
    """Maximum shear stress, Table 20."""
    return float(tables()["table20"][concrete_grade])
