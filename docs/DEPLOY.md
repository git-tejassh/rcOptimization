# Run it, share it, deploy it

There are two kinds of deployment. Pick by what people need to do.

| What people need | Where it runs | Live evaluator + strength review |
|---|---|---|
| Read the results, use the Pareto explorer, price their own design (`My design estimate`) | **Static website** (Vercel / Netlify / GitHub Pages): no Python needed | switched off (a static site cannot run the finite-element model) |
| Everything, including the live evaluator and the IS 456 strength review of an uploaded STAAD file | **One Python server** that serves the dashboard and the API together | on |

## What the live evaluator, the strength review and the price optimiser need
1. **Python environment** of the project: `make setup` (or `pip install -r requirements.txt`). OpenSeesPy runs the exact analysis.
2. **Trained surrogate models** `models/surrogate_A.joblib` and `models/surrogate_B.joblib` (about 300 MB). Either train them (`python -m rcopt.cli phase3`, about 30 min) or copy `models.zip` from the shared Google Drive folder into the repo and unzip it there (`python scripts/fetch_models.py` does it from a link).
   The *strength review* (STAAD upload) needs only OpenSees; the *live evaluator* and the *price optimiser* ("Optimise with my prices", about 1.5 minutes per run, ≈ 1.5 GB of memory while it runs) also need the models.
3. **The dashboard built once**: `cd web && npm install && npm run build`.
4. **Start the server**: `python -m rcopt.cli serve` and open **http://localhost:8000**. `GET /health` shows what is ready (`live_evaluator_ready`, `dashboard_built`, ...).

## 1. Just me, on my laptop
```powershell
.\make.ps1 setup
cd web; npm run build; cd ..
.venv\Scripts\python.exe -m rcopt.cli serve          # http://localhost:8000
```

## 2. Teammates / guide on the same Wi-Fi or college LAN (no internet service needed)
On the host computer: `python -m rcopt.cli serve --host 0.0.0.0 --port 8000`, find its IP (`ipconfig`, the IPv4 address, for example 192.168.1.20), allow Python through the Windows firewall when asked, and everybody else opens `http://192.168.1.20:8000`.
Works only while the host computer is on and on the same network.

## 3. A public link for a demo, from my own laptop (temporary)
Keep the server running and expose it with a tunnel. No account is needed for the first option:
```powershell
winget install Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000      # prints an https://<random>.trycloudflare.com link
```
(ngrok works the same way: `ngrok http 8000`.) The link works from anywhere while the laptop and the command stay running. Anyone with the link can open it, so do not put private data in the app.

## 4. A permanent, always-on link
**a) Static site only (free, 5 minutes).** Everything except the live evaluator, the strength review and the optimiser re-run ("Optimise with my prices" still lets people edit and download the prices) works.
- **GitHub Pages, no command line (recommended for the guide):** the repository already contains `.github/workflows/pages.yml`. The owner does this once: GitHub repository → *Settings* → *Pages* → *Build and deployment* → *Source: GitHub Actions*. Every push to `main` then rebuilds and publishes the site at `https://git-tejassh.github.io/rcOptimization/` (check the *Actions* tab for the run).
- Vercel: `npm i -g vercel`, `cd web`, `vercel login`, `vercel --prod` (framework Vite, output `dist`; `web/vercel.json` is included). Or import the GitHub repo in the Vercel dashboard with root directory `web`.
- GitHub Pages / Netlify: publish `web/dist` (the build is a single `index.html` plus `data/`).
- Before building run `python -m rcopt.cli export` so `web/public/data` is current and committed.

**b) Full app (dashboard + live evaluator + strength review).** Needs a host that runs Docker, with at least 2 GB of memory (OpenSees plus two XGBoost ensembles; the free 512 MB plans are too small).
1. Put `models.zip` somewhere with a direct download link: a Google Drive file shared as “anyone with the link”, or a GitHub release asset (create it with `python scripts/pack_models.py`).
2. Render: New + Blueprint, pick this repository (it contains `render.yaml`), set the environment variable `MODELS_URL` to that link, choose a 2 GB plan. Railway / Fly.io: deploy the `Dockerfile` the same way with `MODELS_URL` as a build argument.
3. Open the service URL: the dashboard is at `/`, the API at `/health`, `/docs` (interactive API page).
```bash
docker build -t rc-app --build-arg MODELS_URL=<link> .      # also usable locally: docker run -p 8000:8000 rc-app
```
This Docker route was written but not built in the development session: run it once locally before relying on it.

## Which one should we use?
For the guide and teammates: deploy the **static site** (4a) so the results are always available, and run **option 3 or 2** from one laptop during a viva or demo when the live evaluator and strength review are needed. Use 4b only if an always-on full app is really required.

## Environment variables and switches
- `VITE_API_URL` (build time) fixes the API address; otherwise the dashboard uses the same origin, or the address typed in the app (remembered in the browser).
- The API allows any origin (it holds no secrets and no accounts).
