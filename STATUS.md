# STATUS (resume from this file + git log)

| Phase | State | Gate / key metrics |
|---|---|---|
| P-1 snapshot + legacy audit | DONE | docs/LEGACY_AUDIT.md |
| P0 scaffolding / config / design space | DONE | 23 genes (incl. cement type); IS 456 Table 5 minimum grade enforced (M25-M40) |
| P0b FE + IS 456 + STAAD benchmark | DONE | reactions 1e-5, column Pu 3e-5, moments 0.12 % vs STAAD (docs/BENCHMARK.md); 75 tests pass |
| P1 sampling | DONE | 15,000 designs (9,000 LHS + 6,000 biased); raw geometry-infeasible 96.6 % -> repair; 0 impossible rows |
| P2 FE batch | DONE | 15,000 OK, 3,439 feasible, 5,237 near boundary; 36 ms cold solve |
| P3 surrogates | DONE | A: U_flex MAE 0.026, boundary feasibility agreement 94.7 %; B: 0.0010 / 99.8 % (after the D-024 fix); AL gave no measurable gain |
| P4 NSGA-II | DONE | 5 configs x 5 seeds, pop 200 x 300 gen; cement type is a variable (D-028) and carbon factors are Indian secondary sources (D-027). Pareto front proper 6-13 points, cost spans ~2.6-3.3 %, carbon ~4-7 % (S1 NOT met, D-025); PSC dominates at market prices |
| P5 verification | DONE | pass rates of 30 designs: A 40 %, A+margin 70 %, B 87 %, B+margin 90 % (target 90 %; B+margin just meets it) |
| P6 seismic hook | stub only | docs/SEISMIC_EXTENSION.md |
| P7 export + API + web | DONE | `rcopt export`, `web/dist/index.html` (single file), API smoke tests pass |
| P8 docs + report | DONE | docs/REPORT_DRAFT.md, VIVA_PREP.md filled from data/results |
| P9 GitHub push | see final message | origin = https://github.com/git-tejassh/rcOptimization |

## Honest headline findings
* Cement type (OPC / PPC / PSC) is now a design variable. At market prices PSC is cheaper AND lower-carbon, so it dominates (best carbon -18 % vs the run without it) and the rank-1 Pareto sets grow to 6-13 points, still below 25. A real cost-carbon trade-off needs a low-carbon cement that costs more: `data/results/cement_tradeoff.json` scans that premium; the cement prices are provisional.
* Surrogate A without a margin lands on the constraint boundary (verification pass 40 %); B (exact capacity) is best: 87 %, and 90 % with the margin.
* Surrogate speed-up vs direct FE: see docs/REPORT_DRAFT.md section 7; including data generation and training it does not pay off.
* Cost rates, cement content, transport and IS-table transcriptions are still provisional (docs/ASSUMPTIONS.md); gravity only.

## Definition of Done checklist
- [x] LEGACY_AUDIT; originals under legacy/ - [x] IS 456 anchors - [x] STAAD benchmark - [x] FE dataset with status flags
- [x] Two surrogates - [x] NSGA-II surrogate + direct, 5 seeds, HV + compute table - [x] verification incl. failures
- [x] web builds, all 10 pages render - [x] API smoke tests - [x] ASSUMPTIONS - [x] REPORT_DRAFT with real numbers - [x] CI config
- [ ] `make setup && make all` on a clean clone was NOT re-run end to end after the final changes (stages were run individually; cached)

Commands: `.venv\Scripts\python.exe -m rcopt.cli all` (phases 0-5, sensitivity, report, export); `.venv\Scripts\python.exe -m pytest`; web: `cd web && npm run build` then open `web/dist/index.html`.
