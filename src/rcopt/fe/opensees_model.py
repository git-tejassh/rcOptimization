"""OpenSeesPy 3D elastic frame: model build + linear static solve of several load cases.

Units here: kN, m (E in kN/m2). One ``elasticBeamColumn`` element per member. Local axes: for beams the
section depth D lies along local z = global Y (vecxz = up); for columns local z lies along the column D
axis (``column_D_axis``). Slab / wall / self-weight loads arrive as equivalent nodal loads (fixed-end forces),
so element forces from OpenSees are ``k u``; the caller adds the fixed-end reactions (see ``analysis``).
OpenSees keeps global state: always call ``solve_cases`` inside one process at a time (each worker owns its model).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import openseespy.opensees as ops

from rcopt.geometry.frame_spec import FrameSpec


@dataclass(frozen=True)
class ElementProps:
    """Per-element section data (m, m2, m4, kN/m2)."""

    A: float
    Iy: float
    Iz: float
    J: float
    E: float
    G: float


def rect_props(b_m: float, D_m: float, E: float, nu: float, stiff_factor: float) -> ElementProps:
    """Rectangle b x D (D along local z). Iy = b D^3/12, Iz = D b^3/12; J (Roark) and Iy, Iz scaled by factor."""
    lo, hi = min(b_m, D_m), max(b_m, D_m)
    J = hi * lo**3 * (1.0 / 3.0 - 0.21 * (lo / hi) * (1.0 - lo**4 / (12.0 * hi**4)))
    return ElementProps(
        A=b_m * D_m, Iy=stiff_factor * b_m * D_m**3 / 12.0, Iz=stiff_factor * D_m * b_m**3 / 12.0,
        J=stiff_factor * J, E=E, G=E / (2.0 * (1.0 + nu)),
    )


@dataclass
class Solution:
    """Result of one load case: element end forces (global, on the element) and node displacements."""

    ef: dict[int, np.ndarray]      # element id -> 12-vector [Fx,Fy,Fz,Mx,My,Mz] at node i then node j
    disp: dict[int, np.ndarray]    # node id -> 6-vector
    reaction_sum: np.ndarray       # sum of base reactions (6)
    reactions: dict[int, np.ndarray] = None   # base node id -> reaction (6)
    ok: bool = True


def solve_cases(frame: FrameSpec, props: dict[int, ElementProps],
                cases: dict[str, dict[int, np.ndarray]], shear_deformation: bool = False) -> dict[str, Solution]:
    """Build the model once and solve each nodal-load case (``node id -> 6-vector``) linearly."""
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    for nid, (x, y, z) in frame.nodes.items():
        ops.node(nid, x, y, z)
    for nid in frame.base_nodes():
        ops.fix(nid, 1, 1, 1, 1, 1, 1)
    ops.geomTransf("Linear", 1, 0.0, 1.0, 0.0)
    ops.geomTransf("Linear", 2, *((1.0, 0.0, 0.0) if frame.column_D_axis == "x" else (0.0, 0.0, 1.0)))
    for m in frame.members:
        p = props[m.id]
        tr = 1 if m.kind in ("bx", "bz") else 2
        if shear_deformation:      # Timoshenko: shear area 5/6 A (rectangle), as STAAD includes shear deformation
            ops.element("ElasticTimoshenkoBeam", m.id, m.n1, m.n2, p.E, p.G, p.A, p.J, p.Iy, p.Iz,
                        5.0 / 6.0 * p.A, 5.0 / 6.0 * p.A, tr)
        else:
            ops.element("elasticBeamColumn", m.id, m.n1, m.n2, p.A, p.E, p.G, p.J, p.Iy, p.Iz, tr)
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr", 1e-8, 5)
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0)
    ops.analysis("Static")

    out: dict[str, Solution] = {}
    for k, (name, loads) in enumerate(cases.items(), start=1):
        ops.timeSeries("Constant", k)
        ops.pattern("Plain", k, k)
        for nid, f in loads.items():
            if np.any(f):
                ops.load(nid, *[float(v) for v in f])
        ok = ops.analyze(1) == 0
        ef = {m.id: np.array(ops.eleResponse(m.id, "globalForce")) for m in frame.members}
        disp = {nid: np.array(ops.nodeDisp(nid)) for nid in frame.nodes}
        ops.reactions()
        react = {nid: np.array(ops.nodeReaction(nid)) for nid in frame.base_nodes()}
        out[name] = Solution(ef, disp, np.sum(list(react.values()), axis=0), react, ok)
        ops.remove("loadPattern", k)
        ops.remove("timeSeries", k)
        ops.reset()
    ops.wipe()
    return out
