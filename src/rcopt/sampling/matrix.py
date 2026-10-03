"""Phase 1: build the design matrix (LHS stratum + feasibility-biased stratum) and its sanity report."""
from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.geometric_feasibility import check_geometry
from rcopt.design.variables import DesignSpace, default_space
from rcopt.sampling.biased_sampler import biased_sample
from rcopt.sampling.discrete_lhs import discrete_lhs

MATRIX_PATH = ROOT / "data" / "processed" / "design_matrix.parquet"
REPORT_PATH = ROOT / "data" / "results" / "sampling_report.json"


def _frame(space: DesignSpace, genomes: np.ndarray, stratum: str, start: int, extra: dict | None = None) -> pd.DataFrame:
    df = pd.DataFrame(genomes, columns=[f"g_{n}" for n in space.gene_names])
    df.insert(0, "id", np.arange(start, start + len(df)))
    df.insert(1, "sample_stratum", stratum)
    for k, v in (extra or {}).items():
        df[k] = v
    return df


def build_design_matrix(space: DesignSpace | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (design matrix, report). All genomes in the matrix are repaired, unique and buildable."""
    space = space or default_space()
    cfg = config.load_dict("sampling")
    n_base, frac, seed = cfg["n_base"], cfg["biased_fraction"], cfg["seed"]
    n_biased = int(round(n_base * frac))
    n_lhs = n_base - n_biased

    raw = discrete_lhs(space, n_lhs, seed)
    raw_reasons: Counter = Counter()
    raw_bad = 0
    repaired = np.empty_like(raw)
    changed = np.zeros(len(raw), dtype=bool)
    for i, g in enumerate(raw):
        res = check_geometry(space.decode(g, repair=False))
        if not res.ok:
            raw_bad += 1
            raw_reasons.update(r.split("_", 1)[1] if r[0] in "BC" else r for r in res.reasons)
        repaired[i] = space.repair(g)
        changed[i] = bool((repaired[i] != g).any())
    df_lhs = _frame(space, repaired, "lhs", 0, {"raw_geom_infeasible": [check_geometry(space.decode(g, repair=False)).ok is False
                                                                          for g in raw], "repaired": changed})
    n_dup = int(df_lhs.duplicated(subset=[c for c in df_lhs if c.startswith("g_")]).sum())
    df_lhs = df_lhs.drop_duplicates(subset=[c for c in df_lhs if c.startswith("g_")]).reset_index(drop=True)
    df_lhs["id"] = np.arange(len(df_lhs))

    rng = np.random.default_rng(seed + 1)
    seen = {tuple(r) for r in df_lhs[[c for c in df_lhs if c.startswith("g_")]].to_numpy()}
    bg, rej, drawn = biased_sample(space, n_biased, rng, exclude=seen)
    df_b = _frame(space, bg, "biased", len(df_lhs), {"raw_geom_infeasible": False, "repaired": False})
    df = pd.concat([df_lhs, df_b], ignore_index=True)

    report = {
        "n_requested": {"lhs": n_lhs, "biased": n_biased}, "n_rows": {"lhs": len(df_lhs), "biased": len(df_b)},
        "lhs_raw_geometry_infeasible_fraction": raw_bad / n_lhs,
        "lhs_raw_infeasible_reason_counts": dict(raw_reasons.most_common()),
        "lhs_rows_changed_by_repair_fraction": float(changed.mean()),
        "lhs_duplicates_after_repair_dropped": n_dup,
        "biased_candidates_drawn": drawn, "biased_acceptance": len(df_b) / max(drawn, 1),
        "biased_rejection_counts": dict(rej.most_common()), "seed": seed, "config_hash": config.config_hash(("sampling", "design_space", "geometry")),
    }
    report.update(sanity_check(space, df))
    return df, report


def sanity_check(space: DesignSpace, df: pd.DataFrame) -> dict:
    """Count physically impossible rows (must be 0): unbuildable geometry, negative effective depth, D < b, bad pt."""
    cols = [f"g_{n}" for n in space.gene_names]
    cfg = config.design_space()
    bad: Counter = Counter()
    for g in df[cols].to_numpy():
        d = space.decode(g, repair=False)
        res = check_geometry(d)
        for r in res.reasons:
            bad[r] += 1
        for sec in d.beams:
            if sec.D_mm <= 100:
                bad["NEG_D"] += 1
    gene_ok = bool(all(0 <= df[c].min() and df[c].max() < n for c, n in zip(cols, space.n_options, strict=True)))
    return {"physically_impossible_rows": int(sum(bad.values())), "impossible_reasons": dict(bad), "genes_in_range": gene_ok,
            "option_coverage_lhs": {n: int(df[df.sample_stratum == "lhs"][f"g_{n}"].nunique()) for n in space.gene_names},
            "cover_exposure": cfg.cover_mm.exposure}


def write_matrix(df: pd.DataFrame, report: dict) -> None:
    MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(MATRIX_PATH, index=False)
    REPORT_PATH.write_text(json.dumps(report, indent=1), encoding="utf-8")
