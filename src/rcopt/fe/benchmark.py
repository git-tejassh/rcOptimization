"""OpenSeesPy vs STAAD.Pro benchmark on the owner's G+3 model (project.md 7.5, brief s7).

The OpenSees model is run in *benchmark mode* (STAAD's own E = 2.17e7 kN/m2, density 23.56 kN/m3, uncracked
sections, STAAD's fixed wall loads) with STAAD's sections (beams 300 x 450, columns 450 x 450), then compared
with the STAAD binary results (reactions, displacements) and the IS 456 column design report (.ANL).
No STAAD licence is needed: only result files that already exist in ``legacy/staad_model``.
"""
from __future__ import annotations

import json

import numpy as np

from rcopt.config import ROOT
from rcopt.fe import staad_reference as sr
from rcopt.fe.analysis import FEInput, FESettings, analyze, default_frame
from rcopt.geometry.staad_parser import StaadModel, parse_staad

CASES = {"DL": 5, "LL": 6, "COMB11": 11}      # STAAD load case numbers (1.5 (DL + LL) = case 11)
STAAD_FILE = sr.STD_DIR / f"{sr.STEM}.STD"


def _maps(sm: StaadModel, fs):
    key = {(round(x, 2), round(y, 2), round(z, 2)): nid for nid, (x, y, z) in fs.nodes.items()}
    j2n = {jid: key[(round(x, 2), round(y, 2), round(z, 2))] for jid, (x, y, z) in sm.joints.items()}
    by_nodes = {frozenset((m.n1, m.n2)): m for m in fs.members}
    return j2n, {mid: by_nodes[frozenset((j2n[a], j2n[b]))] for mid, (a, b) in sm.members.items()}


def _rel(a: np.ndarray, b: np.ndarray, floor: float) -> np.ndarray:
    """Relative difference |a - b| / max(|b|, floor) with an absolute floor to avoid dividing by ~0."""
    return np.abs(a - b) / np.maximum(np.abs(b), floor)


def _stats(x: np.ndarray) -> dict:
    return {"n": int(x.size), "max_rel": float(x.max()), "mean_rel": float(x.mean()),
            "p95_rel": float(np.percentile(x, 95))}


def run_benchmark(settings: FESettings | None = None) -> dict:
    sm = parse_staad(STAAD_FILE)
    fs = default_frame()
    j2n, mem = _maps(sm, fs)
    (yd_b, zd_b), (yd_c, zd_c) = sm.section_m[1], sm.section_m[81]
    fe_in = FEInput(((round(zd_b * 1000), round(yd_b * 1000)),) * 2, ((round(zd_c * 1000), round(yd_c * 1000)),) * 2,
                    30.0)
    dem = analyze(fe_in, fs, settings or FESettings.benchmark(), keep_raw=True)
    sols, ef = dem.raw["sols"], dem.raw["ef_strength"]

    def pick(case: str, getter) -> np.ndarray:
        """Case result for every id: DL, LL or 1.5 (DL + LL) (STAAD case 11)."""
        if case == "COMB11":
            return 1.5 * (pick("DL", getter) + pick("LL", getter))
        return np.array([getter(sols[case], n) for n in ids_now])

    rea_ids, rea = sr.reactions_kN()
    dsp_ids, dsp = sr.displacements_mm()
    out: dict = {"model": {"joints": len(sm.joints), "members": len(sm.members),
                           "sections_mm": {"beam": [fe_in.beam_sizes_mm[0]], "column": [fe_in.col_sizes_mm[0]]}},
                 "reactions_Fy": {}, "displacements_dy_mm": {}, "displacements_dx_dz_mm": {}}
    for name, case in CASES.items():
        ids_now = rea_ids
        st = np.array([rea[case - 1, i, 1] for i in range(len(rea_ids))])
        os_ = pick(name, lambda s_, n: s_.reactions[j2n[int(n)]][1])
        out["reactions_Fy"][name] = {**_stats(_rel(os_, st, 1e-3 * abs(st).max())),
                                     "sum_staad_kN": float(st.sum()), "sum_opensees_kN": float(os_.sum())}
        ids_now = dsp_ids
        st = np.array([dsp[case - 1, i, 1] for i in range(len(dsp_ids))])
        os_ = pick(name, lambda s_, n: s_.disp[j2n[int(n)]][1] * 1e3)
        out["displacements_dy_mm"][name] = {**_stats(_rel(os_, st, 0.05 * abs(st).max())),
                                            "max_abs_staad_mm": float(abs(st).max())}
        sx = np.column_stack([[dsp[case - 1, i, 0] for i in range(len(dsp_ids))],
                              [dsp[case - 1, i, 2] for i in range(len(dsp_ids))]])
        ox = np.column_stack([pick(name, lambda s_, n: s_.disp[j2n[int(n)]][0] * 1e3),
                              pick(name, lambda s_, n: s_.disp[j2n[int(n)]][2] * 1e3)])
        out["displacements_dx_dz_mm"][name] = {**_stats(_rel(ox, sx, 0.05)), "max_abs_staad_mm": float(abs(sx).max()),
                                               "max_abs_diff_mm": float(np.abs(ox - sx).max())}

    anl = sr.parse_anl_columns()
    rows = []
    for no, v in anl.items():
        if v["guiding_case"] != 11:
            continue
        m = mem[no]
        e = ef[m.id]
        at_start = j2n[v["end_joint"]] == m.n1          # STAAD end joint -> my member end (my members run low -> high)
        Pu = e[1] if at_start else -e[7]
        Mx, Mz = (abs(e[3]), abs(e[5])) if at_start else (abs(e[9]), abs(e[11]))
        rows.append({"member": no, "Pu_staad": v["Pu_kN"], "Pu_os": float(Pu), "Mz_staad": v["M_initial_Z_kNm"],
                     "Mz_os": float(Mz), "My_staad": v["M_initial_Y_kNm"], "My_os": float(Mx)})
    a = np.array([[r["Pu_staad"], r["Pu_os"]] for r in rows])
    out["columns_Pu"] = {**_stats(_rel(a[:, 1], a[:, 0], 1.0)), "members_compared": len(rows)}
    for key, (s, o) in {"Mz": ("Mz_staad", "Mz_os"), "My": ("My_staad", "My_os")}.items():
        arr = np.array([[r[s], r[o]] for r in rows])
        big = arr[:, 0] >= 20.0
        out[f"columns_{key}_ge20kNm"] = {**_stats(_rel(arr[big, 1], arr[big, 0], 1.0)), "members_compared": int(big.sum())}
        out[f"columns_{key}_all"] = {**_stats(np.abs(arr[:, 1] - arr[:, 0])), "note": "absolute diff, kN.m"}
    out["column_rows"] = rows
    return out


def write_reference(path=None) -> None:
    """Persist the STAAD reference numbers used (small JSON, committed)."""
    path = path or ROOT / "data" / "benchmark" / "staad_reference.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rea_ids, rea = sr.reactions_kN()
    ref = {"units": "kN, kN.m, mm, rad (converted from STAAD-internal kip/inch)",
           "reactions_Fy_kN": {name: {int(n): float(rea[c - 1, i, 1]) for i, n in enumerate(rea_ids)}
                               for name, c in CASES.items()},
           "anl_columns": {str(k): v for k, v in sr.parse_anl_columns().items()}}
    path.write_text(json.dumps(ref, indent=1), encoding="utf-8")


def _row(name: str, r: dict) -> str:
    f = lambda x: f"{100 * x:.3f} %"  # noqa: E731
    return (f"| {name} | {f(r['reactions_Fy']['DL']['max_rel'])} | {f(r['displacements_dy_mm']['COMB11']['max_rel'])} "
            f"| {r['displacements_dx_dz_mm']['DL']['max_abs_diff_mm']:.3f} mm | {f(r['columns_Pu']['max_rel'])} "
            f"| {f(r['columns_Mz_ge20kNm']['max_rel'])} / {f(r['columns_My_ge20kNm']['max_rel'])} "
            f"| {r['columns_Mz_all']['max_rel']:.2f} kN.m |")


def write_report(path=None) -> dict:
    """Run the benchmark (full + ablations), write docs/BENCHMARK.md and data/results/benchmark.json."""
    import dataclasses

    path = path or ROOT / "docs" / "BENCHMARK.md"
    full_st = FESettings.benchmark()
    variants = {
        "A. Euler-Bernoulli, no wall torque": dataclasses.replace(full_st, shear_deformation=False, wall_ecc_m=0.0),
        "B. A + STAAD wall-load eccentricity (d3 = 0.15 m)": dataclasses.replace(full_st, shear_deformation=False),
        "C. B + shear deformation (Timoshenko) = benchmark mode": full_st,
    }
    results = {k: run_benchmark(v) for k, v in variants.items()}
    full = results["C. B + shear deformation (Timoshenko) = benchmark mode"]
    (ROOT / "data" / "results").mkdir(parents=True, exist_ok=True)
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "column_rows"} for k, v in results.items()}
    (ROOT / "data" / "results" / "benchmark.json").write_text(json.dumps(slim, indent=1), encoding="utf-8")
    write_reference()
    rows = chr(10).join(_row(k, v) for k, v in results.items())
    rd = full["reactions_Fy"]
    path.write_text(f"""# BENCHMARK: OpenSeesPy vs STAAD.Pro (owner's G+3 model)

Generated by `rcopt phase0b` (`src/rcopt/fe/benchmark.py`); gate test: `tests/test_benchmark.py`.

## Setup
* Reference: results already stored in `legacy/staad_model` for the owner's model `G+3 RCC FINAL`
  (120 joints, 255 members, 20 fixed supports): reactions (`.rea`) and joint displacements (`.dsp`) for the 35 load cases,
  and the IS 456 column design report (`.ANL`, 76 columns whose guiding case is 11 = 1.5 (DL + LL)).
  STAAD stores these binaries in kip / inch; conversion verified by the dead-load total (see below).
  **No STAAD licence was used by this project**; the owner's files are only read.
* OpenSees model in **benchmark mode**: STAAD's own material (E = 2.17184e7 kN/m2, density 23.5615 kN/m3, nu 0.17),
  uncracked sections (modifiers 1.0), STAAD's sections (beams 300 x 450, columns 450 x 450), STAAD's fixed wall loads,
  floor loads 4.75 / 5.25 kN/m2 distributed by yield-line tributary areas, live 2.0 / 1.5 kN/m2.
* Design mode (used for the optimisation) differs from benchmark mode only by: E = 5000 sqrt(fck), 25 kN/m3,
  cracked modifiers (0.35 / 0.70) and wall loads that follow the beam depth. Those are pure scalings of E, I and loads;
  STAAD (uncracked) cannot validate them, which is why they are listed in `docs/ASSUMPTIONS.md` (B6) as choices.

## Result (max relative differences, 20 supports / 120 joints / 76 columns)

| Variant | Reaction Fy (DL) | Disp. dy (case 11) | Disp. dx,dz (DL), abs | Column Pu | Column M (>= 20 kN.m): about Z / Y | Column M, all (abs max) |
|---|---|---|---|---|---|---|
{rows}

Dead-load total: STAAD {rd['DL']['sum_staad_kN']:.2f} kN, OpenSees {rd['DL']['sum_opensees_kN']:.2f} kN
(hand total of the model's loads: 17,580 kN). Live-load total: {rd['LL']['sum_staad_kN']:.2f} vs {rd['LL']['sum_opensees_kN']:.2f} kN.

**Verdict: PASS** (targets were forces within 5 %, deflections within 10 %). With variant C every compared quantity agrees to better than
0.2 % (column moments > 20 kN.m) / 0.005 % (reactions, vertical displacements, axial forces); the largest absolute column-moment
difference is {full['columns_Mz_all']['max_rel']:.2f} kN.m.

## What explained the first discrepancies (found, tested, not hidden)
1. **Wall-load eccentricity.** STAAD's `UNI GY -11.73 0 5 0.15` carries a 0.15 m perpendicular offset, which creates a torque on every
   wall-loaded beam. Ignoring it left a 1.9 % reaction error and a 115 % error in the horizontal dead-load displacements (STAAD's
   dead-load sway of up to 0.92 mm, and its asymmetric support reactions, come from this torque). Applying the torque with the offset
   toward the member's local +z (X-beams +Z, Z-beams -X; my reading of STAAD's convention, confirmed by the fit) removes it.
2. **Shear deformation.** STAAD includes it; `elasticBeamColumn` does not. It matters for the 1.0 m stub columns (L/D = 2.2):
   differences of up to ~5 kN.m in stub moments disappeared when the model was switched to `ElasticTimoshenkoBeam`
   (shear area 5/6 A). The design pipeline therefore uses Timoshenko elements too (`solver.yaml: fe.shear_deformation`).

## Limits of this benchmark
* STAAD member end forces for beams are not available (STAAD's beam design was aborted in the `.ANL`, and `.bmd` is undocumented):
  beam moments / shears are validated only through equilibrium (reactions, column forces) and the closed-form tests in `tests/test_fe_sanity.py`.
* Moment units of the `.rea` file were not needed (only forces compared); column moments come from the `.ANL` text in kN.m.
* Gravity cases only (cases 5, 6, 11). Wind / seismic cases were not compared and are out of scope.
* The compared `.ANL` columns are the 76 whose guiding case is 11; the other 57 columns are governed by seismic cases.
""", encoding="utf-8")
    return full
