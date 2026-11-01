# `surrogate/` — fast machine-learning stand-ins for the slow analysis

**Plain words:** a "surrogate" is a model trained on the 15,000 analysed designs so it can *predict* the result of the analysis in microseconds. The
optimiser asks for tens of thousands of designs, so a fast approximation can save time — but it is only trustworthy if tested, especially close to the
pass/fail limit. Two surrogates are built and compared (XGBoost = a gradient-boosted decision-tree library; each output is an ensemble of 5 for an
uncertainty estimate):

* **Surrogate A** ("as in the brief"): predicts the four safety ratios (bending, shear, column, deflection) directly from all design numbers.
* **Surrogate B** (our improvement): predicts only the *forces* (which depend just on member sizes and concrete grade) and then applies the **exact** IS 456 formulas. Much more accurate (near-boundary agreement 99.8 % versus 96.6 % for A).

| File | What it does |
|---|---|
| `features.py` | Turns design numbers into model inputs without Python loops: real sizes, bar areas, effective depths, steel ratios, stiffness proxies. The cement gene is deliberately excluded (it does not change the structure). |
| `models.py` | The model classes `SurrogateA` and `SurrogateB`: `fit()`, `predict()`, `predict_eval()` (cost, carbon and the 7 constraint values for many designs at once), feature importances. B predicts the demands of 30 column *position classes* (decision D-024: the first version with 4 extreme columns failed verification). |
| `pipeline.py` | **Phase 3**: splits data (a fixed 20 % hold-out never used for tuning), tunes hyper-parameters by cross-validation on the training part only, trains A and B, measures errors overall *and near the boundary*, runs **one** active-learning round (500 extra boundary designs, no measurable gain — reported as such), computes the safety margins (95th-percentile error: A 0.065, B 0.005), draws parity/residual/importance plots, saves `models/surrogate_A.joblib`, `surrogate_B.joblib`, `manifest.json`. |
| `__init__.py` | Marks the folder as a package. |

The two trained model files are ~300 MB and are not in git (see `models/README.md`).
