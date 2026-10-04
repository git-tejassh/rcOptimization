"""Strength review of a user's regular RC frame given as a STAAD input (the "revise strength" step of the dashboard).

Pipeline: parse STAAD -> recognise a complete regular grid frame (columns at every grid node, beams on every grid line,
one section per level / storey) -> run the project's OpenSees gravity analysis with the member sizes of the file ->
design the cheapest standard reinforcement per group that satisfies IS 456 (beam bending / shear / steel limits, column
biaxial interaction, deflection) -> report utilisations, the revised steel quantity and any check that fails even with
the largest bars (meaning the *sizes* must grow).

Loads are the project's IS 875 defaults (``config/loads.yaml``), NOT the load cases of the STAAD file; gravity only.
"""
from __future__ import annotations

import dataclasses
import itertools
from dataclasses import dataclass

import numpy as np

from rcopt import config
from rcopt.codes import beam as beam_code
from rcopt.codes import column as col_code
from rcopt.codes import detailing as dt
from rcopt.cost_carbon.quantities import compute_quantities
from rcopt.design.geometric_feasibility import beam_layers
from rcopt.design.repair import _col_feasible
from rcopt.design.variables import BeamSection, ColumnSection, Design
from rcopt.fe.analysis import FEInput, analyze
from rcopt.geometry.frame_spec import build_frame
from rcopt.geometry.staad_parser import StaadModel, parse_staad

TOL = 0.005          # coordinate clustering tolerance, m


class ReviewError(ValueError):
    """The file cannot be reviewed (reason is user-readable)."""


def _cluster(values: list[float], tol: float = TOL) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def _snap(v: float, grid: list[float]) -> int:
    return int(np.argmin([abs(v - g) for g in grid]))


@dataclass
class Derived:
    geom: config.GeometryCfg
    fs: object
    beam_sizes: list[tuple[int, int]]        # (b, D) mm per beam group
    col_sizes: list[tuple[int, int]]         # (b, D) mm per column group (last one may be a stub-only group)
    beam_levels: list[list[int]]
    col_storeys: list[list[int]]
    stub_group: int
    notes: list[str]


def derive_frame(model: StaadModel) -> Derived:
    """Recognise a complete regular grid frame in a parsed STAAD model or raise ``ReviewError``."""
    if not model.members or not model.joints:
        raise ReviewError("No joints / members found: is this a STAAD input (.std) text file?")
    missing = [m for m in model.members if m not in model.section_m]
    if missing:
        raise ReviewError(f"{len(missing)} member(s) have no PRISMATIC YD/ZD section (e.g. member {missing[0]}); catalogue sections are not supported.")
    xs = _cluster([p[0] for p in model.joints.values()])
    ys = _cluster([p[1] for p in model.joints.values()])
    zs = _cluster([p[2] for p in model.joints.values()])
    base_y = ys[0]
    kinds: dict[int, str] = {}
    cell: dict[tuple, tuple[int, int]] = {}
    for mid, (a, b) in model.members.items():
        p, q = model.joints[a], model.joints[b]
        dx, dy, dz = (abs(q[0] - p[0]), abs(q[1] - p[1]), abs(q[2] - p[2]))
        if dx < TOL and dz < TOL:
            kind = "col"
        elif dy < TOL and dz < TOL:
            kind = "bx"
        elif dy < TOL and dx < TOL:
            kind = "bz"
        else:
            raise ReviewError(f"Member {mid} is inclined or diagonal: only orthogonal beam-column frames are supported.")
        kinds[mid] = kind
        lo, hi = (p, q) if (p[1], p[0], p[2]) <= (q[1], q[0], q[2]) else (q, p)
        key = (kind, _snap(lo[0], xs), _snap(lo[1], ys), _snap(lo[2], zs), _snap(hi[0], xs), _snap(hi[1], ys), _snap(hi[2], zs))
        if key in cell:
            raise ReviewError(f"Members {cell[key][0]} and {mid} overlap.")
        yd, zd = model.section_m[mid]
        cell[key] = (mid, 0)
        kinds[mid] = (kind, key, yd, zd)  # type: ignore[assignment]

    beam_ys = _cluster([model.joints[model.members[m][0]][1] for m, k in kinds.items() if k[0] in ("bx", "bz")])  # type: ignore[index]
    if not beam_ys:
        raise ReviewError("No beams found.")
    if beam_ys[0] <= base_y + 0.2:
        raise ReviewError("There are beams at the support level; the review needs the column bases at least 0.2 m below the first beam level (as in the project model).")
    levels = beam_ys
    stub_m = levels[0] - base_y
    nx, nz = len(xs), len(zs)
    if nx < 2 or nz < 2:
        raise ReviewError("A plan of at least 2 x 2 grid lines is needed.")
    storey_h = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]
    if not storey_h:
        raise ReviewError("At least two beam levels (one storey above the first level) are needed.")
    # completeness check of the regular grid
    ysall = [base_y] + levels
    expect: dict[tuple, str] = {}
    for y in levels:
        for iz in range(nz):
            for ix in range(nx - 1):
                expect[("bx", ix, ysall.index(y), iz, ix + 1, ysall.index(y), iz)] = "bx"
        for ix in range(nx):
            for iz in range(nz - 1):
                expect[("bz", ix, ysall.index(y), iz, ix, ysall.index(y), iz + 1)] = "bz"
    for iy in range(len(ysall) - 1):
        for iz in range(nz):
            for ix in range(nx):
                expect[("col", ix, iy, iz, ix, iy + 1, iz)] = "col"
    have = {}
    for mid, (kind, key, yd, zd) in ((m, k) for m, k in kinds.items()):  # type: ignore[misc]
        have[(key[0], key[1], _lvl(ysall, ys, key[2]), key[3], key[4], _lvl(ysall, ys, key[5]), key[6])] = (mid, kind, yd, zd)
    absent = [k for k in expect if k not in have]
    extra = [k for k in have if k not in expect]
    if absent:
        raise ReviewError(f"The frame is not a complete regular grid: {len(absent)} expected member(s) are missing (first: {absent[0][0]} at grid cell {absent[0][1:]}).")
    if extra:
        raise ReviewError(f"{len(extra)} member(s) do not belong to a regular beam-column grid (first: member {have[extra[0]][0]}).")

    def mm(v: float) -> int:
        return int(round(v * 1000.0 / 5.0) * 5)

    beam_sec_by_level: dict[int, set] = {}
    col_sec_by_storey: dict[int, set] = {}
    for key, (_mid, kind, yd, zd) in have.items():
        if kind in ("bx", "bz"):
            beam_sec_by_level.setdefault(key[2], set()).add((mm(zd), mm(yd)))      # (b = ZD, D = YD)
        else:
            lo, hi = sorted((mm(yd), mm(zd)))
            col_sec_by_storey.setdefault(key[2], set()).add((lo, hi))              # (b <= D)
    for lv, s in beam_sec_by_level.items():
        if len(s) > 1:
            raise ReviewError(f"Beams of level {lv - 1} have different sections {sorted(s)}: one section per level is required.")
    for st, s in col_sec_by_storey.items():
        if len(s) > 1:
            raise ReviewError(f"Columns of storey {st - 1} have different sections {sorted(s)}: one section per storey is required.")
    beam_sizes_level = [next(iter(beam_sec_by_level[i + 1])) for i in range(len(levels))]
    col_sizes_storey = [next(iter(col_sec_by_storey[i + 1])) for i in range(len(levels) - 1)]
    stub_size = next(iter(col_sec_by_storey[0]))

    beam_sizes: list[tuple[int, int]] = []
    beam_levels: list[list[int]] = []
    for lv, sz in enumerate(beam_sizes_level):
        if sz in beam_sizes:
            beam_levels[beam_sizes.index(sz)].append(lv)
        else:
            beam_sizes.append(sz)
            beam_levels.append([lv])
    col_sizes: list[tuple[int, int]] = []
    col_storeys: list[list[int]] = []
    for st, sz in enumerate(col_sizes_storey):
        if sz in col_sizes:
            col_storeys[col_sizes.index(sz)].append(st)
        else:
            col_sizes.append(sz)
            col_storeys.append([st])
    notes: list[str] = []
    if stub_size in col_sizes:
        stub_group = col_sizes.index(stub_size)
    else:
        col_sizes.append(stub_size)
        stub_group = len(col_sizes) - 1
        notes.append(f"The columns between the base and the first beam level ({stub_size[0]} x {stub_size[1]} mm) form their own group.")
    base = config.geometry()
    geom = config.GeometryCfg(
        source="config", staad_file="", bays_x_m=[round(xs[i + 1] - xs[i], 4) for i in range(nx - 1)],
        bays_z_m=[round(zs[i + 1] - zs[i], 4) for i in range(nz - 1)], storey_heights_m=[round(h, 4) for h in storey_h],
        stub_height_m=round(stub_m, 4), beam_groups=beam_levels, column_groups=col_storeys, column_D_axis=base.column_D_axis,
    )
    fs = build_frame(geom)
    fs.members = [dataclasses.replace(m, group=stub_group) if m.kind == "stub" else m for m in fs.members]
    return Derived(geom, fs, beam_sizes, col_sizes, beam_levels, col_storeys, stub_group, notes)


def _lvl(ysall: list[float], ys: list[float], iy_cluster: int) -> int:
    """Index of a joint-elevation cluster in the list of [base] + beam levels (the base cluster maps to 0)."""
    y = ys[iy_cluster]
    return int(np.argmin([abs(y - v) for v in ysall]))


# ----------------------------------------------------------------------------- reinforcement design
BAR_N = None


def _beam_options(cfg: config.DesignSpaceCfg):
    bs = cfg.beam
    return list(itertools.product(bs.bottom_bar_dia_mm, bs.bar_count, bs.top_bar_dia_mm, bs.bar_count))


def design_beam_group(b: int, D: int, concrete: str, steel: str, demand: np.ndarray, cfg: config.DesignSpaceCfg) -> dict:
    """Cheapest (least steel) bar arrangement passing IS 456 flexure / shear / steel limits; best-effort + flags if none passes."""
    msag, mhog, vu = (float(x) for x in demand)
    best = None
    fallback = None
    for bd, bn, td, tn in _beam_options(cfg):
        sec = BeamSection(b, D, bd, bn, td, tn)
        if beam_layers(sec, cfg, False) is None or beam_layers(sec, cfg, True) is None:
            continue
        ck = beam_code.check_beam_group(sec, concrete, steel, msag, mhog, vu, cfg)
        steel_mm2 = ck.Ast_bot_mm2 + ck.Ast_top_mm2
        stirrup = (2 * (b + D) * dt.bar_area_mm2(cfg.beam.stirrup_dia_mm)) / max(ck.sv_mm, cfg.beam.stirrup_spacing_min_mm)
        cost_key = steel_mm2 + stirrup
        ok = ck.U_flex <= 1.0 and ck.U_shear <= 1.0 and ck.g_steel <= 0
        if ok and (best is None or cost_key < best[0]):
            best = (cost_key, sec, ck)
        score = max(ck.U_flex, ck.U_shear, 1.0 + max(ck.g_steel, 0))
        if fallback is None or score < fallback[0] or (abs(score - fallback[0]) < 1e-9 and cost_key < fallback[1]):
            fallback = (score, cost_key, sec, ck)
    if best:
        _, sec, ck = best
        ok = True
    elif fallback:
        _, _, sec, ck = fallback
        ok = False
    else:
        raise ReviewError(f"No standard bar arrangement fits in a {b} x {D} mm beam.")
    reasons = []
    if ck.U_flex > 1.0:
        reasons.append(f"bending: demand exceeds capacity even with the largest bars (U = {ck.U_flex:.2f}); increase the depth")
    if ck.U_shear > 1.0:
        reasons.append(f"shear: tau_v / tau_c,max or stirrup spacing limit exceeded (U = {ck.U_shear:.2f}); increase width or depth")
    if ck.g_steel > 0:
        reasons.append("reinforcement limits (minimum / maximum steel) cannot be met")
    return {"ok": ok, "sec": sec, "check": ck, "demand": {"Msag_kNm": msag, "Mhog_kNm": mhog, "Vu_kN": vu}, "reasons": reasons}


def design_column_group(b: int, D: int, concrete: str, steel: str, members: np.ndarray, cfg: config.DesignSpaceCfg) -> dict:
    """Least-steel symmetric bar layout with every column of the group passing the biaxial interaction and steel limits."""
    solver = config.load_dict("solver")["checks"]
    uniq = np.unique(np.round(members, 1), axis=0)
    best = None
    fallback = None
    for dia, n in itertools.product(cfg.column.bar_dia_mm, cfg.column.bar_count):
        if not _col_feasible(b, D, dia, n):
            continue
        sec = ColumnSection(b, D, dia, n)
        worst, gpt, worst_ck, worst_row = 0.0, -np.inf, None, None
        for Pu, MD, Mb, l_mm in uniq:
            ck = col_code.check_column(sec, concrete, steel, Pu, MD, Mb, l_mm, cfg, k_eff=solver["column_k_eff"],
                                       emin_simultaneous=solver["emin_simultaneous"], cap=solver["util_cap"],
                                       max_slenderness=solver["max_slenderness_le_D"])
            gpt = max(gpt, ck.g_pt)
            if ck.U >= worst:
                worst, worst_ck, worst_row = ck.U, ck, (Pu, MD, Mb, l_mm)
        area = n * dt.bar_area_mm2(dia)
        ok = worst <= 1.0 and gpt <= 0
        if ok and (best is None or area < best[0]):
            best = (area, sec, worst_ck, worst_row)
        score = max(worst, 1.0 + max(gpt, 0))
        if fallback is None or score < fallback[0] or (abs(score - fallback[0]) < 1e-9 and area < fallback[1]):
            fallback = (score, area, sec, worst_ck, worst_row)
    if best:
        _, sec, ck, row = best
        ok = True
    elif fallback:
        _, _, sec, ck, row = fallback
        ok = False
    else:
        raise ReviewError(f"No standard bar layout fits in a {b} x {D} mm column.")
    reasons = []
    if ck.U > 1.0:
        reasons.append(f"axial + bending interaction exceeds 1.0 even with the largest bars (U = {ck.U:.2f}); increase the section")
    if ck.g_pt > 0:
        reasons.append("steel percentage outside 0.8-4 %")
    return {"ok": ok, "sec": sec, "check": ck, "row": row, "reasons": reasons}


# ----------------------------------------------------------------------------- main entry
def review_staad(text: str, concrete: str = "M30", steel: str = "Fe500", cement: str = "PPC") -> dict:
    """Run the full review and return a JSON-serialisable report."""
    model = parse_staad_text(text)
    dv = derive_frame(model)
    cfg = config.design_space()
    solver = config.load_dict("solver")["checks"]
    tables = config.load_dict("is456_tables")
    fck, fy = float(tables["concrete"]["fck_MPa"][concrete]), float(tables["steel"]["fy_MPa"][steel])
    fe_in = FEInput(tuple(dv.beam_sizes), tuple(dv.col_sizes), fck)
    dem = analyze(fe_in, dv.fs)
    if not dem.ok or dem.equilibrium_err > config.load_dict("solver")["fe"]["equilibrium_tol"]:
        raise ReviewError("The finite-element analysis did not converge or failed the equilibrium check.")

    beams = [design_beam_group(b, D, concrete, steel, dem.beam[g], cfg) for g, (b, D) in enumerate(dv.beam_sizes)]
    cols = [design_column_group(b, D, concrete, steel, dem.col_all[g], cfg) for g, (b, D) in enumerate(dv.col_sizes)]
    design = Design(tuple(x["sec"] for x in beams), tuple(x["sec"] for x in cols), concrete, steel, fck, fy, cement)
    sv = tuple(x["check"].sv_mm for x in beams)
    q = compute_quantities(design, sv, dv.fs)
    defl_ratio = dem.defl_max_over_L * solver["deflection_limit_ratio"]
    defl_ok = defl_ratio <= 1.0

    beam_rows, col_rows = [], []
    for g, x in enumerate(beams):
        s, ck = x["sec"], x["check"]
        beam_rows.append({
            "group": g, "levels": dv.beam_levels[g], "b_mm": s.b_mm, "D_mm": s.D_mm, "demand": x["demand"],
            "bottom": f"{s.bot_n}-{s.bot_dia_mm} mm", "top": f"{s.top_n}-{s.top_dia_mm} mm", "stirrups": f"2-L 8 mm @ {ck.sv_mm:.0f} mm",
            "Mu_sag_kNm": ck.Mu_sag_kNm, "Mu_hog_kNm": ck.Mu_hog_kNm, "U_sag": ck.U_sag, "U_hog": ck.U_hog, "U_shear": ck.U_shear,
            "tau_v": ck.tau_v, "tau_c": ck.tau_c, "pt_bot": ck.pt_bot, "pt_top": ck.pt_top, "pass": x["ok"], "reasons": x["reasons"],
        })
    for g, x in enumerate(cols):
        s, ck = x["sec"], x["check"]
        Pu, MD, Mb, l_mm = x["row"]
        col_rows.append({
            "group": g, "storeys": dv.col_storeys[g] if g < len(dv.col_storeys) else [], "is_base_group": g == dv.stub_group,
            "b_mm": s.b_mm, "D_mm": s.D_mm, "bars": f"{s.n}-{s.dia_mm} mm", "pt_percent": ck.pt_percent,
            "governing": {"Pu_kN": float(Pu), "MD_kNm": float(MD), "Mb_kNm": float(Mb), "l_mm": float(l_mm)},
            "MuD1_kNm": ck.MuD1_kNm, "Mub1_kNm": ck.Mub1_kNm, "alpha_n": ck.alpha_n, "Puz_kN": ck.Puz_kN, "U": ck.U,
            "slender": bool(ck.slender_D or ck.slender_b), "pass": x["ok"], "reasons": x["reasons"],
        })
    all_ok = all(x["ok"] for x in beams) and all(x["ok"] for x in cols) and defl_ok
    fails = [f"beam group {r['group']}: {m}" for r in beam_rows for m in r["reasons"]] + \
            [f"column group {r['group']}: {m}" for r in col_rows for m in r["reasons"]]
    if not defl_ok:
        fails.append(f"deflection: {defl_ratio:.2f} x the L/250 limit; increase beam depth")
    return {
        "verdict": "PASS" if all_ok else "FAIL",
        "failures": fails,
        "frame": {"bays_x_m": dv.geom.bays_x_m, "bays_z_m": dv.geom.bays_z_m, "storey_heights_m": dv.geom.storey_heights_m,
                  "base_to_first_beam_level_m": dv.geom.stub_height_m, "n_members": len(model.members), "n_joints": len(model.joints)},
        "materials": {"concrete": concrete, "steel": steel, "cement": cement, "fck_MPa": fck, "fy_MPa": fy},
        "beams": beam_rows, "columns": col_rows,
        "deflection": {"ratio_to_L_over_250": defl_ratio, "max_mm": dem.defl_mm, "pass": defl_ok},
        "quantities": {"concrete_m3": q.concrete_m3, "beam_concrete_m3": q.beam_concrete_m3, "column_concrete_m3": q.column_concrete_m3,
                       "steel_kg": q.steel_kg, "beam_steel_kg": q.beam_steel_kg, "column_steel_kg": q.column_steel_kg,
                       "formwork_m2": q.formwork_m2},
        "notes": dv.notes,
        "assumptions": [
            "Gravity loads only: 1.5 (DL + LL), IS 456:2000; slab, wall and live loads are the project's IS 875 defaults (config/loads.yaml), not the load cases of the STAAD file.",
            "Cracked stiffness 0.35 Ig (beams) / 0.70 Ig (columns); fixed bases; slab not designed; beams rectangular; uniform reinforcement over the span.",
            "Reinforcement is DESIGNED here (cheapest standard bars that pass); a STAAD input contains none. Detailing (development length, curtailment, torsion, seismic) is not checked.",
            "Only complete regular orthogonal grid frames with one section per level / storey are supported.",
        ],
    }


def parse_staad_text(text: str) -> StaadModel:
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile("w", suffix=".std", delete=False, encoding="latin-1", errors="replace") as fh:
        fh.write(text)
        path = fh.name
    try:
        return parse_staad(path)
    finally:
        Path(path).unlink(missing_ok=True)
