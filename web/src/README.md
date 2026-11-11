# `web/src/` — the dashboard's source code

**Layout of the site:** a charcoal header with grouped menus **Overview | Designs | Method | Data | Live evaluator** and a green button **My design estimate**; every page opens with one hero banner (the page's single title) and ends with a dark footer. Pages are chosen by the address after `#`, so no server is needed. A render error on a page shows a message instead of a blank screen (`ErrorBoundary`).

## Top-level files
| File | What it does |
|---|---|
| `main.tsx` | Starts React and mounts `App`. |
| `App.tsx` | The frame of the site: header menus, page routing by `#hash`, footer, light/dark theme (remembered in the browser), the error boundary, and the yellow "Provisional data" banner shown on every page. |
| `data.tsx` | Loads all exported JSON (from `window` bundle, else `fetch`) once and gives every page access through `useData()`. |
| `types.ts` | TypeScript descriptions of every JSON file (what fields a design, a front, a verification record has). |
| `format.ts` | Small helpers to print numbers: ₹ lakh, tonnes, percent. |
| `index.css` | The whole look: charcoal/green colour tokens, hero, buttons, pills, tables, cards, light/dark. |

## `pages/` — one file per tab
| File | Tab | What the visitor sees |
|---|---|---|
| `Overview.tsx` | Overview | What the project is, key-number tiles, "what the results say (including the unfavourable ones)" (narrow front, PSC dominates, verification pass rates) and the honest novelty statement. |
| `DesignSpacePage.tsx` | Design space | Elevation/plan sketch of the frame coloured by group; the 23 variables with their allowed options; counts of combinations. |
| `ParetoPage.tsx` | Pareto explorer | The cost-vs-carbon scatter with **red / yellow / green zones** (worst / good / best) and adjustable thresholds, switchable fronts, click a point to see every property, "best case" cards below, and a table of every front point with all 30 feature columns (sortable, CSV download). |
| `SurrogatePage.tsx` | Surrogate performance | Errors of A and B overall and near the boundary, parity/residual plots, learning curve, active-learning effect, feature importance. |
| `VerificationPage.tsx` | Verification | Pass rates per front; every failure listed in red with its reason. |
| `ComputePage.tsx` | Compute comparison | Time and evaluation counts: surrogate vs direct FE, with and without training cost; convergence of hypervolume. |
| `SensitivityPage.tsx` | Sensitivity | ±20 % steel cost / cement carbon / steel carbon and the cement-type (price-premium) trade-off. |
| `ProvenancePage.tsx` | Data & assumptions | The assumptions, decisions, benchmark and carbon audit shown as readable documents; provisional items list. |
| `LivePage.tsx` | Live evaluator | Pick a design, compare surrogate prediction vs exact FE (needs the server); otherwise a readiness checklist and a box to type a server address. |
| `OptimisePage.tsx` | **Optimise with my prices** | Step 1: one input box + slider per unit price (changed prices turn green, "reset" per price), load/download prices as CSV. Step 2: choose quick or thorough, press Optimise (needs the local server; shows live progress). Step 3: the new designs on a cost-vs-carbon plot (colour = cement), the earlier optimum re-priced, a table of all designs with every property, downloads. |
| `AboutPage.tsx` | About | Honest novelty, the method in one paragraph, deviations from the original brief, what is out of scope, how to reproduce. |
| `MyDesignPage.tsx` | **My design estimate** | Step 1 choose the source (upload STAAD file / start from an optimised design / enter member totals) → Step 2 materials → Step 3 **strength review** (server) → Step 4 edit any price or carbon factor (changed fields turn green, one-click reset) → quantities, cost, carbon, zone vs the optimiser → **suggested optimised designs** → table of **every Pareto point** → downloadable/printable **final report**. |

## `components/` — reusable building blocks
| File | What it does |
|---|---|
| `PageHeader.tsx` | The hero (single H1, one-line purpose, next-step buttons) and the `Section` heading helper. |
| `Caveat.tsx` | `GravityCaveat` (gravity-only banner), `Finding` (info/warn/bad note), `Stat` (key-number tile). |
| `Plot.tsx` | Thin wrapper around Plotly (scatter/bar/histogram), theme-aware and responsive. |
| `DesignDetails.tsx` | One design explained in words: materials, member sizes, bars, quantities, cost, carbon, the four checks, verification result. |
| `FrontTable.tsx` | The sortable table of Pareto points with all feature columns, search and CSV export. |
| `Suggestions.tsx` | Picks and lists several optimised designs (lowest cost, lowest carbon, best balance, FE-verified, spread along the front) compared with the user's estimate. |
| `StrengthReview.tsx` | The strength-review panel: sends the STAAD text to the API and shows PASS/FAIL, designed bars, utilisations and failures. |

## `lib/` — logic without screens
| File | What it does |
|---|---|
| `staad.ts` | Browser-side STAAD reader (units, joints, members, section sizes) for the quantity estimate. |
| `estimate.ts` | Cost / carbon / quantity arithmetic — same formulas and constants as the Python code, with user-edited rates. |
| `zones.ts` | Best/good/bad zone logic and the coloured rectangles drawn on the Pareto plot. |
| `report.ts` | Builds the downloadable HTML design review report. |
| `api.ts` | Talks to the local server (health, strength review, start/poll a price-driven optimisation): finds its address (same origin, or one typed in and remembered), health check. Static hosting simply has no API and the callers handle that. |
