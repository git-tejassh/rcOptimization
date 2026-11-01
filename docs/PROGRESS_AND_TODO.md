# What is finished, what is left (written for the whole team)

*Snapshot of the repository after a complete walk-through of every file. "Verified" below means it was actually run: **77 automatic tests pass, the code-style check is clean**, the website builds and every page renders (checked in a browser).*

---

## 1. Finished

### 1.1 The calculation pipeline (all 9 planned phases)
| Phase | What it means in plain words | State | Evidence |
|---|---|---|---|
| P-1 Snapshot + legacy audit | Saved the owner's original files untouched, wrote down what the old code did wrong | ✅ done | `legacy/`, `docs/LEGACY_AUDIT.md`, git tag `snapshot-original` |
| P0 Setup, config, design space | All settings in text files; 23 choices, all IS-standard options | ✅ done | `config/`, `tests/test_design_space.py` |
| P0b Structural model + IS 456 + STAAD cross-check | OpenSees model of the G+3 frame, IS 456 checks, compared with the owner's STAAD | ✅ done | reactions 1e-5, column axial 3e-5, moments 0.12 % (`docs/BENCHMARK.md`); STAAD column-81 ratio 0.39 reproduced |
| P1 Sampling | Chose 15,000 designs (9,000 evenly spread + 6,000 near the safe/unsafe boundary) | ✅ done | `data/results/sampling_report.json` |
| P2 Analysis of every design | 15,000 designs analysed and checked; none dropped, 0 failed runs | ✅ done | 3,424 feasible, 5,298 near boundary, 156 s on 8 cores |
| P3 Surrogates | Trained two models (A and B), measured errors overall and near the boundary, one active-learning round | ✅ done | `data/results/surrogate_metrics.json` |
| P4 Optimisation | NSGA-II, 5 configurations × 5 seeds (population 200, 300 generations), plus the slow "direct" baseline | ✅ done | `data/results/optimization_summary.json` |
| P5 Verification | 30 designs per front re-checked exactly; failures listed with reasons | ✅ done | A 40 %, A+margin 70 %, **B 87 %, B+margin 90 %** |
| P6 Seismic hook | Only an empty placeholder with documentation (earthquake design is *not* done) | ⚪ stub by design | `src/rcopt/seismic/`, `docs/SEISMIC_EXTENSION.md` |
| P7 Export, server, website | Results exported; website and local server working | ✅ done | `web/`, `api/`, `rcopt serve` |
| P8 Docs + report draft + CI | Report draft filled with real numbers; GitHub workflow present | ✅ done | `docs/REPORT_DRAFT.md`, `.github/workflows/ci.yml` |
| P9 GitHub push | Everything pushed to `git-tejassh/rcOptimization` (14 commits, 14 tags, latest tag `review-report`) | ✅ done up to the last code commit | the new README files from this walk-through are **not yet committed** |

### 1.2 Extra work added after the original plan (at the owner's request)
* **Standards compliance** — minimum concrete grade per IS 456 Table 5 enforced (M25–M40 for moderate exposure); cover, bar sizes, spacing, ties, steel limits all per code (`docs/STANDARDS_COMPLIANCE.md`).
* **More FE data** — 15,000 designs instead of 5,000 (the learning curve was still improving).
* **Realistic Indian carbon factors** (PPC 0.507, OPC 0.92, PSC 0.312, rebar 2.5 kgCO₂e/kg; secondary sources, `docs/CARBON_DATA_AUDIT.md`).
* **Cement type as the 23rd design variable** and a cement price-premium study (`cement_tradeoff.json`).
* **Professional website** — light/green, grouped header menus, one title per page, plain-language page guides, red/yellow/green Pareto zones, full property sheet of any point, best-case cards, a table of *every* Pareto point with all its feature values.
* **"My design estimate" tab** — upload a STAAD file, edit every price/carbon factor, quantities + cost + carbon, **IS 456 strength review with designed reinforcement**, **several suggested optimised designs**, downloadable final report.
* **One-command server** (`rcopt serve`) and a **deployment guide**, Dockerfile, Render and Vercel files.

### 1.3 Success criteria of the project brief (S1–S5)
| # | Criterion | Result |
|---|---|---|
| S1 | ≥ 25 non-dominated Pareto points | ❌ **Not met** — rank-1 sets have 6–13 points (cost and carbon move together; reported as a finding, not "fixed"). A ~100-design near-Pareto set is used for verification. |
| S2 | ≥ 90 % of 30 verified designs correct | ⚠️ **Met only by B + margin (90 %)**; plain A gets 40 % (reported honestly). |
| S3 | Errors reported overall and near the boundary | ✅ done |
| S4 | Compute savings quantified (surrogate vs direct FE) | ✅ done — 1.6–3.5× faster for the optimisation alone, but **no saving** once data generation + training are counted (0.67–0.87×). |
| S5 | Only IS-standard discrete options | ✅ done (tested) |

---

## 2. Left to do

### 2.1 Must be done by the team (nobody else can do these) — highest priority
| # | Task | Where | Why it matters |
|---|---|---|---|
| 1 | **Replace the placeholder prices** with current Bhopal rates (Essco list / MP PWD SOR / CPWD DSR): concrete per m³ by grade, steel per kg, formwork per m², cement per kg (OPC/PPC/PSC). Set `status: sourced`. | `config/cost_rates.yaml` | All ₹ values are indicative until then; the shape of the front depends on price ratios. |
| 2 | **Check the IS 456 table transcriptions** (Table 19, Table 20, xu,max/d, stress-strain curve, steel limits…) against the printed code / SP 16. | `config/is456_tables.yaml`, list `docs/ASSUMPTIONS.md` A1–A12 | They were typed from memory; a wrong cell changes the safety results. |
| 3 | **Replace provisional carbon inputs**: cement content per grade, other concrete constituents, transport distances (ideally supplier EPDs). | `config/carbon_factors.yaml`, `docs/CARBON_DATA_AUDIT.md` | Absolute kgCO₂e is indicative until then. |
| 4 | After changing 1–3, **re-run** everything (`.\make.ps1 all`, about 2 h) and rebuild the website (`cd web; npm run build`). | – | Updates all numbers, plots and the report draft automatically. |
| 5 | **Decide with the guide**: defend the cracked-stiffness factors (beams 0.35, columns 0.70), exposure/cover (moderate, 30/40 mm), PPC as the baseline cement, 6 %/4 % column steel cap. | `config/solver.yaml`, `config/design_space.yaml` | Not validated by STAAD; the guide may prefer other values. |
| 6 | **Upload the large files to Google Drive** and paste the link into `README.md` (`<ADD LINK HERE>`). `models.zip` (286 MB) is already packed in the repo folder; other files are listed in `docs/LARGE_FILES.md`. | `README.md`, `docs/LARGE_FILES.md` | Teammates cannot use the live evaluator without the models. |
| 7 | **Write the final project report** from `docs/REPORT_DRAFT.md` (it has the real numbers but is a draft) and prepare the presentation. Practise the questions in `docs/VIVA_PREP.md`. | `docs/` | Main deliverable for the guide. |
| 8 | **Re-derive one beam and one column by hand** from `docs/hand_calcs/` so you can defend the code in the viva. | `docs/hand_calcs/` | Shows the IS 456 implementation is understood. |
| 9 | **Decide whether seismic/wind is in scope.** At present the designs are *not* complete code-compliant designs (57 of 133 columns in the STAAD report are governed by seismic cases). The project must say "gravity-only" everywhere (the website already does). | `docs/SEISMIC_EXTENSION.md` | Scope honesty; the project stops after the 7th semester. |

### 2.2 Sharing the website (needs one person with a GitHub / Vercel account)
* **Always-on, results only:** deploy `web/` on Vercel or GitHub Pages (needs a login I cannot do for you) — [`docs/DEPLOY.md`](DEPLOY.md) section 4a.
* **Live evaluator for the guide:** run `rcopt serve` on one laptop and share the temporary tunnel link or the same-Wi-Fi address (section 2–3 of the guide).
* **Full online server (Docker/Render):** written but **never built or run**; test it once locally before depending on it.

### 2.3 Known limits of the work (honest list — keep in the report)
* Pareto front is narrow; S1 not met. A real trade-off needs a low-carbon cement that costs more (price premium unverified).
* Surrogate A without a margin is unreliable at the boundary; active learning gave no measurable gain; the surrogate does not save time overall.
* Gravity only; torsion, P-delta, T-beam action, bar curtailment, slab design, foundations and construction carbon are ignored; beams are checked at centre-line moments.
* The strength review (website) handles only complete regular rectangular grid frames, uses the project's default IS 875 loads (not the STAAD load cases) and checks no detailing (development length, torsion).
* The "vs yours" comparison of suggested designs is meaningful only for a frame of the project size (4 × 3 bays of 5 m, G+3).
* STAAD benchmark covers gravity results only; the STAAD beam design was aborted by the owner, so beams are not benchmarked against STAAD.

### 2.4 Optional improvements if time remains (none required)
* Run `make setup && make all` once on a **fresh clone** to prove reproducibility (not done after the last changes; stages were run individually).
* `make all` / `make.ps1 all` run phase0–5 + export only; sensitivity, cement scan and report are run by `python -m rcopt.cli all`. Make the two consistent.
* Confirm the GitHub Actions workflow is green after the next push (it has not been checked on GitHub).
* Add automatic tests for the website (currently verified by building and by hand).
* Extend the strength review to irregular frames and to the STAAD load cases; add a detailing check.
* Update `STATUS.md` text and `REPORT_DRAFT.md` (generated) to mention the strength-review and server features (REPORT section 2 lists scope; the new tabs are described only in README/web docs).
* Minor doc inconsistency: `docs/hand_calcs/hand_calcs.py` mentions `tests/test_hand_calcs.py`; those comparisons actually live in `tests/test_is456_anchors.py`.

---

## 3. Suggested split of work for 3–4 non-technical teammates (a suggestion — adjust freely)
| Person | Task | Needs coding? |
|---|---|---|
| Civil/IS-code person | Task 2 (check IS 456 tables) and Task 8 (hand calculations), read `docs/STANDARDS_COMPLIANCE.md` | No |
| Costing person | Task 1 (Bhopal rates) — just edit numbers in `config/cost_rates.yaml` | No (edit a text file) |
| Sustainability person | Task 3 (carbon inputs, EPDs) and read `docs/CARBON_DATA_AUDIT.md` | No (edit a text file) |
| Writer/presenter | Task 7 (report + slides + viva questions) using `docs/REPORT_DRAFT.md`, `docs/VIVA_PREP.md` and the website | No |
| Whoever has the laptop that runs it | Tasks 4, 6 and 2.2 (re-run, upload files, share the link) | Copy-paste commands only |

*Everyone can explore the website to learn what the project shows; start with the **Overview**, **Pareto explorer** and **My design estimate** tabs.*

---

## 4. Checklist from the working rules (Definition of Done)
- [x] `docs/LEGACY_AUDIT.md` exists; legacy files archived, none deleted
- [ ] `make setup && make all` verified end-to-end on a clean checkout *(not re-run after the last changes)*
- [x] IS 456 anchor tests pass
- [x] OpenSeesPy-vs-STAAD benchmark documented
- [x] FE dataset with status flags and failure table; nothing dropped
- [x] Two surrogate variants trained, metrics compared
- [x] NSGA-II with surrogate **and** direct FE, 5 seeds, hypervolume + compute table
- [x] Verification of 30 designs per front, pass rate and failures reported
- [x] Website builds; all pages render from real data
- [x] API smoke tests pass
- [x] `docs/ASSUMPTIONS.md` lists every provisional value with "owner must verify" flags
- [x] `docs/REPORT_DRAFT.md` filled with real numbers
- [x] CI config present; repository pushed
