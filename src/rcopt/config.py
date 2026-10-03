"""Validated YAML config loaders and config hashing.

All tunables live in ``config/*.yaml`` (CLAUDE.md prime directive 4). Loaders return pydantic models for the
structural sections (geometry, loads, design space) and validated plain dicts for the rest.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ----------------------------------------------------------------------------- geometry
class GeometryCfg(_Strict):
    source: str = "config"
    staad_file: str
    bays_x_m: list[float]
    bays_z_m: list[float]
    storey_heights_m: list[float]
    stub_height_m: float
    beam_groups: list[list[int]]
    column_groups: list[list[int]]
    column_D_axis: str = "x"

    @model_validator(mode="after")
    def _check_groups(self) -> GeometryCfg:
        n_levels = len(self.storey_heights_m) + 1
        n_storeys = len(self.storey_heights_m)
        if sorted(i for g in self.beam_groups for i in g) != list(range(n_levels)):
            raise ValueError(f"beam_groups must partition levels 0..{n_levels - 1}")
        if sorted(i for g in self.column_groups for i in g) != list(range(n_storeys)):
            raise ValueError(f"column_groups must partition storeys 0..{n_storeys - 1}")
        if self.column_D_axis not in ("x", "z"):
            raise ValueError("column_D_axis must be 'x' or 'z'")
        return self


# ----------------------------------------------------------------------------- loads
class SlabCfg(_Strict):
    thickness_mm: float
    finish_kNm2: float
    roof_finish_kNm2: float


class WallCfg(_Strict):
    perimeter_thickness_m: float
    interior_thickness_m: float
    unit_weight_kNm3: float
    height_from_beam_depth: bool
    fixed_perimeter_kNm: float
    fixed_interior_kNm: float
    apply_at_roof: bool


class LiveCfg(_Strict):
    floor_kNm2: float
    roof_kNm2: float


class LoadsCfg(_Strict):
    unit_weight_rc_kNm3: float
    slab: SlabCfg
    wall: WallCfg
    live: LiveCfg
    combinations: dict[str, dict[str, float]]


# ----------------------------------------------------------------------------- design space
class BeamSpace(_Strict):
    b_mm: list[int]
    D_mm: list[int]
    bottom_bar_dia_mm: list[int]
    top_bar_dia_mm: list[int]
    bar_count: list[int]
    stirrup_dia_mm: int
    stirrup_legs: int
    stirrup_spacing_step_mm: int
    stirrup_spacing_min_mm: int
    max_layers: int


class ColumnSpace(_Strict):
    b_mm: list[int]
    D_mm: list[int]
    bar_dia_mm: list[int]
    bar_count: list[int]
    tie_dia_min_mm: int


class GlobalSpace(_Strict):
    concrete_grade: list[str]
    steel_grade: list[str]


class CoverCfg(_Strict):
    exposure: str
    beam: float
    column: float


class DetailingCfg(_Strict):
    aggregate_size_mm: float
    min_clear_spacing_mm: float
    min_clear_vertical_mm: float
    beam_pt_max_percent: float
    column_pt_min_percent: float
    column_pt_max_percent: float
    column_pt_abs_max_percent: float
    column_clear_spacing_max_mm: float
    min_stirrup_ratio_k: float
    stirrup_fy_cap_MPa: float
    beam_b_le_column_b: bool


class DesignSpaceCfg(_Strict):
    repair: bool = True
    beam: BeamSpace
    column: ColumnSpace
    global_: GlobalSpace = Field(alias="global")
    cover_mm: CoverCfg
    detailing: DetailingCfg

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _sorted(self) -> DesignSpaceCfg:
        for name, lst in {
            "beam.b_mm": self.beam.b_mm, "beam.D_mm": self.beam.D_mm,
            "beam.bar_count": self.beam.bar_count, "column.b_mm": self.column.b_mm,
            "column.D_mm": self.column.D_mm, "column.bar_dia_mm": self.column.bar_dia_mm,
            "column.bar_count": self.column.bar_count,
        }.items():
            if lst != sorted(set(lst)):
                raise ValueError(f"{name} must be strictly increasing")
        if any(c % 2 or c < 4 for c in self.column.bar_count):
            raise ValueError("column.bar_count must be even and >= 4 (symmetric rectangular layout)")
        return self


# ----------------------------------------------------------------------------- loaders
def _read(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=None)
def load_dict(name: str) -> dict[str, Any]:
    """Raw dict of ``config/<name>.yaml`` (cached; treat as read-only)."""
    return _read(name)


@lru_cache(maxsize=None)
def geometry() -> GeometryCfg:
    return GeometryCfg(**_read("geometry"))


@lru_cache(maxsize=None)
def loads() -> LoadsCfg:
    return LoadsCfg(**_read("loads"))


@lru_cache(maxsize=None)
def design_space() -> DesignSpaceCfg:
    return DesignSpaceCfg(**_read("design_space"))


def config_hash(names: tuple[str, ...] | None = None) -> str:
    """Stable SHA-256 (first 16 hex chars) over the named YAML files (default: all)."""
    files = sorted(CONFIG_DIR.glob("*.yaml")) if names is None else [CONFIG_DIR / f"{n}.yaml" for n in names]
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode())
        h.update(json.dumps(yaml.safe_load(f.read_text(encoding="utf-8")), sort_keys=True).encode())
    return h.hexdigest()[:16]


def provisional_items() -> list[str]:
    """Dotted names of every config value flagged ``status: provisional`` (drives UI/report banners)."""
    out: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("status") == "provisional":
                out.append(path)
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))

    for name in ("cost_rates", "carbon_factors", "is456_tables"):
        walk(_read(name), name)
    return out
