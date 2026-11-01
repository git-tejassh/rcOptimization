# `design/` — what a "design" is, and which designs are allowed

**Plain words:** one *design* is a list of 23 whole numbers (called *genes*): for each of 2 beam groups the width, depth and the bottom/top steel bars;
for each of 2 column groups the width, depth and the bars; plus the concrete grade (M25–M40), the steel grade (Fe415/Fe500) and the cement
type (OPC/PPC/PSC). Every number is an *index* into a list of real, standard choices in `config/design_space.yaml` — so the optimiser can never invent a
300.7 mm beam or a 13 mm bar. This folder translates between the list of numbers and a real design, throws out or repairs impossible designs, and
decides whether a design passes.

| File | What it does |
|---|---|
| `variables.py` | The dictionary of choices. `DesignSpace` knows every option list; `decode()` turns the 23 numbers into a `Design` (beam sizes, bar diameters/counts, grades, cement); `encode()` does the reverse; `physical()` gives real values (mm, MPa). `size_key` is a short label of "only the sizes + concrete grade", because the structural analysis does not depend on steel bars — so results are re-used (cached) between designs with the same sizes. |
| `geometric_feasibility.py` | Checks whether a design can physically be built *before* any analysis: column depth ≥ width, beam not wider than the column, bars fit inside the section with legal spacing (IS 456 cl. 26.3.2), at most 2 layers of bars, tie size rule. Returns the reason codes if not. |
| `repair.py` | **"Snap to the nearest buildable design"** (decision D-012). About 96.6 % of random designs are not buildable, so instead of wasting them, deterministic rules fix them (swap width/depth, pick the closest bar layout that fits, shrink the beam to the column…). The result is always a real, standard design — never a made-up in-between value. |
| `constraints.py` | The **referee**. `evaluate_from_demands()` takes the forces on the members, runs all IS 456 checks, computes cost and carbon, and returns a pass/fail "constraint vector" (7 numbers; ≤ 0 means OK): deflection, beam bending, beam shear, column interaction, beam steel limits, column steel limits, geometry. Used for the truth, for Surrogate B and for the API, so all three judge identically. |
| `describe.py` | Turns one design into a human-readable, JSON-friendly description (sizes, bars, grades, quantities, cost/carbon breakdown, utilisations). Feeds the website's design cards and the API. |
| `__init__.py` | Marks the folder as a package. |

**Words used:** *utilisation ratio* = demand ÷ capacity (1.0 = exactly at the limit, above 1.0 = fails). *Feasible* = every ratio ≤ 1 and the design is buildable.
