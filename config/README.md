# `config/` — every setting of the project (change a number here, re-run, done)

**Plain words:** no price, load, size option or algorithm setting is written inside the code. They are all in these text (YAML) files, so the guide or a
teammate can change a value and re-run the pipeline without programming. A value marked `status: provisional` is a placeholder nobody has verified —
it triggers the yellow "PROVISIONAL DATA" warnings on the website and in the report. Replacing provisional values with real ones is mostly the **team's job** (see the to-do list in the main README).

| File | What it controls |
|---|---|
| `geometry.yaml` | Building frame: bay widths (4 × 5 m in x, 3 × 5 m in z), storey heights (4 × 3 m), 1 m stub columns, and the optimisation groups (beam levels {0,1,2} / {3,4}; column storeys {0,1} / {2,3}). Taken from the owner's STAAD model; a test proves they match. |
| `loads.yaml` | Gravity loads: RC unit weight 25 kN/m³, slab 150 mm + finishes, live loads (2.0 kN/m², roof 1.5), brick-wall loads (they follow the beam depth), load factors (1.5 for strength, 1.0 for service). |
| `design_space.yaml` | All the choices an optimiser may pick: beam widths/depths, column sizes, bar diameters/counts, concrete grades (M25–M40, limited by IS 456 Table 5 for moderate exposure), steel grades (Fe415/Fe500), **cement type (OPC/PPC/PSC)**, cover, steel-percentage limits, repair on/off. |
| `is456_tables.yaml` | IS 456 numbers: concrete/steel strengths, Table 19 and 20 shear values, stress-strain curve. **Checked against the printed code on 2026-11-11 (`status: sourced`, record in `docs/IS456_VERIFICATION.md`).** |
| `solver.yaml` | Analysis settings: cracked-section factors (beams 0.35, columns 0.70), Ec = 5000√fck, shear deformation on/off, equilibrium tolerance, number of parallel workers, and the STAAD-benchmark mode values. |
| `cost_rates.yaml` | Prices in ₹: concrete per m³ by grade, steel per kg, formwork per m², cement prices per kg by type. **All placeholders** — replace them with current Bhopal rates (Essco list / MP PWD SOR / CPWD DSR) here, or try your own rates without editing files on the dashboard tab "Optimise with my prices". |
| `carbon_factors.yaml` | Embodied-carbon factors: cement (OPC 0.92, PPC 0.507, PSC 0.312 kgCO₂e/kg, Indian secondary sources), steel 2.5 kgCO₂e/kg, cement content per grade, other constituents, transport. |
| `prices_template.csv` | The same unit prices as a CSV (`item,value`), every one marked as a placeholder. Copy it, edit the numbers, then run `python -m rcopt.cli reoptimize --prices my_prices.csv` (or load it on the dashboard tab "Optimise with my prices"). Re-create it with `python -m rcopt.cli prices-template`. |
| `quantities.yaml` | How materials are counted: lap lengths, hook lengths, formwork rules, column-tie pitch. |
| `sampling.yaml` | Dataset: 15,000 designs, 40 % feasibility-biased, seed 42. |
| `surrogate.yaml` | Machine learning: 20 % hold-out, 5-fold cross-validation, "near the boundary" band 0.85–1.15, 500 active-learning designs, XGBoost parameters, ensemble size 5. |
| `optimize.yaml` | NSGA-II: population 200, 300 generations, seeds 1–5, safety-margin rule, direct-FE budget, ±20 % sensitivity. |
| `verify.yaml` | Verification: 30 designs per front, 5 boundary picks, tolerances (0.05 / 5 %), pass target 90 %. |
