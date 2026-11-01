# `legacy/` — the owner's original files (kept untouched)

Nothing here is used by the automatic pipeline, **except** the STAAD model, which is the source of the frame geometry/loads and the benchmark for validating the new model. The pristine state before any restructuring is the git tag `snapshot-original`. Full analysis: [`../docs/LEGACY_AUDIT.md`](../docs/LEGACY_AUDIT.md).

| Item | What it is | Used now? |
|---|---|---|
| `staad_model/G+3 RCC FINAL.STD` | The owner's STAAD.Pro input for the G+3 building: 120 joints, 255 members, loads and 25 combinations. | **Yes** — geometry, loads, benchmark. |
| `staad_model/G+3 RCC FINAL_Modified.std` | Same model after the old optimiser ran; the only difference is one beam width (0.30 → 0.25 m). | Evidence only. |
| `staad_model/*.cod .cut .log .png .App.log .STD_Modified` | Small STAAD side files (design code settings, logs, screenshots). | No. |
| `staad_model/` result binaries (`.ANL .rea .dsp .bmd .dbs …`) | STAAD's analysis results (2–3 MB each). **On the owner's laptop only — not in git.** Needed to re-run `phase0b` and `tests/test_benchmark.py` (otherwise those tests are skipped). | Benchmark only. |
| `python/rcc_nsga2_optimization.py`, `Optimization.py` | The earlier NSGA-II against STAAD: continuous variables, constant "demands", wrong member lengths, collapsed to a single point. | No — replaced. |
| `python/openstaad_handler.py`, `staad_file_handler.py` | Stubs that pretend to drive STAAD / rewrite its file with a regex. | No. |
| `python/plot_pareto_front.py`, `pareto_front*.png` | Old plot script and pictures (hard-coded path of another PC). | No. |
| `context.txt` | An old chat dump with the project's origin and example prices/factors. Source of the first (unverified) cost placeholders. | Hints only. |
| `README_old.md` | The original README. | No. |
