# `verify/` — are the optimiser's answers actually right?

**Plain words:** the optimiser using a surrogate might report a "great" design that is secretly unsafe. This folder re-runs designs from each Pareto front
through the exact analysis and counts honestly how many pass. Failures are listed with their reasons, never hidden.

| File | What it does |
|---|---|
| `verify_pareto.py` | Phase 5. Picks 30 designs per front by a **fixed rule decided before looking at results** (spread along the cost axis + 5 designs with the smallest predicted safety slack, where surrogates are weakest). A design *passes* if it is truly feasible **and** the surrogate's predicted ratios are within ±0.05 (deflection ±5 %) of the truth. Writes `data/results/verification.json`. Result: A 40 %, A + margin 70 %, B 87 %, B + margin 90 % (target 90 %). |
| `full_front_check.py` | Extra finding: re-evaluates the **entire** pooled front of every configuration (not only 30 designs) with the exact analysis; writes `full_front_check.json`. |
| `__init__.py` | Marks the folder as a package. |

Settings (number of designs, tolerances, pass target) are in `config/verify.yaml`.
