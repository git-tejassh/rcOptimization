"""Generate docs/REPORT_DRAFT.md and docs/VIVA_PREP.md with the real numbers from data/results (no placeholders)."""
from __future__ import annotations

import json

from rcopt import config
from rcopt.config import ROOT

RES = ROOT / "data" / "results"
DOCS = ROOT / "docs"


def _j(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def _p(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f} %"


def make_report() -> None:
    sm, ver, cmp_, opt = _j("surrogate_metrics.json"), _j("verification.json"), _j("compute_comparison.json"), _j("optimization_summary.json")
    ff, bench, rt = _j("full_front_check.json"), _j("benchmark.json"), _j("fe_runtime.json")
    samp = _j("sampling_report.json")
    sens = _j("sensitivity.json") if (RES / "sensitivity.json").exists() else None
    b_last = bench[list(bench)[-1]]
    a1, b1, a0, b0 = sm["after_AL"]["A"], sm["after_AL"]["B"], sm["before_AL"]["A"], sm["before_AL"]["B"]
    h = ver["variants"]["A"]
    cc = cmp_["configs"]
    prov = config.provisional_items()

    def fails(v: dict) -> str:
        if not v["failures"]:
            return "none"
        return "; ".join(f"#{f['index']}{' (boundary pick)' if f['boundary_pick'] else ''}: {', '.join(f['reasons'])}" for f in v["failures"])

    ver_rows = "\n".join(
        f"| {k} | {v['n_verified']} | {v['n_pass']} ({_p(v['pass_rate'], 0)}) | {v['n_truly_feasible']} | {v['n_within_tolerance']} | "
        f"{v['boundary_picks']['n_pass']}/{v['boundary_picks']['n']} |" for k, v in ver["variants"].items())
    cmp_rows = "\n".join(
        f"| {k} | {x['evaluations_requested_per_seed']:.0f} | {x['unique_fe_solves_per_seed']:.0f} | {x['wall_s_per_seed']:.0f} | {x['hv_pooled_front_true']:.4f} | "
        + (f"{x['speedup_optimisation_only']:.1f}x / {x['speedup_vs_direct_incl_datagen_and_training']:.2f}x |" if "speedup_optimisation_only" in x else "- |")
        for k, x in cc.items())
    sens_txt = sens["verdict"] if sens else "not run"
    text = f"""# Report draft: Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon

*Owner: Tejas Shrivastava, MANIT Bhopal (7th-semester major project). Generated from `data/results/` by `rcopt.report.report_draft`; every number below
comes from the pipeline outputs. Provisional inputs (cost rates, emission factors, IS 456 table transcriptions) are listed in section 8.*

## Abstract
A reproducible pipeline is built for a regular G+3 RC moment frame (the owner's STAAD model: 4 x 3 bays of 5 m, storey 3 m). OpenSeesPy 3D elastic analyses
(validated against the owner's STAAD results to {_p(b_last['reactions_Fy']['DL']['max_rel'], 4)} on reactions) feed IS 456:2000 limit-state checks of discrete,
IS-standard designs under gravity loading only. A dataset of {rt['dataset_rows']} analysed designs (all kept, {rt['status_counts'].get('OK', 0)} OK, {rt['feasible']} truly feasible) trains two surrogates;
constrained NSGA-II minimises cost and embodied carbon. Surrogate-driven and direct-FE fronts are compared, {h['n_verified']} headline-front designs are re-verified
({h['n_pass']} pass, {_p(h['pass_rate'], 0)}; target 90 %), and the whole pooled front is re-evaluated. No novelty of algorithm is claimed.

## 1. Introduction and literature position
NSGA-II for RC frame cost optimisation has been published since at least 2016 (Kaveh et al., J. Civil Eng. & Management, 2016); surrogate-assisted NSGA-II for cost/carbon
exists in adjacent domains (concrete mix design). The contribution here is a validated, India-contextualised application: IS-code basis, discrete IS-standard sections / bars / grades,
Indian-context carbon factors with the gaps flagged (`docs/CARBON_DATA_AUDIT.md`), and a measured surrogate-versus-ground-truth reliability.

## 2. Problem and scope
Gravity only (1.5 (DL + LL) strength; 1.0 (DL + LL) service), beams and columns, frame-material cost and A1-A4 carbon, formwork carbon excluded. Out of scope: seismic / wind (IS 1893 / IS 875-3; hook only,
`docs/SEISMIC_EXTENSION.md`), foundations, slab design, operational carbon. **The optimum is not a code-compliant design of the building**: {57} of the 133 columns in the STAAD report are governed by seismic cases.

## 3. Method
* **Design space**: 22 integer genes ({_j('design_space.json')['total_combinations']:.2e} combinations): per beam group (2) b, D, bottom bars (dia, n), top bars (dia, n); per column group (2) b, D, bars (dia, n); concrete M20-M40; steel Fe415 / Fe500. A deterministic repair snaps candidates to buildable designs ({_p(samp['lhs_raw_geometry_infeasible_fraction'])} of raw uniform genomes are unbuildable).
* **FE**: OpenSeesPy `ElasticTimoshenkoBeam` frame, beams 0.35 Ig / columns 0.70 Ig, Ec = 5000 sqrt(fck), slab loads by yield-line tributary areas, wall loads following beam depth. One cold solve {1e3 * cmp_['mean_fe_solve_time_s_single_process']:.0f} ms.
* **Checks**: IS 456 flexure (strain-compatible, doubly reinforced), shear (Tables 19-20), steel limits, column P-M interaction by strain compatibility with biaxial formula and slenderness, deflection <= L/250. Anchor tests, independent hand calculations (`docs/hand_calcs`) and the STAAD column-81 result are reproduced.
* **Validation against STAAD** (`docs/BENCHMARK.md`): reactions {_p(b_last['reactions_Fy']['DL']['max_rel'], 4)}, vertical displacements {_p(b_last['displacements_dy_mm']['COMB11']['max_rel'], 4)}, column axial forces {_p(b_last['columns_Pu']['max_rel'], 4)}, column moments > 20 kN.m {_p(b_last['columns_Mz_ge20kNm']['max_rel'], 2)}. Two causes of earlier differences (wall-load eccentricity torque, shear deformation) were found and are documented.
* **Sampling**: {samp['n_rows']['lhs']} discrete-aware LHS designs + {samp['n_rows']['biased']} feasibility-biased designs; seed {samp['seed']}.
* **Surrogates**: A = direct utilisation regression (bootstrap XGBoost ensembles, log targets) per the brief; B = FE demands from sizes + fck, utilisations by the exact IS 456 module. One active-learning round of {sm['active_learning']['n_selected']} boundary-targeted designs.
* **Optimisation**: pymoo NSGA-II, population {opt['A']['pop_size']}, {opt['A']['n_gen']} generations, {opt['A']['seeds']} seeds; configurations A, A + margin, B, B + margin, and direct FE (population {opt['direct']['pop_size']}, {opt['direct']['n_gen']} generations).

## 4. Results: dataset and surrogates
Dataset: {rt['dataset_rows']} rows, status counts {rt['status_counts']}, {rt['near_boundary_rows']} rows with a ratio in [0.85, 1.15]; failure table in `data/results/failure_table.csv`.
Hold-out: {sm['n_test']} designs ({sm['n_test_boundary']} near the boundary).

| Output | A MAE | A boundary MAE | B MAE | B boundary MAE |
|---|---|---|---|---|
""" + "\n".join(
        f"| {t} | {a1['overall'][t]['MAE']:.4f} | {a1['boundary'][t]['MAE']:.4f} | {b1['overall'][t]['MAE']:.4f} | {b1['boundary'][t]['MAE']:.4f} |"
        for t in ("U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max")) + f"""

Feasibility agreement near the boundary: A {_p(a1['feasibility_boundary']['agreement'])} ({a1['feasibility_boundary']['FP_pred_feasible_but_truly_infeasible']} designs wrongly accepted), B {_p(b1['feasibility_boundary']['agreement'])} ({b1['feasibility_boundary']['FP_pred_feasible_but_truly_infeasible']}).
Active learning changed A's boundary U_flex MAE from {a0['boundary']['U_flex_max']['MAE']:.4f} to {a1['boundary']['U_flex_max']['MAE']:.4f} and B's from {b0['boundary']['U_flex_max']['MAE']:.4f} to {b1['boundary']['U_flex_max']['MAE']:.4f}.
Hypothesis D2 (capacity is closed-form, so learn only demands) is {'supported' if b1['overall']['U_flex_max']['MAE'] < a1['overall']['U_flex_max']['MAE'] else 'NOT supported'} by the U_flex error. Figures: `docs/figures/parity_*_after_AL.png`.

## 5. Results: Pareto fronts
Pooled fronts (truly feasible, re-evaluated): """ + ", ".join(f"{k} {v['true_front_size']} pts (HV {v['hv_pooled_front_true']:.4f})" for k, v in opt.items()) + f""".
Cost and carbon are strongly correlated along the front (r = {opt['A']['cost_carbon_correlation_pooled']:.3f} for A): both follow material volume, so the front is narrow. Figure: `docs/figures/pareto_fronts.png`.
Sensitivity (+/-20 %): {sens_txt}

## 6. Verification (`data/results/verification.json`)
| Front | verified | pass | truly feasible | within tolerance | boundary picks passing |
|---|---|---|---|---|---|
{ver_rows}

Headline (A) failures: {fails(h)}. Tolerance: utilisation +/-{ver['tolerance']['util_abs']}, deflection +/-{_p(ver['tolerance']['defl_rel'], 0)}.
Whole-front check (A): {_p(ff['A']['truly_feasible_fraction'], 0)} truly feasible; HV gap predicted vs true {_p(ff['A']['hv_gap_relative'])}; margin variant A + margin: {_p(ff['A_margin']['truly_feasible_fraction'], 0)} truly feasible, verification pass {_p(ver['variants']['A_margin']['pass_rate'], 0)}.

## 7. Compute comparison
| Config | evaluations / seed | FE solves / seed | wall / seed (s) | HV (true) | speed-up (opt. only / incl. data + training) |
|---|---|---|---|---|---|
{cmp_rows}

One-time costs charged to the surrogate rows: data generation {cmp_['data_generation']['fe_solves']} FE solves (about {cmp_['data_generation']['serial_equivalent_s']:.0f} s serial-equivalent) and training {cmp_['surrogate_training_s']:.0f} s.
{'The surrogate paid off.' if cc['A']['speedup_vs_direct_incl_datagen_and_training'] > 1 else 'The surrogate did NOT pay off against direct FE in this setting: an elastic frame solve is a few tens of milliseconds.'}

## 8. Limitations and provisional values
* Provisional (unverified): {len(prov)} config entries (all cost rates, carbon factors, IS 456 table transcriptions): see `docs/ASSUMPTIONS.md`. Absolute INR and kgCO2e values are indicative only.
* Gravity only; no seismic / wind; no foundations; beam torsion ignored; slab not designed; cracked-stiffness modifiers 0.35 / 0.70 not validated by STAAD.
* Deflection and shear never governed in the dataset; flexure, column interaction and steel limits did.
* Surrogate B approximates the column demand by 4 critical triples per group; its error is part of the reported utilisation errors.

## 9. Conclusions
See the numbers above; the claims supported are: (i) the FE + IS 456 pipeline reproduces the owner's STAAD gravity results; (ii) surrogate reliability was measured, including near the boundary, with the failures listed; (iii) the surrogate speed-up against direct FE is as tabulated, including data generation; (iv) the cost-carbon front is narrow because both objectives follow material volume.
"""
    (DOCS / "REPORT_DRAFT.md").write_text(text, encoding="utf-8")

    viva = f"""# Viva preparation: likely examiner questions with evidence-backed answers

1. **Why a surrogate if one FE solve takes only {1e3 * cmp_['mean_fe_solve_time_s_single_process']:.0f} ms?** It may not be worth it, and the project measures that: speed-up {cc['A']['speedup_optimisation_only']:.1f}x for the optimisation alone and {cc['A']['speedup_vs_direct_incl_datagen_and_training']:.2f}x including data generation and training (`compute_comparison.json`). The brief asked for a surrogate; the direct-FE baseline is the honest test. The surrogate would matter for a larger model (more storeys, nonlinear or seismic load cases).
2. **Why not seismic?** Brief s5 defers it; the optimum is gravity-only. The STAAD report shows 57 of 133 columns governed by seismic cases, so the optimum is not a compliant design (`docs/SEISMIC_EXTENSION.md`).
3. **Why is the front narrow?** Cost and carbon both follow material volume (r = {opt['A']['cost_carbon_correlation_pooled']:.3f}). Spread comes from concrete grade (cement content) and steel quantity. We did not distort rates to widen it.
4. **How do you know the IS checks are right?** Anchor tests (Mu,lim/bd2 2.76 / 3.45 / 4.14, Tables 19-20 spot values), independent hand calculations (`docs/hand_calcs`), and STAAD's own column-81 design numbers reproduced (Puz 2901.43 kN, Muz1 150.87 kN.m within 1.5 %, IR 0.39). The IS table transcriptions are still marked provisional until you check them against the printed code.
5. **How do you know the FE is right?** Closed-form beam tests and equilibrium checks, and a benchmark against your STAAD model: reactions to {_p(b_last['reactions_Fy']['DL']['max_rel'], 4)}, column axial force {_p(b_last['columns_Pu']['max_rel'], 4)}, column moments {_p(b_last['columns_Mz_ge20kNm']['max_rel'], 2)} (`docs/BENCHMARK.md`).
6. **Why OpenSees and not STAAD in the loop?** Brief s7: STAAD needs a licence, is slow to drive, and cannot run on any OS. STAAD is used as geometry source and benchmark only. The legacy STAAD-driven optimiser was archived because it had fixed demands and a single-point front (`docs/LEGACY_AUDIT.md`).
7. **Is the surrogate reliable near the feasibility boundary?** Boundary U_flex MAE A {a1['boundary']['U_flex_max']['MAE']:.4f}, B {b1['boundary']['U_flex_max']['MAE']:.4f}; feasibility agreement near the boundary A {_p(a1['feasibility_boundary']['agreement'])}, B {_p(b1['feasibility_boundary']['agreement'])}. Verification pass rate (A) {_p(h['pass_rate'], 0)} against a 90 % target; failures: {fails(h)}.
8. **What did active learning achieve?** {sm['active_learning']['n_selected']} boundary-targeted designs; boundary MAE changes quoted in the report, section 4. One round only (brief).
9. **Why two surrogates?** FE demands depend only on sizes and fck; capacity is closed-form. B learns only demands (D2). It is {'more' if b1['overall']['U_flex_max']['MAE'] < a1['overall']['U_flex_max']['MAE'] else 'not more'} accurate on U_flex.
10. **Are the cost and carbon numbers real?** No: every rate and factor is provisional (`docs/ASSUMPTIONS.md`, `docs/CARBON_DATA_AUDIT.md`); the dashboard shows a permanent banner. Replace them in `config/*.yaml` and re-run.
11. **What does repair do to the optimiser?** It maps any genome to the nearest buildable IS-standard design; {_p(samp['lhs_raw_geometry_infeasible_fraction'])} of raw uniform draws were unbuildable. No continuous relaxation is reported as a design.
12. **Is the NSGA-II converged, are results seed-independent?** 5 seeds per configuration, hypervolume against a fixed pooled reference with mean and std (`optimization_summary.json`, dashboard "Compute comparison").
13. **How robust is the front to input uncertainty?** {sens_txt}
14. **What is novel?** Nothing algorithmic; NSGA-II for RC frames is published since 2016 (Kaveh et al.). The contribution is a validated, India-contextualised application with a measured surrogate reliability.
15. **Why 0.35 Ig / 0.70 Ig?** Common cracked-section practice; deflection uses the same factors (about 2.9x gross-section deflection, comparable to the IS 456 creep factor 1 + 1.6). Not validated by STAAD (uncracked): flagged in ASSUMPTIONS B6.
16. **What would you do next?** Replace provisional data, add seismic cases and IS 13920 detailing (the hook exists), T-beam action and curtailment, and test on a larger structure where FE cost makes the surrogate pay.
"""
    (DOCS / "VIVA_PREP.md").write_text(viva, encoding="utf-8")
