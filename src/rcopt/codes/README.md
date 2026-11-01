# `codes/` — IS 456:2000 rules written as code

**Plain words:** IS 456 is the Indian standard for reinforced-concrete design. These files contain the formulas a designer would apply by hand —
"how much moment can this beam carry?", "is this column safe under load + bending?", "how far apart must stirrups be?" — and compare them with the
forces from `fe/`. Every function names its IS clause in its docstring and has a test against a value that can be derived independently
(`tests/test_is456_anchors.py`, `docs/hand_calcs/`).

> The code-table numbers (Table 19, Table 20, stress-strain curve …) were typed in from memory. They are marked **provisional** and the owner must
> check each against the printed IS 456 / SP 16 (list: `docs/ASSUMPTIONS.md` A1–A12).

| File | What it does |
|---|---|
| `is456_tables.py` | Material constants and tables read from `config/is456_tables.yaml`: concrete/steel strengths, Ec = 5000√fck, Table 19 (shear strength of concrete τc), Table 20 (maximum shear τc,max), xu,max/d, the steel design stress-strain curve, and the parabola-rectangle concrete stress block. |
| `beam.py` | **Beam checks**: bending capacity by strain compatibility (handles doubly reinforced sections), shear design (stirrup spacing from cl. 40 and 26.5.1.5-6), steel min/max limits (cl. 26.5.1.1). `check_beam_group()` returns the utilisation of bending (sagging and hogging), shear and the adopted stirrup spacing. |
| `column.py` | **Column checks**: axial-load/moment interaction curve by strain compatibility, biaxial bending formula (cl. 39.6), minimum eccentricity (cl. 25.4), slender-column additional moment (cl. 39.7), steel limits (cl. 26.5.3). `check_column()` returns the interaction ratio. Reproduces STAAD's column-81 result exactly (ratio 0.39). |
| `detailing.py` | Bar layout and fit rules: minimum clear spacing, how many layers a beam needs, how many bars go on each column face; used identically by the optimiser and the verifier. |
| `deflection.py` | IS 456 span/depth cross-check (cl. 23.2.1). Only a *diagnostic* — the hard limit used in the optimisation is the FE deflection ≤ span/250. |
| `__init__.py` | Marks the folder as a package. |
