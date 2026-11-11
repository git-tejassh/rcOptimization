# `api/` — the local server behind the "Live evaluator" and "Strength review"

**Plain words:** the website alone cannot run the structural analysis (it is Python/OpenSees). This small server (FastAPI) does it on request. Start it with
`python -m rcopt.cli serve` and it serves **both** the website and these services at http://localhost:8000. Without it the website still works, but the
Live evaluator tab and the Strength review step switch themselves off with an explanation.

| File | What it does |
|---|---|
| `main.py` | The server. Endpoints: `GET /health` (what is ready: models present, dashboard built), `GET /design-space`, `/pareto/{variant}`, `/verification` (results as JSON); `POST /evaluate/surrogate` (instant prediction of cost, carbon and safety ratios for a design), `POST /evaluate/fe` (exact OpenSees + IS 456 evaluation, ≈ 50 ms), `POST /evaluate/cost-carbon` (quantities, cost, carbon only), `GET /prices/items` (editable prices + CSV template), `POST /optimize/prices` (start a price-driven optimisation in a separate process; returns a job id) and `GET /optimize/jobs/{id}` (progress and, when done, the designs), `POST /review/staad` (strength review and reinforcement design of an uploaded STAAD file, ≈ 0.5 s). Allows any browser origin (no secrets, no accounts) and serves `web/dist/` as static files. Interactive docs at `/docs`. |
| `schemas.py` | The exact shape of the requests/responses (a design is 23 integers; the review request is STAAD text + materials; the optimise request is prices as a JSON object or CSV text + effort), so wrong input gets a clear error instead of a crash. |
| `__init__.py` | Marks the folder as a package. |

Needs the trained models in `models/` for the surrogate endpoints (otherwise they answer HTTP 503); the exact-FE, cost and review endpoints need only the Python
environment. How to share it with teammates / deploy it: [`../docs/DEPLOY.md`](../docs/DEPLOY.md). Tests: `tests/test_api.py`.
