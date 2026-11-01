# `docs/` — the written documentation (read these before the viva)

**Plain words:** explanations, justifications, and the draft of the report. Files marked *(generated)* are written by the code from real results — do not edit them by hand; re-run `python -m rcopt.cli report` instead.

| File | Who should read it | What it contains |
|---|---|---|
| `PROGRESS_AND_TODO.md` | **everyone — start here** | What is finished, what is left, who can do which task, success-criteria status, known limits. |
| `REPORT_DRAFT.md` *(generated)* | everyone — it is the skeleton of the final report | Abstract, method, results (dataset, surrogates, Pareto fronts, verification, compute comparison), limitations, conclusions — all with the real numbers. Needs editing into the final written report. |
| `VIVA_PREP.md` *(generated)* | everyone | Likely questions from the guide with answers backed by the numbers. |
| `ASSUMPTIONS.md` | **the team (must act)** | The master list of every unverified or chosen value (IS 456 tables A1–A12, loads, prices, carbon, cement) with "owner must verify" flags. |
| `DECISIONS.md` | anyone curious "why?" | 28 numbered decisions (D-001 … D-028): the question, options, choice, reason and how to reverse it — e.g. why genome repair, why Surrogate B uses column position classes, why cement is a variable. |
| `STANDARDS_COMPLIANCE.md` | civil members | What IS clauses are enforced in every reported design and what is **not** (seismic, wind, torsion, detailing…). |
| `BENCHMARK.md` *(generated)* | civil members | The OpenSees-versus-STAAD comparison tables and how two early differences (wall-load torque, shear deformation) were found and fixed. |
| `CARBON_DATA_AUDIT.md` | whoever replaces the carbon data | Where each carbon factor came from, its confidence and what a real source would be. |
| `LEGACY_AUDIT.md` | anyone asking "what about the old code?" | What the original files were, their defects (wrong quantities, no real analysis, single-point "front"), what was reused and what was discarded. |
| `SEISMIC_EXTENSION.md` | next-semester / future work | What would be needed to add IS 1893 seismic design (not done). |
| `DEPLOY.md` | whoever shares the site | Run it on one laptop, share on the same Wi-Fi, a temporary public link (tunnel), a permanent static website (Vercel / GitHub Pages), or a full online server (Docker / Render). |
| `LARGE_FILES.md` | whoever manages the Google Drive | List of big files not in git, their size and where each must be put. |
| `figures/` | report writers | Ready-made report figures: `pareto_fronts.png`, `convergence.png`, `parity_A_after_AL.png`, `parity_B_after_AL.png`. |
| `hand_calcs/` | civil members, viva | `beam_example.md` and `column_example.md`: independent worked IS 456 examples with every intermediate value, produced by `hand_calcs.py` (which does not import the project code, so it is a true cross-check). Re-derive at least one by hand. |
