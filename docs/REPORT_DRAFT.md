# Report draft: Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon

*Owner: Tejas Shrivastava, MANIT Bhopal (7th-semester major project). Generated from `data/results/` by `rcopt.report.report_draft`; every number below
comes from the pipeline outputs. Provisional inputs (cost rates, emission factors, IS 456 table transcriptions) are listed in section 8.*

## Abstract
A reproducible pipeline is built for a regular G+3 RC moment frame (the owner's STAAD model: 4 x 3 bays of 5 m, storey 3 m). OpenSeesPy 3D elastic analyses
(validated against the owner's STAAD results to 0.0012 % on reactions) feed IS 456:2000 limit-state checks of discrete,
IS-standard designs under gravity loading only. A dataset of 15000 analysed designs (all kept, 15000 OK, 3424 truly feasible) trains two surrogates;
constrained NSGA-II minimises cost and embodied carbon. Surrogate-driven and direct-FE fronts are compared, 30 headline-front designs are re-verified
(12 pass, 40 %; target 90 %), and the whole pooled front is re-evaluated. No novelty of algorithm is claimed.

## 1. Introduction and literature position
NSGA-II for RC frame cost optimisation has been published since at least 2016 (Kaveh et al., J. Civil Eng. & Management, 2016); surrogate-assisted NSGA-II for cost/carbon
exists in adjacent domains (concrete mix design). The contribution here is a validated, India-contextualised application: IS-code basis, discrete IS-standard sections / bars / grades,
Indian-context carbon factors with the gaps flagged (`docs/CARBON_DATA_AUDIT.md`), and a measured surrogate-versus-ground-truth reliability.

## 2. Problem and scope
Gravity only (1.5 (DL + LL) strength; 1.0 (DL + LL) service), beams and columns, frame-material cost and A1-A4 carbon, formwork carbon excluded. Out of scope: seismic / wind (IS 1893 / IS 875-3; hook only,
`docs/SEISMIC_EXTENSION.md`), foundations, slab design, operational carbon. **The optimum is not a code-compliant design of the building**: 57 of the 133 columns in the STAAD report are governed by seismic cases.

## 3. Method
* **Design space**: 23 integer genes (3.14e+17 combinations): per beam group (2) b, D, bottom bars (dia, n), top bars (dia, n); per column group (2) b, D, bars (dia, n); cement OPC/PPC/PSC; concrete M25-M40 (IS 456 Table 5 minimum for moderate exposure); steel Fe415 / Fe500; cement OPC / PPC / PSC. A deterministic repair snaps candidates to buildable designs (96.6 % of raw uniform genomes are unbuildable).
* **FE**: OpenSeesPy `ElasticTimoshenkoBeam` frame, beams 0.35 Ig / columns 0.70 Ig, Ec = 5000 sqrt(fck), slab loads by yield-line tributary areas, wall loads following beam depth. One cold solve 36 ms.
* **Checks**: IS 456 flexure (strain-compatible, doubly reinforced), shear (Tables 19-20), steel limits, column P-M interaction by strain compatibility with biaxial formula and slenderness, deflection <= L/250. Anchor tests, independent hand calculations (`docs/hand_calcs`) and the STAAD column-81 result are reproduced.
* **Validation against STAAD** (`docs/BENCHMARK.md`): reactions 0.0012 %, vertical displacements 0.0012 %, column axial forces 0.0035 %, column moments > 20 kN.m 0.12 %. Two causes of earlier differences (wall-load eccentricity torque, shear deformation) were found and are documented.
* **Sampling**: 9000 discrete-aware LHS designs + 6000 feasibility-biased designs; seed 42.
* **Surrogates**: A = direct utilisation regression (bootstrap XGBoost ensembles, log targets) per the brief; B = FE demands from sizes + fck, utilisations by the exact IS 456 module. One active-learning round of 500 boundary-targeted designs.
* **Optimisation**: pymoo NSGA-II, population 200, 300 generations, 5 seeds; configurations A, A + margin, B, B + margin, and direct FE (population 200, 300 generations).

## 4. Results: dataset and surrogates
Dataset: 15000 rows, status counts {'OK': 15000}, 5298 rows with a ratio in [0.85, 1.15]; failure table in `data/results/failure_table.csv`.
Hold-out: 3000 designs (1077 near the boundary).

| Output | A MAE | A boundary MAE | B MAE | B boundary MAE |
|---|---|---|---|---|
| U_flex_max | 0.0252 | 0.0200 | 0.0010 | 0.0009 |
| U_shear_max | 0.0051 | 0.0047 | 0.0001 | 0.0001 |
| U_col_max | 0.1052 | 0.0848 | 0.0044 | 0.0042 |
| defl_ratio_max | 0.0035 | 0.0035 | 0.0060 | 0.0057 |

Feasibility agreement near the boundary: A 96.6 % (22 designs wrongly accepted), B 99.8 % (1).
Active learning (one round) moved A's boundary U_flex MAE from 0.0202 to 0.0200 and B's from 0.0010 to 0.0009: no measurable benefit on this hold-out, so the extra FE runs of the initial sample (15,000 instead of 5,000) did more than the round itself.
Hypothesis D2 (capacity is closed-form, so learn only demands) is supported by the U_flex error. Figures: `docs/figures/parity_*_after_AL.png`.

## 5. Results: Pareto fronts
**Criterion S1 (at least 25 non-dominated points) is NOT met**, although the front is wider than before cement type became a variable: the rank-1 sets of the optimisation runs have A 10, A_margin 13, B 7, B_margin 8, direct 6 points (the dataset alone has 2 non-dominated of 3424 truly feasible designs). Over the direct-FE near-Pareto set cost spans INR 2237456 to 2295172 (2.6 %) and carbon 46453 to 48183 kgCO2e (3.7 %); cost and carbon are strongly correlated over the feasible designs (r = 0.800) because both follow material volume. Inputs: provisional cost rates, Indian secondary-source carbon factors (PPC 0.507, PSC 0.312, OPC 0.92, rebar 2.5 kgCO2e/kg). With the market cement prices of the config PSC is both cheaper and lower-carbon, so it dominates (it is the cement of 98 % of the direct-FE near-Pareto designs) and lowered the best carbon by about 18 % compared with the run without the cement variable. The exhaustive cement scan (`data/results/cement_tradeoff.json`) shows the front at market prices has 4 points (cost span 6.4 %, carbon span 5.7 %) and at a PSC premium of INR 4.0 per kg 5 points (cost span 15.3 %, carbon span 18.6 %): a real cost-carbon trade-off needs a low-carbon cement that costs more, and that price premium is exactly the input that is not verified. For verification and the full-front check the report uses a *near-Pareto set*: the first non-dominated ranks (about 100 designs) of the pooled, algorithm-feasible final populations of the five seeds (decision D-025).

Near-Pareto sets re-evaluated with ground truth (truly feasible / set size; non-dominated true front; best cost INR; best carbon kgCO2e; HV of the true front): A: 94/118; 8; 2297579; 46557; 0.711; A_margin: 122/122; 13; 2341465; 48252; 0.459; B: 114/119; 7; 2245292; 45343; 1.032; B_margin: 117/117; 8; 2252487; 45409; 1.003; direct: 103/103; 6; 2237456; 46453; 1.010.
Surrogate B (and B + margin) reach designs at least as good as the direct-FE run within the same evaluation budget; plain surrogate A converges to designs on the constraint boundary, most of which are infeasible in truth, which is why the safety margin matters for A. Figure: `docs/figures/pareto_fronts.png`.
Sensitivity (+/-20 %): Under +/-20 % changes of steel cost, cement carbon and steel carbon, the baseline cost/carbon optima lose at most 4.9 % against the best design available under each scenario, and the worst rank correlation of cost/carbon across the baseline set is 0.884. The optimum or the ordering is NOT fully robust to these perturbations: see the scenario table.

## 6. Verification (`data/results/verification.json`)
| Front | verified | pass | truly feasible | within tolerance | boundary picks passing |
|---|---|---|---|---|---|
| A | 30 | 12 (40 %) | 25 | 15 | 2/5 |
| A_margin | 30 | 21 (70 %) | 30 | 21 | 4/5 |
| B | 30 | 26 (87 %) | 26 | 30 | 3/5 |
| B_margin | 30 | 27 (90 %) | 30 | 27 | 3/5 |

Headline (A) failures: #25: TOLERANCE:U_col_max |err|=0.076 > 0.05; #30: TRULY_INFEASIBLE:U_col_max=1.014; #34: TOLERANCE:U_col_max |err|=0.123 > 0.05; #45: TOLERANCE:U_col_max |err|=0.130 > 0.05; #49: TOLERANCE:U_col_max |err|=0.121 > 0.05; #50 (boundary pick): TOLERANCE:U_col_max |err|=0.051 > 0.05; #66: TOLERANCE:U_col_max |err|=0.065 > 0.05; #71: TOLERANCE:U_flex_max |err|=0.058 > 0.05, TOLERANCE:U_col_max |err|=0.088 > 0.05; #76: TOLERANCE:U_col_max |err|=0.064 > 0.05; #77: TOLERANCE:U_col_max |err|=0.072 > 0.05; #80: TRULY_INFEASIBLE:U_col_max=1.044; #84: TOLERANCE:U_flex_max |err|=0.095 > 0.05, TRULY_INFEASIBLE:U_col_max=1.004; #89 (boundary pick): TOLERANCE:U_col_max |err|=0.130 > 0.05; #98 (boundary pick): TRULY_INFEASIBLE:U_flex_max=1.007; #104: TOLERANCE:U_flex_max |err|=0.058 > 0.05; #105: TOLERANCE:U_col_max |err|=0.053 > 0.05, TRULY_INFEASIBLE:U_flex_max=1.026; #112: TOLERANCE:U_col_max |err|=0.139 > 0.05; #116: TOLERANCE:U_col_max |err|=0.119 > 0.05. Tolerance: utilisation +/-0.05, deflection +/-5 %.
Whole-front check (A): 80 % truly feasible; HV gap predicted vs true 5.7 %; margin variant A + margin: 100 % truly feasible, verification pass 70 %.

## 7. Compute comparison
| Config | evaluations / seed | FE solves / seed | wall / seed (s) | HV (true) | speed-up (opt. only / incl. data + training) |
|---|---|---|---|---|---|
| A | 60000 | 0 | 143 | 0.7114 | 3.5x / 0.87x |
| A_margin | 60000 | 0 | 143 | 0.4590 | 3.5x / 0.87x |
| B | 60000 | 0 | 316 | 1.0316 | 1.6x / 0.67x |
| B_margin | 60000 | 0 | 298 | 1.0035 | 1.7x / 0.69x |
| direct | 60000 | 6818 | 503 | 1.0095 | - |

One-time costs charged to the surrogate rows: data generation 15490 FE solves (about 558 s serial-equivalent) and training 1614 s.
The surrogate did NOT pay off against direct FE in this setting: an elastic frame solve is a few tens of milliseconds.

## 8. Limitations and provisional values
* Provisional (unverified): 20 config entries (all cost rates, carbon factors, IS 456 table transcriptions): see `docs/ASSUMPTIONS.md`. Absolute INR and kgCO2e values are indicative only.
* Gravity only; no seismic / wind; no foundations; beam torsion ignored; slab not designed; cracked-stiffness modifiers 0.35 / 0.70 not validated by STAAD.
* Deflection and shear never governed in the dataset; flexure, column interaction and steel limits did.
* Surrogate B regresses the column demands per position class (30 classes); the earlier 4-extremal-triples variant failed verification (D-024) and was replaced.

## 9. Conclusions
See the numbers above; the claims supported are: (i) the FE + IS 456 pipeline reproduces the owner's STAAD gravity results; (ii) surrogate reliability was measured, including near the boundary, with the failures listed; (iii) the surrogate speed-up against direct FE is as tabulated, including data generation; (iv) the cost-carbon front is narrow because both objectives follow material volume.
