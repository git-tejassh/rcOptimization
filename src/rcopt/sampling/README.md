# `sampling/` — choosing the 15,000 example designs

**Plain words:** to teach a machine-learning model, we first need many example designs with the "right answers" from the real analysis. Picking them
at random wastes most of the budget (almost all random designs are too small to be safe), so two methods are mixed.

| File | What it does |
|---|---|
| `discrete_lhs.py` | **Latin-hypercube sampling for discrete choices**: spreads the samples evenly so every option of every gene (every beam size, bar diameter, grade…) is represented almost equally. 9,000 designs come from here. |
| `biased_sampler.py` | **Feasibility-biased sampling**: draws designs and keeps only those passing cheap hand-style pre-checks (geometry, steel percentages, rough capacity vs a rough demand estimate) so the dataset contains many designs *near the pass/fail boundary* — where the surrogate must be accurate. 6,000 designs (40 %). Rejections are counted by reason. |
| `matrix.py` | Combines both groups, repairs and de-duplicates them, runs a sanity check (0 physically impossible rows) and writes `data/processed/design_matrix.parquet` plus `data/results/sampling_report.json` (it reports the raw 96.6 % geometric-infeasibility fraction). |
| `__init__.py` | Marks the folder as a package. |

Settings (`n_base` = 15,000, `biased_fraction` = 0.40, seed 42) are in `config/sampling.yaml`.
