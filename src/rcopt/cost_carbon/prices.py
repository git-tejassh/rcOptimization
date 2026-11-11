"""Editable unit prices (INR) and their CSV form, applied BEFORE an optimisation (``rcopt reoptimize``, API ``/optimize/prices``).

Every price has a key (``concrete_M25``, ``steel_Fe500``, ``formwork_m2``, ``cement_PSC``) and a default read from
``config/cost_rates.yaml`` (all defaults are PLACEHOLDERS, status ``provisional``). Overrides are applied through the
process-local scenario of ``rcopt.cost_carbon.scenario`` so that every cost evaluation of the process (surrogate, FE check,
quantities) sees the same prices. CSV format: header ``item,value`` (extra columns are ignored), one price per line,
``#`` starts a comment.
"""
from __future__ import annotations

import csv
import io
import math

from rcopt import config
from rcopt.design.variables import default_space


def items() -> list[dict]:
    """Ordered price items with label, unit, placeholder default and group (concrete / steel / formwork / cement)."""
    r = config.load_dict("cost_rates")
    grades = list(default_space().options[default_space().gene_index("fck")])      # grades the optimiser may use
    out: list[dict] = []
    for g in grades:
        out.append({"key": f"concrete_{g}", "label": f"Concrete {g} (placed)", "unit": "INR/m3", "group": "Concrete",
                    "default": float(r["concrete_per_m3"][g]["value"]), "status": r["concrete_per_m3"][g].get("status", "provisional")})
    for s, v in r["steel_per_kg"].items():
        out.append({"key": f"steel_{s}", "label": f"Reinforcement {s} (supplied, cut, bent, placed)", "unit": "INR/kg", "group": "Steel",
                    "default": float(v["value"]), "status": v.get("status", "provisional")})
    out.append({"key": "formwork_m2", "label": "Formwork (contact area)", "unit": "INR/m2", "group": "Formwork",
                "default": float(r["formwork_per_m2"]["value"]), "status": r["formwork_per_m2"].get("status", "provisional")})
    cp = r["cement_price_per_kg"]
    for c in ("OPC", "PPC", "PSC"):
        out.append({"key": f"cement_{c}", "label": f"Cement {c} (concrete rates assume {cp['baseline']})", "unit": "INR/kg", "group": "Cement",
                    "default": float(cp[c]["value"]), "status": cp[c].get("status", "provisional")})
    return out


def defaults() -> dict[str, float]:
    return {i["key"]: i["default"] for i in items()}


def validate(values: dict) -> dict[str, float]:
    """Return ``values`` as floats; unknown keys, non-numbers and non-positive prices raise ValueError with a readable message."""
    known = defaults()
    out: dict[str, float] = {}
    for k, v in values.items():
        if k not in known:
            raise ValueError(f"unknown price item '{k}'. Valid items: {', '.join(known)}")
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"price '{k}' is not a number: {v!r}") from None
        if not math.isfinite(x) or x <= 0:
            raise ValueError(f"price '{k}' must be a positive number, got {v!r}")
        out[k] = x
    return out


def from_csv_text(text: str) -> dict[str, float]:
    """Parse ``item,value`` CSV text (header optional, ``#`` comments allowed); items that are missing keep their default."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    values: dict[str, float] = {}
    for row in csv.reader(lines):
        if len(row) < 2:
            raise ValueError(f"CSV line needs 'item,value': {row}")
        key, val = row[0].strip(), row[1].strip()
        if key.lower() == "item":
            continue
        values[key] = val                                         # validated below (one place for the messages)
    if not values:
        raise ValueError("the CSV has no price rows (expected lines like 'steel_Fe500,70')")
    return validate(values)


def to_csv_text(values: dict[str, float] | None = None) -> str:
    """CSV with every price item (current ``values`` or the placeholder defaults) plus label / unit / status columns."""
    vals = values or defaults()
    buf = io.StringIO()
    buf.write("# Unit prices in INR. Every default is a PLACEHOLDER (not a verified market rate): replace with current local rates.\n")
    buf.write("# Only 'item' and 'value' are read; other columns are for people.\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["item", "value", "unit", "label", "status"])
    for i in items():
        w.writerow([i["key"], vals.get(i["key"], i["default"]), i["unit"], i["label"], i["status"]])
    return buf.getvalue()
