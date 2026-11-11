# `src/rcopt/` — the engine (all the Python code)

**In one sentence:** this folder is the whole calculation machine. It builds the building model, runs the structural analysis, checks every design
against the Indian concrete code (IS 456), computes cost and carbon, trains the fast "guessing" models (surrogates), runs the optimiser, double-checks
the answers and writes the results the website shows.

`rcopt` is a Python *package*: each sub-folder below is one job. Nothing here contains a hard-coded price, load or option list — those live in
[`../../config/`](../../config/README.md) so they can be changed without touching code.

## How the pieces fit together (the pipeline)

```
config/*.yaml  ──►  design/        what a design IS (23 choices) and which ones are buildable
                    geometry/      the building frame (4 x 3 bays, G+3)
                       │
   sampling/  ──►  15,000 different designs to learn from
                       │
   fe/ + codes/ ─►  for each design: structural analysis (OpenSees) + IS 456 checks  ──► data/processed/fe_dataset.parquet
                       │
   cost_carbon/ ─►  quantities → cost (INR) and embodied carbon (kgCO2e)
                       │
   surrogate/  ──►  train fast models that imitate the analysis (A and B)
                       │
   optimize/   ──►  NSGA-II search for the cheapest / lowest-carbon designs  ──► the "Pareto front"
                       │
   verify/     ──►  re-run the answers through the exact analysis (honest pass rate)
                       │
   report/     ──►  figures, report draft, JSON files for the website
   review/     ──►  extra: check & reinforce a user's own STAAD frame (website "My design estimate")
   seismic/    ──►  empty placeholder (earthquake design is NOT done)
```

## Sub-folders

| Folder | Job in plain words | README |
|---|---|---|
| `design/` | Defines a "design" (23 numbers), repairs impossible ones, combines checks + cost + carbon | [open](design/README.md) |
| `geometry/` | The frame layout and a reader for STAAD input files | [open](geometry/README.md) |
| `fe/` | OpenSees structural analysis, loads, batch runs, STAAD comparison | [open](fe/README.md) |
| `codes/` | IS 456 rules: beams, columns, deflection, bar layout, code tables | [open](codes/README.md) |
| `cost_carbon/` | Material quantities, cost, embodied carbon, sensitivity and cement studies | [open](cost_carbon/README.md) |
| `sampling/` | Chooses the 15,000 example designs | [open](sampling/README.md) |
| `surrogate/` | Machine-learning stand-ins for the slow analysis | [open](surrogate/README.md) |
| `optimize/` | The NSGA-II search and its quality measures | [open](optimize/README.md) |
| `verify/` | Re-checks the optimiser's answers with the exact method | [open](verify/README.md) |
| `report/` | Writes figures, the report draft and the website data | [open](report/README.md) |
| `review/` | Strength check + reinforcement design of a user's STAAD frame | [open](review/README.md) |
| `seismic/` | Placeholder for earthquake design (not implemented on purpose) | [open](seismic/README.md) |

## Files directly in this folder

| File | What it does |
|---|---|
| `__init__.py` | Empty file that makes `rcopt` an importable package. |
| `config.py` | Reads every YAML file in `config/`, checks it is valid (so a typo fails loudly), and offers helpers: `design_space()`, `geometry()`, `loads()`, `config_hash()` (a fingerprint used to skip stages whose inputs did not change; metadata edits and price/carbon edits do not trigger a new FE batch or retraining) and `provisional_items()` (the list of unverified values that trigger the yellow "PROVISIONAL DATA" banners). |
| `cli.py` | The command-line "control panel". `python -m rcopt.cli phase0` … `phase5`, `sensitivity`, `cement`, `report`, `export`, `all`, and `reoptimize` (change prices, then optimise), `prices-template` (CSV of editable prices) and `serve` (starts the website + live API on one address). Each command only calls the matching package and caches its output. |
