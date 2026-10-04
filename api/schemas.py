"""Pydantic request / response models of the local API (project.md 11.4)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenomeIn(BaseModel):
    """A design as integer indices into the option lists of ``config/design_space.yaml`` (22 genes by default)."""

    genome: list[int] = Field(..., description="gene indices, in the order of GET /design-space -> genes")


class SurrogateOut(BaseModel):
    U_flex_max: float
    U_shear_max: float
    U_col_max: float
    defl_ratio_max: float
    cost: float
    carbon: float
    feasible: bool
    g: list[float]


class SurrogateResponse(BaseModel):
    repaired_genome: list[int]
    A: SurrogateOut
    B: SurrogateOut
    note: str = "feasible = all seven constraints <= 0 as predicted; gravity-only IS 456 check"


class CostCarbonResponse(BaseModel):
    repaired_genome: list[int]
    status: str
    quantities: dict | None = None
    cost_inr: dict | None = None
    carbon_kgco2e: dict | None = None
    provisional: bool = True


class ReviewIn(BaseModel):
    """STAAD input text plus the materials to design with."""

    text: str = Field(..., description="contents of the STAAD .std input file")
    concrete: str = "M30"
    steel: str = "Fe500"
    cement: str = "PPC"
