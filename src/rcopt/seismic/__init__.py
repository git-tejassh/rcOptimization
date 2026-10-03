"""Phase 6 stub: seismic design hook (interfaces only; NO seismic results are produced or claimed).

See docs/SEISMIC_EXTENSION.md for what would change. Every function raises ``NotImplementedError`` on purpose so that
nothing can silently pretend to be seismic design.
"""
from __future__ import annotations

from dataclasses import dataclass

MESSAGE = (
    "Seismic design (IS 1893:2016 / IS 13920:2016) is deliberately out of scope: this project is gravity-only (brief s5). "
    "See docs/SEISMIC_EXTENSION.md."
)


@dataclass(frozen=True)
class SeismicSpec:
    """Inputs an equivalent-static seismic extension would need (IS 1893 (Part 1):2016)."""

    zone_factor_Z: float             # Table 3 (confirm the zone for the site from the code)
    importance_factor_I: float       # Table 8
    response_reduction_R: float      # Table 9 (e.g. SMRF 5.0)
    soil_type: str                   # I / II / III (Table 4 spectra)
    damping_ratio: float = 0.05


def base_shear_equivalent_static(spec: SeismicSpec, seismic_weight_kN: float, period_s: float) -> float:
    """Design base shear Vb = Ah W with Ah = (Z/2)(I/R)(Sa/g) (IS 1893 cl. 6.4.2). Not implemented."""
    raise NotImplementedError(MESSAGE)


def seismic_load_combinations() -> list[dict[str, float]]:
    """1.2 (DL + LL +/- EL), 1.5 (DL +/- EL), 0.9 DL +/- 1.5 EL (IS 456 Table 18 / IS 1893 cl. 6.3.4). Not implemented."""
    raise NotImplementedError(MESSAGE)


def check_ductile_detailing(design, demands) -> dict:
    """IS 13920:2016 checks (strong-column/weak-beam, confinement, drift <= 0.004 h). Not implemented."""
    raise NotImplementedError(MESSAGE)
