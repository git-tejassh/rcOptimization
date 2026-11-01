# `fe/` — the structural analysis ("finite element", FE) and data generation

**Plain words:** FE is how a computer finds the forces inside a building. We build the frame in **OpenSeesPy** (free, open-source — replaces the paid
STAAD in the automatic loop), apply the gravity loads, and read off the bending moments, shear forces, axial forces and deflections. One solve takes
about 36 milliseconds. These forces are then judged against IS 456 (see `../codes/`).

| File | What it does |
|---|---|
| `opensees_model.py` | Builds the 3-D frame in OpenSees (one beam element per member, shear deformation included via `ElasticTimoshenkoBeam`) and solves several load cases. Knows the section properties of a rectangle (area, inertia, torsion) with the cracked-section reduction. |
| `analysis.py` | The heart: for one set of member sizes it computes the loads — beam self-weight, brick walls (depth-dependent), slab load shared to beams by the two-way "yield-line" triangle/trapezoid rule, column weight — applies them, solves, draws the moment/shear diagrams and the deflection along every beam, and returns the **design demands per group** (and per column *position class* for Surrogate B). Also contains `FEInput`/`FESettings` (design mode versus STAAD-matching benchmark mode) and an equilibrium check (sum of reactions = total load). |
| `runner.py` | Runs **one design end-to-end**: repair → geometry check → FE (cached per size set) → IS 456 checks → cost and carbon → one flat row. Every design returns exactly one row with a status (`OK`, `GEOM_INFEASIBLE`, `FE_SINGULAR`, `FE_ERROR`, `CHECK_ERROR`, `EQUILIBRIUM_FAIL`) — nothing is ever silently dropped. Also turns stored rows back into demands (`row_to_demands`). |
| `batch.py` | Phase 2: runs all 15,000 designs in parallel worker processes (each with its own OpenSees; at most 8 workers), writes `fe_dataset.parquet`, the failure table and the runtime record. |
| `benchmark.py` | Phase 0b: runs the OpenSees model in "benchmark mode" (STAAD's own material and loads) and compares with STAAD's results — reactions, displacements, column forces/moments, the IS 456 interaction ratio of column 81. Writes `docs/BENCHMARK.md` and `data/results/benchmark.json`. Result: reactions to 1e-5, column axial 3e-5, moments 0.12 %. |
| `staad_reference.py` | Decodes the owner's STAAD result files (`.rea` reactions, `.dsp` displacements — binary, in kip/inch — and the `.ANL` text report) into numbers for the benchmark. Needs the STAAD binaries in `legacy/staad_model/` (not in git; see `docs/LARGE_FILES.md`). |
| `__init__.py` | Marks the folder as a package. |
