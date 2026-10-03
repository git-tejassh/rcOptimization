"""Report figures from data/results (saved to docs/figures and data/results/figures)."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from rcopt.config import ROOT  # noqa: E402

RES = ROOT / "data" / "results"
OUT = ROOT / "docs" / "figures"
COL = {"A": "#0e7490", "A_margin": "#6366f1", "B": "#d97706", "B_margin": "#be185d", "direct": "#475569"}


def make_figures() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    # 1. Pareto fronts (ground truth objectives) + verification marks
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for v in ("direct", "B", "A"):
        d = pd.read_parquet(RES / ("pareto_direct.parquet" if v == "direct" else f"pareto_surrogate_{v}.parquet"))
        ok = d[(d.true_status == "OK") & (d.true_feasible == 1)]
        bad = d[~d.index.isin(ok.index) & (d.true_status == "OK")]
        ax.scatter(ok.true_cost / 1e5, ok.true_carbon / 1e3, s=14, color=COL[v], label=f"{v} (truly feasible, {len(ok)})")
        if len(bad):
            ax.scatter(bad.true_cost / 1e5, bad.true_carbon / 1e3, s=22, facecolors="none", edgecolors="red", label=f"{v} truly infeasible ({len(bad)})")
    ax.set_xlabel("cost (INR lakh, provisional rates)")
    ax.set_ylabel("embodied carbon (t CO2e, provisional factors)")
    ax.legend(fontsize=8)
    ax.set_title("Pareto fronts re-evaluated with FE + IS 456 (gravity only)")
    fig.tight_layout()
    fig.savefig(OUT / "pareto_fronts.png", dpi=140)
    plt.close(fig)
    made.append("pareto_fronts.png")
    # 2. convergence
    opt = json.loads((RES / "optimization_summary.json").read_text())
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for k, v in opt.items():
        cv = v["convergence"]
        ax.plot(cv["n_eval"], cv["hv_mean"], color=COL[k], label=k)
    ax.set_xlabel("evaluations")
    ax.set_ylabel("hypervolume (normalised)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "convergence.png", dpi=140)
    plt.close(fig)
    made.append("convergence.png")
    # 3. copy surrogate parity figures
    for f in (RES / "figures").glob("parity_*_after_AL.png"):
        (OUT / f.name).write_bytes(f.read_bytes())
        made.append(f.name)
    return made
