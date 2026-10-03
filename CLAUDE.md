# CLAUDE.md — Operating Manual

> You are the sole engineer on this repository. This file tells you **how to work**.
> `project.md` (same directory) tells you **what to build**. Read both fully before touching anything.
> If the two ever conflict: `project.md` wins on *technical content*, `CLAUDE.md` wins on *process*.
> Original source brief: `RC-Optimization-Project-Brief.PDF` (same directory). Where the PDF and `project.md`
> differ, `project.md` is authoritative — it records the deliberate deviations (see `project.md` §14).

Owner: Tejas Shrivastava ("Taru"), final-year B.Tech Civil, MANIT Bhopal.
Context: compulsory major project, **7th semester only** (does not continue into 8th). Time is short. Do not expand scope.

---

## 0. Reading order (do this first, in this order)

1. `CLAUDE.md` (this file)
2. `project.md`
3. `RC-Optimization-Project-Brief.PDF` (the guide-facing brief — background only)
4. `context.txt` (26 KB, unknown provenance — likely a prior chat/context dump). Treat as **hints, not truth**.
   Anything in it that contradicts `project.md` is recorded in `docs/DECISIONS.md` and `project.md` wins.
5. `README.md` (existing, 2 KB — will be replaced; archive the old one to `legacy/README_old.md`)
6. The legacy Python files (see §2) — read them *before* writing new code; they may contain reusable logic
   (cost model, constraint definitions, section lists) and may reveal what was already decided.

Write `docs/LEGACY_AUDIT.md` summarizing: what each legacy file does, what is reusable, what contradicts the brief,
and what you chose to do about it. This is the first deliverable of the run.

---

## 1. Prime directives

1. **Truth over polish.** Never fabricate a number, code clause, table value, price, emission factor, citation, or test result.
   If a value cannot be verified, mark it `status: provisional` in its YAML/JSON, surface a visible warning in the
   report and UI, and continue. Do not silently guess.
2. **Fail loud, never silent.** Failed / infeasible / non-converged FE runs are **logged with a reason code and kept in the
   dataset with a flag** — never dropped, never interpolated over. (Brief §6 Phase 2 and §11.)
3. **Report unfavorable results.** If the surrogate is bad near the feasibility boundary, if verification fails for some
   designs, if the Pareto front is narrow — say so in the report and UI. A clean narrative built on omitted failures is a
   project failure. (Brief §6 Phase 5, §13.)
4. **Everything is config-driven.** Variable ranges, loads, unit rates, emission factors, GA hyper-parameters, seeds:
   all in `config/*.yaml`. The faculty guide will change scope defaults after you finish; changing a YAML and re-running
   must be enough. No magic numbers in source files.
5. **Reproducible by a stranger.** Fixed seeds, pinned dependencies, one command per phase, one command for everything.
6. **IS-code correctness is the highest technical risk.** Every code-check function cites the IS clause in its docstring and has a
   unit test against an independently derivable value (see `project.md` §7.4). Do not trust your memory of tables:
   transcribe → test → flag for the owner's manual verification in `docs/ASSUMPTIONS.md`.
7. **Do not widen scope.** Out of scope (explicit): foundations, construction-sequence carbon, operational carbon,
   seismic design (except the optional Phase 6 stub described in `project.md`). Don't add multiple building typologies.
8. **Decide, record, continue.** When something is ambiguous, pick the most defensible option, write it to
   `docs/DECISIONS.md` (date, question, options, choice, reason, how to reverse), and keep going. Do not stop to ask
   unless a *hard blocker* in §6 applies.

---

## 2. The existing files (inventory from the owner's folder)

The folder was provided as two directory listings (possibly truncated — **enumerate the real directory yourself**).

**STAAD.Pro model family (`G+3 RCC FINAL*` and `G+3 RCC FINAL_Modified*`)** — the owner's existing G+3 RCC building model.
- Source-of-truth text inputs (read these): `G+3 RCC FINAL` (12 KB "Text Document", probably the STAAD input/export —
  verify), `G+3 RCC FINAL_Modified.std` (10 KB), `G+3 RCC FINAL.App` / `_Modified.App` (small text).
  Diff `FINAL` vs `FINAL_Modified` to learn what the previous optimizer modified.
- STAAD-generated binaries/results (**do not parse unless needed for benchmark, never commit**): `.ANL` (analysis output),
  `.bmd` (2.7 MB), `.dbs`, `.dgn`, `.dsp`, `.FLD`, `.rea`, `.day`, `.EQL`, `.CFR`, `.cod`, `.cut`, `.num`, `.sbk`, `.slg`,
  `.uid`, `.metadata`, `*_AutoRecovery.zip`, `REI_Saved_Picture`, `__pycache__/`.
- Extract from the STAAD text: node coordinates, member incidences, storey heights, bay spans, section assignments,
  material constants, load cases (DL / LL / floor load / wall load), load combinations, supports.
  This becomes the **default geometry and loading** for the new OpenSeesPy frame (see `project.md` §4).
- The existing STAAD analysis results (`.ANL` text report if readable) are the **independent benchmark** for validating the
  new OpenSeesPy model (`project.md` §7.5). Use them; don't ignore them.

**Legacy Python (all small):**
- `openstaad_handler.py`, `staad_file_handler.py` — drive/edit STAAD from Python (Windows + licensed STAAD only).
- `rcc_nsga2_optimization.py` (5 KB), `Optimization.py` (2 KB) — an earlier NSGA-II attempt, apparently against STAAD.
- `plot_pareto_front.py` (3 KB) + `pareto_front.png`, `pareto_front_highres.png` — an earlier Pareto plot.
- `README.md`, `context.txt`.

⚠ **Known tension:** the brief (§7) says STAAD is *deliberately excluded* from the automated loop, yet this folder contains a
STAAD-driven NSGA-II and Pareto plots. Do not assume which is current. Resolve it in `docs/LEGACY_AUDIT.md`:
legacy STAAD-in-the-loop code is archived and used **only** as (a) a geometry/load source and (b) a benchmark.
The new pipeline is OpenSeesPy-based and must run on any OS with no STAAD license.

**Handling rule:** first commit a pristine snapshot of the folder as-is (see §7), *then* restructure.
Move originals into `legacy/` (`legacy/staad_model/`, `legacy/python/`); never delete the owner's files.

---

## 3. Environment

- Python **3.11** in `.venv` (OpenSeesPy wheels are version-sensitive; if 3.11 is unavailable use 3.10 or 3.12;
  record the version in `docs/DECISIONS.md`).
- Pinned `requirements.txt` + `pyproject.toml` (package name `rcopt`, `src/` layout, installed editable).
  Core: `openseespy`, `numpy`, `scipy`, `pandas`, `pyarrow`, `pyyaml`, `pydantic`, `scikit-learn`, `xgboost`, `pymoo>=0.6`,
  `matplotlib`, `plotly`, `fastapi`, `uvicorn`, `joblib`, `tqdm`, `pytest`, `ruff`, `typer`.
- Node 18+ for `web/` (Vite + React + TypeScript + Tailwind).
- Task runner: a `Makefile` (and `make.ps1` mirror for Windows — the owner is on Windows).
  Required targets: `setup`, `audit`, `phase0` … `phase5`, `all`, `test`, `lint`, `web-dev`, `web-build`, `api`, `export`, `clean`.
- Units: **SI — N, mm, MPa** internally; kN, kN·m, m only at presentation. Money: ₹ (INR). Carbon: kgCO₂e. State units in every
  variable name or docstring (`Mu_kNm`, `fck_MPa`).
- Parallelism: `joblib`/`multiprocessing` for FE batch runs; each worker builds its own OpenSees model (OpenSees is global-state — never share).
  Must work on a laptop; default `n_jobs = cpu_count - 1`.

---

## 4. Repository layout (create exactly this; details in `project.md` §13)

```
<repo root = the parent working folder>
├── CLAUDE.md  project.md  README.md  STATUS.md  PROMPT.md
├── RC-Optimization-Project-Brief.PDF
├── config/            # all tunables (YAML)
├── src/rcopt/         # package: geometry, fe, codes, design, sampling, cost_carbon, surrogate, optimize, verify, report
├── scripts/           # thin CLI wrappers, one per phase
├── tests/
├── data/              # raw/ (gitignored if large), processed/, results/ (small, committed, feeds the UI)
├── models/            # trained surrogate artifacts
├── api/               # FastAPI local server (live surrogate evaluation)
├── web/               # static dashboard (Vite+React+TS) — deployable to Vercel
├── docs/              # LEGACY_AUDIT.md DECISIONS.md ASSUMPTIONS.md hand_calcs/ DEPLOY.md REPORT_DRAFT.md
├── legacy/            # the owner's original files, untouched
└── .github/workflows/ci.yml
```

---

## 5. Execution protocol (autonomous, phase-gated, resumable)

Run **all** phases in one session. After each phase: run its gate, write results to `STATUS.md`, commit, tag `phase-N`.
`STATUS.md` is your memory across context resets — keep it current: phase, gate result, key metrics, open issues, next step.
If the session is interrupted, a new session must be able to resume from `STATUS.md` + git log alone. Every pipeline stage
caches its output and is skipped if inputs (config hash) are unchanged.

| Phase | Name | Gate (must pass before moving on; if it cannot pass, record why and continue with a visible warning) |
|---|---|---|
| P-1 | Snapshot + legacy audit | Pristine snapshot commit exists; `docs/LEGACY_AUDIT.md` written |
| P0 | Scaffolding, config, design space | `config/*.yaml` complete; `pytest tests/test_design_space.py` passes; ASSUMPTIONS.md lists every unverified value |
| P0b | Geometry + FE model + IS 456 checker + STAAD cross-check | Hand-calc anchor tests pass; OpenSees vs STAAD benchmark within tolerance **or** discrepancy explained in docs |
| P1 | Sampling (discrete-aware LHS) | Design matrix generated; sanity script reports 0 physically impossible rows; infeasible-by-geometry fraction reported |
| P2 | FE batch data generation | Dataset parquet with every run + status flag; failure table by reason code; runtime recorded |
| P3 | Surrogate training | Metrics report (overall + near-boundary); parity plots; boundary active-learning round executed once |
| P4 | NSGA-II (surrogate) + NSGA-II (direct FE baseline) | ≥5 seeds; hypervolume/convergence logged; compute-saving comparison table |
| P5 | Verification | 20–30 Pareto designs re-run through FE + IS checks; pass rate reported **including failures** |
| P6 | (Optional stub) seismic hook | Only the interface + docs; no seismic results claimed |
| P7 | Export + API + Web UI | `make web-build` succeeds; UI renders from `web/public/data/*.json`; API smoke tests pass |
| P8 | Docs + report skeleton + CI | `docs/REPORT_DRAFT.md` populated with real numbers from `data/results/` |
| P9 | GitHub push | Remote `main` matches local; tags pushed |

**Quality bar per phase:** unit tests for new logic, no TODO-stubs presented as complete, type hints on public functions,
docstrings citing IS clauses/papers where relevant, `ruff` clean.

---

## 6. When you may stop and ask (hard blockers only)

1. `openseespy` cannot be installed for this OS/Python after trying 3.10/3.11/3.12 → stop and report exact error.
2. Nothing else is a blocker. In particular:
   - **STAAD files unparsable** → build a parametric regular frame from `config/geometry.yaml` defaults; document; continue.
   - **`gh` not authenticated / no network for GitHub** → finish everything locally, commit, and print the exact push commands
     as the final output. Never ask for or embed tokens/passwords.
   - **Emission factors / unit rates unverifiable** → provisional + visible warning; continue.
   - **Surrogate underperforms** → run the active-learning round, tune once, report honestly, continue.
   - **Pareto front is narrow** → expected (cost and carbon are both driven mostly by material volume); report it as a finding
     (see `project.md` §9.4) — do not "fix" it by distorting the objectives.

---

## 7. Git & GitHub protocol

1. `git init` (if not already a repo). Branch `main`.
2. **Before any restructuring:** write a conservative `.gitignore` (see `project.md` §13.3), then commit a snapshot of the
   original files: `chore: snapshot original working folder`. Large STAAD binaries are excluded by `.gitignore`
   (`.bmd`, `.ANL`, `.dbs`, `.dgn`, `.dsp`, `.FLD`, `.rea`, `.day`, AutoRecovery zip, `__pycache__`); the STAAD *text inputs*
   (`.std`, input text docs) **are** committed under `legacy/staad_model/`.
3. Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`), one commit (min.) per phase; tag `phase-N`.
4. Never commit: secrets, tokens, `.env`, venv, `node_modules`, files > 25 MB, STAAD result binaries.
5. Final step: `gh repo create rc-pareto-optimization --private --source=. --remote=origin --push` (if `gh auth status` is OK),
   then `git push --tags`. If the repo name exists, use `rc-pareto-optimization-<yyyymmdd>`. Make it **private**; the owner decides on publicity.
6. Add `.github/workflows/ci.yml`: ruff + pytest (fast tests only, mark heavy ones `@pytest.mark.slow`) + `web` build.

---

## 8. Web UI & API protocol

- **Static dashboard is the primary deliverable** (deploys to Vercel/Netlify/GitHub Pages): all heavy computation is done
  offline; the UI reads `web/public/data/*.json` produced by `make export`. Do **not** put OpenSeesPy/XGBoost/pymoo on Vercel
  serverless (size limits, native deps).
- **Optional local API** (`api/`, FastAPI): live "evaluate this design" using the surrogate, and ground-truth FE on demand.
  The UI detects the API (`VITE_API_URL`); if absent, the live-evaluator panel is hidden/disabled with an explanatory note.
- Provide `vercel.json`, `docs/DEPLOY.md` (local run, Vercel deploy via `vercel --prod` with `web/` as root, GitHub Pages alternative),
  and a `Dockerfile` for the API. You cannot authenticate to Vercel — prepare everything and print the commands.
- UI honesty requirements: visible **PROVISIONAL DATA** banner whenever any used factor has `status: provisional`; verification
  failures shown in red, not hidden; "gravity-only" caveat shown on every design page.
- Full UI spec: `project.md` §11.

---

## 9. Definition of Done (verify each item and tick it in `STATUS.md`)

- [ ] `docs/LEGACY_AUDIT.md` exists; legacy files archived under `legacy/`, none deleted
- [ ] `make setup && make all` runs end-to-end on a clean checkout and regenerates all `data/results/*`
- [ ] IS 456 anchor tests pass (Mu,lim/bd², τc,max, τc spot values, column interaction spot values)
- [ ] OpenSeesPy-vs-STAAD benchmark documented (pass or explained)
- [ ] FE dataset with status flags + failure table; no silently dropped rows
- [ ] Two surrogate variants trained (A: direct utilization regression per brief; B: demand-surrogate + analytic capacity), metrics compared
- [ ] NSGA-II run with surrogate AND direct-FE baseline, ≥5 seeds, hypervolume + compute-saving table
- [ ] Verification of 20–30 Pareto designs, pass rate + failures reported
- [ ] `web/` builds; all pages in `project.md` §11 render from real data; Lighthouse-style sanity (no console errors)
- [ ] API smoke tests pass
- [ ] `docs/ASSUMPTIONS.md` lists every provisional value with source/confidence and "owner must verify" flags
- [ ] `docs/REPORT_DRAFT.md` filled with real numbers; no placeholder numbers
- [ ] CI config present; repo pushed (or exact push commands printed)

---

## 10. Never do

- Never invent emission factors, unit rates, or IS table values and present them as sourced.
- Never drop failed runs, cherry-pick seeds, or tune on the verification set.
- Never use STAAD/OpenSTAAD inside the automated loop; never require a STAAD license to run the pipeline.
- Never present continuous relaxations of discrete IS-standard sizes/bars/grades as buildable designs.
- Never claim the design is fully IS-compliant: it is **gravity-only** unless Phase 6 is actually completed.
- Never claim a novel algorithm. The contribution is a validated, India-contextualized application (Brief §3).
- Never delete or overwrite the owner's original files; never commit secrets.
- Never leave `print`-debugging, dead code, or notebooks as the only record of an analysis.

---

## 11. Final message to the owner (your last output)

Plain, blunt, short. Include: (1) what was built and where; (2) key numbers (dataset size, runtime, surrogate R²/MAE overall and near-boundary,
hypervolume, surrogate-vs-direct speedup, verification pass rate); (3) every failure/limitation/provisional value;
(4) the exact commands to run locally, to deploy on Vercel, and — if the push failed — to push to GitHub;
(5) the list of items the owner/guide **must** manually verify (IS table transcriptions, emission factors, unit rates, STAAD benchmark gap).
