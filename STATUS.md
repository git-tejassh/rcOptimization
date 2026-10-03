# STATUS (resume from this file + git log)

| Phase | State | Gate / key metrics |
|---|---|---|
| P-1 snapshot + legacy audit | DONE | docs/LEGACY_AUDIT.md |
| P0 scaffolding / config / design space | DONE | 22 genes; IS 456 Table 5 minimum grade enforced (M25-M40) |
| P0b FE + IS 456 + STAAD benchmark | DONE | reactions 1e-5, column Pu 3e-5, moments 0.12 % vs STAAD (docs/BENCHMARK.md); 75 tests pass |
| P1 sampling | DONE | 15,000 designs (9,000 LHS + 6,000 biased); raw geometry-infeasible 96.6 % -> repair; 0 impossible rows |
| P2 FE batch | DONE | 15,000 OK, 3,439 feasible, 5,237 near boundary; 36 ms cold solve |
| P3 surrogates | DONE | A: U_flex MAE 0.026, boundary feasibility agreement 94.7 %; B: 0.0010 / 99.8 % (after the D-024 fix); AL gave no measurable gain |
| P4 NSGA-II | DONE | 5 configs x 5 seeds, pop 200 x 300 gen. Pareto front proper 1-3 points (S1 NOT met, D-025) |
| P5 verification | DONE | pass rates of 30 designs: A 7 %, A+margin 60 %, B 87 %, B+margin 97 % (target 90 %) |
| P6 seismic hook | stub only | docs/SEISMIC_EXTENSION.md |
| P7 export + API + web | DONE | `rcopt export`, `web/dist/index.html` (single file), API smoke tests pass |
| P8 docs + report | DONE | docs/REPORT_DRAFT.md, VIVA_PREP.md filled from data/results |
| P9 GitHub push | see final message | origin = https://github.com/git-tejassh/rcOptimization |

## Honest headline findings
* Cost and carbon are almost the same objective with the provisional data (r = 0.975): one dominant design; the near-Pareto set (~100 designs) is used for verification.
* Plain surrogate A drives the GA onto the constraint boundary: 16 of 103 designs truly feasible; the safety margin fixes that (101/101) at +3 % cost; surrogate B (exact capacity) is best.
* Surrogate speed-up vs direct FE: optimisation only A 3.1x, B 1.3x; including data generation and training 0.93x / 0.67x: the surrogate did NOT pay off.
* Everything cost / carbon / IS-table related is provisional (docs/ASSUMPTIONS.md); gravity only.

## Definition of Done checklist
- [x] LEGACY_AUDIT; originals under legacy/ - [x] IS 456 anchors - [x] STAAD benchmark - [x] FE dataset with status flags
- [x] Two surrogates - [x] NSGA-II surrogate + direct, 5 seeds, HV + compute table - [x] verification incl. failures
- [x] web builds, all 10 pages render - [x] API smoke tests - [x] ASSUMPTIONS - [x] REPORT_DRAFT with real numbers - [x] CI config
- [ ] `make setup && make all` on a clean clone was NOT re-run end to end after the final changes (stages were run individually; cached)

Commands: `.venv\Scripts\python.exe -m rcopt.cli all` (phases 0-5, sensitivity, report, export); `.venv\Scripts\python.exe -m pytest`; web: `cd web && npm run build` then open `web/dist/index.html`.
