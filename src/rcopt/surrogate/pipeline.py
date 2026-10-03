"""Phase 3: train both surrogates, evaluate (overall + near the feasibility boundary), run ONE active-learning round.

Honesty rules (CLAUDE.md prime directives 2-3): all metrics are on a fixed hold-out that is never used for tuning or
training; boundary metrics are reported next to the overall ones; before/after active learning are both stored.
"""
from __future__ import annotations

import json
import time

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.metrics import r2_score  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

from rcopt import config  # noqa: E402
from rcopt.config import ROOT  # noqa: E402
from rcopt.design.variables import default_space  # noqa: E402
from rcopt.fe.batch import run_rows  # noqa: E402
from rcopt.sampling.biased_sampler import precheck  # noqa: E402
from rcopt.surrogate.features import FeatureBuilder  # noqa: E402
from rcopt.surrogate.models import TARGETS_A, SurrogateA, SurrogateB, _to_log, _xgb  # noqa: E402

MODELS = ROOT / "models"
RESULTS = ROOT / "data" / "results"
FIGS = RESULTS / "figures"
AL_PATH = ROOT / "data" / "processed" / "fe_dataset_al.parquet"
TUNE_GRID = [
    {"max_depth": 6, "n_estimators": 400, "learning_rate": 0.08, "subsample": 0.9, "colsample_bytree": 0.9, "min_child_weight": 2},
    {"max_depth": 8, "n_estimators": 600, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9, "min_child_weight": 2},
    {"max_depth": 10, "n_estimators": 800, "learning_rate": 0.04, "subsample": 0.9, "colsample_bytree": 0.9, "min_child_weight": 2},
]


# ----------------------------------------------------------------------------- data / split
def load_ok(path=None) -> pd.DataFrame:
    df = pd.read_parquet(path or ROOT / "data" / "processed" / "fe_dataset.parquet")
    return df[df.status == "OK"].reset_index(drop=True)


def genomes(df: pd.DataFrame) -> np.ndarray:
    return df[[f"g_{n}" for n in default_space().gene_names]].to_numpy()


def size_key(df: pd.DataFrame) -> pd.Series:
    fb = FeatureBuilder()
    return fb.physical(genomes(df))[fb.size_columns()].astype(int).astype(str).agg("_".join, axis=1)


def boundary_mask(df: pd.DataFrame) -> np.ndarray:
    lo, hi = config.load_dict("surrogate")["boundary_band"]
    v = df[list(TARGETS_A)]
    return ((v >= lo) & (v <= hi)).any(axis=1).to_numpy()


def make_split(df: pd.DataFrame, seed: int, holdout: float) -> tuple[np.ndarray, np.ndarray]:
    """Group-aware random hold-out (designs with identical sizes never straddle the split)."""
    keys = size_key(df)
    uniq = keys.unique()
    rng = np.random.default_rng(seed)
    test_keys = set(rng.choice(uniq, int(round(holdout * len(uniq))), replace=False))
    te = keys.isin(test_keys).to_numpy()
    return ~te, te


def feasible_fe(v: pd.DataFrame | dict) -> np.ndarray:
    return np.all([np.asarray(v[t]) <= 1.0 for t in TARGETS_A], axis=0)


# ----------------------------------------------------------------------------- metrics
def regression_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    e = np.abs(y - p)
    return {"n": int(len(y)), "R2": float(r2_score(y, p)) if len(y) > 2 else float("nan"), "MAE": float(e.mean()),
            "RMSE": float(np.sqrt(np.mean((y - p) ** 2))), "max_abs_err": float(e.max()),
            "p95_abs_err": float(np.percentile(e, 95))}


def confusion(true_f: np.ndarray, pred_f: np.ndarray) -> dict:
    tp, tn = int((true_f & pred_f).sum()), int((~true_f & ~pred_f).sum())
    fp, fn = int((~true_f & pred_f).sum()), int((true_f & ~pred_f).sum())
    return {"TP": tp, "TN": tn, "FP_pred_feasible_but_truly_infeasible": fp, "FN_pred_infeasible_but_truly_feasible": fn,
            "agreement": (tp + tn) / max(tp + tn + fp + fn, 1)}


def evaluate_outputs(df_te: pd.DataFrame, pred: dict) -> dict:
    """Metrics per output, overall and on the boundary subset, plus feasibility agreement."""
    band = boundary_mask(df_te)
    out: dict = {"overall": {}, "boundary": {}, "n_boundary": int(band.sum())}
    for t in TARGETS_A:
        y, p = df_te[t].to_numpy(float), np.asarray(pred[t], float)
        out["overall"][t] = regression_metrics(y, p)
        out["boundary"][t] = regression_metrics(y[band], p[band])
    true_f, pred_f = feasible_fe(df_te), feasible_fe(pred)
    out["feasibility_overall"] = confusion(true_f, pred_f)
    out["feasibility_boundary"] = confusion(true_f[band], pred_f[band])
    ymax = np.max([df_te[t].to_numpy(float) for t in TARGETS_A], axis=0)
    pmax = np.max([np.asarray(pred[t], float) for t in TARGETS_A], axis=0)
    # safety margin: error of the *binding* utilisation, i.e. rows whose true worst ratio lies in the boundary band
    lo, hi = config.load_dict("surrogate")["boundary_band"]
    bind = (ymax >= lo) & (ymax <= hi)
    out["n_binding_boundary"] = int(bind.sum())
    out["gmax_boundary_abs_err_q95"] = float(np.percentile(np.abs(ymax - pmax)[bind], 95))
    return out


def evaluate_b_demands(df_te: pd.DataFrame, D: pd.DataFrame) -> dict:
    res = {}
    for c in D.columns:
        y = df_te[c].to_numpy(float)
        res[c] = {**regression_metrics(y, D[c].to_numpy()), "mean_abs_value": float(np.mean(np.abs(y)))}
    return res


# ----------------------------------------------------------------------------- tuning
def tune(G: np.ndarray, df: pd.DataFrame, groups: pd.Series) -> tuple[dict, list]:
    """Pick xgboost params by 5-fold group CV on the training portion only (mean log-space MAE over the 4 targets)."""
    fb = FeatureBuilder()
    if len(G) > 6000:                                    # CV on a fixed 6000-row subsample keeps tuning affordable
        sub = np.sort(np.random.default_rng(0).choice(len(G), 6000, replace=False))
        G, df, groups = G[sub], df.iloc[sub].reset_index(drop=True), groups.iloc[sub].reset_index(drop=True)
    X = fb.features_a(G)
    results = []
    folds = list(GroupKFold(n_splits=config.load_dict("surrogate")["cv_folds"]).split(X, groups=groups))
    for params in TUNE_GRID:
        maes = []
        for tr, va in folds:
            fold_mae = []
            for t in TARGETS_A:
                y = _to_log(df[t].to_numpy(float))
                m = _xgb(params, 0)
                m.fit(X.iloc[tr], y[tr])
                fold_mae.append(np.mean(np.abs(m.predict(X.iloc[va]) - y[va])))
            maes.append(np.mean(fold_mae))
        results.append({"params": params, "cv_mean_log_mae": float(np.mean(maes)), "cv_std": float(np.std(maes))})
    best = min(results, key=lambda r: r["cv_mean_log_mae"])
    return best["params"], results


# ----------------------------------------------------------------------------- active learning
def select_al(A: SurrogateA, known: set, n_select: int, seed: int, n_cand: int = 40_000) -> np.ndarray:
    """Pick ``n_select`` designs near the predicted feasibility boundary / with high ensemble disagreement."""
    sp = default_space()
    rng = np.random.default_rng(seed)
    raw = sp.random_genomes(n_cand, rng)
    cand, seen = [], set(known)
    for g in raw:
        g = sp.repair(g)
        k = tuple(g)
        if k in seen:
            continue
        seen.add(k)
        if len(cand) < n_cand // 2 or precheck(sp.decode(g, repair=False)) is None:   # half uniform, half pre-checked
            cand.append(g)
    cand = np.array(cand)
    X = A.fb.features_a(cand)[A.feature_names]
    per_member = np.stack([np.stack([m.predict(X) for m in A.models[t]], axis=1) for t in TARGETS_A], axis=0)
    log_gmax = per_member.max(axis=0)                      # (n, members): log of the largest predicted ratio
    score = np.abs(log_gmax.mean(axis=1)) / (log_gmax.std(axis=1) + 0.02)
    return cand[np.argsort(score)[:n_select]]


# ----------------------------------------------------------------------------- plots
def parity_plot(df_te: pd.DataFrame, pred: dict, title: str, path) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    band = boundary_mask(df_te)
    for ax, t in zip(axes, TARGETS_A, strict=True):
        y, p = df_te[t].to_numpy(), np.asarray(pred[t])
        ax.scatter(y[~band], p[~band], s=4, alpha=0.35, label="hold-out")
        ax.scatter(y[band], p[band], s=5, alpha=0.6, color="tab:red", label="near boundary")
        lim = [0, max(1.6, np.percentile(y, 98))]
        ax.plot(lim, lim, "k--", lw=0.8)
        ax.axvline(1, color="gray", lw=0.5), ax.axhline(1, color="gray", lw=0.5)
        ax.set_xlim(lim), ax.set_ylim(lim), ax.set_title(t, fontsize=9), ax.set_xlabel("FE + IS 456 (true)")
        ax.set_ylabel("predicted")
    axes[0].legend(fontsize=7)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def residual_plot(df_te: pd.DataFrame, pred: dict, title: str, path) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.2))
    for ax, t in zip(axes, TARGETS_A, strict=True):
        r = np.asarray(pred[t]) - df_te[t].to_numpy()
        ax.hist(np.clip(r, np.percentile(r, 1), np.percentile(r, 99)), bins=50)
        ax.set_title(f"{t} residual", fontsize=9)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def importance_plot(imp: dict, path) -> None:
    fig, axes = plt.subplots(1, len(imp), figsize=(5 * len(imp), 4))
    for ax, (name, s) in zip(np.atleast_1d(axes), imp.items(), strict=True):
        s.head(12)[::-1].plot.barh(ax=ax)
        ax.set_title(name, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _sample_points(df_te: pd.DataFrame, pred: dict, n: int = 500, seed: int = 0) -> dict:
    idx = np.random.default_rng(seed).choice(len(df_te), min(n, len(df_te)), replace=False)
    band = boundary_mask(df_te)
    return {t: {"true": df_te[t].to_numpy()[idx].round(4).tolist(), "pred": np.asarray(pred[t])[idx].round(4).tolist()}
            for t in TARGETS_A} | {"near_boundary": band[idx].tolist()}


# ----------------------------------------------------------------------------- orchestration
def run_phase3(force: bool = False) -> dict:
    sc = config.load_dict("surrogate")
    chash = config.config_hash()
    out_path = RESULTS / "surrogate_metrics.json"
    if out_path.exists() and not force:
        m = json.loads(out_path.read_text())
        if m.get("config_hash") == chash:
            return m
    t_start = time.time()
    FIGS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    df = load_ok()
    G = genomes(df)
    tr, te = make_split(df, sc["seed"], sc["holdout"])
    df_tr, df_te, G_tr, G_te = df[tr].reset_index(drop=True), df[te].reset_index(drop=True), G[tr], G[te]
    groups = size_key(df_tr)

    params, tuning = tune(G_tr, df_tr, groups)
    metrics: dict = {"config_hash": chash, "n_train": len(df_tr), "n_test": len(df_te),
                     "n_test_boundary": int(boundary_mask(df_te).sum()), "tuning": tuning, "chosen_params": params,
                     "boundary_band": sc["boundary_band"], "split_seed": sc["seed"]}

    def fit_all(G_fit, df_fit):
        a = SurrogateA(params=params).fit(G_fit, df_fit)
        b = SurrogateB(params=params).fit(G_fit, df_fit)
        return a, b

    def evaluate_all(a, b, tag):
        pa = a.predict(G_te)
        eb = b.predict_eval(G_te)
        pb = {t: eb[t] for t in TARGETS_A}
        res = {"A": evaluate_outputs(df_te, pa), "B": evaluate_outputs(df_te, pb)}
        res["A"]["sv_mae_mm"] = {f"sv_B{g}": float(np.mean(np.abs(pa[f"sv_B{g}"] - df_te[f"sv_B{g}"]))) for g in range(a.space.n_bg)}
        res["B"]["demands"] = evaluate_b_demands(df_te, b.predict_demands(G_te))
        # the cost/carbon the optimiser would see vs truth
        pc = a.predict_eval(G_te)
        res["A"]["cost_mape"] = float(np.mean(np.abs(pc["cost"] - df_te.cost) / df_te.cost))
        res["B"]["cost_mape"] = float(np.mean(np.abs(eb["cost"] - df_te.cost) / df_te.cost))
        parity_plot(df_te, pa, f"Surrogate A ({tag})", FIGS / f"parity_A_{tag}.png")
        parity_plot(df_te, pb, f"Surrogate B ({tag})", FIGS / f"parity_B_{tag}.png")
        residual_plot(df_te, pa, f"Surrogate A residuals ({tag})", FIGS / f"residuals_A_{tag}.png")
        residual_plot(df_te, pb, f"Surrogate B residuals ({tag})", FIGS / f"residuals_B_{tag}.png")
        return res, pa, pb

    # ---- round 0: before active learning (+ random-forest baseline for A)
    A0, B0 = fit_all(G_tr, df_tr)
    r0, pa0, pb0 = evaluate_all(A0, B0, "before_AL")
    metrics["before_AL"] = r0
    fbx = FeatureBuilder()
    Xtr, Xte = fbx.features_a(G_tr), fbx.features_a(G_te)
    rf_pred = {}
    for t in TARGETS_A:
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, n_jobs=4, random_state=sc["seed"])
        rf.fit(Xtr, _to_log(df_tr[t].to_numpy(float)))
        rf_pred[t] = np.exp(rf.predict(Xte))
    metrics["baseline_random_forest_A_before_AL"] = evaluate_outputs(df_te, rf_pred)
    importance = {t: A0.importances(t) for t in ("U_flex_max", "U_col_max")}
    importance |= {t: B0.importances(t) for t in ("B0_Mhog", "T1_0_0_Pu")}
    importance_plot(importance, FIGS / "feature_importance.png")
    metrics["feature_importance_top"] = {k: v.head(10).round(4).to_dict() for k, v in importance.items()}
    metrics["parity_points_before"] = {"A": _sample_points(df_te, pa0), "B": _sample_points(df_te, pb0)}

    # ---- active learning: ONE round
    known = {tuple(r) for r in genomes(df)}
    sel = select_al(A0, known, sc["al_samples"], sc["seed"] + 5)
    ids = np.arange(df.id.max() + 1, df.id.max() + 1 + len(sel))
    al_df, al_timing = run_rows(sel, ids, ["al"] * len(sel))
    al_df.to_parquet(AL_PATH, index=False)
    al_ok = al_df[al_df.status == "OK"].reset_index(drop=True)
    metrics["active_learning"] = {"n_selected": len(sel), "n_ok": len(al_ok), "status_counts": al_df.status.value_counts().to_dict(),
                                  "feasible_among_selected": int(al_ok.feasible.sum()),
                                  "near_boundary_among_selected": int(boundary_mask(al_ok).sum()), "timing": al_timing}
    df_tr2 = pd.concat([df_tr, al_ok], ignore_index=True)
    A1, B1 = fit_all(genomes(df_tr2), df_tr2)
    r1, pa1, pb1 = evaluate_all(A1, B1, "after_AL")
    metrics["after_AL"] = r1
    metrics["parity_points_after"] = {"A": _sample_points(df_te, pa1), "B": _sample_points(df_te, pb1)}
    metrics["margin_q95"] = {"A": r1["A"]["gmax_boundary_abs_err_q95"], "B": r1["B"]["gmax_boundary_abs_err_q95"]}
    metrics["margin_q95_before_AL"] = {"A": r0["A"]["gmax_boundary_abs_err_q95"], "B": r0["B"]["gmax_boundary_abs_err_q95"]}
    metrics["runtime_s"] = time.time() - t_start

    # ---- persist the final (after-AL) models
    joblib.dump(A1, MODELS / "surrogate_A.joblib", compress=3)
    joblib.dump(B1, MODELS / "surrogate_B.joblib", compress=3)
    for t, members in A1.models.items():
        members[0].save_model(str(MODELS / f"xgb_A_{t}.json"))
    (MODELS / "manifest.json").write_text(json.dumps({
        "config_hash": chash, "n_train_final": len(df_tr2), "chosen_params": params, "margin_q95": metrics["margin_q95"],
        "boundary_band": sc["boundary_band"], "dataset_rows": int(len(df)), "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "after_AL_overall_MAE_A": {t: r1["A"]["overall"][t]["MAE"] for t in TARGETS_A},
        "after_AL_overall_MAE_B": {t: r1["B"]["overall"][t]["MAE"] for t in TARGETS_A}}, indent=1), encoding="utf-8")
    out_path.write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    return metrics
