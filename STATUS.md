# STATUS (resume from this file + git log)

| Phase | State | Gate / key metrics |
|---|---|---|
| P-1 snapshot + legacy audit | DONE (tags `snapshot-original`, `phase-m1`) | docs/LEGACY_AUDIT.md |
| P0 scaffolding/config/design space | DONE (tag `phase-0`) | 22 genes, 1.3e17 combinations, 21 provisional config items |
| P0b geometry + FE + IS 456 + STAAD cross-check | DONE (tag `phase-0b`) | 60 tests pass; STAAD benchmark: reactions 1e-5, column Pu 3e-5, moments 0.13 % (docs/BENCHMARK.md) |
| P1 sampling | next | |

Key facts: FE ~35-45 ms per unique size set (cached by size key); 16 cores; random genomes 96 % unbuildable raw -> repair (D-012); ~9 % of repaired uniform random designs are IS-feasible.
Open issues: all cost/carbon/IS-table values provisional (docs/ASSUMPTIONS.md).
Venv: `.venv` (Python 3.12.14, openseespy 3.8.0.0). Remote: origin = https://github.com/git-tejassh/rcOptimization (push at P9).
Commands: `.venv\Scripts\python.exe -m rcopt.cli phase0|phase0b`, `.venv\Scripts\python.exe -m pytest -m "not slow"`.
