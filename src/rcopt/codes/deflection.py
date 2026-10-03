"""Span / effective-depth deflection check, IS 456 cl. 23.2.1 (DIAGNOSTIC only).

The hard deflection constraint of the pipeline is the FE value delta <= L/250 (project.md 6.3). This module
gives the code's independent span/depth cross-check. Fig. 4 / Fig. 5 modification factors are approximated by
the BS 8110-type fits  MF_t = 1 / (0.225 + 0.00322 fs - 0.625 log10(pt)) <= 2.0  and
MF_c = 1 + pc / (3 + pc) <= 1.5 (docs/ASSUMPTIONS.md A12: owner must verify against the printed figures).
"""
from __future__ import annotations

import math

from rcopt.codes import is456_tables as t


def mf_tension(fs_MPa: float, pt_percent: float) -> float:
    """Modification factor for tension reinforcement (Fig. 4), capped at 2.0."""
    pt = max(pt_percent, 0.05)
    return min(2.0, 1.0 / (0.225 + 0.00322 * fs_MPa - 0.625 * math.log10(pt)))


def mf_compression(pc_percent: float) -> float:
    """Modification factor for compression reinforcement (Fig. 5), capped at 1.5."""
    return min(1.5, 1.0 + pc_percent / (3.0 + pc_percent))


def span_depth_ratio_check(span_mm: float, d_mm: float, fy: float, pt_percent: float, pc_percent: float,
                           util_flex: float, kind: str = "continuous") -> dict:
    """Allowable vs actual L/d. ``fs = 0.58 fy (Ast_req / Ast_prov)`` with Ast_req/Ast_prov ~ utilisation."""
    basic = t.tables()["span_depth_basic"][kind]
    fs = 0.58 * fy * min(max(util_flex, 0.05), 1.0)
    allow = basic * mf_tension(fs, pt_percent) * mf_compression(pc_percent)
    actual = span_mm / d_mm
    return {"allowable": allow, "actual": actual, "ratio": actual / allow}
