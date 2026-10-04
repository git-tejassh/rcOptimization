"""Command line entry points: ``rcopt phase0 .. phase5``, ``rcopt all``, ``rcopt export`` (see Makefile)."""
from __future__ import annotations

import json
import os
import time

import typer

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.variables import default_space

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # one BLAS thread per worker process
    os.environ.setdefault(_v, "1")

app = typer.Typer(add_completion=False, help="RC frame cost/carbon optimisation pipeline")
RESULTS = ROOT / "data" / "results"


@app.callback()
def _main() -> None:
    """RC frame cost/carbon optimisation pipeline."""


@app.command()
def phase0() -> None:
    """P0: validate all config, write data/results/design_space.json."""
    t0 = time.time()
    sp = default_space()
    for name in ("geometry", "loads", "design_space"):
        getattr(config, name)()
    for name in ("solver", "cost_rates", "carbon_factors", "is456_tables", "surrogate", "optimize", "verify",
                 "sampling"):
        config.load_dict(name)
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {
        "genes": [{"name": n, "options": list(o)} for n, o in zip(sp.gene_names, sp.options, strict=True)],
        "n_genes": sp.n_genes,
        "total_combinations": sp.total_combinations(),
        "beam_groups": config.geometry().beam_groups,
        "column_groups": config.geometry().column_groups,
        "cover_mm": config.design_space().cover_mm.model_dump(),
        "config_hash": config.config_hash(),
        "provisional_items": config.provisional_items(),
    }
    (RESULTS / "design_space.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    typer.echo(f"phase0 ok: {sp.n_genes} genes, {sp.total_combinations():.3e} combinations, "
               f"{len(out['provisional_items'])} provisional config items ({time.time() - t0:.1f}s)")


@app.command()
def phase0b() -> None:
    """P0b: FE/IS-456 validation: STAAD benchmark report, hand-calc documents, anchor tests."""
    import subprocess
    import sys

    from rcopt.fe.benchmark import write_report

    full = write_report()
    typer.echo(f"benchmark: reactions max rel diff {full['reactions_Fy']['DL']['max_rel']:.2e}, "
               f"column Pu {full['columns_Pu']['max_rel']:.2e} -> docs/BENCHMARK.md")
    subprocess.run([sys.executable, str(ROOT / "docs" / "hand_calcs" / "hand_calcs.py")], check=True)
    code = subprocess.run([sys.executable, "-m", "pytest", "-q", "-m", "not slow", "tests/test_is456_anchors.py",
                           "tests/test_fe_sanity.py", "tests/test_benchmark.py"], cwd=ROOT).returncode
    if code:
        raise typer.Exit(code)


@app.command()
def phase1() -> None:
    """P1: discrete-aware LHS + feasibility-biased design matrix -> data/processed/design_matrix.parquet."""
    from rcopt.sampling.matrix import build_design_matrix, write_matrix

    df, rep = build_design_matrix()
    write_matrix(df, rep)
    typer.echo(f"phase1 ok: {len(df)} designs ({rep['n_rows']}), raw LHS geometry-infeasible "
               f"{100 * rep['lhs_raw_geometry_infeasible_fraction']:.1f} %, impossible rows after repair: "
               f"{rep['physically_impossible_rows']}")


@app.command()
def phase2(force: bool = False) -> None:
    """P2: FE batch over the design matrix -> data/processed/fe_dataset.parquet + failure table."""
    from rcopt.fe.batch import run_phase2

    r = run_phase2(force=force)
    typer.echo(f"phase2 ok: {r['dataset_rows']} rows, status {r['status_counts']}, feasible {r['feasible']}, "
               f"near-boundary {r['near_boundary_rows']}, wall {r['wall_s']:.1f}s, mean FE {1e3 * r['mean_fe_time_s']:.1f} ms")


@app.command()
def phase3(force: bool = False) -> None:
    """P3: train surrogates A and B, evaluate, one active-learning round -> models/ + surrogate_metrics.json."""
    from rcopt.surrogate.pipeline import run_phase3

    m = run_phase3(force=force)
    for tag in ("before_AL", "after_AL"):
        a, b = m[tag]["A"], m[tag]["B"]
        typer.echo(f"{tag}: U_flex MAE A {a['overall']['U_flex_max']['MAE']:.4f} B {b['overall']['U_flex_max']['MAE']:.4f} | "
                   f"U_col MAE A {a['overall']['U_col_max']['MAE']:.3f} B {b['overall']['U_col_max']['MAE']:.3f} | "
                   f"boundary feas.agree A {a['feasibility_boundary']['agreement']:.3f} B {b['feasibility_boundary']['agreement']:.3f}")
    typer.echo(f"phase3 ok in {m['runtime_s']:.0f}s; margins q95 {m['margin_q95']}")


@app.command()
def phase4(force: bool = False, n_jobs: int = 8) -> None:
    """P4: NSGA-II (surrogate A/B, +/- margin, direct FE) x seeds -> pooled fronts + compute comparison."""
    from rcopt.optimize.phase4 import run_phase4

    r = run_phase4(force=force, n_jobs=n_jobs)
    for c, v in r["compute"]["configs"].items():
        typer.echo(f"{c:9s} HV(true front) {v['hv_pooled_front_true']:.4f}  wall/seed {v['wall_s_per_seed']:.0f}s  "
                   f"unique evals {v['unique_evaluations_per_seed']:.0f}  FE solves {v['unique_fe_solves_per_seed']:.0f}")


@app.command()
def phase5() -> None:
    """P5: verify 30 Pareto designs per front with ground truth; full-front re-evaluation."""
    from rcopt.verify.full_front_check import run_full_front_check
    from rcopt.verify.verify_pareto import run_phase5

    v = run_phase5()
    run_full_front_check()
    for name, r in v["variants"].items():
        typer.echo(f"{name:9s} verified {r['n_verified']}  pass {r['n_pass']} ({100 * r['pass_rate']:.0f} %)  "
                   f"truly feasible {r['n_truly_feasible']}  within tolerance {r['n_within_tolerance']}")


@app.command()
def sensitivity(force: bool = False) -> None:
    """+/-20 % sensitivity study of the headline front (steel cost, cement carbon, steel carbon)."""
    from rcopt.cost_carbon.sensitivity import run_sensitivity

    typer.echo(run_sensitivity(force=force)["verdict"])


@app.command()
def export() -> None:
    """Write web/public/data/*.json (pydantic-validated) for the dashboard."""
    from rcopt.report.export_json import export_all

    r = export_all()
    typer.echo(f"export ok: {len(r['files'])} files, {r['bytes'] / 1e6:.2f} MB in {r['seconds']:.0f}s -> web/public/data")


@app.command()
def report() -> None:
    """Figures (docs/figures), docs/REPORT_DRAFT.md and docs/VIVA_PREP.md from data/results."""
    from rcopt.report.figures import make_figures
    from rcopt.report.report_draft import make_report

    typer.echo(f"figures: {make_figures()}")
    make_report()
    typer.echo("report: docs/REPORT_DRAFT.md, docs/VIVA_PREP.md written")


@app.command()
def cement() -> None:
    """Cement-type trade-off scan (price premium of low-carbon cement) -> data/results/cement_tradeoff.json."""
    from rcopt.cost_carbon.cement_tradeoff import run_cement_tradeoff

    for s in run_cement_tradeoff()["scenarios"]:
        typer.echo(f"PSC premium {s['psc_premium_inr_per_kg']}: front {s['front_size']} pts, cost span {s['cost_span_pct']:.1f} %, "
                   f"carbon span {s['carbon_span_pct']:.1f} %, cements {s['cement_types_on_front']}")


@app.command(name="all")
def run_all_phases(force: bool = False) -> None:
    """Run phases 0 -> 5, the sensitivity study and the export (cached stages are skipped unless --force)."""
    import subprocess
    import sys

    steps = ["phase0", "phase0b", "phase1", "phase2", "phase3", "phase4", "phase5", "sensitivity", "cement", "report", "export"]
    for s in steps:
        cmd = [sys.executable, "-m", "rcopt.cli", s] + (["--force"] if force and s in ("phase2", "phase3", "phase4") else [])
        typer.echo(f">> {' '.join(cmd[2:])}")
        if subprocess.run(cmd, cwd=ROOT).returncode:
            raise typer.Exit(1)


if __name__ == "__main__":
    app()
