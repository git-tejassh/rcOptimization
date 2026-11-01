# `scripts/` — helpers for moving the big trained models around

The two trained surrogate files are ~300 MB, too big for git. These scripts pack and unpack them so teammates (or a hosting service) can get them from Google Drive instead of re-training (about 30 minutes).

| File | What it does |
|---|---|
| `pack_models.py` | Zips `models/*.joblib`, the XGBoost JSON files and `manifest.json` into `models.zip` (≈ 286 MB) in the repo root. Upload that zip to Google Drive / a GitHub release. |
| `fetch_models.py` | The reverse: downloads `models.zip` from the link in the `MODELS_URL` environment variable (direct link or Google Drive share link) and unpacks it into `models/`. Does nothing if the models already exist. Used by the Docker build and by teammates. |

Example (PowerShell): `$env:MODELS_URL="<link>"; python scripts/fetch_models.py`
