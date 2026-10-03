# Report draft: Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon

*Owner: Tejas Shrivastava, MANIT Bhopal (7th-semester major project). Generated from `data/results/` by `rcopt.report.report_draft`; every number below
comes from the pipeline outputs. Provisional inputs (cost rates, emission factors, IS 456 table transcriptions) are listed in section 8.*

## Abstract
A reproducible pipeline is built for a regular G+3 RC moment frame (the owner's STAAD model: 4 x 3 bays of 5 m, storey 3 m). OpenSeesPy 3D elastic analyses
(validated against the owner's STAAD results to 0.0012 % on reactions) feed IS 456:2000 limit-state checks of discrete,
IS-standard designs under gravity loading only. A dataset of 15000 analysed designs (all kept, 15000 OK, 3439 truly feasible) trains two surrogates;
constrained NSGA-II minimises cost and embodied carbon. Surrogate-driven and direct-FE fronts are compared, 30 headline-front designs are re-verified
(9 pass, 30 %; target 90 %), and the whole pooled front is re-evaluated. No novelty of algorithm is claimed.

## 1. Introduction and literature position
NSGA-II for RC frame cost optimisation has been published since at least 2016 (Kaveh et al., J. Civil Eng. & Management, 2016); surrogate-assisted NSGA-II for cost/carbon
exists in adjacent domains (concrete mix design). The contribution here is a validated, India-contextualised application: IS-code basis, discrete IS-standard sections / bars / grades,
Indian-context carbon factors with the gaps flagged (`docs/CARBON_DATA_AUDIT.md`), and a measured surrogate-versus-ground-truth reliability.

## 2. Problem and scope
Gravity only (1.5 (DL + LL) strength; 1.0 (DL + LL) service), beams and columns, frame-material cost and A1-A4 carbon, formwork carbon excluded. Out of scope: seismic / wind (IS 1893 / IS 875-3; hook only,
`docs/SEISMIC_EXTENSION.md`), foundations, slab design, operational carbon. **The optimum is not a code-compliant design of the building**: 57 of the 133 columns in the STAAD report are governed by seismic cases.

## 3. Method
* **Design space**: 22 integer genes (1.31e+17 combinations): per beam group (2) b, D, bottom bars (dia, n), top bars (dia, n); per column group (2) b, D, bars (dia, n); concrete M25-M40 (IS 456 Table 5 minimum for moderate exposure); steel Fe415 / Fe500. A deterministic repair snaps candidates to buildable designs (96.6 % of raw uniform genomes are unbuildable).
* **FE**: OpenSeesPy `ElasticTimoshenkoBeam` frame, beams 0.35 Ig / columns 0.70 Ig, Ec = 5000 sqrt(fck), slab loads by yield-line tributary areas, wall loads following beam depth. One cold solve 28 ms.
* **Checks**: IS 456 flexure (strain-compatible, doubly reinforced), shear (Tables 19-20), steel limits, column P-M interaction by strain compatibility with biaxial formula and slenderness, deflection <= L/250. Anchor tests, independent hand calculations (`docs/hand_calcs`) and the STAAD column-81 result are reproduced.
* **Validation against STAAD** (`docs/BENCHMARK.md`): reactions 0.0012 %, vertical displacements 0.0012 %, column axial forces 0.0035 %, column moments > 20 kN.m 0.12 %. Two causes of earlier differences (wall-load eccentricity torque, shear deformation) were found and are documented.
* **Sampling**: 9000 discrete-aware LHS designs + 6000 feasibility-biased designs; seed 42.
* **Surrogates**: A = direct utilisation regression (bootstrap XGBoost ensembles, log targets) per the brief; B = FE demands from sizes + fck, utilisations by the exact IS 456 module. One active-learning round of 500 boundary-targeted designs.
* **Optimisation**: pymoo NSGA-II, population 200, 300 generations, 5 seeds; configurations A, A + margin, B, B + margin, and direct FE (population 200, 300 generations).

## 4. Results: dataset and surrogates
Dataset: 15000 rows, status counts {'OK': 15000}, 5237 rows with a ratio in [0.85, 1.15]; failure table in `data/results/failure_table.csv`.
Hold-out: 3000 designs (1067 near the boundary).

| Output | A MAE | A boundary MAE | B MAE | B boundary MAE |
|---|---|---|---|---|
| U_flex_max | 0.0256 | 0.0213 | 0.0010 | 0.0009 |
| U_shear_max | 0.0051 | 0.0046 | 0.0002 | 0.0002 |
| U_col_max | 0.0991 | 0.0729 | 0.0046 | 0.0038 |
| defl_ratio_max | 0.0036 | 0.0034 | 0.0061 | 0.0059 |

Feasibility agreement near the boundary: A 94.7 % (23 designs wrongly accepted), B 99.8 % (0).
Active learning (one round) moved A's boundary U_flex MAE from 0.0213 to 0.0213 and B's from 0.0009 to 0.0009: no measurable benefit on this hold-out, so the extra FE runs of the initial sample (15,000 instead of 5,000) did more than the round itself.
Hypothesis D2 (capacity is closed-form, so learn only demands) is supported by the U_flex error. Figures: `docs/figures/parity_*_after_AL.png`.

## 5. Results: Pareto fronts
**Criterion S1 (at least 25 non-dominated points) is NOT met.** With the current inputs (provisional cost rates, Indian secondary-source carbon factors: PPC 0.507, steel 2.5 kgCO2e/kg) the Pareto front proper is narrow: among the 3439 truly feasible designs of the dataset only 2 are non-dominated, and the rank-1 sets of the optimisation runs have A 4, A_margin 7, B 4, B_margin 5, direct 3 points. Over the direct-FE near-Pareto set cost spans only INR 2245703 to 2288829 (1.9 %) and carbon 55247 to 56224 kgCO2e (1.8 %). Cost and carbon are strongly correlated over the feasible designs (r = 0.985) because both follow material volume; the only trade-offs that exist (more concrete to save steel, concrete grade) are worth a few per cent. Realistic carbon factors widened the front (rank-1 size 1-3 -> 3-7 points) but not to 25 points; it was not widened by tuning rates or objectives. A genuinely wider front needs a design lever with a strong carbon-cost exchange (for example cement type / SCM replacement), which is outside the brief's variable list. For verification and the full-front check the report uses a *near-Pareto set*: the first non-dominated ranks (about 100 designs) of the pooled, algorithm-feasible final populations of the five seeds (decision D-025).

Near-Pareto sets re-evaluated with ground truth (truly feasible / set size; non-dominated true front; best cost INR; best carbon kgCO2e; HV of the true front): A: 95/102; 4; 2277813; 56751; 0.704; A_margin: 111/111; 7; 2343418; 58115; 0.244; B: 102/106; 4; 2245703; 55275; 1.076; B_margin: 104/104; 5; 2245703; 55525; 1.031; direct: 103/103; 3; 2245703; 55247; 1.081.
Surrogate B (and B + margin) reach designs at least as good as the direct-FE run within the same evaluation budget; plain surrogate A converges to designs on the constraint boundary, most of which are infeasible in truth, which is why the safety margin matters for A. Figure: `docs/figures/pareto_fronts.png`.
Sensitivity (+/-20 %): Under +/-20 % changes of steel cost, cement carbon and steel carbon, the baseline cost/carbon optima lose at most 1.0 % against the best design available under each scenario, and the worst rank correlation of cost/carbon across the baseline set is 0.488. The optimum or the ordering is NOT fully robust to these perturbations: see the scenario table.

## 6. Verification (`data/results/verification.json`)
| Front | verified | pass | truly feasible | within tolerance | boundary picks passing |
|---|---|---|---|---|---|
| A | 30 | 9 (30 %) | 29 | 10 | 2/5 |
| A_margin | 30 | 17 (57 %) | 30 | 17 | 2/5 |
| B | 30 | 26 (87 %) | 27 | 29 | 4/5 |
| B_margin | 30 | 27 (90 %) | 30 | 27 | 5/5 |

Headline (A) failures: #2 (boundary pick): TOLERANCE:U_col_max |err|=0.078 > 0.05; #5: TOLERANCE:U_flex_max |err|=0.057 > 0.05, TOLERANCE:U_col_max |err|=0.075 > 0.05; #6: TOLERANCE:U_col_max |err|=0.066 > 0.05; #10: TOLERANCE:U_flex_max |err|=0.065 > 0.05, TOLERANCE:U_col_max |err|=0.078 > 0.05; #12 (boundary pick): TOLERANCE:U_col_max |err|=0.095 > 0.05; #15: TOLERANCE:U_col_max |err|=0.069 > 0.05; #18: TOLERANCE:U_flex_max |err|=0.080 > 0.05, TOLERANCE:U_col_max |err|=0.094 > 0.05; #19: TOLERANCE:U_col_max |err|=0.097 > 0.05; #24: TOLERANCE:U_flex_max |err|=0.054 > 0.05, TOLERANCE:U_col_max |err|=0.103 > 0.05; #32: TOLERANCE:U_col_max |err|=0.128 > 0.05; #43: TOLERANCE:U_col_max |err|=0.065 > 0.05; #44: TRULY_INFEASIBLE:U_col_max=1.004; #46: TOLERANCE:U_col_max |err|=0.077 > 0.05; #55: TOLERANCE:U_col_max |err|=0.069 > 0.05; #65: TOLERANCE:U_col_max |err|=0.072 > 0.05; #71: TOLERANCE:U_flex_max |err|=0.068 > 0.05; #75 (boundary pick): TOLERANCE:U_col_max |err|=0.063 > 0.05; #80: TOLERANCE:U_col_max |err|=0.067 > 0.05; #81: TOLERANCE:U_flex_max |err|=0.063 > 0.05, TOLERANCE:U_col_max |err|=0.103 > 0.05; #98: TOLERANCE:U_flex_max |err|=0.066 > 0.05; #100: TOLERANCE:U_col_max |err|=0.083 > 0.05. Tolerance: utilisation +/-0.05, deflection +/-5 %.
Whole-front check (A): 93 % truly feasible; HV gap predicted vs true 0.0 %; margin variant A + margin: 100 % truly feasible, verification pass 57 %.

## 7. Compute comparison
| Config | evaluations / seed | FE solves / seed | wall / seed (s) | HV (true) | speed-up (opt. only / incl. data + training) |
|---|---|---|---|---|---|
| A | 60000 | 0 | 165 | 0.7037 | 3.0x / 0.81x |
| A_margin | 60000 | 0 | 123 | 0.2439 | 4.0x / 0.87x |
| B | 60000 | 0 | 267 | 1.0760 | 1.9x / 0.70x |
| B_margin | 60000 | 0 | 223 | 1.0313 | 2.2x / 0.74x |
| direct | 60000 | 5953 | 498 | 1.0808 | - |

One-time costs charged to the surrogate rows: data generation 15489 FE solves (about 427 s serial-equivalent) and training 1805 s.
The surrogate did NOT pay off against direct FE in this setting: an elastic frame solve is a few tens of milliseconds.

## 8. Limitations and provisional values
* Provisional (unverified): 17 config entries (all cost rates, carbon factors, IS 456 table transcriptions): see `docs/ASSUMPTIONS.md`. Absolute INR and kgCO2e values are indicative only.
* Gravity only; no seismic / wind; no foundations; beam torsion ignored; slab not designed; cracked-stiffness modifiers 0.35 / 0.70 not validated by STAAD.
* Deflection and shear never governed in the dataset; flexure, column interaction and steel limits did.
* Surrogate B regresses the column demands per position class (30 classes); the earlier 4-extremal-triples variant failed verification (D-024) and was replaced.

## 9. Conclusions
See the numbers above; the claims supported are: (i) the FE + IS 456 pipeline reproduces the owner's STAAD gravity results; (ii) surrogate reliability was measured, including near the boundary, with the failures listed; (iii) the surrogate speed-up against direct FE is as tabulated, including data generation; (iv) the cost-carbon front is narrow because both objectives follow material volume.
