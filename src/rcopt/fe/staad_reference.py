"""Decode the STAAD reference results of the owner's model (benchmark source, project.md 7.5).

* ``.rea`` / ``.dsp``: little-endian records ``<i`` node id + ``<6f`` (3 forces/displacements, 3 moments/rotations),
  35 load cases in file order, 20 (supports) / 120 (joints) records per case. STAAD-internal units: kip and inch
  (verified: sum of case-5 reactions 3952.34 kip x 4.44822 = 17,580 kN = independent hand total of the dead load).
* ``.ANL``: text report; IS 456 column design blocks give Pu, moments, Puz, Muz1, Muy1 and the interaction ratio.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from rcopt.config import ROOT

KIP_TO_KN = 4.4482216152605
INCH_TO_MM = 25.4
N_CASES = 35
STD_DIR = ROOT / "legacy" / "staad_model"
STEM = "G+3 RCC FINAL"


def _read_records(path: Path, n_per_case: int) -> tuple[np.ndarray, np.ndarray]:
    dt = np.dtype([("id", "<i4"), ("v", "<f4", 6)])
    rec = np.frombuffer(path.read_bytes(), dtype=dt)
    if rec.size != N_CASES * n_per_case:
        raise ValueError(f"{path.name}: {rec.size} records, expected {N_CASES * n_per_case}")
    rec = rec.reshape(N_CASES, n_per_case)
    return rec["id"][0], rec["v"].astype(float)


def reactions_kN(std_dir: Path = STD_DIR) -> tuple[np.ndarray, np.ndarray]:
    """(support node ids, array [case, node, 6]) in kN / kN.m (moments assumed kip-ft; see BENCHMARK.md)."""
    ids, v = _read_records(std_dir / f"{STEM}.rea", 20)
    v = v.copy()
    v[..., :3] *= KIP_TO_KN
    return ids, v


def displacements_mm(std_dir: Path = STD_DIR) -> tuple[np.ndarray, np.ndarray]:
    """(joint ids, array [case, joint, 6]) with translations in mm and rotations in rad (assumed units)."""
    ids, v = _read_records(std_dir / f"{STEM}.dsp", 120)
    v = v.copy()
    v[..., :3] *= INCH_TO_MM
    return ids, v


_COL = re.compile(r"C O L U M N\s+N O\.\s+(\d+)\s+D E S I G N")


def parse_anl_columns(path: Path | None = None) -> dict[int, dict]:
    """IS 456 column design results of every column block in the STAAD ``.ANL`` report."""
    path = path or STD_DIR / f"{STEM}.ANL"
    text = path.read_text(encoding="latin-1")
    parts = _COL.split(text)
    out: dict[int, dict] = {}
    for k in range(1, len(parts), 2):
        no, blk = int(parts[k]), parts[k + 1]
        g = re.search(r"GUIDING LOAD CASE:\s+(\d+)\s+END JOINT:\s+(\d+)", blk)
        pu = re.search(r"DESIGN AXIAL FORCE \(Pu\)\s*:\s*([-\d.]+)", blk)
        mi = re.search(r"INITIAL MOMENTS\s*:\s*([-\d.]+)\s+([-\d.]+)", blk)
        me = re.search(r"MOMENTS DUE TO MINIMUM ECC\.\s*:\s*([-\d.]+)\s+([-\d.]+)", blk)
        cap = re.search(r"Puz\s*:\s*([-\d.]+)\s+Muz1\s*:\s*([-\d.]+)\s+Muy1\s*:\s*([-\d.]+)", blk)
        ir = re.search(r"INTERACTION RATIO:\s*([-\d.]+)", blk)
        ast = re.search(r"REQD\. STEEL AREA\s*:\s*([-\d.]+)", blk)
        if not (g and pu and mi and cap and ir):
            continue
        out[no] = {
            "guiding_case": int(g.group(1)), "end_joint": int(g.group(2)), "Pu_kN": float(pu.group(1)),
            "M_initial_Z_kNm": float(mi.group(1)), "M_initial_Y_kNm": float(mi.group(2)),
            "M_emin_kNm": float(me.group(1)) if me else None, "Puz_kN": float(cap.group(1)),
            "Muz1_kNm": float(cap.group(2)), "Muy1_kNm": float(cap.group(3)), "IR": float(ir.group(1)),
            "Ast_req_mm2": float(ast.group(1)) if ast else None,
        }
    return out
