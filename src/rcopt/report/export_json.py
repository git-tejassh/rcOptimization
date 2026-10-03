"""Export every result the dashboard needs to ``web/public/data/*.json`` (pydantic-validated, project.md 11.1).

The UI is a static site: nothing is computed in the browser except filtering/plotting. All honesty flags
(provisional data, gravity-only, verification failures, narrow front, deviations from the brief) are exported here
so that the UI cannot silently drop them.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from pydantic import BaseModel

from rcopt import config
from rcopt.config import ROOT
from rcopt.cost_carbon.carbon import recompute_dataset_objectives
from rcopt.design.describe import describe_genome
from rcopt.design.variables import default_space
from rcopt.optimize.metrics import objective_correlation

RESULTS = ROOT / "data" / "results"
WEB_DATA = ROOT / "web" / "public" / "data"

GRAVITY_CAVEAT = (
    "Designs are checked for gravity loading only (1.5 (DL + LL), IS 456:2000). A real building in India must also be designed for "
    "seismic (IS 1893:2016) and, where applicable, wind (IS 875-3) loading. Bhopal falls in a low-seismicity zone, but code-mandated "
    "seismic design still applies; confirm the zone from IS 1893 (Part 1):2016. Results are for design-stage trade-off exploration, not final design."
)
HONEST_NOVELTY = (
    "NSGA-II for RC frame cost optimisation has been published since at least 2016 (e.g. Kaveh et al., J. Civil Eng. & Management, 2016), and "
    "surrogate-assisted NSGA-II for cost/carbon exists in adjacent domains (concrete mix design). This project does not claim a new algorithm. "
    "Its contribution is a carefully validated, India-contextualised application: IS-code basis, discrete IS-standard sections / bars / grades, "
    "Indian-context carbon factors with the gaps flagged, and a reported surrogate-versus-ground-truth reliability result."
)
DEVIATIONS = [
    ("D0", "STAAD excluded from the automated loop", "Same: STAAD used only as geometry/load source and benchmark", "The folder held legacy STAAD-driven code; it is archived"),
    ("D1", "Reinforcement ratio continuous", "Reinforcement as discrete (bar diameter, count); ratio derived", "The brief's own rule against continuous relaxation"),
    ("D2", "One surrogate (direct utilisation)", "Surrogate A (brief) + Surrogate B (demands + analytic IS 456)", "FE demands depend only on sizes and fck; capacity is closed-form"),
    ("D3", "Surrogate-NSGA-II only", "Plus a direct-FE NSGA-II baseline", "Elastic frame FE is cheap: an honest test of whether the surrogate is warranted"),
    ("D4", "Verify 20-30 designs", "Same, plus re-evaluation of the entire pooled front", "Strengthens the verification result honestly"),
    ("D5", "20-week timeline", "Compressed: the pipeline runs in hours", "7th-semester-only project"),
    ("D6", "(not in the brief)", "Genome repair snaps every candidate to the nearest buildable IS-standard design", "96 % of uniform random genomes were geometrically unbuildable"),
    ("D7", "(not in the brief)", "Surrogate B regresses the demands of column position classes (level x position, 30 classes) instead of every column", "Members of a class are equivalent by symmetry, so this is exact and smooth; the first attempt with 4 extremal triples failed verification (decision D-024)"),
]
CONSTRAINTS = [
    ("Beam flexure", "Mu,demand / Mu,capacity <= 1 for sagging (bottom steel) and hogging (top steel), strain-compatible, xu <= xu,max", "IS 456 cl. 38.1, Annex G"),
    ("Beam shear", "tau_v <= tau_c,max and stirrup spacing >= 75 mm", "cl. 40, Tables 19-20"),
    ("Beam steel limits", "0.85 b d / fy <= Ast <= 4 % b D (top and bottom)", "cl. 26.5.1.1"),
    ("Column biaxial interaction", "(Mux/Mux1)^alpha + (Muy/Muy1)^alpha <= 1, minimum eccentricity, slenderness moments", "cl. 39.6, 25.4, 39.7"),
    ("Column steel limits", "0.8 % <= pt <= 4 % (6 % absolute), bar spacing 25-300 mm", "cl. 26.5.3.1"),
    ("Deflection", "service deflection <= L / 250 (relative to the beam chord)", "cl. 23.2 (a)"),
    ("Geometry", "D >= b for columns; beam width <= column width; bars fit in <= 2 layers; genome repaired to buildable", "cl. 26.3.2, practice"),
]
LABELS = {"A": "Surrogate A (headline)", "A_margin": "Surrogate A + safety margin", "B": "Surrogate B (hybrid)",
          "B_margin": "Surrogate B + safety margin", "direct": "Direct FE (baseline)"}


class _Out(BaseModel):
    model_config = {"extra": "allow"}


class MetaModel(_Out):
    project: str
    generated: str
    config_hash: str
    provisional: bool
    provisional_items: list[str]
    gravity_only_caveat: str
    honest_novelty: str


class DesignModel(_Out):
    id: int
    genome: list[int]
    concrete: str
    steel: str
    pred_cost: float
    pred_carbon: float
    feasible_true: bool


_BUNDLE: dict = {}


def _write(name: str, obj) -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, default=float, allow_nan=False, separators=(",", ":"))
    (WEB_DATA / name).write_text(txt, encoding="utf-8")
    _BUNDLE[name[:-5]] = txt


def _write_bundle() -> None:
    """Classic script with every JSON file, so the single-file build also works when opened from disk (file://)."""
    body = ",".join(f'"{k}":{v}' for k, v in _BUNDLE.items())
    (WEB_DATA / "bundle.js").write_text("window.__RCOPT_DATA__={" + body + "};", encoding="utf-8")


def _clean(x):
    """Replace NaN/inf by None recursively (strict JSON)."""
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def _load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def _findings(ds: pd.DataFrame, sm: dict, ver: dict, ff: dict, cmp_: dict, opt: dict, sens: dict | None) -> list[dict]:
    f: list[dict] = []
    ok = ds[ds.status == "OK"]
    f.append({"level": "warn", "text": "Cost rates, emission factors and the IS 456 table transcriptions are PROVISIONAL (not verified). Absolute INR / kgCO2e values are indicative only."})
    f.append({"level": "warn", "text": "Gravity loading only: no seismic or wind design. See the caveat on every design page."})
    if ok.defl_ratio_max.max() < 1.0:
        f.append({"level": "info", "text": f"Deflection (L/250) never governed in the {len(ok)} analysed designs (largest ratio {ok.defl_ratio_max.max():.2f}); shear (tau_v / tau_c,max) never exceeded {ok.U_shear_max.max():.2f}. "
                  "Flexure, column interaction and steel limits are the binding constraints."})
    a, b = sm["after_AL"]["A"], sm["after_AL"]["B"]
    f.append({"level": "info", "text": f"Surrogate hold-out MAE of U_flex: A {a['overall']['U_flex_max']['MAE']:.3f}, B {b['overall']['U_flex_max']['MAE']:.4f}; near the feasibility boundary A {a['boundary']['U_flex_max']['MAE']:.3f}, B {b['boundary']['U_flex_max']['MAE']:.4f}."})
    fa, fb = a["feasibility_boundary"], b["feasibility_boundary"]
    f.append({"level": "info" if fa["agreement"] > 0.9 else "warn",
              "text": f"Feasibility agreement near the boundary: A {100 * fa['agreement']:.1f} %, B {100 * fb['agreement']:.1f} % "
                      f"(A: {fa['FP_pred_feasible_but_truly_infeasible']} false-feasible of {a['n_boundary']})."})
    h = ver["variants"]["A"]
    f.append({"level": "info" if h["target_met"] else "bad",
              "text": f"Verification (headline front A): {h['n_pass']} of {h['n_verified']} designs pass ({100 * h['pass_rate']:.0f} %; target {100 * h['pass_target']:.0f} %). "
                      f"{h['n_truly_feasible']} are truly feasible. " + ("" if h["target_met"] else "The 90 % target was NOT met: see the failure list.")})
    for k in ("A_margin", "B", "B_margin"):
        v = ver["variants"][k]
        f.append({"level": "info" if v["target_met"] else "warn", "text": f"Verification {LABELS[k]}: {v['n_pass']} / {v['n_verified']} pass ({100 * v['pass_rate']:.0f} %)."})
    feas = ds[ds.feasible == 1]
    corr = float(feas[["cost", "carbon"]].corr().iloc[0, 1])
    n1 = {k: v["rank1_front_size"] for k, v in opt.items()}
    f.append({"level": "bad" if max(n1.values()) < 25 else "info", "text": f"Pareto front proper: {n1} non-dominated points per configuration (criterion S1, at least 25, NOT met). Cost and carbon are strongly correlated over the {len(feas)} truly feasible designs (r = {corr:.3f}) because both follow material volume; cost varies only {100 * (opt['direct']['cost_range_true'][1] / opt['direct']['cost_range_true'][0] - 1):.1f} % and carbon {100 * (opt['direct']['carbon_range_true'][1] / opt['direct']['carbon_range_true'][0] - 1):.1f} % across the direct-FE near-Pareto set. The dashboard shows that near-Pareto set (first non-dominated ranks, about 100 designs)."})
    c = cmp_["compute"]["configs"]
    sp = c["A"]["speedup_vs_direct_incl_datagen_and_training"]
    f.append({"level": "info" if sp > 1 else "warn", "text": f"Compute: a cold FE solve takes {1e3 * cmp_['compute']['mean_fe_solve_time_s_single_process']:.0f} ms; the surrogate-driven NSGA-II is "
              f"{c['A']['speedup_optimisation_only']:.1f}x faster than direct FE for the optimisation alone and {sp:.2f}x including data generation and training."
              + (" The surrogate did NOT pay off in this setting." if sp < 1 else "")})
    ff_a = ff["A"]
    f.append({"level": "info" if ff_a["truly_feasible_fraction"] > 0.9 else "warn", "text": f"Entire pooled front A re-evaluated: {100 * ff_a['truly_feasible_fraction']:.0f} % truly feasible; hypervolume gap predicted vs true {100 * ff_a['hv_gap_relative']:.1f} %."})
    if sens:
        f.append({"level": "info", "text": sens["verdict"]})
    return f


def export_all() -> dict:
    t0 = time.time()
    sp = default_space()
    geom, ds_cfg = config.geometry(), config.design_space()
    ds = pd.concat([pd.read_parquet(ROOT / "data" / "processed" / "fe_dataset.parquet"),
                    pd.read_parquet(ROOT / "data" / "processed" / "fe_dataset_al.parquet")], ignore_index=True)
    ok_rows = ds.status == "OK"
    ds.loc[ok_rows, "cost"], ds.loc[ok_rows, "carbon"] = recompute_dataset_objectives(ds[ok_rows])   # current rates / factors
    sm, ver_raw = _load("surrogate_metrics.json"), _load("verification.json")
    ff, opt = _load("full_front_check.json"), _load("optimization_summary.json")
    cmp_ = {"compute": _load("compute_comparison.json")}
    sens = _load("sensitivity.json") if (RESULTS / "sensitivity.json").exists() else None
    bench = _load("benchmark.json")
    rt, samp = _load("fe_runtime.json"), _load("sampling_report.json")

    # ---------------- pareto
    variants = {}
    for v, fname in (("A", "pareto_surrogate_A"), ("A_margin", "pareto_surrogate_A_margin"), ("B", "pareto_surrogate_B"),
                     ("B_margin", "pareto_surrogate_B_margin"), ("direct", "pareto_direct")):
        front = pd.read_parquet(RESULTS / f"{fname}.parquet")
        vrows = {r["index"]: r for r in ver_raw["variants"][v]["designs"]} if v in ver_raw["variants"] else {}
        designs = []
        for i, row in front.reset_index(drop=True).iterrows():
            g = np.array([int(row[f"g_{n}"]) for n in sp.gene_names])
            d = describe_genome(g, sp)
            dd = {"id": int(i), "genome": [int(x) for x in g], "concrete": d["concrete"], "steel": d["steel"], "beams": d["beams"],
                  "columns": d["columns"], "pred_cost": float(row.pred_cost), "pred_carbon": float(row.pred_carbon),
                  "true_cost": float(row.true_cost) if row.true_status == "OK" else None,
                  "true_carbon": float(row.true_carbon) if row.true_status == "OK" else None,
                  "feasible_true": bool(d.get("feasible", False)), "status": d["status"]}
            for k in ("quantities", "cost_inr", "carbon_kgco2e", "utilisation", "stirrup_spacing_mm"):
                if k in d:
                    dd[k] = d[k]
            vr = vrows.get(int(i))
            dd["verification"] = ({"verified": True, "passed": bool(vr["passed"]), "boundary_pick": bool(vr["boundary_pick"]),
                                   "reasons": vr["reasons"]} if vr else {"verified": False})
            if vr and "pred_U_flex_max" in vr:
                dd["pred_util"] = {k[5:]: vr[k] for k in vr if k.startswith("pred_") and k.endswith(("_max", "ratio_max"))}
            DesignModel(**dd)
            designs.append(dd)
        variants[v] = designs
    rng = np.random.default_rng(0)
    idx = rng.choice(len(ds[ds.status == "OK"]), size=min(1500, int((ds.status == "OK").sum())), replace=False)
    okd = ds[ds.status == "OK"].iloc[idx]
    cloud = [{"cost": float(r.cost), "carbon": float(r.carbon), "feasible": bool(r.feasible), "stratum": r.sample_stratum}
             for r in okd.itertuples()]
    _write("pareto.json", {"variants": variants, "cloud": cloud, "labels": LABELS})

    # ---------------- design space
    dspace = json.loads((RESULTS / "design_space.json").read_text())
    dspace.update({"detailing": ds_cfg.detailing.model_dump(), "sampling": samp,
                   "constraints": [{"name": a, "description": b, "clause": c} for a, b, c in CONSTRAINTS],
                   "frame": geom.model_dump()})
    _write("design_space.json", _clean(dspace))

    # ---------------- surrogate / verification / compute / sensitivity / benchmark
    _write("surrogate.json", _clean(sm))
    _write("verification.json", _clean({**ver_raw, "full_front": ff}))
    cmpd = cmp_["compute"]
    direct, sa = cmpd["configs"]["direct"], cmpd["configs"]["A"]
    verdict = (f"Direct-FE NSGA-II: {direct['wall_s_per_seed']:.0f} s per seed ({direct['unique_fe_solves_per_seed']:.0f} unique FE solves). "
               f"Surrogate A: {sa['wall_s_per_seed']:.0f} s per seed, plus one-time data generation ({cmpd['data_generation']['serial_equivalent_s']:.0f} s serial-equivalent) "
               f"and training ({cmpd['surrogate_training_s']:.0f} s). Speed-up incl. amortised cost: {sa['speedup_vs_direct_incl_datagen_and_training']:.2f}x; "
               f"true-front hypervolume ratio vs direct: {sa['hv_ratio_true_vs_direct']:.3f}. "
               + ("The surrogate paid off." if sa["speedup_vs_direct_incl_datagen_and_training"] > 1 else "The surrogate did not pay off in this setting: an elastic frame FE is cheap."))
    _write("compute.json", _clean({"compute": cmpd, "optimization": {k: {kk: vv for kk, vv in v.items() if kk != "run_summaries"} for k, v in opt.items()},
                                    "run_summaries": {k: v["run_summaries"] for k, v in opt.items()}, "verdict": verdict}))
    if sens:
        _write("sensitivity.json", _clean(sens))
    _write("benchmark.json", _clean(bench))

    # ---------------- provenance
    cr, cf = config.load_dict("cost_rates"), config.load_dict("carbon_factors")
    cost_rows = [{"item": f"Concrete {g}", **{k: v[k] for k in ("value", "unit", "source", "status")}} for g, v in cr["concrete_per_m3"].items()]
    cost_rows += [{"item": f"Steel {g}", **{k: v[k] for k in ("value", "unit", "source", "status")}} for g, v in cr["steel_per_kg"].items()]
    cost_rows.append({"item": "Formwork", **{k: cr["formwork_per_m2"][k] for k in ("value", "unit", "source", "status")}})
    carb = [{"item": f"Cement {k}", **{x: v[x] for x in ("value", "unit", "source", "confidence", "india_specific", "status")}}
            for k, v in cf["cement"].items() if isinstance(v, dict)]
    carb += [{"item": f"Cement content {g}", "value": v["value"], "unit": "kg/m3", "source": v["source"], "status": v["status"]} for g, v in cf["cement_content_kg_m3"].items()]
    o = cf["concrete_other_kgCO2e_m3"]
    carb.append({"item": "Concrete other constituents", "value": o["value"], "unit": "kgCO2e/m3", "source": o["source"], "confidence": o["confidence"], "india_specific": o["india_specific"], "status": o["status"]})
    carb += [{"item": f"Steel {g}", **{x: v[x] for x in ("value", "unit", "source", "confidence", "india_specific", "status")}} for g, v in cf["steel"].items()]
    carb += [{"item": f"Transport A4 {k}", "value": f"{v['distance_km']} km x {v['factor_kgCO2e_per_t_km']}", "unit": "km x kgCO2e/(t km)", "source": v["source"], "status": v["status"]} for k, v in cf["transport_A4"].items()]
    prov = {"cost_rates": cost_rows, "carbon_factors": carb, "is456_tables_status": config.load_dict("is456_tables")["status"],
            "assumptions_markdown": (ROOT / "docs" / "ASSUMPTIONS.md").read_text(encoding="utf-8"),
            "decisions_markdown": (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8"),
            "benchmark_markdown": (ROOT / "docs" / "BENCHMARK.md").read_text(encoding="utf-8")}
    carbon_audit = ROOT / "docs" / "CARBON_DATA_AUDIT.md"
    prov["carbon_audit_markdown"] = carbon_audit.read_text(encoding="utf-8") if carbon_audit.exists() else ""
    _write("provenance.json", prov)

    # ---------------- meta
    ok = ds[ds.status == "OK"]
    a_front = variants["A"]
    h = ver_raw["variants"]["A"]
    headline = {
        "dataset_rows": int(len(ds)), "dataset_rows_ok": int(len(ok)), "dataset_feasible": int(ok.feasible.sum()),
        "mean_fe_time_ms": 1e3 * cmpd["mean_fe_solve_time_s_single_process"],
        "front_size_A": len(a_front), "front_size_direct": len(variants["direct"]),
        "hv_true_A": opt["A"]["hv_pooled_front_true"], "hv_true_B": opt["B"]["hv_pooled_front_true"], "hv_true_direct": opt["direct"]["hv_pooled_front_true"],
        "verification_pass_rate_A": h["pass_rate"], "verification_n_A": h["n_verified"],
        "verification_pass_rate_B": ver_raw["variants"]["B"]["pass_rate"],
        "verification_best_variant": max(ver_raw["variants"], key=lambda k: ver_raw["variants"][k]["pass_rate"]),
        "verification_best_rate": max(v["pass_rate"] for v in ver_raw["variants"].values()),
        "speedup_A_incl_costs": sa["speedup_vs_direct_incl_datagen_and_training"], "speedup_A_opt_only": sa["speedup_optimisation_only"],
        "surrogate_A_Uflex_MAE": sm["after_AL"]["A"]["overall"]["U_flex_max"]["MAE"], "surrogate_B_Uflex_MAE": sm["after_AL"]["B"]["overall"]["U_flex_max"]["MAE"],
        "surrogate_A_boundary_feas_agree": sm["after_AL"]["A"]["feasibility_boundary"]["agreement"],
        "surrogate_B_boundary_feas_agree": sm["after_AL"]["B"]["feasibility_boundary"]["agreement"],
        "benchmark_max_rel_reaction": bench[list(bench)[-1]]["reactions_Fy"]["DL"]["max_rel"],
        "carbon_cost_correlation_A": objective_correlation(np.array([[d["pred_cost"], d["pred_carbon"]] for d in a_front])) if len(a_front) > 2 else None,
    }
    meta = {"project": "Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon",
            "generated": time.strftime("%Y-%m-%d %H:%M"), "config_hash": config.config_hash(),
            "provisional": bool(config.provisional_items()), "provisional_items": config.provisional_items(),
            "gravity_only_caveat": GRAVITY_CAVEAT, "honest_novelty": HONEST_NOVELTY,
            "deviations": [dict(zip(("id", "brief", "spec", "reason"), d, strict=True)) for d in DEVIATIONS],
            "frame": geom.model_dump(), "headline": headline, "findings": _findings(ds, sm, ver_raw, ff, cmp_, opt, sens),
            "fe_runtime": rt}
    MetaModel(**meta)
    _write("meta.json", _clean(meta))
    _write_bundle()
    return {"files": sorted(p.name for p in WEB_DATA.glob("*.json")), "seconds": time.time() - t0,
            "bytes": sum(p.stat().st_size for p in WEB_DATA.glob("*.json"))}


__all__ = ["export_all"]
