# Surrogate-assisted cost / embodied-carbon optimisation of an RC frame (IS 456, gravity only)

Final-year B.Tech Civil major project (7th semester), MANIT Bhopal. OpenSeesPy-generated data, XGBoost surrogates, constrained NSGA-II (pymoo),
Pareto front, FE re-verification, and a dashboard website. Validated against the owner's STAAD.Pro model (reactions to 1e-5, column moments to 0.12 %).

> **Caveats you must read:** designs are checked for **gravity loading only** (no seismic / wind); unit prices are **placeholders** (you can type your own and re-optimise, see below) and some carbon inputs are provisional (`docs/ASSUMPTIONS.md`, `docs/CARBON_SOURCES_TO_CITE.md`). The IS 456 values were checked against the printed code (`docs/IS456_VERIFICATION.md`).
> No novelty of algorithm is claimed (NSGA-II for RC frames: Kaveh et al., 2016); the contribution is a validated, India-contextualised application.

**New here (especially non-programmers)? Read in this order:** (1) this page → (2) [`docs/PROGRESS_AND_TODO.md`](docs/PROGRESS_AND_TODO.md) (what is finished, what is left, who can do what) → (3) open the website (below) → (4) [`docs/README.md`](docs/README.md) (guide to all documents). Every folder has its own `README.md` explaining each file.

---

## 1. The project in plain words

A reinforced-concrete (RC) building frame can be made *cheaper* or *greener* (less embodied carbon) by choosing smaller sections or less steel — but only down to the point where it stops being safe by the Indian code **IS 456**. Finding the best compromise by hand means trying astronomically many combinations (3.1 × 10¹⁷ for our 23 choices).

What the software does, step by step:

1. **Model the building** — the owner's G+3 frame (4 × 3 bays of 5 m) in a free structural-analysis program (OpenSeesPy), checked against the owner's STAAD.Pro results.
2. **Judge a design** — analyse it under gravity loads and test it against IS 456 (beam bending/shear, column load+moment, deflection, steel limits).
3. **Price a design** — count concrete/steel/formwork → cost (₹) and embodied carbon (kg CO₂e).
4. **Create examples** — evaluate 15,000 different designs this way (≈ 2.5 minutes of computing on 8 cores).
5. **Teach a fast guesser (surrogate)** — two machine-learning models learn to predict the safety result without running the analysis.
6. **Search** — a genetic algorithm (NSGA-II) looks for designs that are as cheap *and* as low-carbon as possible while staying safe. The set of best compromises is the **Pareto front**.
7. **Double-check** — re-run the answers through the exact analysis and report honestly how many pass.
8. **Show it** — a website with the results, a tool to price your own design, and (with the local server) a live evaluator and an IS 456 strength review of an uploaded STAAD file.

### What we found (the honest headline)
* The new analysis reproduces the owner's STAAD results (reactions within 0.001 %, column moments within 0.12 %).
* The surrogate "B" (predict forces, then exact IS 456) is accurate near the safety boundary (99.8 % agreement); the brief's plain surrogate "A" is not (96.6 %).
* Verification of 30 designs per front: A 40 % pass, A + safety margin 70 %, **B 87 %, B + margin 90 %** (target 90 %).
* The Pareto front is **narrow** (only 6–13 strictly best designs; the target of 25 is not met) because cost and carbon both mostly follow material volume. Slag cement (PSC) is both cheaper and lower-carbon at the prices we assumed, so it wins everywhere.
* The surrogate is faster *per optimisation* (1.6–3.5×) but does **not** pay off once data generation and training are counted — an elastic frame analysis is only ~40 ms.
* Prices, cement content, transport and the IS 456 table transcriptions are still **provisional**; everything is gravity-only.

---

## 2. Open the website (pick one)

| Situation | What to do |
|---|---|
| I only want to look | Build once (`cd web` → `npm install` → `npm run build`), then double-click **`web/dist/index.html`**. |
| I want everything (live evaluator + strength review) | Windows PowerShell: `.venv\Scripts\python.exe -m rcopt.cli serve` → open http://localhost:8000 |
| I want to show it to the guide / teammates | See [`docs/DEPLOY.md`](docs/DEPLOY.md): same Wi-Fi (`--host 0.0.0.0`), temporary public link (cloudflared/ngrok), permanent static site (Vercel/GitHub Pages), or full online server (Docker/Render). |

Tabs: Overview · Design space · Pareto explorer (red/yellow/green zones, full property sheet, best-case cards, table of all front points) · **Optimise with my prices** (type prices or load a CSV, then re-run the optimiser) · Surrogate performance · Verification · Compute comparison · Sensitivity (incl. cement type) · Data & assumptions · Live evaluator · About · **My design estimate** (upload a STAAD `.std` or start from an optimised design, edit every price and carbon factor, run the IS 456 strength review, see suggested optimised designs, download a final report). Details: [`web/src/README.md`](web/src/README.md).

### Change the prices, then optimise
All unit prices are placeholders. Two ways to use your own, **before** the optimiser runs:
* **Website** (needs `rcopt serve`): tab *Optimise with my prices* → type a price or move a slider (or load a CSV) → *Optimise* (about 1.5 minutes) → new designs, plot and table, all re-checked with the exact IS 456 model under your prices.
* **Command line:** copy `config/prices_template.csv`, edit the numbers, run `.venv\Scripts\python.exe -m rcopt.cli reoptimize --prices my_prices.csv` (result in `data/results/custom/reoptimized.json`).
For the full five-seed study with new prices, edit `config/cost_rates.yaml` and run `python -m rcopt.cli all` (trained models and the FE dataset are re-used).

## 3. Run the pipeline yourself (Windows PowerShell; Python 3.12)
```powershell
.\make.ps1 setup          # virtual environment + pinned libraries + npm install
.\make.ps1 all            # every stage: phase0 .. phase5, sensitivity, cement scan, report, export (about 2 h the first time; changed prices/carbon only redo phases 4-5 onwards)
.\make.ps1 test           # automatic checks
```
Single steps: `.venv\Scripts\python.exe -m rcopt.cli phase0 | phase0b | phase1 | phase2 | phase3 | phase4 | phase5 | sensitivity | cement | report | export | reoptimize | prices-template | serve`.
Each stage caches its output and is skipped when its inputs did not change (`--force` to redo).

---

## 4. What every folder is for

| Folder | Function (click for the file-by-file guide) |
|---|---|
| [`config/`](config/README.md) | **Every setting** in text (YAML) files: frame geometry, loads, design options, IS 456 numbers, prices, carbon factors, optimiser and ML settings. Change a value → re-run → new results. |
| [`src/rcopt/`](src/rcopt/README.md) | **The engine** (Python): `design`, `geometry`, `fe` (structural analysis), `codes` (IS 456), `cost_carbon`, `sampling`, `surrogate`, `optimize`, `verify`, `report`, `review`, `seismic` (placeholder) — each has its own README. |
| [`api/`](api/README.md) | The small local **server** (FastAPI) that runs the exact analysis, the surrogate and the strength review for the website, and also serves the website. |
| [`web/`](web/README.md) | The **dashboard website** (React). `web/src` = code, `web/public/data` = the exported results it displays, `web/dist` = the built site. |
| [`data/`](data/README.md) | **Inputs and outputs** of the pipeline: the STAAD reference numbers, the 15,000-design dataset, and the small final result files. |
| [`models/`](models/README.md) | The **trained surrogate models** (≈ 300 MB, not in git; get them from Google Drive or retrain). |
| [`tests/`](tests/README.md) | **Automatic checks** that prove the code is right (textbook formulas, STAAD, physics). |
| [`docs/`](docs/README.md) | **Documentation**: report draft, viva prep, assumptions to verify, decisions log, benchmark, standards compliance, deployment guide. |
| [`scripts/`](scripts/README.md) | Helpers to pack/download the large model files. |
| [`legacy/`](legacy/README.md) | The **owner's original files** (STAAD model, old optimiser, old README), untouched. |
| `.github/workflows/` | `ci.yml`: on every push GitHub runs the code-style check, the fast tests and the website build. |
| `.venv/`, `web/node_modules/`, `.claude/` | Local, generated or tool folders (Python environment, JavaScript libraries, assistant settings). Never committed. |

## 5. What every file in the main folder is for

| File | Function |
|---|---|
| `README.md` | This page. |
| `STATUS.md` | Phase-by-phase progress table and the headline findings — the project's "memory" if work is resumed. |
| `CLAUDE.md` | The working rules given to the AI engineer that built this (truth over polish, report failures, everything in config, no invented numbers, etc.). |
| `project.md` | The full technical specification (what to build, success criteria S1–S5, design space, checks, UI spec). |
| `RC-Optimization-Project-Brief.PDF` | The guide-facing project brief (the original assignment). Where it differs from `project.md`, the differences are listed on the website's About page. |
| `Makefile`, `make.ps1` | One-word commands (`setup`, `phase0` … `phase5`, `all`, `test`, `lint`, `export`, `web-build`, `api`, `clean`). `Makefile` is for Mac/Linux, `make.ps1` is the Windows twin. |
| `pyproject.toml` | Python package definition (`rcopt`), test and code-style settings. |
| `requirements.txt` | Exact pinned versions of every Python library (so a stranger gets identical results). |
| `Dockerfile`, `render.yaml` | Recipe to run the full app (website + server) in a container / on Render. Written but **never built or tested** yet. |
| `vercel.json` | Settings for hosting the static website on Vercel. |
| `.gitignore` | Tells git not to store environments, STAAD binaries, big datasets and models. |
| `models.zip` | *(local only, git-ignored, 286 MB)* the packed trained models, ready to upload to Google Drive. |

---

## 6. Large files (not in git)
Trained models, the 15,000-design FE dataset, optimiser histories and the STAAD binaries are too large for the repository.
They are regenerated by `make all`, or download them from the shared folder:

**Google Drive: `<ADD LINK HERE>`**  (contents and where to put them: [`docs/LARGE_FILES.md`](docs/LARGE_FILES.md))

## 7. Glossary for non-engineers / non-programmers

| Term | Meaning |
|---|---|
| **IS 456:2000** | The Indian standard code for plain and reinforced concrete design. Our safety rules come from it. |
| **STAAD.Pro** | Commercial structural-analysis software the owner used. We do not need it to run the project; we only compare against its results. |
| **OpenSees / OpenSeesPy** | Free structural-analysis program (driven from Python) that we use to compute forces in the frame. |
| **FE (finite element) analysis** | Computer method to find forces/deflections in a structure. One run ≈ 40–70 ms here. |
| **Gravity-only** | Only self-weight, walls, floor finishes and people (live load) are considered; no earthquake or wind. |
| **Embodied carbon (kg CO₂e)** | Greenhouse gas emitted to make and transport the materials (cement, steel, concrete). |
| **PPC / OPC / PSC** | Cement types: Portland Pozzolana, Ordinary Portland, Portland Slag Cement. |
| **Design variable / gene** | One of the 23 choices (e.g. beam width, bar diameter, cement type). |
| **Feasible design** | A design that passes every IS 456 check and can be built. |
| **Utilisation ratio** | Demand ÷ capacity. 0.6 = 60 % used; above 1.0 = fails. |
| **Pareto front** | The set of designs where you cannot reduce cost without raising carbon (or vice versa) — the best compromises. |
| **NSGA-II** | The genetic algorithm used to find the Pareto front. |
| **Surrogate** | A machine-learning model trained to imitate the slow analysis quickly. "A" = predicts safety ratios directly; "B" = predicts forces then applies exact IS 456. |
| **Hypervolume** | One number scoring how good and how spread-out a Pareto front is (bigger = better). |
| **Verification** | Re-running optimiser answers through the exact analysis to see whether the surrogate was right. |
| **Provisional** | A number that has not been verified against a real source; shown with yellow warnings. |
| **Active learning** | Adding extra training examples where the model is least sure (here near the safe/unsafe boundary). |

## 8. Status
See [`STATUS.md`](STATUS.md) for the phase gates and [`docs/PROGRESS_AND_TODO.md`](docs/PROGRESS_AND_TODO.md) for what is finished and what is left.
