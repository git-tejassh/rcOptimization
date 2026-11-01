# `seismic/` — placeholder for earthquake design (NOT implemented)

The project is **gravity-only**. This folder only defines the *shape* that a future earthquake (IS 1893) extension would have, so the rest of the code does
not need to change. Every function deliberately raises `NotImplementedError`, so nothing can pretend to be seismic design.

| File | What it does |
|---|---|
| `__init__.py` | `SeismicSpec` (zone, importance, response reduction…), and stub functions for base shear (IS 1893 cl. 6.4.2), seismic load combinations (IS 456 Table 18) and ductile detailing checks (IS 13920). See `docs/SEISMIC_EXTENSION.md` for what would be needed. |

Why it matters: the STAAD report shows 57 of the 133 columns are governed by seismic cases, so **the optimised designs are not complete code-compliant designs of the building**.
