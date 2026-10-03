# STATUS (resume from this file + git log)

| Phase | State | Gate / key metrics |
|---|---|---|
| P-1 snapshot + legacy audit | DONE | docs/LEGACY_AUDIT.md |
| P0 scaffolding / config / design space | DONE | 22 genes; IS 456 Table 5 minimum grade enforced (M25-M40) |
| P0b FE + IS 456 + STAAD benchmark | DONE | reactions 1e-5, column Pu 3e-5, moments 0.12 % vs STAAD (docs/BENCHMARK.md); 75 tests pass |
| P1 sampling | DONE | 15,000 designs (9,000 LHS + 6,000 biased); raw geometry-infeasible 96.6 % -> repair; 0 impossible rows |
| P2 FE batch | DONE | 15,000 OK, 3,439 feasible, 5,237 near boundary; 36 ms cold solve |
| P3 surrogates | DONE | A: U_flex MAE 0.026, boundary feasibility agreement 94.7 %; B: 0.0010 / 99.8 % (after the D-024 fix); AL gave no measurable gain |
| P4 NSGA-II | DONE | 5 configs x 5 seeds, pop 200 x 300 gen; carbon factors = Indian secondary sources (D-027). Pareto front proper 3-7 points, cost spans 1.9 %, carbon 1.7 % (S1 NOT met, D-025) |
| P5 verification | DONE | pass rates of 30 designs: A 30 %, A+margin 57 %, B 87 %, B+margin 90 % (target 90 %; B+margin just meets it) |
| P6 seismic hook | stub only | docs/SEISMIC_EXTENSION.md |
| P7 export + API + web | DONE | `rcopt export`, `web/dist/index.html` (single file), API smoke tests pass |
| P8 docs + report | DONE | docs/REPORT_DRAFT.md, VIVA_PREP.md filled from data/results |
| P9 GitHub push | see final message | origin = https://github.com/git-tejassh/rcOptimization |

## Honest headline findings
* With Indian secondary-source carbon factors (PPC 0.507, rebar 2.5 kgCO2e/kg) the rank-1 Pareto sets grow from 1-3 to 3-7 points, but cost varies only 1.9 % and carbon 1.7 % across the near-Pareto set (r = 0.985 over feasible designs): the front is still narrow. A wider front needs a lever with a strong carbon-cost exchange (cement type / SCM replacement), outside the brief.
* Surrogate A without a margin lands on the constraint boundary (verification pass 30 %); B (exact capacity) is best: 87 %, and 90 % with the margin.
* Surrogate speed-up vs direct FE: see docs/REPORT_DRAFT.md section 7; including data generation and training it does not pay off.
* Cost rates, cement content, transport and IS-table transcriptions are still provisional (docs/ASSUMPTIONS.md); gravity only.

## Definition of Done checklist
- [x] LEGACY_AUDIT; originals under legacy/ - [x] IS 456 anchors - [x] STAAD benchmark - [x] FE dataset with status flags
- [x] Two surrogates - [x] NSGA-II surrogate + direct, 5 seeds, HV + compute table - [x] verification incl. failures
- [x] web builds, all 10 pages render - [x] API smoke tests - [x] ASSUMPTIONS - [x] REPORT_DRAFT with real numbers - [x] CI config
- [ ] `make setup && make all` on a clean clone was NOT re-run end to end after the final changes (stages were run individually; cached)

Commands: `.venv\Scripts\python.exe -m rcopt.cli all` (phases 0-5, sensitivity, report, export); `.venv\Scripts\python.exe -m pytest`; web: `cd web && npm run build` then open `web/dist/index.html`.
