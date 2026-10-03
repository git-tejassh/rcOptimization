"""Process-local rate/factor scenario for the +/-20 % sensitivity study (project.md 9.5)."""
from __future__ import annotations

from contextlib import contextmanager

_ACTIVE: dict[str, float] = {}


def active() -> dict[str, float]:
    """Currently active scale factors: steel_cost_scale, cement_carbon_scale, steel_carbon_scale (default 1.0)."""
    return _ACTIVE


@contextmanager
def scenario(**scales: float):
    """``with scenario(steel_cost_scale=1.2): ...`` applies to every cost / carbon evaluation in this process."""
    old = dict(_ACTIVE)
    _ACTIVE.update(scales)
    try:
        yield
    finally:
        _ACTIVE.clear()
        _ACTIVE.update(old)


def set_scenario(scales: dict[str, float] | None) -> None:
    """Replace the active scenario (used at worker start-up)."""
    _ACTIVE.clear()
    _ACTIVE.update(scales or {})
