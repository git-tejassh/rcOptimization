# `optimize/` — the multi-objective search (NSGA-II)

**Plain words:** NSGA-II is a genetic algorithm. It keeps a "population" of 200 designs, repeatedly mixes and mutates them for 300 generations and keeps the
ones that are not beaten on both cost and carbon. The set of designs that cannot be improved on one objective without getting worse on the other is the
**Pareto front**. We run five versions — **A, A + safety margin, B, B + safety margin** (all use a surrogate) and **direct** (every design through the real
OpenSees analysis, the slow honest baseline) — each with 5 random seeds, with the same budget, so they can be compared fairly.

| File | What it does |
|---|---|
| `problem.py` | Defines the problem for pymoo: 2 objectives (cost, carbon), 7 constraints, 23 integer genes. Three evaluators — `SurrogateEvaluator` (A or B), `DirectFEEvaluator` (ground truth) — each remembers designs it already evaluated and counts real evaluations. `GenomeRepair` snaps every offspring to a buildable design. |
| `run.py` | Runs NSGA-II for each configuration × seed, records the best feasible designs after every generation (for the convergence plot) and stores each run in `data/processed/opt/`. |
| `metrics.py` | Quality measures: non-dominated filtering, **hypervolume** (one number for "how good and how spread-out is the front", with a fixed reference so configs are comparable), spacing, and the cost-carbon correlation (close to 1 = narrow front). |
| `phase4.py` | Orchestrates Phase 4: runs everything, pools the five seeds, builds the "near-Pareto set" (~100 designs, because the strict rank-1 front is only 6–13 points — criterion S1 ≥ 25 is **not met**, reported honestly), re-evaluates every front with the exact analysis, and writes `compute_comparison.json`, `optimization_summary.json` and `pareto_*.parquet`. |
| `__init__.py` | Marks the folder as a package. |

Settings (population, generations, seeds, margin rule) are in `config/optimize.yaml`.
