"""Bar layout and fit rules (IS 456 cl. 26.3.2 spacing, cl. 26.4 cover, cl. 26.5.3 columns).

Units: mm. Layouts are deterministic so the FE check, the optimizer and the verifier see the same bars.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

AREA_FACTOR = math.pi / 4.0


def bar_area_mm2(dia_mm: float) -> float:
    return AREA_FACTOR * dia_mm * dia_mm


def min_clear_spacing_mm(dia_mm: float, aggregate_mm: float, practical_min_mm: float) -> float:
    """IS 456 cl. 26.3.2: clear spacing >= max(bar dia, aggregate + 5 mm); plus a practical floor."""
    return max(dia_mm, aggregate_mm + 5.0, practical_min_mm)


@dataclass(frozen=True)
class BeamLayer:
    """Result of laying out ``n`` bars of one diameter in a beam face."""

    counts: tuple[int, ...]      # bars per layer (outermost first)
    y_centroid_mm: float          # distance from the extreme (cover) face to the bar centroid


def beam_bar_layers(
    b_mm: float, n: int, dia_mm: float, cover_mm: float, stirrup_dia_mm: float,
    aggregate_mm: float, practical_min_mm: float, vertical_min_mm: float, max_layers: int,
) -> BeamLayer | None:
    """Lay ``n`` bars in layers of a beam of width ``b``. ``None`` if more than ``max_layers`` are needed.

    Bars per layer: floor((b - 2(c + st) + s) / (dia + s)) with s the minimum clear spacing.
    Layer 2 sits ``dia + max(dia, vertical_min)`` above layer 1.
    """
    s = min_clear_spacing_mm(dia_mm, aggregate_mm, practical_min_mm)
    avail = b_mm - 2.0 * (cover_mm + stirrup_dia_mm)
    n_max = int(math.floor((avail + s) / (dia_mm + s)))
    if n_max < 2:
        return None
    counts: list[int] = []
    left = n
    for _ in range(max_layers):
        take = min(left, n_max)
        counts.append(take)
        left -= take
        if left == 0:
            break
    if left > 0:
        return None
    y1 = cover_mm + stirrup_dia_mm + dia_mm / 2.0
    pitch = dia_mm + max(dia_mm, vertical_min_mm)
    y_c = sum(c * (y1 + i * pitch) for i, c in enumerate(counts)) / n
    return BeamLayer(tuple(counts), y_c)


def column_layout(count: int) -> tuple[int, int]:
    """(n_b, n_D): bars across the b-face and along the D-face, 2(n_b + n_D) - 4 = count, n_D >= n_b."""
    s = count // 2 + 2
    n_b = s // 2
    return n_b, s - n_b


@dataclass(frozen=True)
class ColumnLayers:
    """Bar rows for bending with strain varying over depth ``H`` (rows run parallel to the neutral axis)."""

    y_mm: np.ndarray       # row positions measured from the compression face
    area_mm2: np.ndarray   # steel area in each row
    H_mm: float
    W_mm: float


def column_layers(b_mm: float, D_mm: float, dia_mm: float, count: int, cover_mm: float, tie_dia_mm: float,
                  about: str) -> ColumnLayers:
    """Rows for bending about ``'x'`` (strain varies over D) or ``'y'`` (strain varies over b)."""
    n_b, n_D = column_layout(count)
    if about == "x":
        H, W, n_H, n_W = D_mm, b_mm, n_D, n_b
    elif about == "y":
        H, W, n_H, n_W = b_mm, D_mm, n_b, n_D
    else:
        raise ValueError("about must be 'x' or 'y'")
    c = cover_mm + tie_dia_mm + dia_mm / 2.0
    y = c + np.arange(n_H) * (H - 2.0 * c) / (n_H - 1)
    cnt = np.full(n_H, 2.0)
    cnt[0] = cnt[-1] = n_W
    return ColumnLayers(y, cnt * bar_area_mm2(dia_mm), H, W)


def column_clear_spacings_mm(b_mm: float, D_mm: float, dia_mm: float, count: int, cover_mm: float,
                             tie_dia_mm: float) -> tuple[float, float]:
    """Clear spacing between adjacent bars along the b-face and the D-face."""
    n_b, n_D = column_layout(count)
    c = cover_mm + tie_dia_mm + dia_mm / 2.0
    sb = (b_mm - 2 * c) / (n_b - 1) - dia_mm
    sD = (D_mm - 2 * c) / (n_D - 1) - dia_mm
    return sb, sD
