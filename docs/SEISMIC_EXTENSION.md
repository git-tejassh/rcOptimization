# Seismic extension (Phase 6: stub only, nothing claimed)

This project checks **gravity loading only** (1.5 (DL + LL), IS 456:2000). A building in India must also be designed for
seismic loading (IS 1893 (Part 1):2016) and, where applicable, wind (IS 875-3). Bhopal lies in a low-seismicity zone, but
code-mandated seismic design and ductile detailing still apply; confirm the zone from IS 1893 (Part 1):2016.

`src/rcopt/seismic/__init__.py` contains interfaces (`SeismicSpec`, base-shear, load combinations, ductile detailing) that raise
`NotImplementedError`. No seismic result is produced anywhere in the pipeline, report or dashboard.

## What would change
| Area | Change |
|---|---|
| Loads | Equivalent-static (or response-spectrum) lateral loads from IS 1893:2016: Vb = Ah W, Ah = (Z/2)(I/R)(Sa/g); the STAAD model already carries `DEFINE IS1893 2016` (ZONE 0.1, RF 5, SS = 1, ST = 1, DM 0.05) which gives the owner's base shear (VB = 339.3 kN, T = 0.513 s in the `.ANL`). |
| Combinations | 1.2 (DL + LL +/- EL), 1.5 (DL +/- EL), 0.9 DL +/- 1.5 EL (IS 456 Table 18); both horizontal directions |
| Analysis | Same OpenSees frame, lateral load cases; P-delta and torsion; storey drift <= 0.004 h (IS 1893 cl. 7.11.1.1) |
| Member checks | Columns become governed by Pu-Mx-My under lateral cases; beams get reversal moments (top and bottom steel both matter) |
| Detailing (IS 13920:2016) | Strong-column / weak-beam (sum Mc >= 1.4 sum Mb), minimum steel ratios, confinement ties in plastic hinge zones, shear design from capacity moments, minimum member sizes (b >= 200 mm, b/D >= 0.3 for beams; 300 mm columns) |
| Design space | Larger sections / more steel; cost and carbon rise; the Pareto front would move and probably widen (steel quantity vs concrete) |
| Surrogates | FE responses grow from ~1 to ~5 load cases per design; surrogate B's demand vector grows accordingly; the 4-critical-triples approximation must be revisited |

## Evidence the owner can use now
The STAAD `.ANL` already shows that 57 of the 133 columns are governed by the seismic load cases (guiding case 12-19), i.e. the gravity-only
optimum is **not** a code-compliant design of the owner's building.
