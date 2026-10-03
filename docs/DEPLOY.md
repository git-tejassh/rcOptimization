# Deploy and run

## Local (Windows PowerShell)
```powershell
.\make.ps1 setup        # venv + pip install -r requirements.txt + npm install   (or: make setup)
.\make.ps1 all          # phase0 .. phase5, sensitivity, export  (about 1-2 h on a laptop; cached stages are skipped)
.\make.ps1 web-dev      # dashboard at http://localhost:5173 (reads web/public/data/*.json)
.\make.ps1 api          # optional: FastAPI at http://localhost:8000 (live evaluator)
```
Live evaluator: `$env:VITE_API_URL="http://localhost:8000"; npm run dev` inside `web/`.

## Vercel (static dashboard; Claude cannot authenticate to Vercel, so only prepare)
OpenSeesPy, XGBoost and pymoo must NOT run on Vercel (native deps, size limits): all heavy computation is offline; the site is static.
```bash
npm i -g vercel
cd web
vercel login
vercel --prod            # framework Vite, output dist (vercel.json is included, SPA rewrite)
```
Run `make export` first so `web/public/data/*.json` is up to date and committed.

## GitHub Pages (alternative)
`cd web && npm run build` and publish `web/dist` (the Vite `base` is `./`, so it works under a sub-path). The hash router needs no rewrites.

## API hosting (optional)
`docker build -t rc-api . && docker run -p 8000:8000 rc-api` (build after `make all` so `models/` and `data/results/` exist). Render / Railway / Fly can run the same image.
Then build the dashboard with `VITE_API_URL=https://<api-host>`; the API enables CORS for localhost origins only, so add your site origin in `api/main.py` first.
