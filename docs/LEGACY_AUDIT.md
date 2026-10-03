# Legacy Audit

Date: 2026-10-03. Auditor: Claude (sole engineer on this repo). Everything below was checked against the files, not assumed.
Originals are preserved under `legacy/` (nothing deleted); the pristine pre-restructure state is git tag `snapshot-original`.

## 0. Where the project actually was

The run was started in a git *worktree* of an unrelated home-directory repo (it contained only a diabetes demo). The real
project folder is its parent: `costOptimizationParetoFront7semmajorProject/` (it had `CLAUDE.md`, `PROJECT.md`, the brief PDF and a
sub-folder `RCC_Optimization/` holding the STAAD family + legacy Python). That folder was not a git repo; it is now (own `.git`,
branch `main`). `PROJECT.md` was renamed `project.md` to match the references in `CLAUDE.md` (case-only on Windows).

## 1. File-by-file

| File | What it is | Reusable? | Contradicts brief? | Decision |
|---|---|---|---|---|
| `G+3 RCC FINAL.std` (=`.STD`, `.STD_Modified`, `.sbk`) | STAAD input: 120 joints, 255 members, 4 bays x (X: 5 m) by 3 bays (Z: 5 m), 4 storeys of 3 m + plinth level y=0 + 1 m stub columns to fixed supports at y=-1. One beam section (300x450) and one column section (450x450). Floor loads 4.75 kN/m2 (roof 5.25), live 2.0 (roof 1.5), wall line loads 11.73 (perimeter) / 5.87 (internal) kN/m on beams at all 5 levels, IS 1893/IS 875 wind definitions, 25 combinations. | **Yes - primary geometry/load source** | No | Parsed by `rcopt.geometry.staad_parser`; geometry/loads feed `config/*.yaml` and the FE model |
| `G+3 RCC FINAL_Modified.std` | Identical to the original except beam width `ZD 0.30 -> 0.25` (output of the legacy optimizer). Verified by `diff`: one line differs. | Evidence only | - | Archived. Shows the legacy loop changed exactly one variable pair |
| `G+3 RCC FINAL.ANL` (text, 8605 lines) | STAAD analysis report. Contains the echoed input, base shear (VB = 339.3 kN, T = 0.513 s), and **IS 456 column design results for all 175 columns** (Pu, moments, Muz1/Muy1, interaction ratios). Beam design was aborted by the user ("USER HAS INITIATED ABORT"): **no beam results**. | **Yes - IS 456 column cross-check + gravity cross-check** | - | To be parsed into `data/benchmark/staad_reference.json` (raw file stays gitignored per project.md 13.3) |
| `G+3 RCC FINAL.rea`, `.dsp` (binary) | Reactions / joint displacements for all 35 cases (10 primary + 25 combinations). Format decoded: 35 cases x N nodes x (int32 node + 6 float32), N = 20 supports (.rea, node ids 101-120) / 120 joints (.dsp). **Units are STAAD-internal kip / inch**, not kN / m (check: sum of DL reactions 3952.34 kip x 4.44822 = 17,580 kN, which equals my independent hand total of the model's dead load 17,580 kN; case 11 reactions = 1.5 x (case 5 + case 6) exactly). | **Yes - FE benchmark** | - | To be decoded into `staad_reference.json`; used in `docs/BENCHMARK.md` |
| `.bmd`, `.dbs`, `.dgn`, `.FLD`, `.day`, `.EQL`, `.CFR`, `.num`, `.scn`, `.uid`, `.ULD`, `.slg`, AutoRecovery zip | STAAD binaries/GUI state | No | - | Kept on disk in `legacy/staad_model/`, gitignored |
| `openstaad_handler.py` | Class named OpenSTAAD handler, **but it does not call OpenSTAAD**: `run_analysis()` returns a hard-coded `{"status":"SUCCESS"}` | No (dead stub) | Misleading name | Archived |
| `staad_file_handler.py` | Regex rewrite of `PRIS YD .. ZD ..` for one member range | Idea only | - | Archived. New pipeline never edits STAAD files |
| `rcc_nsga2_optimization.py` | pymoo NSGA-II (pop 100, 100 gen), 8 variables, **continuous** rounded to 25 mm; cost/carbon closed-form; "structural constraints" are 3 hard-coded checks | Cost/carbon *structure* only | **Many - see section 2** | Archived; replaced |
| `Optimization.py` | Runs the above, takes `result.X[0]` (first array element, not a "best compromise"), rewrites STAAD file | No | Same | Archived |
| `plot_pareto_front.py` + two PNGs | Plot of 1,000 LHS points vs "Pareto front"; hard-coded `C:\Users\YASH\...` path | No | - | Archived. The PNG shows the legacy "front" is a **single point** far outside the LHS cloud (about 28 t / 8.4 lakh vs cloud >= 39 t / 10.6 lakh) |
| `README.md` (old) | Describes the standalone mode; links to another machine's Downloads path | No | Calls this "STAAD-driven" while no STAAD call exists | `legacy/README_old.md` |
| `context.txt` | Chat transcript (26 KB) of the project's origin: STAAD + NSGA-II plan, variable ranges, example cost/carbon tables. | Hints only | Says STAAD in the loop, Fe550, wind/seismic in scope, 2000 designs | See section 3 |

## 2. Legacy optimizer: defects found

Verified against the STAAD model (member lengths computed from the `.std`: beams 775.0 m = 400 X + 375 Z over 155 members; storey columns 240.0 m over 80 members; stubs 20.0 m).

1. **Wrong quantities.** `TOTAL_BEAM_LENGTH = 320 m` (real: 775 m), column lengths 56 + 144 = 200 m (real: 240 m, or 260 m with stubs). Volumes/steel/cost/carbon are therefore off by more than 2x for beams.
2. **No structural analysis at all.** Demands are constants: `REQUIRED_MOMENT_KNM = 140`, `REQUIRED_AXIAL_KN = 1800`. Beam capacity is checked against a flexural limit only; no shear, no deflection, no biaxial column check, no min/max steel, no bar fit. Changing section sizes does not change the demand (self-weight ignored).
3. **Continuous relaxation** of reinforcement ratio and rounding of sizes: violates the brief's "no continuous relaxation" rule (Brief s8). Reinforcement is a ratio, not (diameter, count).
4. **Fe550 option** and `fy_idx` branch with 0.44 for xu,max/d: Fe550 is outside the brief's grades (Fe415/Fe500); the 0.44 factor is unverified.
5. **Unsourced cost/carbon**: steel carbon 2.8-2.9 kg/kg, concrete 300-420 kg/m3, rates 5200-6800 INR/m3. No source, no date. (They are higher than the context.txt chat values of 1.8 kg/kg and 250-310 kg/m3 - the two legacy sources disagree with each other.)
6. **Column capacity formula** `0.4 fck (Ac-Asc) + 0.67 fy Asc` is the IS 456 cl. 39.3 axial formula (valid), but it ignores eccentricity entirely - STAAD shows the governing moment case matters (interaction ratios up to 0.99 in the ANL).
7. **Degenerate result.** Because all three constraints are loose, minimising cost and carbon (both monotone in material volume) collapses the front to one point (PNG).
8. `Optimization.py` writes `result.X[0]` into STAAD; the first element of an unsorted Pareto set has no "compromise" meaning.
9. Hard-coded personal path in the plot script; `openstaad_handler` stub claims success without analysing anything.

## 3. Tension with the brief, resolved

* Brief s7: STAAD is *deliberately excluded* from the automated loop. The folder contains a STAAD-flavoured NSGA-II. **Resolution (D0):** legacy STAAD-style code is archived and used only as (a) the geometry/load source and (b) the benchmark. The new pipeline is OpenSeesPy-based and needs no STAAD licence on any OS.
* `context.txt` contradictions with `project.md` (project.md wins): STAAD in loop; wind and seismic loads in scope (project.md: gravity only, seismic = stub); Fe550 (excluded); continuous steel ratios (discretised to bar dia x count); 8-variable genome with a single beam section and single upper/lower column (now 2 beam groups + 2 column groups); 2000 designs / pop 40 (now ~6,500 FE samples, pop 200 x 300 gen); cost/carbon numbers are chat examples, not sourced values (kept only as **provisional** rate placeholders).
* The STAAD model's own settings that the new model must not silently inherit: material E = 2.17e7 kN/m2 and density 23.56 kN/m3 are STAAD's *defaults* and do not correspond to the M30 used in design (`FC 30000`, `FYMAIN 500000`); STAAD analysis uses uncracked sections; wall loads carry a 0.15 m eccentricity (torsion); STAAD includes shear deformation. These must be quantified in `docs/BENCHMARK.md`.
* Design-code facts from the ANL usable as an independent anchor: STAAD min eccentricity `emin = l/500 + D/30` uses the full 3000 mm storey length (column 81: Pu = 775.79 kN, e_min moment 16.29 kN.m = 775.79 x 0.021); STAAD cover 40 mm; STAAD's required-steel minimum is 0.8 % of the *required* concrete area (463.85 mm2 = 0.8 % x 57,981 mm2); STAAD IS 456 interaction ratio reproduces by hand (column 81: Pu/Puz = 0.267, alpha_n = 1.112, (35.20/150.87)^1.112 + (34.65/150.87)^1.112 = 0.393 = STAAD's 0.39). STAAD Puz = 0.45 fck Ac + 0.75 fy Asc reproduces exactly (2901.43 kN).

## 4. What I reuse

* Geometry, section sizes, loads, cover, materials from the STAAD text input.
* Reference results (reactions, displacements, column design forces) for validation.
* The legacy cost/carbon *shape* (volume x factor per grade + steel mass x factor + formwork area x rate) - re-implemented with correct quantities and provisional flags.
* Nothing else: the legacy optimiser is not run anywhere in the new pipeline.
