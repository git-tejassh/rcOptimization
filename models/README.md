# `models/` — the trained surrogate models (big files, NOT in git)

| File | In git? | What it is |
|---|---|---|
| `manifest.json` | yes | Small record of the training: config fingerprint, 12,500 final training rows, chosen XGBoost parameters, the safety margins (A 0.0656, B 0.0050), accuracy after active learning, creation time. |
| `surrogate_A.joblib` (≈ 72 MB), `surrogate_B.joblib` (≈ 227 MB) | **no** | The two trained surrogates (A: direct safety-ratio regression, B: force regression + exact IS 456). Needed by the Live evaluator and by the optimisation with surrogates. |
| `xgb_A_*.json` (≈ 8–12 MB each) | **no** | Native XGBoost files of surrogate A's six outputs (four ratios + two stirrup spacings). |
| `.gitkeep` | yes | Keeps the otherwise-empty folder in git. |

**Where to get them:** (1) retrain, `python -m rcopt.cli phase3` (≈ 30 min on a laptop), or (2) download `models.zip` from the team's Google Drive folder and unzip into this folder
(`python scripts/fetch_models.py`). The local file `models.zip` (286 MB, repo root) is already packed; it only needs uploading. The link must still be pasted into the main README
(placeholder `<ADD LINK HERE>`).
