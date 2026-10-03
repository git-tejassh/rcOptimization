"""Command line entry points: ``rcopt phase0 .. phase5``, ``rcopt all``, ``rcopt export`` (see Makefile)."""
from __future__ import annotations

import json
import time

import typer

from rcopt import config
from rcopt.config import ROOT
from rcopt.design.variables import default_space

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


if __name__ == "__main__":
    app()
