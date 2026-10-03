# Dashboard (Vite + React + TypeScript + Tailwind)

Static site: all numbers come from `public/data/*.json`, produced by `rcopt export` (`make export`).

```bash
npm i
npm run dev      # http://localhost:5173
npm run build    # tsc + vite build -> dist/
```

Live-evaluator page: start the local API (`make api`) and run `VITE_API_URL=http://localhost:8000 npm run dev`
(PowerShell: `$env:VITE_API_URL="http://localhost:8000"; npm run dev`). Without it that page explains why it is disabled.
