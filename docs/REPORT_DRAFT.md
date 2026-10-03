# Report draft: Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon

*Owner: Tejas Shrivastava, MANIT Bhopal (7th-semester major project). Generated from `data/results/` by `rcopt.report.report_draft`; every number below
comes from the pipeline outputs. Provisional inputs (cost rates, emission factors, IS 456 table transcriptions) are listed in section 8.*

## Abstract
A reproducible pipeline is built for a regular G+3 RC moment frame (the owner's STAAD model: 4 x 3 bays of 5 m, storey 3 m). OpenSeesPy 3D elastic analyses
(validated against the owner's STAAD results to 0.0012 % on reactions) feed IS 456:2000 limit-state checks of discrete,
IS-standard designs under gravity loading only. A dataset of 15000 analysed designs (all kept, 15000 OK, 3439 truly feasible) trains two surrogates;
constrained NSGA-II minimises cost and embodied carbon. Surrogate-driven and direct-FE fronts are compared, 30 headline-front designs are re-verified
(2 pass, 7 %; target 90 %), and the whole pooled front is re-evaluated. No novelty of algorithm is claimed.

## 1. Introduction and literature position
NSGA-II for RC frame cost optimisation has been published since at least 2016 (Kaveh et al., J. Civil Eng. & Management, 2016); surrogate-assisted NSGA-II for cost/carbon
exists in adjacent domains (concrete mix design). The contribution here is a validated, India-contextualised application: IS-code basis, discrete IS-standard sections / bars / grades,
Indian-context carbon factors with the gaps flagged (`docs/CARBON_DATA_AUDIT.md`), and a measured surrogate-versus-ground-truth reliability.

## 2. Problem and scope
Gravity only (1.5 (DL + LL) strength; 1.0 (DL + LL) service), beams and columns, frame-material cost and A1-A4 carbon, formwork carbon excluded. Out of scope: seismic / wind (IS 1893 / IS 875-3; hook only,
`docs/SEISMIC_EXTENSION.md`), foundations, slab design, operational carbon. **The optimum is not a code-compliant design of the building**: 57 of the 133 columns in the STAAD report are governed by seismic cases.

## 3. Method
* **Design space**: 22 integer genes (1.31e+17 combinations): per beam group (2) b, D, bottom bars (dia, n), top bars (dia, n); per column group (2) b, D, bars (dia, n); concrete M25-M40 (IS 456 Table 5 minimum for moderate exposure); steel Fe415 / Fe500. A deterministic repair snaps candidates to buildable designs (96.6 % of raw uniform genomes are unbuildable).
* **FE**: OpenSeesPy `ElasticTimoshenkoBeam` frame, beams 0.35 Ig / columns 0.70 Ig, Ec = 5000 sqrt(fck), slab loads by yield-line tributary areas, wall loads following beam depth. One cold solve 36 ms.
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
**Criterion S1 (at least 25 non-dominated points) is NOT met.** With the provisional cost and carbon data the Pareto front proper is tiny: among the 3439 truly feasible designs of the dataset exactly 1 is non-dominated, and the rank-1 sets of the optimisation runs have A 1, A_margin 3, B 1, B_margin 3, direct 1 points. Cost and carbon are strongly correlated over the feasible designs (r = 0.975) because both follow material volume, and no variable (grade, steel grade, section) trades one against the other with these factors. This is a finding, not something to be widened by changing rates or objectives. For verification and the full-front check the report therefore uses a *near-Pareto set*: the first non-dominated ranks (about 100 designs) of the pooled, algorithm-feasible final populations of the five seeds (decision D-025).

Near-Pareto sets re-evaluated with ground truth (truly feasible / set size; non-dominated true front; best cost INR; best carbon kgCO2e; HV of the true front): A: 16/103; 4; 2299072; 65044; 0.502; A_margin: 101/101; 3; 2337968; 66157; 0.194; B: 101/106; 1; 2241157; 63668; 1.103; B_margin: 101/102; 3; 2260218; 64190; 0.858; direct: 108/108; 1; 2262459; 64033; 0.882.
Surrogate B (and B + margin) reach designs at least as good as the direct-FE run within the same evaluation budget; plain surrogate A converges to designs on the constraint boundary, most of which are infeasible in truth, which is why the safety margin matters for A. Figure: `docs/figures/pareto_fronts.png`.
Sensitivity (+/-20 %): Under +/-20 % changes of steel cost, cement carbon and steel carbon, the baseline cost/carbon optima lose at most 0.7 % against the best design available under each scenario, and the worst rank correlation of cost/carbon across the baseline set is 0.801. The optimum or the ordering is NOT fully robust to these perturbations: see the scenario table.

## 6. Verification (`data/results/verification.json`)
| Front | verified | pass | truly feasible | within tolerance | boundary picks passing |
|---|---|---|---|---|---|
| A | 30 | 2 (7 %) | 2 | 24 | 0/5 |
| A_margin | 30 | 18 (60 %) | 30 | 18 | 3/5 |
| B | 30 | 26 (87 %) | 26 | 30 | 5/5 |
| B_margin | 30 | 29 (97 %) | 29 | 30 | 5/5 |

Headline (A) failures: #2 (boundary pick): TRULY_INFEASIBLE:U_flex_max=1.018,U_col_max=1.004; #4 (boundary pick): TRULY_INFEASIBLE:U_col_max=1.014; #7: TRULY_INFEASIBLE:U_col_max=1.014; #10: TRULY_INFEASIBLE:U_col_max=1.016; #12: TRULY_INFEASIBLE:U_flex_max=1.005,U_col_max=1.016; #16: TRULY_INFEASIBLE:U_flex_max=1.002; #18: TRULY_INFEASIBLE:U_flex_max=1.009,U_col_max=1.017; #20: TRULY_INFEASIBLE:U_flex_max=1.018; #29 (boundary pick): TRULY_INFEASIBLE:U_col_max=1.001; #32: TOLERANCE:U_flex_max |err|=0.066 > 0.05, TRULY_INFEASIBLE:U_flex_max=1.063; #33: TRULY_INFEASIBLE:U_flex_max=1.009; #38: TOLERANCE:U_col_max |err|=0.071 > 0.05, TRULY_INFEASIBLE:U_col_max=1.065; #40: TRULY_INFEASIBLE:U_col_max=1.012; #41: TRULY_INFEASIBLE:U_flex_max=1.006; #55: TOLERANCE:U_col_max |err|=0.158 > 0.05, TRULY_INFEASIBLE:U_col_max=1.115; #57: TRULY_INFEASIBLE:U_col_max=1.017; #58: TRULY_INFEASIBLE:U_flex_max=1.015; #66: TRULY_INFEASIBLE:U_flex_max=1.005; #67: TRULY_INFEASIBLE:U_col_max=1.016; #72 (boundary pick): TOLERANCE:U_col_max |err|=0.087 > 0.05, TRULY_INFEASIBLE:U_flex_max=1.023,U_col_max=1.048; #76: TRULY_INFEASIBLE:U_col_max=1.005; #80: TRULY_INFEASIBLE:U_col_max=1.019; #84 (boundary pick): TRULY_INFEASIBLE:U_flex_max=1.018,U_col_max=1.008; #91: TRULY_INFEASIBLE:U_flex_max=1.020,U_col_max=1.005; #92: TOLERANCE:U_col_max |err|=0.110 > 0.05, TRULY_INFEASIBLE:U_col_max=1.015; #95: TRULY_INFEASIBLE:U_col_max=1.017; #96: TOLERANCE:U_col_max |err|=0.190 > 0.05, TRULY_INFEASIBLE:U_col_max=1.139; #98: TRULY_INFEASIBLE:U_flex_max=1.002,U_col_max=1.003. Tolerance: utilisation +/-0.05, deflection +/-5 %.
Whole-front check (A): 16 % truly feasible; HV gap predicted vs true 26.5 %; margin variant A + margin: 100 % truly feasible, verification pass 60 %.

## 7. Compute comparison
| Config | evaluations / seed | FE solves / seed | wall / seed (s) | HV (true) | speed-up (opt. only / incl. data + training) |
|---|---|---|---|---|---|
| A | 60000 | 0 | 206 | 0.5022 | 3.1x / 0.93x |
| A_margin | 60000 | 0 | 193 | 0.1943 | 3.3x / 0.95x |
| B | 60000 | 0 | 469 | 1.1025 | 1.3x / 0.67x |
| B_margin | 60000 | 0 | 396 | 0.8585 | 1.6x / 0.72x |
| direct | 60000 | 5079 | 628 | 0.8823 | - |

One-time costs charged to the surrogate rows: data generation 15489 FE solves (about 550 s serial-equivalent) and training 1805 s.
The surrogate did NOT pay off against direct FE in this setting: an elastic frame solve is a few tens of milliseconds.

## 8. Limitations and provisional values
* Provisional (unverified): 21 config entries (all cost rates, carbon factors, IS 456 table transcriptions): see `docs/ASSUMPTIONS.md`. Absolute INR and kgCO2e values are indicative only.
* Gravity only; no seismic / wind; no foundations; beam torsion ignored; slab not designed; cracked-stiffness modifiers 0.35 / 0.70 not validated by STAAD.
* Deflection and shear never governed in the dataset; flexure, column interaction and steel limits did.
* Surrogate B regresses the column demands per position class (30 classes); the earlier 4-extremal-triples variant failed verification (D-024) and was replaced.

## 9. Conclusions
See the numbers above; the claims supported are: (i) the FE + IS 456 pipeline reproduces the owner's STAAD gravity results; (ii) surrogate reliability was measured, including near the boundary, with the failures listed; (iii) the surrogate speed-up against direct FE is as tabulated, including data generation; (iv) the cost-carbon front is narrow because both objectives follow material volume.
