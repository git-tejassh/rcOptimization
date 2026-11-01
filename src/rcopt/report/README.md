# `report/` — turning results into figures, a report draft and website data

| File | What it does |
|---|---|
| `export_json.py` | `rcopt export`. Gathers everything the website needs from `data/results/` and writes validated JSON files into `web/public/data/` (`pareto.json`, `design_space.json`, `surrogate.json`, `verification.json`, `compute.json`, `sensitivity.json`, `cement.json`, `benchmark.json`, `factors.json`, `sample.json`, `provenance.json`, `meta.json`) **plus** `bundle.js`, a single script containing all of them so the built page also works when double-clicked (no web server). It also exports the honesty flags (provisional data, gravity-only, narrow front, failures) so the website cannot leave them out. |
| `figures.py` | Draws the report figures (Pareto fronts, convergence, parity plots) into `docs/figures/` and `data/results/figures/`. |
| `report_draft.py` | Writes `docs/REPORT_DRAFT.md` and `docs/VIVA_PREP.md` with the real numbers read from `data/results/` — no typed-in numbers. (Do not hand-edit those two files: re-run `rcopt report`.) |
| `__init__.py` | Marks the folder as a package. |
