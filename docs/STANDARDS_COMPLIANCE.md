# Standards compliance of the designs (what is enforced, what is not)

All designs are built only from IS-standard options and checked against IS 456:2000 for **gravity loading**. Table transcriptions are from memory
and still need the owner's check against the printed code (`docs/ASSUMPTIONS.md` A1-A12). "Enforced" = every reported design satisfies it.

## Enforced
| Item | Standard / clause | How |
|---|---|---|
| Concrete grades | IS 456 Table 2 (M20-M40) and **Table 5 minimum grade for the exposure** (moderate: M25) | grade options filtered by exposure (D-022) |
| Cover | Table 16 (moderate: 30 mm beams) and cl. 26.4.2.1 (columns 40 mm) | `design_space.yaml` |
| Bar diameters | IS 1786 standard sizes (12, 16, 20, 25, 32 mm) | option lists; tested |
| Steel grades | Fe415, Fe500 (IS 1786) | option lists (Fe500D ductility class not distinguished) |
| Cement types | OPC (IS 269), PPC (IS 1489 Part 1), PSC (IS 455), all permitted by IS 456 cl. 5.1 | option list; the Table 5 minimum cement content is met by the assumed mixes. Strength gain of PPC / PSC (28-day grade is what IS 456 designs for) and striking times are not modelled |
| Loads | IS 875 Part 1 (RC 25 kN/m3, masonry 20 kN/m3), Part 2 (residential 2.0, roof 1.5 kN/m2) | `loads.yaml` |
| Load combination | Table 18 / cl. 36.4: 1.5 (DL + LL) strength, 1.0 (DL + LL) service | `loads.yaml` |
| Beam flexure | cl. 38.1, Annex G (xu <= xu,max, doubly reinforced by strain compatibility) | `codes/beam.py` |
| Beam shear | cl. 40, Tables 19-20, cl. 26.5.1.5-6 (max spacing, minimum stirrups, fy <= 415 for stirrups) | `codes/beam.py` |
| Beam steel limits | cl. 26.5.1.1: 0.85 bd/fy <= Ast <= 4 % bD | constraint |
| Bar spacing / layers | cl. 26.3.2 minimum clear spacing; at most 2 layers | repair + check |
| Column strength | cl. 39.6 biaxial interaction (P-M by strain compatibility), cl. 25.4 minimum eccentricity, cl. 39.7 slender columns, slenderness <= 60 | `codes/column.py` |
| Column steel | cl. 26.5.3.1: min 4 bars (12 mm min), 0.8 % <= pt <= 4 % (design cap; 6 % absolute), spacing <= 300 mm | repair + constraint |
| Ties | cl. 26.5.3.2: dia >= max(bar/4, 6), pitch <= min(b, 16 phi, 300) | `quantities.py` (ties are sized, not a variable) |
| Deflection | cl. 23.2 (a): <= L/250 from the FE analysis | hard constraint; span/depth (Fig. 4/5 fit) reported as a diagnostic |
| Beam width <= column width | practice | repair |

## Not implemented (limits of this study; do not claim otherwise)
* Seismic design and ductile detailing (IS 1893, IS 13920), wind (IS 875-3): gravity only.
* Development length / anchorage and lap checks (cl. 26.2): only a lap allowance in the quantities; no curtailment, bars run the full span.
* Crack-width / bar-spacing limit for crack control (cl. 26.3.3, Table 15) and the effective-flange (T-beam) action: not checked / ignored (conservative for flexure).
* Torsion (cl. 41), pattern live loading (cl. 22.4.1 allows ignoring it when LL <= 3/4 DL, as here), foundations, slab design.
* Durability items other than the minimum grade: minimum cement content and maximum water/cement ratio (Table 5) are recorded in `design_space.yaml` and the assumed mix cement contents satisfy the cement minimum; w/c is not modelled.
* Fire resistance covers (Table 16A), member-specific minimum dimensions of IS 13920.

## Does the repair (snapping) add error?
No evaluation error: both the FE ground truth and the surrogates always evaluate and report the *repaired* design, which is itself an IS-standard discrete design.
What it does change is the search space: many genomes map to one design, so (a) the LHS stratification is exact over genes but only approximately uniform over designs, and
(b) the GA has plateaus (a mutation that is repaired away does nothing). Both are efficiency effects, not correctness effects; the repair rules are listed in `rcopt/design/repair.py` and tested for idempotence and buildability.
