# project.md — Technical Specification

**Title:** Surrogate-Assisted Multi-Objective Optimization of RC Structures for Cost and Embodied Carbon
**Method:** OpenSeesPy-generated data → ML surrogates → constrained NSGA-II (pymoo) → Pareto front → FE re-verification
**Owner:** Tejas Shrivastava ("Taru"), B.Tech Civil (final year), MANIT Bhopal — major project, 7th semester only
**Companion files:** `CLAUDE.md` (process rules — read first), `RC-Optimization-Project-Brief.PDF` (guide-facing brief),
STAAD model family `G+3 RCC FINAL*` and legacy Python files (see `CLAUDE.md` §2)

---

## 1. Goal in one paragraph

Build a reproducible pipeline and dashboard that, for a regular RC moment-resisting frame (G+3 default, G+3…G+5 configurable),
produces a **validated Pareto front of construction cost vs. embodied carbon** over discrete, buildable, IS-standard design options,
every point satisfying IS 456:2000 strength and serviceability limits (gravity loading). The surrogate model's reliability is
**measured and reported**, not assumed, by re-verifying a stratified subset of Pareto designs with ground-truth analysis.

**Honest-novelty framing (must appear in report and UI "About" page):** NSGA-II for RC frame cost optimization is published since ≥2016
(e.g. Kaveh et al., J. Civil Eng. & Management, 2016); surrogate-assisted NSGA-II for cost/carbon exists in adjacent domains (concrete mix design).
This project's contribution is a **carefully validated, India-contextualized application**: IS-code basis, discrete IS-standard
sections/bars/grades, Indian-context carbon factors with gaps flagged, and a reported surrogate-vs-ground-truth reliability result.

---

## 2. Success criteria (from Brief §13, made testable)

| # | Criterion | How measured |
|---|---|---|
| S1 | Non-dominated Pareto front produced (surrogate-driven NSGA-II) | `data/results/pareto_surrogate.parquet`, ≥ 25 distinct non-dominated points |
| S2 | ≥ 90 % of the re-verified subset matches surrogate predictions within tolerance **and** is truly feasible | `data/results/verification.json`; tolerance in `config/solver.yaml` (default: abs. error ≤ 0.05 on utilization ratios, ≤ 5 % on deflection) |
| S3 | Surrogate validation error reported overall and **near the feasibility boundary** | `data/results/surrogate_metrics.json` |
| S4 | Compute savings quantified: surrogate-NSGA-II vs. direct-FE-NSGA-II (evaluations, wall-clock, hypervolume parity) | `data/results/compute_comparison.json` |
| S5 | All discrete choices come from IS-standard option lists | `tests/test_design_space.py` |
| S6 | Pipeline reproducible end-to-end from code + config | `make setup && make all` on clean clone |
| S7 | Unfavorable results reported (failed verifications, weak boundary accuracy, narrow front, provisional data) | Visible in report and UI |

---

## 3. Scope

**In scope**
- Regular-plan RC moment frame, gravity loads (DL + LL per IS 875 Parts 1–2), IS 456:2000 limit-state design.
- Beams and columns (with slabs entering as loads; slab design/quantities excluded unless added as a fixed-cost constant — default excluded and stated).
- Cost and cradle-to-site embodied carbon of **frame materials** (concrete, reinforcement; formwork cost included, formwork carbon excluded by default and flagged).
- Discrete IS-standard sections, bar diameters, grades.

**Out of scope (explicit)**
- Foundations; construction sequencing carbon; operational carbon; steel (IS 800) members (optional only if guide requires — default **excluded**; the brief lists IS 800 "if steel members included");
  multiple typologies; seismic design (IS 1893 / IS 13920) — **Phase 6 stub only**.

**Mandatory caveat (every report page / UI design page):** *Designs are checked for gravity loading only. A real building in India must also
be designed for seismic (IS 1893:2016) and, where applicable, wind (IS 875-3). Bhopal falls in a low-seismicity zone, but code-mandated
seismic design still applies — confirm the zone from IS 1893 (Part 1):2016 Table/Annex. Results are for design-stage trade-off exploration, not final design.*

---

## 4. Geometry & loading (defaults, all in `config/geometry.yaml` and `config/loads.yaml`)

### 4.1 Source of truth
1. **Parse the STAAD text input** (`G+3 RCC FINAL_Modified.std` and/or the 12 KB `G+3 RCC FINAL` text; diff them) with `rcopt.geometry.staad_parser`:
   joints, members, member property assignments, materials, supports, load cases (DL, LL, floor loads, member loads), combinations.
2. Convert to a **parametric frame description** (`FrameSpec`): bay lengths in x and y, storey heights, plan regularity flag, member lists by
   type (beam X, beam Y, column) and level, tributary slab loads, wall (infill) line loads.
3. If parsing fails or data are incomplete → fall back to defaults below and log it in `docs/DECISIONS.md`.

### 4.2 Fallback defaults
- Plan: 3 bays × 3 bays, 4.0 m bays (config), storey height 3.0 m, plinth/ground level per STAAD if available, base fixed.
- Levels: G+3 (4 floors + roof). Configurable to G+5.
- Materials (design): Ec = 5000√fck MPa (IS 456 cl. 6.2.3.1); unit weight RC = 25 kN/m³.
- Dead: self-weight (computed from sections — **self-weight must update with design variables**), floor finish 1.0–1.5 kN/m² (config), slab self-weight from slab thickness
  (default 125 mm, config; slab is not optimized), brick infill wall line load on perimeter beams (config; from STAAD if present).
- Live: IS 875 Part 2 — residential 2.0 kN/m², roof 1.5 kN/m² (config; verify the intended occupancy from the STAAD model).
- Load transfer: two-way slab → beams via IS 456 Annex/yield-line tributary (triangular/trapezoidal) **or** simple tributary area; choose one, document in DECISIONS.md.
- Combinations: **Strength:** 1.5 (DL + LL). **Serviceability:** 1.0 (DL + LL) (IS 456 Table 18 / cl. 36.4).

### 4.3 Structural model
- OpenSeesPy 3D (preferred) or 2D plane frame (acceptable if documented and the STAAD benchmark is done on an equivalent 2D slice).
- `elasticBeamColumn` elements; geomTransf Linear (P-Δ off; gravity only); rigid-diaphragm optional.
- **Cracked-section stiffness modifiers** (config; documented assumption): beams 0.35·Ig, columns 0.70·Ig for strength analysis (ACI-style, commonly used with IS 456 practice);
  for **deflection**, use effective-moment-of-inertia per IS 456 Annex C or the span/depth method (cl. 23.2) as a cross-check (see §6.3).
  Record in `ASSUMPTIONS.md`; the same modifiers must be applied in the STAAD benchmark comparison.
- Note: elastic analysis ⇒ the FE response depends on **member sizes and Ec (fck) only — not on reinforcement**. This is exploited in Surrogate B (§8.2).

---

## 5. Design space (`config/design_space.yaml`)

### 5.1 Grouping (keeps dimensionality tractable and designs buildable)
Defaults (derive from STAAD storey/member structure; configurable):
- **Beam groups:** 2 (e.g. levels 1–2, levels 3–roof). Same section for X and Y beams within a group unless config says otherwise.
- **Column groups:** 2 (storey bands) × optionally corner/edge/interior types (default: storey bands only).
- **Global material grades:** one concrete grade, one steel grade (configurable per group as an extension).

### 5.2 Variables
| Variable | Type | Options (from Brief §8; keep in YAML) |
|---|---|---|
| Beam width `b_beam` | discrete | 230–450 mm in 25 mm steps (default; 230, 250, 300, 350, 400, 450 acceptable — decide, record) |
| Beam depth `D_beam` | discrete | 300–750 mm in 25 or 50 mm steps |
| Beam bottom bars | discrete pair (dia, count) | dia ∈ {12, 16, 20, 25, 32 *optional*}, count ∈ [2, 8] subject to fit |
| Beam top bars | discrete pair (dia, count) | dia ∈ {12, 16, 20, 25}, count ∈ [2, 8] subject to fit |
| Beam stirrups | derived | 2-legged, dia fixed 8 mm (config), spacing **designed** by §6.1 shear routine, rounded to 25 mm, must be ≥ 75 mm & ≤ limits |
| Column width / depth | discrete | 230–600 mm in 25/50 mm steps; square and rectangular allowed; `D ≥ b`; min 230 |
| Column bars | discrete pair (dia, count) | dia ∈ {12, 16, 20, 25, 32}, count ∈ {4, 6, 8, 10, 12, 16} placed symmetrically (document layout rule) |
| Concrete grade | discrete | M20, M25, M30, M35, M40 |
| Steel grade | discrete | Fe415, Fe500 (Fe500D/Fe550 only if guide asks) |

> **Deviation D1 (flag to owner/guide):** Brief §8 lists "longitudinal reinforcement ratio — continuous, bounded" but also forbids continuous
> relaxation presented as buildable. Resolved here: reinforcement is encoded as **(bar diameter, bar count)**; the ratio is *derived* and constrained to IS 456 bounds.
> This satisfies the brief's own hard-constraint rule.

### 5.3 Genome encoding
Every variable is encoded as an **integer index into its option list** (so pymoo handles all variables uniformly, no rounding of floats into "fake" sizes).
`rcopt.design.decoder` maps genome → physical design → `Design` dataclass; and `Design` → feature vector for the surrogate.
Geometric feasibility (bars fit in width with cover and minimum spacing; column bar layout valid; `D_beam` ≥ minimum for span) is a **pre-FE check** returning a reason code.

---

## 6. IS 456:2000 checking module (`src/rcopt/codes/`)

> Every function: docstring with clause number, units, assumptions. Every table: transcribed to YAML with source note, unit-tested, and listed in `ASSUMPTIONS.md` as **"owner must verify against own copy of IS 456 / SP 16"**.

### 6.1 Beams
- **Effective depth** `d = D − cover − stirrup_dia − bar_dia/2` (cover default 25 mm mild exposure; config by exposure per Table 16 — **record chosen exposure**).
- **Flexure (cl. 38.1, Annex G):** `xu,max/d` = 0.48 (Fe415), 0.46 (Fe500) (cl. 38.1 table).
  `Mu,lim = 0.36·fck·b·xu,max·(d − 0.42·xu,max)`.
  Singly reinforced: `xu = 0.87·fy·Ast/(0.36·fck·b)` capped at `xu,max`; `Mu = 0.87·fy·Ast·d·(1 − Ast·fy/(b·d·fck))` (Annex G-1.1(b)).
  Doubly reinforced (when `Mu_demand > Mu,lim` and compression steel provided): Annex G-1.2 with `fsc` from strain compatibility at `d'/d`.
  Treat sections as rectangular (conservative for sagging T-action; state it). Sagging checks use bottom steel; hogging checks (supports) use top steel.
  **Utilization** `U_flex = Mu_demand / Mu_capacity` (capacity from *provided* steel).
- **Min/max steel (cl. 26.5.1.1):** `Ast,min ≥ 0.85·b·d/fy`; `Ast,max ≤ 0.04·b·D`.
- **Shear (cl. 40):** `τv = Vu/(b·d)`; `τc` from **Table 19** (function of `pt = 100·Ast/(b·d)` and grade); `τc,max` from **Table 20**;
  require `τv ≤ τc,max`. If `τv > τc`: `Vus = Vu − τc·b·d`, `sv = 0.87·fy·Asv·d / Vus` (cl. 40.4). Min shear steel: `Asv/(b·sv) ≥ 0.4/(0.87·fy)` (cl. 26.5.1.6).
  Max stirrup spacing: `min(0.75d, 300 mm)` (cl. 26.5.1.5). `U_shear = τv / τc,max` plus feasibility of a valid spacing.
- **Bar spacing/fit (cl. 26.3.2):** clear horizontal spacing ≥ max(bar dia, aggregate size + 5 mm [default 20 mm agg → 25 mm]) and ≥ a practical 25 mm minimum (config); bars must fit in a single/double layer; beyond 2 layers → infeasible (config).
- **Deflection (cl. 23.2.1):** span/effective-depth check: basic ratio 20 (simply supported) / 26 (continuous) × modification factor for tension steel (Fig. 4, uses `fs` and `pt`) × compression-steel factor (Fig. 5). Used as *secondary* check and cross-validation of the FE deflection.

### 6.2 Columns
- **Slenderness (cl. 25.1.2):** `le/D` and `le/b`; effective length from Annex E (braced/unbraced per frame behavior; **gravity-only frame → state the assumption and use the conservative option unless STAAD model indicates otherwise**). If `le/D > 12` apply additional moments (cl. 39.7.1).
- **Minimum eccentricity (cl. 25.4):** `emin = max(l/500 + D/30, 20 mm)` in each direction.
- **Axial capacity:** `Puz = 0.45·fck·Ac + 0.75·fy·Asc`.
- **Uniaxial capacity** `Mux1, Muy1` at the given `Pu`: strain-compatibility P–M interaction with the IS 456 stress block and steel stress–strain per cl. 38.1 / SP 16 (Fe415/Fe500 design curves).
  Implement numerically (layer-by-layer along the depth); validate against SP 16 chart points (spot tests).
- **Biaxial (cl. 39.6):** `(Mux/Mux1)^αn + (Muy/Muy1)^αn ≤ 1`, `αn` linear 1.0 at `Pu/Puz ≤ 0.2` to 2.0 at `≥ 0.8`.
  **Utilization** `U_col` = LHS of the interaction equation (≤ 1.0).
- **Steel limits (cl. 26.5.3.1):** `0.8 % ≤ pt ≤ 4 %` (design cap 4 % for lap practicality; code max 6 %), min 4 bars (rectangular) with min dia 12 mm; tie design per cl. 26.5.3.2 (dia ≥ max(bar/4, 6), spacing ≤ min(b, 16·bar dia, 300 mm)).
- **Strong-column/weak-beam** is a seismic criterion — **not** enforced in gravity-only scope (Phase 6 stub).

### 6.3 Deflection constraint (FE-based, per brief)
`δ_max,service ≤ L/250` (total, IS 456 cl. 23.2(a)) from the serviceability combination; additionally **report** `≤ L/350 or 20 mm` after-partition limit (cl. 23.2(b)) as a secondary diagnostic (not a hard constraint unless config says so).
Account for creep/shrinkage per IS 456 Annex C **or** state that long-term effects are covered only through the span/depth check. Record the choice.

### 6.4 Responses recorded per FE run
Per group: max sagging `Mu`, max hogging `Mu`, max `Vu` (beams); max `Pu`, `Mux`, `Muy` (columns); max beam deflection ratio `δ/L`; **plus** the derived utilizations `U_flex`, `U_shear`, `U_col` and the constraint-violation vector `g`.
Store demands *and* utilizations — Surrogate B needs the demands.

---

## 7. Validation of the pipeline itself (do this before generating data)

### 7.1 Why
A wrong IS-check or a mis-built FE model invalidates everything downstream while looking plausible. This section is the integrity firewall.

### 7.2 Anchor tests (`tests/test_is456_anchors.py`)
- **Flexure:** `Mu,lim/(b·d²)` — Fe415: M20 ≈ 2.76, M25 ≈ 3.45, M30 ≈ 4.14 N/mm² (tolerance 0.5 %). Fe500 computed with cl. 38.1 values (0.46) — report the value and note SP 16 lists a marginally different number because it uses 0.456 (tolerance 1 %).
- **Table 20 `τc,max`:** M20 2.8, M25 3.1, M30 3.5, M35 3.7, M40 4.0 N/mm².
- **Table 19 `τc`:** spot values — (pt 0.5 %, M20) = 0.48; (pt 1.0 %, M20) = 0.62 N/mm². Implement linear interpolation in `pt`; test interpolation at midpoints.
- **Column:** pure axial `Puz` hand value; uniaxial capacity at `Pu = 0` equals beam-type flexure capacity of the symmetric section (within 2 %); `αn` endpoints (1.0 / 2.0) and midpoint (1.5 at `Pu/Puz = 0.5`).
- **Hand-calculation documents:** `docs/hand_calcs/beam_example.md` and `column_example.md` — fully worked numbers (done independently of the code path, e.g. via a minimal script that *only* uses the closed formulas), and the unit tests compare the module against them. **The owner will hand-verify at least one beam and one column — make this easy** (show intermediate values).

### 7.3 Determinism & units
Round-trip tests for the decoder (genome → design → genome), unit tests for all unit conversions, seed-reproducibility test (same seed ⇒ identical design matrix).

### 7.4 FE model sanity
- Single-bay cantilever and simply supported beam vs. closed-form `wL⁴/(8EI)`, `5wL⁴/(384EI)`, `wL²/12` fixed-end moments (tolerance 0.1 %).
- Equilibrium check: sum of vertical reactions = total applied vertical load (tolerance 0.1 %) for the full frame, every run (cheap; also logged as a status check).

### 7.5 STAAD cross-check (benchmark)
Reproduce the **existing G+3 RCC STAAD model** (geometry, sections, loads from `G+3 RCC FINAL*`) in OpenSeesPy with identical section sizes, modifiers and loads. Compare member end forces (selected beams/columns) and joint displacements against the STAAD `.ANL` report if readable (else against values the owner can export). Report: max/mean relative differences table in `docs/BENCHMARK.md`. Tolerance target: forces within 5 %, deflections within 10 % (differences from stiffness modifiers, self-weight, slab load distribution must be identified and explained, not hidden). If STAAD results are unreadable, state it and skip — do not fabricate a comparison.

---

## 8. Data → surrogate → optimization

### 8.1 Phase 1 — Sampling (`rcopt.sampling`)
- Base design matrix **N = 5,000** (config; brief says 2–5k; FE is cheap here, so use the top of the range). Seeded.
- **Discrete-aware LHS:** stratified Latin hypercube on the unit cube, each coordinate mapped to option **indices** (equal-probability bins per option list). Do **not** sample continuous values and snap afterwards without stratification.
- **Enrichment:** because uniform sampling yields mostly infeasible designs (undersized members), add a second stratum (default 30 % of N) drawn from a **biased-to-feasible** proposal: reject candidates that fail cheap analytic pre-checks (geometry fit, `pt` bounds, gross capacity ≥ crude demand estimate). Record each row's `sample_stratum` (`lhs` / `biased`).
- Output `data/processed/design_matrix.parquet`. Sanity script: no negative effective depth, `pt` in bounds, bars fit; report counts per rejection reason.

### 8.2 Phase 2 — FE data generation (`rcopt.fe.runner`)
- For each design: build model → run gravity cases → extract §6.4 responses → run IS checks → append row.
- Status codes: `OK`, `GEOM_INFEASIBLE` (pre-FE), `FE_SINGULAR`, `FE_ERROR`, `CHECK_ERROR`, `EQUILIBRIUM_FAIL`. **All rows kept** in `data/processed/fe_dataset.parquet`; `data/results/failure_table.csv` summarizes.
- Record per-run wall time; report mean FE time (**needed for S4**).
- Parallel with `joblib`; each worker isolates OpenSees state (`ops.wipe()` per run; separate processes).

### 8.3 Phase 3 — Surrogates (`rcopt.surrogate`)
Train **two variants**, compare:
- **Surrogate A (brief-faithful):** inputs = full genome features; outputs = continuous `U_flex_max`, `U_shear_max`, `U_col_max`, `defl_ratio_max` (one regressor per output, XGBoost default; also fit a Random Forest or LightGBM-free baseline for comparison). Continuous outputs, **not** a feasible/infeasible classifier, so the optimizer sees a violation gradient.
- **Surrogate B (hybrid, Deviation D2):** inputs = **sizes + fck only** (the only things FE demand depends on); outputs = demands (§6.4) and deflection ratio; **utilizations computed exactly by the analytic IS 456 module** from predicted demands and the design's reinforcement. Expected to be more accurate and cheaper because capacity (reinforcement-dependent) is closed-form.
> **D2 rationale:** Brief's surrogate would waste capacity learning a closed-form function of bar choice. B tests that hypothesis. A remains the headline per the brief; B is reported alongside. State both honestly; whichever wins on near-boundary error is flagged for the guide.
- Feature engineering allowed: derived geometry (e.g. `b·D³`, `pt`, `d`, span/depth).
- Splits: random hold-out (20 %) **and** a **boundary hold-out** (rows with any true utilization/deflection ratio in [0.85, 1.15]) — report metrics on both. Group K-fold CV (5-fold). Hyper-parameter tuning via CV only; the verification set (Phase 5) is never used for tuning.
- Metrics per output: R², MAE, RMSE, max error, 95th-percentile abs error; **classification-style** feasibility agreement (does predicted `g ≤ 0` match true?) with confusion matrix near the boundary.
- Plots: parity plots, residual vs. value, feature importances (`data/results/figures/`).
- **One active-learning round (required):** select N_AL (default 500) designs in the surrogate's high-uncertainty / near-boundary region (use ensemble spread or residual-proximity to `g = 0`), run through FE, append to dataset, retrain, report before/after metrics.
- Save with `joblib` + XGBoost native JSON (`models/`), plus `models/manifest.json` (config hash, dataset hash, metrics, timestamp).

### 8.4 Phase 4 — Optimization (`rcopt.optimize`)
- **Problem:** minimize `[Cost, Carbon]`; constraints `g(x) ≤ 0` (pymoo convention): `defl_ratio − 1`, `U_flex − 1`, `U_shear − 1`, `U_col − 1`, `pt` bounds (min/max), geometric-fit violations (as continuous slack or 1/0 penalty — document), min-shear-steel / spacing validity.
- **Algorithm:** pymoo ≥ 0.6 NSGA-II, integer-index genome (`IntegerRandomSampling`, SBX/PM with rounding repair — or `MixedVariableGA`; choose and document), constrained-domination (pymoo default).
  Defaults (config): population 200, generations 300, seeds 1–5 (minimum five independent runs).
- **Three configurations:**
  1. **Surrogate-NSGA-II (A)** — headline per brief.
  2. **Surrogate-NSGA-II (B)** — hybrid.
  3. **Direct-FE-NSGA-II (baseline)** — same GA, constraints from live OpenSeesPy + analytic checks. *Why:* an elastic frame analysis costs milliseconds, so direct optimization may be feasible. The comparison **tests whether the surrogate is actually worth it** — this is an honest, reportable result either way.
- **Surrogate safety margin:** option `margin_q` (default: use the 95th-percentile boundary absolute error from §8.3) so the optimizer targets `U ≤ 1 − margin`. Run both with and without margin; report the effect on verification pass rate.
- **Metrics:** hypervolume (fixed reference point from nadir of pooled fronts, same for all configs), spacing, number of non-dominated points, convergence curve (HV vs. evaluations), total evaluations, wall-clock time. Surrogate speed-up = (direct FE time) / (surrogate time incl. one-time data-generation + training cost — **include the amortized data-generation cost; do not hide it**).
- Pooled non-dominated filtering across seeds → final fronts saved to `data/results/pareto_*.parquet`.

### 8.5 Phase 5 — Verification (`rcopt.verify`)
- Select **20–30 designs** (default 30) from the headline front: stratified along the cost axis (equal-quantile bins) **plus** the 5 designs with the smallest predicted constraint slack (boundary-closest — where surrogates are weakest, Brief §11).
- Re-run through OpenSeesPy + IS 456 checks. Per design record predicted vs. true responses, errors, truly-feasible flag, tolerance pass flag.
- Output `data/results/verification.json` with: pass rate, list of **failures with reasons**, error stats. Pass rule: truly feasible **and** within tolerance. S2 threshold 90 % is **reported against, not engineered toward** (no re-selection after seeing results).
- Also verify the **entire** pooled front cheaply (it's FE-cheap): report the fraction of the whole front that is truly feasible, and the *true* front vs. predicted front gap (hypervolume of true re-evaluated front). Full-front re-evaluation is an extra finding; the 20–30 subset remains the formal reported check.

---

## 9. Cost & embodied carbon

### 9.1 Quantities (`rcopt.cost_carbon.quantities`)
Per design: concrete volume by grade (m³) from sections × member lengths (net of overlaps — document the rule, e.g. beams span clear between columns; slab excluded);
reinforcement mass (kg) = longitudinal (bars × lengths + lap/development allowance, config) + stirrups/ties (computed from designed spacing) × 7850 kg/m³;
formwork contact area (m²): beam sides + soffit, column perimeter × height.

### 9.2 Cost (`config/cost_rates.yaml`)
Rates per: concrete by grade (₹/m³, placed), reinforcement (₹/kg, supplied-cut-bent-placed), formwork (₹/m²). **Do not invent rates.**
Each rate carries `value`, `unit`, `source`, `date`, `status` (`sourced` | `provisional`). Preferred sources: the owner's family building-materials
business (Essco, Bhopal) for current local cement/steel prices — leave clearly labeled placeholders for the owner to fill — and the CPWD DSR / MP PWD SOR as a published fallback.
If no verified value is available, use a provisional placeholder, mark `status: provisional`, and surface the banner everywhere.
Note: concrete grade cost increments (M20→M40) and the steel-vs-concrete price ratio drive trade-offs; the sensitivity study (§9.5) covers this.

### 9.3 Embodied carbon (`config/carbon_factors.yaml`) — scope: cradle-to-site (A1–A4)
- Baseline: **ICE database (University of Bath)** — fetch the current version's concrete-by-strength and reinforcing-steel factors; record version, table, row, value, unit.
  ICE factors are A1–A3; A4 (transport to site) is added via a configurable transport distance × factor (default plausible Bhopal-region distances, **provisional**).
- **India-adaptation, explicitly flagged:** concrete carbon is dominated by cement content. Derive per-grade concrete factors from **typical mix proportions** (IS 10262-style cement content per grade, config) × cement factor (OPC/PPC, with India-specific EPD/literature values where findable; else ICE and flagged). Reinforcement: India's steel mix (BF-BOF vs. scrap/EAF vs. DRI-induction) differs from ICE's global average — if no verified Indian factor is found, use ICE and flag it.
- Every factor: `value`, `unit`, `source`, `confidence` (`high|medium|low`), `india_specific` (`true|false`), `status`.
- **Deliverable (Brief §4 secondary objective):** `docs/CARBON_DATA_AUDIT.md` — a table of which factors were available India-specific vs. adapted vs. assumed. This gap is itself a reportable finding.
- Never present provisional carbon values as final; the UI banner and report must say which results depend on them.

### 9.4 Expected behavior of the Pareto front (to avoid mis-reading)
Cost and carbon are both dominated by material volume (concrete + steel), so they are strongly correlated; the front may be **narrow**. The genuinely
interesting trade-offs come from (i) concrete grade (higher grade → smaller sections but more cement per m³), (ii) steel grade and quantity (steel is carbon-intense per ₹),
(iii) section-size vs. reinforcement balance. A narrow front is a **finding** — report it, show the correlation, and show which variables create the spread.
Do not change objectives or rates to widen it.

### 9.5 Sensitivity (cheap, required)
Re-evaluate the final front's designs and re-run the headline optimization under ±20 % on (a) steel ₹/kg, (b) cement carbon factor, (c) steel carbon factor.
Report whether the Pareto ordering/shape and the recommended trade-off region are robust. Save `data/results/sensitivity.json`.

---

## 10. Phase 6 — Seismic hook (stub only)

Create `rcopt/seismic/` with interfaces (`SeismicSpec`, equivalent-static base shear per IS 1893:2016, IS 13920 detailing check signatures) raising `NotImplementedError`
with a clear message, and a `docs/SEISMIC_EXTENSION.md` describing what would change (load combinations 1.2(DL+LL±EL), 1.5(DL±EL), 0.9DL±1.5EL; drift limit 0.004h; strong-column/weak-beam; ductile detailing constraints; larger FE responses).
**No seismic results may be claimed.** This is deliberately deferred per Brief §5.

---

## 11. Web UI (`web/`) and API (`api/`)

### 11.1 Stack
Vite + React + TypeScript + Tailwind; charts with `plotly.js-basic-dist-min` (scatter hover/selection) and/or Recharts; no server runtime needed.
Data: `web/public/data/*.json` produced by `rcopt.report.export_json` (`make export`). Schema-validated (pydantic on export, TS types on import).

### 11.2 Pages
1. **Overview** — project summary, headline numbers (HV, front size, verification pass rate, surrogate speed-up), honest-novelty statement, gravity-only caveat, provisional-data banner (conditional).
2. **Design space** — table of variables, option lists, constraints (read from `design_space.json`), geometry sketch of the frame (SVG: plan + elevation with the group coloring).
3. **Pareto explorer (main page)** — cost vs. carbon scatter for: surrogate-A front, surrogate-B front, direct-FE front, verified subset overlaid (verified = ✓ green ring, failed = ✕ red). Toggle fronts, color-by (concrete grade / steel grade / beam depth / column size), hover tooltip, click a point → **design detail drawer**: sections per group, reinforcement layout (bar dia × count), grades, quantities (concrete m³, steel kg, formwork m²), cost and carbon breakdown (stacked bars), true utilization ratios, deflection ratio, verification status. Export selected design(s) to CSV/JSON; "download full front CSV".
4. **Surrogate performance** — parity plots, residual histograms, metrics tables (overall vs. boundary hold-out; A vs. B; before vs. after active learning), confusion matrix at the feasibility boundary, feature importance.
5. **Verification** — table of the 20–30 verified designs: predicted vs. true, error, pass/fail; failures highlighted red with reason; pass-rate gauge vs. the 90 % target (shown as measured, not as pass/fail theater).
6. **Compute comparison** — evaluations, wall-clock (incl. amortized data-gen), hypervolume-vs-evaluations convergence curves for surrogate vs. direct FE; plain statement of whether the surrogate paid off.
7. **Sensitivity** — front shifts under ±20 % factors.
8. **Data provenance & assumptions** — every cost rate and carbon factor with source/confidence/status; list from `ASSUMPTIONS.md`; downloadable.
9. **Live evaluator (local only)** — choose a design via dropdowns; call the API: surrogate prediction (A and B) and, on request, ground-truth FE + IS check; show side by side. Hidden with an explanatory note when `VITE_API_URL` isn't reachable (static/Vercel deployment).

### 11.3 UX requirements
Responsive; dark/light; accessible color choices (don't rely on red/green alone — add icons); no console errors; loads < 3 s on a laptop with the data bundle < ~10 MB (downsample dense point clouds, keep the full front downloadable).
`web/README.md` with `npm i && npm run dev` and `npm run build`.

### 11.4 API (`api/`, FastAPI, local)
`GET /health`, `GET /design-space`, `GET /pareto/{variant}`, `GET /verification`, `POST /evaluate/surrogate`, `POST /evaluate/fe`, `POST /evaluate/cost-carbon`.
Pydantic request/response models; CORS for `http://localhost:5173`; `make api` runs `uvicorn api.main:app --reload`. Smoke tests via `TestClient`.

### 11.5 Deployment
- **Local:** `make web-dev` (+ `make api` for live evaluator).
- **Vercel:** project root `web/`, framework Vite, output `dist`; `vercel.json` with SPA rewrites; commands documented in `docs/DEPLOY.md` (`npm i -g vercel`, `vercel login`, `vercel --prod`) — Claude cannot authenticate to Vercel, so only prepare.
- **Alternative:** GitHub Pages workflow (optional second workflow file) for static hosting.
- **API hosting (optional):** `Dockerfile` for Render/Railway/Fly; documented but not required.

---

## 12. Documentation deliverables (`docs/`)

| File | Content |
|---|---|
| `LEGACY_AUDIT.md` | What each original file is, reusability, contradictions with the brief, decisions |
| `DECISIONS.md` | Dated log of every ambiguous call with reversal instructions |
| `ASSUMPTIONS.md` | Every assumption and every provisional value, with source/confidence and an **"owner must verify"** column (IS tables, cover/exposure, load values, rates, factors) |
| `BENCHMARK.md` | OpenSeesPy vs. STAAD comparison (or why not possible) |
| `CARBON_DATA_AUDIT.md` | Indian-context carbon factor availability audit |
| `hand_calcs/` | Independent worked beam & column examples used by tests |
| `SEISMIC_EXTENSION.md` | Phase 6 stub description |
| `DEPLOY.md` | Local, Vercel, GitHub Pages, API hosting |
| `REPORT_DRAFT.md` | Report skeleton following the brief's structure, **filled with real numbers/figures from `data/results/`** (abstract, literature position, method, results, verification, limitations, conclusions). Figures saved to `docs/figures/` |
| `VIVA_PREP.md` | 15–20 likely examiner questions with defensible, evidence-backed answers (e.g. "why a surrogate if FE takes milliseconds?", "why not seismic?", "why is the front narrow?", "how do you know IS checks are right?") |

---

## 13. Repository layout, config files, Makefile

### 13.1 Layout
```
config/
  geometry.yaml  loads.yaml  design_space.yaml  cost_rates.yaml  carbon_factors.yaml
  is456_tables.yaml  solver.yaml  surrogate.yaml  optimize.yaml  verify.yaml
src/rcopt/
  config.py                 # pydantic-validated loaders, config hashing
  geometry/                 # staad_parser.py  frame_spec.py
  fe/                       # opensees_model.py  analysis.py  runner.py
  codes/                    # is456_tables.py  beam.py  column.py  detailing.py  deflection.py
  design/                   # variables.py  decoder.py  geometric_feasibility.py  constraints.py
  sampling/                 # discrete_lhs.py  biased_sampler.py
  cost_carbon/              # quantities.py  cost.py  carbon.py  sensitivity.py
  surrogate/                # features.py  train.py  evaluate.py  active_learning.py  predict.py
  optimize/                 # problem.py  run_surrogate.py  run_direct.py  metrics.py
  verify/                   # verify_pareto.py  full_front_check.py
  report/                   # figures.py  export_json.py  report_draft.py
  seismic/                  # stub (Phase 6)
  cli.py                    # typer: `rcopt phase0..5`, `rcopt all`, `rcopt export`
scripts/                    # thin wrappers
tests/                      # unit + slow marks
api/main.py  api/schemas.py
web/                        # Vite app
legacy/                     # original files
```

### 13.2 Makefile targets (and a PowerShell mirror `make.ps1`)
`setup` (venv + install + npm i), `audit`, `phase0`…`phase5`, `all` (0→5 + export), `test`, `test-slow`, `lint`, `export`, `web-dev`, `web-build`, `api`, `clean`.

### 13.3 `.gitignore` (minimum)
`.venv/ __pycache__/ *.pyc node_modules/ web/dist/ .env .DS_Store`
STAAD binaries/outputs: `*.bmd *.ANL *.dbs *.dgn *.dsp *.FLD *.rea *.day *.EQL *.CFR *.num *.sbk *.slg *.uid *.metadata *AutoRecovery* *REI_Saved_Picture*`
Large intermediates: `data/processed/*.parquet` above 25 MB (commit only `data/results/` and small manifests); `data/raw/`; model files above 25 MB.
**Commit** `.std`/STAAD text inputs under `legacy/staad_model/`, small result JSON/CSV/Parquet in `data/results/`, trained surrogate artifacts if < 25 MB.

### 13.4 Key config defaults (summary)
```yaml
sampling:    {n_base: 5000, biased_fraction: 0.30, seed: 42}
fe:          {beam_stiffness_factor: 0.35, column_stiffness_factor: 0.70, n_jobs: auto}
surrogate:   {holdout: 0.20, cv_folds: 5, boundary_band: [0.85, 1.15], al_samples: 500}
optimize:    {pop_size: 200, n_gen: 300, seeds: [1,2,3,4,5], margin: auto_q95}
verify:      {n_designs: 30, n_boundary: 5, tol_util_abs: 0.05, tol_defl_rel: 0.05, pass_target: 0.90}
```

---

## 14. Deviations from the Brief (all must be listed in the report and UI "About")

| ID | Brief says | This spec does | Reason |
|---|---|---|---|
| D0 | STAAD excluded from the loop | Same — STAAD used only for geometry/load source and benchmark | Folder contains legacy STAAD-driven code; the brief's position is retained, legacy is archived |
| D1 | Reinforcement ratio continuous | Reinforcement as discrete (dia, count), ratio derived | Brief's own "no continuous relaxation" rule |
| D2 | One surrogate (direct utilization) | Surrogate A (brief) + Surrogate B (demand surrogate + analytic capacity) | FE demands depend only on sizes & fck; capacity is closed-form |
| D3 | Surrogate-NSGA-II only | Plus direct-FE-NSGA-II baseline | Elastic frame FE is cheap; honest test of whether the surrogate is warranted |
| D4 | Verify 20–30 designs | Same, plus cheap full-front re-evaluation as an extra finding | Strengthens S2 honestly |
| D5 | 20-week timeline | Compressed; tool runs in hours — remaining effort is guide sign-off and report writing | Project is 7th-semester only |

---

## 15. Risk register (from Brief §11, with mitigations built into the pipeline)

| Risk | Mitigation in this spec |
|---|---|
| India-specific carbon data missing | Provisional flags, §9.3 audit doc, UI banner, sensitivity §9.5 |
| FE non-convergence / singular | Status codes, rows kept, failure table |
| Surrogate weak near feasibility boundary | Boundary hold-out metrics, active-learning round, safety margin, boundary-targeted verification, full-front re-check |
| Scope creep (seismic, typologies) | Hard out-of-scope list, Phase 6 stub only |
| IS-check implementation errors | Anchor tests, independent hand calcs, STAAD cross-check, owner manual verification |
| Timeline vs. academic backlog | Automated pipeline; resumable; docs/VIVA_PREP.md reduces report-writing load |
| Front too narrow to be interesting | §9.4 — report as finding; sensitivity study shows what drives spread |
