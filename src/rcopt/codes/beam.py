"""IS 456:2000 beam checks: flexure (cl. 38.1, Annex G), shear (cl. 40), steel limits (cl. 26.5.1).

Units: N, mm, MPa; demands arrive in kN / kN.m and are converted here. All sections are treated as
rectangular (conservative for sagging T-action).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from scipy.optimize import brentq

from rcopt import config
from rcopt.codes import detailing as dt
from rcopt.codes import is456_tables as t
from rcopt.design.geometric_feasibility import beam_layers
from rcopt.design.variables import BeamSection


@lru_cache(maxsize=400_000)
def flexural_capacity_Nmm(b: float, d: float, d_comp: float, Ast: float, Asc: float, fck: float,
                          fy: float, steel_grade: str) -> float:
    """Design moment of resistance of a rectangular section, Annex G-1.1 / G-1.2 (strain compatibility).

    ``Ast`` tension steel at effective depth ``d``; ``Asc`` compression steel at ``d_comp`` from the
    compression face. Concrete block C = 0.36 fck b xu at 0.42 xu; compression steel stress from the design
    curve at strain 0.0035 (xu - d')/xu, less the displaced concrete stress. xu is capped at
    xu,max = k d (cl. 38.1): beyond it the section is over-reinforced and the capacity is held at the
    xu,max value (never extrapolated).
    """
    if Ast <= 0 or d <= 0:
        return 0.0
    xu_max = t.xu_max_ratio(steel_grade) * d
    T = t.fyd_MPa(fy) * Ast

    def comp_steel_force(xu: float) -> float:
        if Asc <= 0:
            return 0.0
        eps = t.EPS_CU * (xu - d_comp) / xu
        return Asc * (float(t.steel_stress_MPa(eps, fy)) - float(t.concrete_stress_MPa(eps, fck)))

    def total_compression(xu: float) -> float:
        return t.BLOCK_AREA * fck * b * xu + comp_steel_force(xu)

    if total_compression(xu_max) <= T:
        xu = xu_max
    else:
        xu = brentq(lambda x: total_compression(x) - T, 1e-6 * d, xu_max, xtol=1e-6, rtol=1e-10)
    return t.BLOCK_AREA * fck * b * xu * (d - t.BLOCK_ARM * xu) + comp_steel_force(xu) * (d - d_comp)


def mu_singly_closed_form_Nmm(b: float, d: float, Ast: float, fck: float, fy: float) -> float:
    """Annex G-1.1 (b): Mu = 0.87 fy Ast d (1 - Ast fy / (b d fck)) (independent cross-check formula)."""
    return 0.87 * fy * Ast * d * (1.0 - Ast * fy / (b * d * fck))


def shear_design(Vu_kN: float, b: float, d: float, pt_percent: float, Asv: float, concrete: str, fy: float,
                 sv_step: float, sv_min: float, k_min: float, fy_cap: float) -> dict:
    """Beam shear design, cl. 40.1-40.4 and 26.5.1.5-6.

    Returns tau_v, tau_c, tau_c,max, strength-required spacing (inf if concrete alone suffices), the
    adopted spacing (strength, minimum-steel and cl. 26.5.1.5 limits, rounded down to ``sv_step``), and
    ``U_shear = max(tau_v / tau_c,max, sv_min / sv_strength)`` (>1 = infeasible: section crushing or
    stirrups would have to be closer than ``sv_min``).
    """
    fy_s = min(fy, fy_cap)
    Vu = Vu_kN * 1e3
    tau_v = Vu / (b * d)
    tau_c = t.tau_c_MPa(pt_percent, concrete)
    tau_max = t.tau_c_max_MPa(concrete)
    vus = Vu - tau_c * b * d
    sv_strength = math.inf if vus <= 0 else 0.87 * fy_s * Asv * d / vus
    sv_minsteel = 0.87 * fy_s * Asv / (k_min * b)            # Asv/(b sv) >= 0.4 / (0.87 fy)
    sv_limit = min(0.75 * d, 300.0)                           # cl. 26.5.1.5
    sv_adopt = min(sv_strength, sv_minsteel, sv_limit)
    sv_adopt = math.floor(sv_adopt / sv_step) * sv_step
    u_sv = 0.0 if math.isinf(sv_strength) else sv_min / sv_strength
    return {
        "tau_v": tau_v, "tau_c": tau_c, "tau_c_max": tau_max, "sv_strength_mm": sv_strength,
        "sv_mm": float(sv_adopt), "U_shear": max(tau_v / tau_max, u_sv),
    }


@dataclass(frozen=True)
class BeamCheck:
    """Result of checking one beam group against its design demands."""

    U_sag: float
    U_hog: float
    U_flex: float
    U_shear: float
    Mu_sag_kNm: float
    Mu_hog_kNm: float
    d_sag_mm: float
    d_hog_mm: float
    Ast_bot_mm2: float
    Ast_top_mm2: float
    sv_mm: float
    tau_v: float
    tau_c: float
    g_steel: float        # >0 = violation of Ast,min / Ast,max (worst of the four, normalised)
    pt_bot: float
    pt_top: float


def check_beam_group(sec: BeamSection, concrete: str, steel: str, M_sag_kNm: float, M_hog_kNm: float,
                     Vu_kN: float, cfg: config.DesignSpaceCfg | None = None, cap: float = 10.0) -> BeamCheck:
    """Check one beam group. ``M_hog_kNm`` is the hogging magnitude (>= 0)."""
    cfg = cfg or config.design_space()
    fck, fy = t.fck_MPa(concrete), t.fy_MPa(steel)
    bot = beam_layers(sec, cfg, top=False)
    top = beam_layers(sec, cfg, top=True)
    if bot is None or top is None:
        raise ValueError("beam bars do not fit; call design.geometric_feasibility.check_geometry first")
    b, D = float(sec.b_mm), float(sec.D_mm)
    Ast_b = sec.bot_n * dt.bar_area_mm2(sec.bot_dia_mm)
    Ast_t = sec.top_n * dt.bar_area_mm2(sec.top_dia_mm)
    d_sag, d_hog = D - bot.y_centroid_mm, D - top.y_centroid_mm
    Mu_sag = flexural_capacity_Nmm(b, d_sag, top.y_centroid_mm, Ast_b, Ast_t, fck, fy, steel) / 1e6
    Mu_hog = flexural_capacity_Nmm(b, d_hog, bot.y_centroid_mm, Ast_t, Ast_b, fck, fy, steel) / 1e6
    u_sag = M_sag_kNm / Mu_sag if Mu_sag > 0 else cap
    u_hog = M_hog_kNm / Mu_hog if Mu_hog > 0 else cap

    pt_top = 100.0 * Ast_t / (b * d_hog)
    pt_bot = 100.0 * Ast_b / (b * d_sag)
    asv = cfg.beam.stirrup_legs * dt.bar_area_mm2(cfg.beam.stirrup_dia_mm)
    sh = shear_design(Vu_kN, b, d_hog, pt_top, asv, concrete, fy, cfg.beam.stirrup_spacing_step_mm,
                      cfg.beam.stirrup_spacing_min_mm, cfg.detailing.min_stirrup_ratio_k,
                      cfg.detailing.stirrup_fy_cap_MPa)

    ast_min_b, ast_min_t = 0.85 * b * d_sag / fy, 0.85 * b * d_hog / fy        # cl. 26.5.1.1 (a)
    ast_max = cfg.detailing.beam_pt_max_percent / 100.0 * b * D                # cl. 26.5.1.1 (b)
    g_steel = max(ast_min_b / Ast_b - 1.0, ast_min_t / Ast_t - 1.0, Ast_b / ast_max - 1.0, Ast_t / ast_max - 1.0)
    return BeamCheck(
        U_sag=min(u_sag, cap), U_hog=min(u_hog, cap), U_flex=min(max(u_sag, u_hog), cap),
        U_shear=min(sh["U_shear"], cap), Mu_sag_kNm=Mu_sag, Mu_hog_kNm=Mu_hog, d_sag_mm=d_sag, d_hog_mm=d_hog,
        Ast_bot_mm2=Ast_b, Ast_top_mm2=Ast_t, sv_mm=sh["sv_mm"], tau_v=sh["tau_v"], tau_c=sh["tau_c"],
        g_steel=g_steel, pt_bot=pt_bot, pt_top=pt_top,
    )
