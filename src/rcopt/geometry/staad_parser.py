"""Parser for the subset of the STAAD.Pro input language used by ``G+3 RCC FINAL.STD`` (project.md 4.1).

Understood: JOINT COORDINATES, MEMBER INCIDENCES, MEMBER PROPERTY (PRIS YD ZD), DEFINE MATERIAL (E, POISSON,
DENSITY, G), SUPPORTS FIXED, LOAD n ... (SELFWEIGHT, FLOOR LOAD, MEMBER LOAD UNI), LOAD COMB. Anything else
(wind/seismic definitions, concrete design commands) is skipped. Units follow the file: UNIT METER KN.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StaadModel:
    joints: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    members: dict[int, tuple[int, int]] = field(default_factory=dict)
    section_m: dict[int, tuple[float, float]] = field(default_factory=dict)   # member -> (YD, ZD)
    supports: list[int] = field(default_factory=list)
    material: dict[str, float] = field(default_factory=dict)
    selfweight: dict[int, float] = field(default_factory=dict)                # load case -> factor (Y)
    floor_loads: dict[int, list[dict]] = field(default_factory=dict)
    member_loads: dict[int, list[dict]] = field(default_factory=dict)
    combos: dict[int, list[tuple[int, float]]] = field(default_factory=dict)
    titles: dict[int, str] = field(default_factory=dict)


def _ids(tokens: list[str]) -> list[int]:
    """Expand ``1 TO 5 9 11 TO 12`` style member lists."""
    out: list[int] = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and tokens[i + 1].upper() == "TO":
            out.extend(range(int(tokens[i]), int(tokens[i + 2]) + 1))
            i += 3
        else:
            out.append(int(tokens[i]))
            i += 1
    return out


def _logical_lines(text: str) -> list[str]:
    lines: list[str] = []
    buf = ""
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("<!"):
            continue
        if s.endswith("-"):
            buf += s[:-1] + " "
            continue
        lines.append((buf + s).strip())
        buf = ""
    return lines


def parse_staad(path: str | Path) -> StaadModel:
    """Parse a STAAD input file (latin-1: titles contain non-ASCII symbols)."""
    text = Path(path).read_text(encoding="latin-1")
    m = StaadModel()
    block = ""
    case = 0
    sub = ""
    for line in _logical_lines(text):
        up = line.upper()
        if up.startswith("JOINT COORDINATES"):
            block = "joints"
            continue
        if up.startswith("MEMBER INCIDENCES"):
            block = "incid"
            continue
        if up.startswith("MEMBER PROPERTY"):
            block = "prop"
            continue
        if up.startswith("DEFINE MATERIAL"):
            block = "material"
            continue
        if up.startswith("END DEFINE MATERIAL"):
            block = ""
            continue
        if up.startswith("SUPPORTS"):
            block = "supports"
            continue
        if up.startswith("CONSTANTS") or up.startswith("DEFINE ") or up.startswith("PERFORM"):
            block = "skip"
            continue
        mload = re.match(r"LOAD COMB\s+(\d+)", up)
        if mload:
            block, case = "combo", int(mload.group(1))
            m.combos[case] = []
            continue
        mload = re.match(r"LOAD\s+(\d+)\s+LOADTYPE\s+\S+\s+TITLE\s*(.*)", line, re.I)
        if mload:
            block, case, sub = "load", int(mload.group(1)), ""
            m.titles[case] = mload.group(2).strip()
            continue
        if block == "joints":
            for stmt in filter(None, (s.strip() for s in line.split(";"))):
                t = stmt.split()
                m.joints[int(t[0])] = (float(t[1]), float(t[2]), float(t[3]))
        elif block == "incid":
            for stmt in filter(None, (s.strip() for s in line.split(";"))):
                t = stmt.split()
                m.members[int(t[0])] = (int(t[1]), int(t[2]))
        elif block == "prop":
            mp = re.match(r"(.*?)PRIS\s+YD\s+([\d.]+)\s+ZD\s+([\d.]+)", line, re.I)
            if mp:
                for mid in _ids(mp.group(1).split()):
                    m.section_m[mid] = (float(mp.group(2)), float(mp.group(3)))
        elif block == "material":
            t = line.split()
            if t[0].upper() in ("E", "POISSON", "DENSITY", "G"):
                m.material[t[0].upper()] = float(t[1])
        elif block == "supports":
            t = line.split()
            if t[-1].upper() == "FIXED":
                m.supports.extend(_ids(t[:-1]))
        elif block == "combo":
            t = line.split()
            if re.fullmatch(r"[\d.]+", t[0]):
                m.combos[case].extend((int(float(t[k])), float(t[k + 1])) for k in range(0, len(t) - 1, 2))
        elif block == "load":
            if up.startswith("SELFWEIGHT"):
                m.selfweight[case] = float(up.split()[-1])
            elif up.startswith("FLOOR LOAD"):
                sub = "floor"
            elif up.startswith("MEMBER LOAD"):
                sub = "member"
            elif sub == "floor" and "FLOAD" in up:
                t = line.split()
                d = {"w": float(t[t.index("FLOAD") + 1])}
                for key in ("YRANGE", "XRANGE", "ZRANGE"):
                    if key in up:
                        k = t.index(key)
                        d[key] = (float(t[k + 1]), float(t[k + 2]))
                m.floor_loads.setdefault(case, []).append(d)
            elif sub == "member" and " UNI " in f" {up} ":
                mu = re.match(r"(.*?)\sUNI\s+(G[XYZ])\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S+))?", line, re.I)
                if mu:
                    m.member_loads.setdefault(case, []).append({
                        "members": _ids(mu.group(1).split()), "dir": mu.group(2).upper(), "w": float(mu.group(3)),
                        "d1": float(mu.group(4)), "d2": float(mu.group(5)),
                        "d3": float(mu.group(6) or 0.0)})
    return m


def staad_grid(model: StaadModel, ndigits: int = 2) -> tuple[list[float], list[float], list[float]]:
    """Sorted unique x, y, z coordinates (rounded; STAAD's 3.00001 style noise removed)."""
    xs = sorted({round(p[0], ndigits) for p in model.joints.values()})
    ys = sorted({round(p[1], ndigits) for p in model.joints.values()})
    zs = sorted({round(p[2], ndigits) for p in model.joints.values()})
    return xs, ys, zs
