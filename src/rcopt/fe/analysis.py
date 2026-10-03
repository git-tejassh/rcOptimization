"""Gravity analysis of the frame and extraction of design demands (project.md 4.3, 6.4).

Pipeline for one set of member sizes (the only FE inputs besides fck - reinforcement does not enter an elastic
analysis, which is why the FE result is cached by ``FEInput.key()``):

1. member section properties (cracked modifiers) and E = 5000 sqrt(fck);
2. loads: beam self-weight + wall (UDL) + slab (two-way yield-line triangles / trapezoids ``w min(x, L-x, s/2)``),
   column self-weight; applied as equivalent nodal loads (fixed-end forces, trapezoidal quadrature);
3. two linear cases (DL, LL) solved in OpenSees; member end forces = k u + fixed-end reactions;
4. combinations from config (strength 1.5(DL+LL), service 1.0(DL+LL)); beam M(x), V(x), chord-relative deflection
   by statics and curvature integration; column Pu, MD, Mb.

Units: kN, m internally; demands reported in kN, kN.m, mm.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from rcopt import config
from rcopt.fe.opensees_model import ElementProps, rect_props, solve_cases
from rcopt.geometry.frame_spec import FrameSpec, build_frame

N_GRID = 201
_FRAME: list = []


def default_frame() -> FrameSpec:
    """Frame of config/geometry.yaml (built once per process)."""
    if not _FRAME:
        _FRAME.append(build_frame())
    return _FRAME[0]


XI = np.linspace(0.0, 1.0, N_GRID)


@dataclass(frozen=True)
class FEInput:
    """Everything the elastic response depends on."""

    beam_sizes_mm: tuple[tuple[int, int], ...]     # (b, D) per beam group
    col_sizes_mm: tuple[tuple[int, int], ...]      # (b, D) per column group
    fck_MPa: float

    @staticmethod
    def from_design(design) -> FEInput:
        return FEInput(tuple((b.b_mm, b.D_mm) for b in design.beams),
                       tuple((c.b_mm, c.D_mm) for c in design.columns), design.fck_MPa)

    def key(self) -> tuple:
        return (self.beam_sizes_mm, self.col_sizes_mm, self.fck_MPa)


@dataclass(frozen=True)
class FESettings:
    """Material / stiffness / load conventions (design mode or STAAD-matching benchmark mode)."""

    E_kNm2: float | None          # None -> 5000 sqrt(fck)
    poisson: float
    beam_factor: float
    col_factor: float
    unit_weight_kNm3: float
    wall_fixed: bool              # True: STAAD's fixed wall loads; False: follow beam depth
    wall_perimeter_kNm: float
    wall_interior_kNm: float
    ec_factor: float = 5000.0
    shear_deformation: bool = False
    wall_ecc_m: float = 0.0       # STAAD member-load offset d3 (benchmark only): torque = w * ecc about the beam axis

    @staticmethod
    def design() -> FESettings:
        s, l = config.load_dict("solver")["fe"], config.loads()
        return FESettings(None, s["poisson"], s["beam_stiffness_factor"], s["column_stiffness_factor"],
                          l.unit_weight_rc_kNm3, not l.wall.height_from_beam_depth, l.wall.fixed_perimeter_kNm,
                          l.wall.fixed_interior_kNm, s["ec_factor"], s["shear_deformation"])

    @staticmethod
    def benchmark() -> FESettings:
        b, l = config.load_dict("solver")["benchmark"], config.loads()
        return FESettings(b["E_kNm2"], b["poisson"], b["beam_stiffness_factor"], b["column_stiffness_factor"],
                          b["density_kNm3"], True, l.wall.fixed_perimeter_kNm, l.wall.fixed_interior_kNm,
                          shear_deformation=b["shear_deformation"], wall_ecc_m=b["wall_eccentricity_m"])


@dataclass
class FEDemands:
    """Factored (strength) demands per group + service deflection, as stored in the dataset."""

    beam: np.ndarray                  # (n_bg, 3): Msag_kNm, Mhog_kNm, Vu_kN
    col_types: np.ndarray             # (n_storeys + 1, ncx, ncz, 4): (Pu_kN, MD_kNm, Mb_kNm, l_mm) per column position class
    col_all: list[np.ndarray]         # per column group (n_members, 4); not stored in the dataset
    defl_over_L: np.ndarray           # (n_bg,): max service delta / L per beam group
    defl_mm: float                    # max service deflection (mm)
    equilibrium_err: float
    beam_equil_err: float
    ok: bool = True
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def defl_max_over_L(self) -> float:
        return float(np.max(self.defl_over_L))


# ----------------------------------------------------------------------------- loads
def _panel_sides(fs: FrameSpec, m) -> list[float]:
    """Short-side lengths s of the slab panels adjacent to beam ``m`` (0, 1 or 2 values)."""
    out = []
    if m.kind == "bx":
        for jj in (m.j - 1, m.j):
            if 0 <= jj < fs.nz - 1:
                out.append(min(fs.xs[m.i + 1] - fs.xs[m.i], fs.zs[jj + 1] - fs.zs[jj]))
    else:
        for ii in (m.j - 1, m.j):
            if 0 <= ii < fs.nx - 1:
                out.append(min(fs.zs[m.i + 1] - fs.zs[m.i], fs.xs[ii + 1] - fs.xs[ii]))
    return out


def slab_q(x: np.ndarray, L: float, s: float, w: float) -> np.ndarray:
    """Yield-line tributary load on a beam of length L from a panel of short side s: w min(x, L-x, s/2)."""
    return w * np.minimum(np.minimum(x, L - x), s / 2.0)


def beam_load_profiles(fs: FrameSpec, beams: list, beam_sizes_mm, st: FESettings, lc: config.LoadsCfg):
    """(q_DL, q_LL) arrays (n_beams, N_GRID) in kN/m along each beam, and lengths L (n_beams,)."""
    n = len(beams)
    L = np.array([m.length_m for m in beams])
    x = L[:, None] * XI[None, :]
    q_dl = np.zeros((n, N_GRID))
    q_ll = np.zeros((n, N_GRID))
    wall_w = np.zeros(n)
    top = fs.n_levels - 1
    for k, m in enumerate(beams):
        b_mm, D_mm = beam_sizes_mm[m.group]
        b, D = b_mm / 1000.0, D_mm / 1000.0
        sw = st.unit_weight_kNm3 * b * D
        if m.level == top and not lc.wall.apply_at_roof:
            wall = 0.0
        elif st.wall_fixed:
            wall = st.wall_perimeter_kNm if m.perimeter else st.wall_interior_kNm
        else:
            h = fs.storey_h[min(m.level, fs.n_storeys - 1)]
            t = lc.wall.perimeter_thickness_m if m.perimeter else lc.wall.interior_thickness_m
            wall = t * max(h - D, 0.0) * lc.wall.unit_weight_kNm3
        q_dl[k] = sw + wall
        wall_w[k] = wall
        roof = m.level == top
        w_dl = lc.unit_weight_rc_kNm3 * lc.slab.thickness_mm / 1000.0 + (lc.slab.roof_finish_kNm2 if roof
                                                                          else lc.slab.finish_kNm2)
        w_ll = lc.live.roof_kNm2 if roof else lc.live.floor_kNm2
        for s in _panel_sides(fs, m):
            q_dl[k] += slab_q(x[k], L[k], s, w_dl)
            q_ll[k] += slab_q(x[k], L[k], s, w_ll)
    return q_dl, q_ll, L, wall_w


def fixed_end(q: np.ndarray, L: np.ndarray):
    """Fixed-end reactions (V_a, V_b, M_a, M_b; q downward positive, M magnitudes hogging) by trapezoid rule."""
    x = L[:, None] * XI[None, :]
    Lc = L[:, None]
    va = np.trapezoid(q * (Lc - x) ** 2 * (Lc + 2 * x) / Lc**3, x, axis=1)
    vb = np.trapezoid(q * x**2 * (3 * Lc - 2 * x) / Lc**3, x, axis=1)
    ma = np.trapezoid(q * x * (Lc - x) ** 2 / Lc**2, x, axis=1)
    mb = np.trapezoid(q * x**2 * (Lc - x) / Lc**2, x, axis=1)
    return va, vb, ma, mb


def _beam_axes(fs: FrameSpec, beams: list) -> np.ndarray:
    """h = e x u for each beam (CCW-in-vertical-plane rotation axis); memoised on the FrameSpec."""
    if hasattr(fs, "_beam_h"):
        return fs._beam_h
    fs._beam_h = _beam_axes_raw(fs, beams)
    return fs._beam_h


def _beam_axes_raw(fs: FrameSpec, beams: list) -> np.ndarray:
    h = np.zeros((len(beams), 3))
    for k, m in enumerate(beams):
        a, b = np.array(fs.nodes[m.n1]), np.array(fs.nodes[m.n2])
        e = (b - a) / np.linalg.norm(b - a)
        h[k] = np.cross(e, [0.0, 1.0, 0.0])
    return h


def _cumtrapz(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    out = np.zeros_like(y)
    out[:, 1:] = np.cumsum(0.5 * (y[:, 1:] + y[:, :-1]) * np.diff(x, axis=1), axis=1)
    return out


def beam_diagrams(L: np.ndarray, q: np.ndarray, Fa: np.ndarray, ma: np.ndarray):
    """Sagging-positive bending moment Ms(x) and shear V(x) along beams from the end-a actions and the load.

    Ms(x) = Fa x - ma - int_0^x q (x - s) ds ;  V(x) = Fa - int_0^x q ds   (Fa up, ma CCW, both on the element).
    """
    x = L[:, None] * XI[None, :]
    Q = _cumtrapz(q, x)
    return x, Fa[:, None] * x - ma[:, None] - _cumtrapz(Q, x), Fa[:, None] - Q


def beam_chord_deflection(x: np.ndarray, Ms: np.ndarray, EI: np.ndarray, v_a: np.ndarray, v_b: np.ndarray,
                          theta_a: np.ndarray):
    """Vertical displacement v(x) (up +) by double integration of M/EI and its deviation from the chord."""
    slope = theta_a[:, None] + _cumtrapz(Ms / EI[:, None], x)
    v = v_a[:, None] + _cumtrapz(slope, x)
    chord = v_a[:, None] + (v_b - v_a)[:, None] * XI[None, :]
    return v, v - chord


# ----------------------------------------------------------------------------- main entry
def analyze(fe_in: FEInput, fs: FrameSpec | None = None, st: FESettings | None = None,
            lc: config.LoadsCfg | None = None, keep_raw: bool = False) -> FEDemands:
    """Run the gravity FE for ``fe_in`` and return the design demands (see module docstring)."""
    fs = fs or default_frame()
    st = st or FESettings.design()
    lc = lc or config.loads()
    cfg_solver = config.load_dict("solver")
    E = st.E_kNm2 if st.E_kNm2 is not None else st.ec_factor * np.sqrt(fe_in.fck_MPa) * 1e3
    beams = fs.by_kind("bx", "bz")
    cols = fs.by_kind("col", "stub")

    props: dict[int, ElementProps] = {}
    for m in beams:
        b, D = fe_in.beam_sizes_mm[m.group]
        props[m.id] = rect_props(b / 1000.0, D / 1000.0, E, st.poisson, st.beam_factor)
    for m in cols:
        b, D = fe_in.col_sizes_mm[m.group]
        props[m.id] = rect_props(b / 1000.0, D / 1000.0, E, st.poisson, st.col_factor)

    q_dl, q_ll, L, wall_w = beam_load_profiles(fs, beams, fe_in.beam_sizes_mm, st, lc)
    h_axis = _beam_axes(fs, beams)
    fef = {}
    nodal = {"DL": {nid: np.zeros(6) for nid in fs.nodes}, "LL": {nid: np.zeros(6) for nid in fs.nodes}}
    for case, q in (("DL", q_dl), ("LL", q_ll)):
        va, vb, ma, mb = fixed_end(q, L)
        fef[case] = (va, vb, ma, mb)
        for k, m in enumerate(beams):
            nodal[case][m.n1][1] -= va[k]
            nodal[case][m.n2][1] -= vb[k]
            nodal[case][m.n1][3:6] -= ma[k] * h_axis[k]
            nodal[case][m.n2][3:6] += mb[k] * h_axis[k]
    if st.wall_ecc_m:
        for k, m in enumerate(beams):
            e = np.array(fs.nodes[m.n2]) - np.array(fs.nodes[m.n1])
            e /= np.linalg.norm(e)
            tq = st.wall_ecc_m * wall_w[k] * L[k] / 2.0 * e      # torque of the eccentric wall UDL, lumped to both ends
            nodal["DL"][m.n1][3:6] += tq
            nodal["DL"][m.n2][3:6] += tq
    col_w = np.zeros(len(cols))
    for k, m in enumerate(cols):
        b, D = fe_in.col_sizes_mm[m.group]
        col_w[k] = st.unit_weight_kNm3 * (b / 1000.0) * (D / 1000.0) * m.length_m
        nodal["DL"][m.n1][1] -= col_w[k] / 2.0
        nodal["DL"][m.n2][1] -= col_w[k] / 2.0

    sols = solve_cases(fs, props, nodal, st.shear_deformation)
    ok = all(s.ok for s in sols.values())
    applied = {c: sum(f[1] for f in nodal[c].values()) for c in nodal}
    eq_err = max(abs(sols[c].reaction_sum[1] + applied[c]) / max(abs(applied[c]), 1e-9) for c in nodal)

    comb = lc.combinations
    f_str = (comb["strength"]["DL"], comb["strength"]["LL"])
    f_srv = (comb["service"]["DL"], comb["service"]["LL"])

    def member_forces(fd: float, fl: float) -> dict[int, np.ndarray]:
        out = {}
        for k, m in enumerate(beams):
            e = fd * sols["DL"].ef[m.id] + fl * sols["LL"].ef[m.id]
            for case, fac in (("DL", fd), ("LL", fl)):
                va, vb, ma, mb = (a[k] for a in fef[case])
                e[1] += fac * va
                e[7] += fac * vb
                e[3:6] += fac * ma * h_axis[k]
                e[9:12] -= fac * mb * h_axis[k]
            out[m.id] = e
        for k, m in enumerate(cols):
            e = fd * sols["DL"].ef[m.id] + fl * sols["LL"].ef[m.id]
            e[1] += fd * col_w[k] / 2.0
            e[7] += fd * col_w[k] / 2.0
            out[m.id] = e
        return out

    ef_s = member_forces(*f_str)
    ef_v = member_forces(*f_srv)

    # ---- beams: M(x), V(x) at strength level (statics from end actions + load)
    q_s = f_str[0] * q_dl + f_str[1] * q_ll
    Fa = np.array([ef_s[m.id][1] for m in beams])
    Fb = np.array([ef_s[m.id][7] for m in beams])
    ma_ = np.array([ef_s[m.id][3:6] @ h_axis[k] for k, m in enumerate(beams)])
    mb_ = np.array([ef_s[m.id][9:12] @ h_axis[k] for k, m in enumerate(beams)])
    x, Ms, Vs = beam_diagrams(L, q_s, Fa, ma_)
    Q_end = Fa[:, None] - Vs[:, -1:]
    beam_eq = float(np.max(np.abs(Fa + Fb - Q_end[:, 0]) / np.maximum(Q_end[:, 0], 1e-9)))
    # moment equilibrium about end a: ma + mb + Fb L - int q s ds = 0 (relative to the total moment scale)
    mom_resid = np.abs(ma_ + mb_ + Fb * L - np.trapezoid(q_s * x, x, axis=1))
    beam_eq = max(beam_eq, float(np.max(mom_resid / np.maximum(np.abs(Fb * L), 1e-9))))

    n_bg = len(fe_in.beam_sizes_mm)
    beam_out = np.zeros((n_bg, 3))
    grp = np.array([m.group for m in beams])
    for g in range(n_bg):
        sel = grp == g
        beam_out[g] = (max(float(Ms[sel].max()), 0.0), max(float(-Ms[sel].min()), 0.0), float(np.abs(Vs[sel]).max()))

    # ---- beams: service deflection relative to the chord
    q_v = f_srv[0] * q_dl + f_srv[1] * q_ll
    Fa_v = np.array([ef_v[m.id][1] for m in beams])
    ma_v = np.array([ef_v[m.id][3:6] @ h_axis[k] for k, m in enumerate(beams)])
    _, Mv, _ = beam_diagrams(L, q_v, Fa_v, ma_v)
    EI = np.array([props[m.id].E * props[m.id].Iy for m in beams])
    va_n = np.zeros(len(beams))
    vb_n = np.zeros(len(beams))
    th_a = np.zeros(len(beams))
    for k, m in enumerate(beams):
        da = f_srv[0] * sols["DL"].disp[m.n1] + f_srv[1] * sols["LL"].disp[m.n1]
        db = f_srv[0] * sols["DL"].disp[m.n2] + f_srv[1] * sols["LL"].disp[m.n2]
        va_n[k], vb_n[k], th_a[k] = da[1], db[1], da[3:6] @ h_axis[k]
    v, dev = beam_chord_deflection(x, Mv, EI, va_n, vb_n, th_a)   # dev < 0: sag below the chord
    delta = np.maximum(-dev.min(axis=1), 0.0)          # m
    d_over_L = np.zeros(n_bg)
    for g in range(n_bg):
        sel = grp == g
        d_over_L[g] = float((delta[sel] / L[sel]).max())
    defl_mm = float(delta.max() * 1e3 * cfg_solver["checks"]["long_term_factor"])
    d_over_L *= cfg_solver["checks"]["long_term_factor"]

    # ---- columns
    D_is_x = fs.column_D_axis == "x"
    col_all: list[list[list[float]]] = [[] for _ in fe_in.col_sizes_mm]
    for m in cols:
        e = ef_s[m.id]
        Pu = float(e[1])                                  # compression at the bottom end (force on element, +Y)
        Mx = max(abs(e[3]), abs(e[9]))
        Mz = max(abs(e[5]), abs(e[11]))
        MD, Mb = (Mz, Mx) if D_is_x else (Mx, Mz)
        if m.kind == "stub":
            l_mm = m.length_m * 1000.0
        else:
            top_group = fs.beam_group_of_level[m.level + 1]
            l_mm = (m.length_m - fe_in.beam_sizes_mm[top_group][1] / 1000.0) * 1000.0
        col_all[m.group].append([Pu, MD, Mb, l_mm])
    col_all_a = [np.array(c) for c in col_all]
    # position classes (level, min(ix, nx-1-ix), min(iz, nz-1-iz)); level 0 = stub, s + 1 = storey s. Members of a class are
    # equivalent by symmetry, so the class maxima are a smooth, exact summary (Surrogate B regresses these, decision D-024).
    ncx, ncz = (fs.nx + 1) // 2, (fs.nz + 1) // 2
    types = np.zeros((fs.n_storeys + 1, ncx, ncz, 4))
    for m in cols:
        e = ef_s[m.id]
        if D_is_x:
            MD, Mb = max(abs(e[5]), abs(e[11])), max(abs(e[3]), abs(e[9]))
        else:
            MD, Mb = max(abs(e[3]), abs(e[9])), max(abs(e[5]), abs(e[11]))
        lv = 0 if m.kind == "stub" else m.level + 1
        t = types[lv, min(m.i, fs.nx - 1 - m.i), min(m.j, fs.nz - 1 - m.j)]
        if m.kind == "stub":
            l_mm = m.length_m * 1000.0
        else:
            l_mm = (m.length_m - fe_in.beam_sizes_mm[fs.beam_group_of_level[m.level + 1]][1] / 1000.0) * 1000.0
        t[:] = (max(t[0], float(e[1])), max(t[1], MD), max(t[2], Mb), l_mm)

    raw = {"ef_strength": ef_s, "ef_service": ef_v, "beams": beams, "Ms": Ms, "Vs": Vs, "v": v, "x": x,
           "sols": sols, "nodal": nodal, "q_dl": q_dl, "q_ll": q_ll} if keep_raw else {}
    return FEDemands(beam_out, types, col_all_a, d_over_L, defl_mm, float(eq_err), beam_eq, ok, raw)
