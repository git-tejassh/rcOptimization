# `web/public/data/` — the results the website reads

Written by `python -m rcopt.cli export` (do not edit by hand; re-run the export after any change in `data/results/` or `config/`). Committed to git so a static website can be deployed without Python.

| File | What it contains |
|---|---|
| `bundle.js` (≈ 1.6 MB) | All the JSON files below packed into one classic script, so the built page works when opened directly from disk (`file://`) where browsers block normal data loading. |
| `meta.json` | Project title, scope, **honesty flags** (provisional data list, gravity-only, narrow front, S1 not met), headline findings, version/provenance. |
| `design_space.json` | Genes, option lists, number of combinations, groups, frame geometry for the sketch. |
| `pareto.json` (≈ 1 MB) | Every near-Pareto design of every front (A, A_margin, B, B_margin, direct): all 23 genes decoded, sizes, bars, grades, cement, quantities, cost, carbon, the four utilisations, verification record. |
| `surrogate.json` | Metrics, parity-plot samples, learning curve, feature importance, active-learning effect. |
| `verification.json` | The 30 verified designs per front with predicted vs true values and failure reasons. |
| `compute.json` | Runtimes, evaluation counts, speed-ups, hypervolume histories. |
| `sensitivity.json` | ±20 % scenario results. |
| `cement.json` | Cement-type price-premium scan. |
| `benchmark.json` | OpenSees-vs-STAAD comparison. |
| `factors.json` | Cost rates and carbon factors (with status flags) that the "My design estimate" tab loads and lets users edit. |
| `sample.json` | The text of the owner's own STAAD input (G+3), offered by the "Load the sample" button in the "My design estimate" tab. |
| `provenance.json` | Markdown text of assumptions, decisions, standards, carbon audit for the Data & assumptions tab. |
