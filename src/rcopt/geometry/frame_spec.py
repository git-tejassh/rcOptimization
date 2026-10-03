"""Parametric regular-frame description (project.md 4.1-4.2).

Nodes are numbered level by level (level 0 = plinth, y = 0) and the fixed base nodes (y = -stub) last.
Units: m.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rcopt import config


@dataclass(frozen=True)
class Member:
    id: int
    kind: str            # 'bx' | 'bz' | 'col' | 'stub'
    n1: int
    n2: int
    level: int           # beam: level index 0..n ; col: storey index 0..n-1 ; stub: 0
    group: int           # beam group (beams) or column group (columns / stubs)
    length_m: float
    perimeter: bool      # beams only
    i: int               # grid index along the beam (bx: bay index in x, bz: bay index in z; col: ix)
    j: int               # grid line index (bx: z line, bz: x line; col: iz)


@dataclass
class FrameSpec:
    xs: list[float]
    zs: list[float]
    ys: list[float]                      # level elevations, ys[0] = 0 (plinth)
    stub_m: float
    storey_h: list[float]
    nodes: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    members: list[Member] = field(default_factory=list)
    beam_group_of_level: dict[int, int] = field(default_factory=dict)
    col_group_of_storey: dict[int, int] = field(default_factory=dict)
    column_D_axis: str = "x"

    @property
    def nx(self) -> int:
        return len(self.xs)

    @property
    def nz(self) -> int:
        return len(self.zs)

    @property
    def n_levels(self) -> int:
        return len(self.ys)

    @property
    def n_storeys(self) -> int:
        return len(self.ys) - 1

    def node(self, level: int, ix: int, iz: int) -> int:
        return 1 + level * self.nx * self.nz + iz * self.nx + ix

    def base_node(self, ix: int, iz: int) -> int:
        return 1 + self.n_levels * self.nx * self.nz + iz * self.nx + ix

    def base_nodes(self) -> list[int]:
        return [self.base_node(ix, iz) for iz in range(self.nz) for ix in range(self.nx)]

    def by_kind(self, *kinds: str) -> list[Member]:
        return [m for m in self.members if m.kind in kinds]


def build_frame(geom: config.GeometryCfg | None = None) -> FrameSpec:
    """Build the FrameSpec described by ``config/geometry.yaml``."""
    g = geom or config.geometry()
    xs = [0.0]
    for bay in g.bays_x_m:
        xs.append(xs[-1] + bay)
    zs = [0.0]
    for bay in g.bays_z_m:
        zs.append(zs[-1] + bay)
    ys = [0.0]
    for h in g.storey_heights_m:
        ys.append(ys[-1] + h)
    fs = FrameSpec(xs, zs, ys, g.stub_height_m, list(g.storey_heights_m), column_D_axis=g.column_D_axis)
    fs.beam_group_of_level = {lv: gi for gi, grp in enumerate(g.beam_groups) for lv in grp}
    fs.col_group_of_storey = {s: gi for gi, grp in enumerate(g.column_groups) for s in grp}

    for lv in range(fs.n_levels):
        for iz in range(fs.nz):
            for ix in range(fs.nx):
                fs.nodes[fs.node(lv, ix, iz)] = (xs[ix], ys[lv], zs[iz])
    for iz in range(fs.nz):
        for ix in range(fs.nx):
            fs.nodes[fs.base_node(ix, iz)] = (xs[ix], -fs.stub_m, zs[iz])

    mid = 0

    def add(kind, n1, n2, level, group, length, perim, i, j):
        nonlocal mid
        mid += 1
        fs.members.append(Member(mid, kind, n1, n2, level, group, length, perim, i, j))

    for lv in range(fs.n_levels):
        grp = fs.beam_group_of_level[lv]
        for iz in range(fs.nz):
            for ix in range(fs.nx - 1):
                perim = iz in (0, fs.nz - 1)
                add("bx", fs.node(lv, ix, iz), fs.node(lv, ix + 1, iz), lv, grp, xs[ix + 1] - xs[ix], perim, ix, iz)
        for ix in range(fs.nx):
            for iz in range(fs.nz - 1):
                perim = ix in (0, fs.nx - 1)
                add("bz", fs.node(lv, ix, iz), fs.node(lv, ix, iz + 1), lv, grp, zs[iz + 1] - zs[iz], perim, iz, ix)
    for s in range(fs.n_storeys):
        grp = fs.col_group_of_storey[s]
        for iz in range(fs.nz):
            for ix in range(fs.nx):
                add("col", fs.node(s, ix, iz), fs.node(s + 1, ix, iz), s, grp, fs.storey_h[s], False, ix, iz)
    for iz in range(fs.nz):
        for ix in range(fs.nx):
            add("stub", fs.base_node(ix, iz), fs.node(0, ix, iz), 0, fs.col_group_of_storey[0], fs.stub_m, False, ix, iz)
    return fs
