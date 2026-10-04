"""Cement-type trade-off: when does a low-carbon cement create a real cost-carbon front? (exhaustive, no optimiser).

Cement type changes cost and carbon only, never the structural response, so every truly feasible structural design of the
dataset can be paired with every cement type. The non-dominated set of all pairs is scanned over the price premium of the
low-carbon cement (PSC) over the baseline (PPC): at the market prices of the config PSC is both cheaper and lower-carbon
(it dominates), a trade-off appears only when low-carbon cement costs more.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from rcopt import config
from rcopt.config import ROOT
from rcopt.cost_carbon.carbon import carbon_kgco2e
from rcopt.cost_carbon.cost import cost_inr
from rcopt.cost_carbon.quantities import Quantities
from rcopt.design.variables import default_space
from rcopt.optimize.metrics import non_dominated

PREMIUMS = [None, 0.0, 0.25, 0.5, 1.0, 2.0, 4.0]       # None = market prices of config/cost_rates.yaml
CEMENTS = ("OPC", "PPC", "PSC")


def run_cement_tradeoff() -> dict:
    sp = default_space()
    ds = pd.read_parquet(ROOT / "data" / "processed" / "fe_dataset.parquet")
    ds = ds[(ds.status == "OK") & (ds.feasible == 1)].reset_index(drop=True)
    grades = sp.options[sp.gene_index("fck")]
    steels = sp.options[sp.gene_index("fy")]
    prices = config.load_dict("cost_rates")["cement_price_per_kg"]
    content = config.load_dict("carbon_factors")["cement_content_kg_m3"]
    base = prices["baseline"]
    z = 0.0
    rows = []
    for cm, sk, fw, gi, si in zip(ds.concrete_m3, ds.steel_kg, ds.formwork_m2, ds.g_fck, ds.g_fy, strict=True):
        q = Quantities(cm, sk, fw, z, z, z, z, z, z, z, z, z, z)
        g, s = grades[int(gi)], steels[int(si)]
        c0 = cost_inr(q, g, s, cement=None)["total"]
        for ce in CEMENTS:
            rows.append((c0, carbon_kgco2e(q, g, s, cement=ce)["total"], cm * content[g]["value"], ce))
    arr = pd.DataFrame(rows, columns=["cost_base", "carbon", "cement_kg", "cement"])
    out = []
    for prem in PREMIUMS:
        price = {c: prices[c]["value"] for c in CEMENTS}
        if prem is not None:
            price["PSC"] = price[base] + prem
        adj = {c: price[c] - price[base] for c in CEMENTS}
        cost = arr.cost_base + arr.cement_kg * arr.cement.map(adj)
        F = np.column_stack([cost, arr.carbon])
        nd = non_dominated(F)
        front = arr.iloc[nd].assign(cost=cost.iloc[nd].to_numpy())
        out.append({
            "psc_premium_inr_per_kg": prem, "psc_price_inr_per_kg": price["PSC"], "front_size": int(len(nd)),
            "cost_span_pct": float(100 * (front.cost.max() / front.cost.min() - 1)),
            "carbon_span_pct": float(100 * (front.carbon.max() / front.carbon.min() - 1)),
            "cement_types_on_front": {c: int((front.cement == c).sum()) for c in CEMENTS},
            "cost_range": [float(front.cost.min()), float(front.cost.max())],
            "carbon_range": [float(front.carbon.min()), float(front.carbon.max())],
            "front": [{"cost": float(a), "carbon": float(b), "cement": c} for a, b, c in
                      zip(front.cost, front.carbon, front.cement, strict=True)][:60],
        })
    res = {"n_structural_designs": int(len(ds)), "scenarios": out,
           "note": "PSC price premium over PPC in INR per kg of cement; None = config market prices (all provisional)"}
    (ROOT / "data" / "results" / "cement_tradeoff.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res
