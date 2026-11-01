# `data/` — everything the pipeline reads and produces

**Plain words:** four sub-folders, from "input" to "answers". Only small files are kept in git; the big intermediate ones are re-created by the pipeline (or downloaded from Google Drive).

| Folder | In git? | What is inside |
|---|---|---|
| `benchmark/` | yes | `staad_reference.json` (≈ 39 KB): the numbers decoded from the owner's STAAD result files (reactions, displacements, column design forces) that the OpenSees model is compared against. |
| `raw/` | – | Empty on purpose (nothing downloaded; all inputs are the config files and the STAAD text file in `legacy/`). |
| `processed/` | only metadata | The big working data (below). |
| `results/` | yes | The small, final result files that feed the report and the website. |

## `processed/` (re-creatable; parquet files are git-ignored)
| File | Size | What it is |
|---|---|---|
| `design_matrix.parquet` | 0.2 MB | The 15,000 chosen example designs (output of `phase1`, `sampling/`). |
| `fe_dataset.parquet` | 17.8 MB | **The main dataset**: one row per design with the analysis demands, utilisation ratios, quantities, cost, carbon and a status flag (all 15,000 `OK`, 3,424 truly feasible, 5,298 near the boundary). |
| `fe_dataset_al.parquet` | 0.7 MB | The 500 extra boundary designs of the active-learning round. |
| `fe_dataset.meta.json` | tiny | Runtime and counts of the data run (156 s on 8 workers, mean 69 ms per solve in the busy batch). Committed. |
| `opt/` | large | The 25 stored NSGA-II runs (5 configurations × 5 seeds) with convergence histories. |

## `results/` (committed)
| File | What it is |
|---|---|
| `design_space.json` | The 23 genes and their options, as written by `phase0`. |
| `sampling_report.json` | How the design matrix was made (strata, rejection counts, 96.6 % raw infeasibility). |
| `fe_runtime.json`, `failure_table.csv` | FE batch timing; counts by status (15,000 OK, 0 failed runs; 3,424 feasible / 11,576 infeasible-but-valid). |
| `benchmark.json` | OpenSees-vs-STAAD comparison numbers. |
| `surrogate_metrics.json` | Accuracy of surrogates A and B, overall and near the boundary, before/after active learning, learning curve, margins. |
| `optimization_summary.json` | Every NSGA-II run: hypervolume, evaluations, runtimes, front sizes. |
| `compute_comparison.json` | Surrogate vs direct FE: evaluations, wall time, speed-up with and without data generation/training. |
| `pareto_direct.parquet`, `pareto_surrogate_A.parquet`, `…_A_margin`, `…_B`, `…_B_margin` (+ `pareto_surrogate.parquet`, the headline copy) | The near-Pareto designs of each configuration, re-evaluated with the exact analysis. |
| `verification.json` | The 30-design verification of each front, with every failure and its reason. |
| `full_front_check.json` | Exact re-evaluation of the whole pooled fronts. |
| `sensitivity.json` | ±20 % study of steel cost, cement carbon and steel carbon. |
| `cement_tradeoff.json` | When a low-carbon cement creates a real cost-carbon trade-off (price-premium scan). |
| `figures/` | Plots: parity and residual plots for A and B before/after active learning, feature importance. |
