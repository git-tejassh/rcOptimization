# `web/` — the dashboard (the website the guide and teammates look at)

**Plain words:** a website built with React + TypeScript + Tailwind (built with Vite). It shows all results — the Pareto front, how reliable the surrogates are,
the verification, the cost/carbon sensitivity — and lets a user price their own design. It contains **no calculation engine**: every number is read from
the JSON files in `public/data/`, which `python -m rcopt.cli export` writes. The two Python-powered features (Live evaluator, Strength review) are optional and
use the local server in [`../api/`](../api/README.md).

## Open it
| You want to… | Do this |
|---|---|
| Just look (no server) | Double-click `web/dist/index.html` after building once (single self-contained file; works from disk). |
| Everything incl. live features | `python -m rcopt.cli serve`, then open http://localhost:8000 |
| Develop the website | `cd web`, `npm install`, `npm run dev` → http://localhost:5173 |
| Build it | `cd web && npm run build` → `web/dist/index.html` |
| Put it online (static) | see [`../docs/DEPLOY.md`](../docs/DEPLOY.md); `vercel.json` is ready |

## Files in this folder
| File | What it does |
|---|---|
| `index.html` | The page shell: title, green icon, Outfit font, loads `data/bundle.js` (all results) and the app. |
| `package.json`, `package-lock.json` | List and exact versions of the JavaScript libraries (React, Plotly basic charts, marked for Markdown, Tailwind, Vite). `npm run build` = type-check + build. |
| `vite.config.ts` | Build settings; the `singlefile` plugin inlines JS and CSS so `dist/index.html` is one file. |
| `tsconfig.json` | TypeScript strictness settings. |
| `tailwind.config.js`, `postcss.config.js` | Styling toolchain (colour tokens are in `src/index.css`). |
| `vercel.json` | Settings for deploying `dist/` on Vercel (also a copy in the repo root). |
| `src/` | The application code — see [`src/README.md`](src/README.md). |
| `public/data/` | The exported results the app reads — see [`public/data/README.md`](public/data/README.md). |
| `dist/` | The built website (generated, not in git). |
| `node_modules/` | Downloaded libraries (generated, not in git). |
