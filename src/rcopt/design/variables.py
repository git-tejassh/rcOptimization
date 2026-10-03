"""Design variables, genome encoding and decoding (project.md 5).

A genome is a vector of integer indices into the option lists of ``config/design_space.yaml``. Layout::

    per beam group  g : B{g}_b, B{g}_D, B{g}_bd, B{g}_bn, B{g}_td, B{g}_tn
    per column group g: C{g}_b, C{g}_D, C{g}_dia, C{g}_n
    global            : fck, fy

Units: mm and MPa everywhere in this module (``_mm`` / ``_MPa`` suffixes).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from rcopt import config

BEAM_GENES = ("b", "D", "bd", "bn", "td", "tn")
COL_GENES = ("b", "D", "dia", "n")


@dataclass(frozen=True)
class BeamSection:
    """One beam group: rectangular b x D with bottom/top bars (diameter, count)."""

    b_mm: int
    D_mm: int
    bot_dia_mm: int
    bot_n: int
    top_dia_mm: int
    top_n: int


@dataclass(frozen=True)
class ColumnSection:
    """One column group: rectangular b x D (D >= b) with symmetric perimeter bars."""

    b_mm: int
    D_mm: int
    dia_mm: int
    n: int


@dataclass(frozen=True)
class Design:
    """A decoded, buildable design."""

    beams: tuple[BeamSection, ...]
    columns: tuple[ColumnSection, ...]
    concrete: str
    steel: str
    fck_MPa: float
    fy_MPa: float

    def size_key(self) -> tuple:
        """Everything the elastic FE response depends on (sizes + concrete grade; NOT reinforcement)."""
        return (
            tuple((b.b_mm, b.D_mm) for b in self.beams),
            tuple((c.b_mm, c.D_mm) for c in self.columns),
            self.concrete,
        )


class DesignSpace:
    """Option lists + genome <-> Design mapping."""

    def __init__(self, cfg: config.DesignSpaceCfg | None = None, geom: config.GeometryCfg | None = None):
        self.cfg = cfg or config.design_space()
        self.geom = geom or config.geometry()
        self.n_bg = len(self.geom.beam_groups)
        self.n_cg = len(self.geom.column_groups)
        bs, cs, gs = self.cfg.beam, self.cfg.column, self.cfg.global_
        t = config.load_dict("is456_tables")
        self.fck_of = t["concrete"]["fck_MPa"]
        self.fy_of = t["steel"]["fy_MPa"]
        names: list[str] = []
        options: list[list] = []
        for g in range(self.n_bg):
            for gene, opts in zip(
                BEAM_GENES,
                (bs.b_mm, bs.D_mm, bs.bottom_bar_dia_mm, bs.bar_count, bs.top_bar_dia_mm, bs.bar_count),
                strict=True,
            ):
                names.append(f"B{g}_{gene}")
                options.append(list(opts))
        for g in range(self.n_cg):
            for gene, opts in zip(COL_GENES, (cs.b_mm, cs.D_mm, cs.bar_dia_mm, cs.bar_count), strict=True):
                names.append(f"C{g}_{gene}")
                options.append(list(opts))
        names += ["fck", "fy"]
        options += [list(gs.concrete_grade), list(gs.steel_grade)]
        self.gene_names: tuple[str, ...] = tuple(names)
        self.options: tuple[tuple, ...] = tuple(tuple(o) for o in options)
        self.n_options = np.array([len(o) for o in options], dtype=int)
        self.n_genes = len(names)
        self._index = {n: i for i, n in enumerate(names)}

    # ------------------------------------------------------------------ encode / decode
    def decode(self, genome) -> Design:
        """Genome (integer indices) -> Design. Raises ValueError for out-of-range indices."""
        g = [int(x) for x in genome]
        if len(g) != self.n_genes:
            raise ValueError(f"genome length {len(g)} != {self.n_genes}")
        for i, (v, n) in enumerate(zip(g, self.n_options, strict=True)):
            if not 0 <= v < n:
                raise ValueError(f"gene {self.gene_names[i]}={v} outside 0..{n - 1}")
        val = [self.options[i][v] for i, v in enumerate(g)]
        k = 0
        beams = []
        for _ in range(self.n_bg):
            beams.append(BeamSection(*val[k:k + 6]))
            k += 6
        cols = []
        for _ in range(self.n_cg):
            cols.append(ColumnSection(*val[k:k + 4]))
            k += 4
        conc, steel = val[k], val[k + 1]
        fck, fy = float(self.fck_of[conc]), float(self.fy_of[steel])
        return Design(tuple(beams), tuple(cols), conc, steel, fck, fy)

    def encode(self, design: Design) -> np.ndarray:
        """Design -> genome (inverse of ``decode``; ValueError if a value is not an option)."""
        vals: list = []
        for b in design.beams:
            vals += [b.b_mm, b.D_mm, b.bot_dia_mm, b.bot_n, b.top_dia_mm, b.top_n]
        for c in design.columns:
            vals += [c.b_mm, c.D_mm, c.dia_mm, c.n]
        vals += [design.concrete, design.steel]
        return np.array([self.options[i].index(v) for i, v in enumerate(vals)], dtype=int)

    def physical(self, genome) -> np.ndarray:
        """Numeric physical value of every gene (grades -> fck / fy in MPa)."""
        out = np.empty(self.n_genes)
        for i, v in enumerate(genome):
            opt = self.options[i][int(v)]
            if self.gene_names[i] == "fck":
                opt = self.fck_of[opt]
            elif self.gene_names[i] == "fy":
                opt = self.fy_of[opt]
            out[i] = opt
        return out

    def gene_index(self, name: str) -> int:
        return self._index[name]

    def random_genomes(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Uniform random genomes (n x n_genes)."""
        return np.column_stack([rng.integers(0, k, size=n) for k in self.n_options])

    def total_combinations(self) -> int:
        out = 1
        for k in self.n_options:
            out *= int(k)
        return out


@lru_cache(maxsize=None)
def default_space() -> DesignSpace:
    return DesignSpace()
