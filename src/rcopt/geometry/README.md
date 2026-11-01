# `geometry/` — the building frame and the STAAD file reader

**Plain words:** the structure being designed is the owner's G+3 building frame: 4 bays × 3 bays of 5 m, four storeys of 3 m on 1 m stub columns.
This folder builds that skeleton (points and members) and can also read a STAAD.Pro input text file.

| File | What it does |
|---|---|
| `frame_spec.py` | `build_frame()` creates a `FrameSpec` from `config/geometry.yaml`: numbered nodes level by level, every beam, every column and the fixed-base stub nodes, with the optimisation groups (beam levels {0,1,2}/{3,4}; column storeys {0,1}/{2,3}). Everything else (analysis, quantities) works from this object. |
| `staad_parser.py` | Reads a STAAD `.std` text file: units, joint coordinates, member incidences, member sizes, material, supports, floor/member loads. Skips what it does not need (wind/seismic definitions, design commands). Used to (1) prove `config/geometry.yaml` matches the owner's STAAD model, (2) run the benchmark, (3) the strength review of an uploaded file. It remembers the file's length unit and recognises pinned supports. |
| `__init__.py` | Marks the folder as a package. |

The same STAAD reading logic also exists in TypeScript for the website: `web/src/lib/staad.ts` (used for the browser-only quantity estimate).
