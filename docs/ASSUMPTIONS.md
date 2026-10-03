# ASSUMPTIONS and provisional values

Every unverified value or modelling choice in the pipeline. **"Owner must verify"** = I could not check it against a
primary source offline; check it against your own copy before the report goes to the guide.

Legend: status `provisional` = not verified; `chosen` = a modelling decision (reversible, in a YAML); `sourced` = verified.

## A. IS 456:2000 tables and constants (`config/is456_tables.yaml`) - ALL transcribed from memory

| # | Item | Value used | Clause | Status | Owner must verify |
|---|---|---|---|---|---|
| A1 | Table 19 tau_c (pt vs grade, M20-M40) | 13-row table in YAML | Table 19 | provisional | YES - every cell (two cells anchored by tests: M20 pt 0.5 -> 0.48, pt 1.0 -> 0.62) |
| A2 | Table 20 tau_c,max | M20 2.8, M25 3.1, M30 3.5, M35 3.7, M40 4.0 | Table 20 | provisional | YES (anchored by tests) |
| A3 | xu,max/d | Fe415 0.48, Fe500 0.46 | cl. 38.1 note | provisional | YES (SP 16 tabulates Fe500 with a slightly different 0.456-based value) |
| A4 | Steel design stress-strain curve (6 points, 0.80-1.00 fyd; inelastic strain 0, 1e-4, 3e-4, 7e-4, 1e-3, 2e-3) | YAML | Fig. 23 / SP 16 | provisional | YES - checked internally against SP 16 total strains 0.00144 ... 0.00380 (Fe415), 0.00174 ... 0.00417 (Fe500) |
| A5 | Concrete stress block 0.446 fck, strain 0.002/0.0035, pivot 3D/7 | code | cl. 38.1 | provisional | YES |
| A6 | Ec = 5000 sqrt(fck) | solver.yaml | cl. 6.2.3.1 | provisional | no (well known) |
| A7 | Min tension steel 0.85 bd/fy; max 4 % bD | design_space.yaml | cl. 26.5.1.1 | provisional | YES |
| A8 | Shear: stirrup fy capped at 415; min Asv/(b sv) >= 0.4/(0.87 fy); sv <= min(0.75 d, 300) | code | cl. 26.5.1.5-6, 40.4 | provisional | YES |
| A9 | Column: Puz = 0.45 fck Ac + 0.75 fy Asc; alpha_n 1.0 -> 2.0 over Pu/Puz 0.2 -> 0.8; emin = max(l/500 + D/30, 20) | code | cl. 39.6, 25.4 | provisional | YES (Puz and alpha_n reproduce STAAD's column-81 result exactly: IR 0.39) |
| A10 | Column steel 0.8 % <= pt <= 4 % (code max 6 %; 4 % is a lap-practicality cap), clear spacing <= 300 mm | design_space.yaml | cl. 26.5.3.1 | provisional | YES |
| A11 | Slender-column additional moment (cl. 39.7.1) with Pb from the strain-compatibility curve | code | cl. 39.7 | provisional | YES |
| A12 | Span/depth basic ratios 20/26/7 and modification factor Fig. 4 approximated by 1/(0.225 + 0.00322 fs - 0.625 log10 pt) <= 2 (BS 8110-type fit of the Fig. 4 curves) | code | cl. 23.2.1 | provisional | YES - used only as a *diagnostic*, never as a hard constraint |

## B. Loads and structural-model choices (`config/loads.yaml`, `config/solver.yaml`)

| # | Item | Choice | Status | Note |
|---|---|---|---|---|
| B1 | Geometry, sections, floor/wall/live loads | Taken from `G+3 RCC FINAL.STD` | sourced (owner's model) | wall loads re-derived: 0.23 x (3.0 - 0.45) x 20 = 11.73 kN/m, i.e. they follow beam depth in the optimiser |
| B2 | RC unit weight | 25 kN/m3 (IS 875-1) | chosen | STAAD default 23.56 used only in benchmark mode |
| B3 | Slab | 150 mm, not optimised, its self-weight is inside the floor load (3.75 + finish 1.0 / 1.5 roof) | chosen (back-derived from STAAD 4.75/5.25) | slab design and quantities excluded and stated |
| B4 | Slab-to-beam load transfer | two-way yield-line triangles/trapezoids (as STAAD floor load) | chosen | DECISIONS D-011 |
| B5 | Live-load pattern | ignored (LL <= 3/4 DL, IS 456 cl. 22.4.1) | chosen | one analysis scaled 1.5 for strength |
| B6 | Cracked stiffness | beams 0.35 Ig, columns 0.70 Ig for strength AND service | chosen | 0.35 Ig is ~2.9x the gross deflection, comparable to (1 + creep coefficient 1.6) = 2.6, so no separate long-term multiplier (`long_term_factor: 1.0`) |
| B7 | Design sections | member end (centre-line) moments and shears, no reduction to support face | chosen | conservative |
| B8 | Column effective length | le = 1.2 x unsupported length (gravity-only, unbraced-type conservative) | chosen | IS 456 Annex E not evaluated explicitly |
| B9 | Exposure / cover | moderate: beams 30 mm, columns 40 mm | chosen | Table 16 mild would allow 20 mm |
| B10 | Torsion, shear deformation, P-delta, foundation flexibility | ignored | chosen | STAAD includes shear deformation; wall eccentricity torsion ignored in the optimiser, included in benchmark mode |
| B11 | Beams modelled as rectangular (no T-flange action), uniform reinforcement over the span (no curtailment) | | chosen | conservative |

## C. Cost rates (`config/cost_rates.yaml`) - ALL PROVISIONAL

No verified rate was available offline. Values are the chat examples in `legacy/context.txt` plus +/-500 INR/m3 extrapolation (M20, M40) and a placeholder
Fe415 = Fe500 - 2 INR/kg. **Owner: replace with current Bhopal prices (Essco price list / MP PWD SOR / CPWD DSR).**
Cost *level* is not meaningful until you do; the Pareto *shape* depends on the ratios (steel/concrete) so run the sensitivity page.

## D. Embodied-carbon factors (`config/carbon_factors.yaml`) - ALL PROVISIONAL

OPC 0.91 kgCO2e/kg (approx. ICE v3.0 CEM I), PPC 0.65 (assumed), concrete = cement content (330-450 kg/m3 by grade, typical mixes) x cement factor + 12 kgCO2e/m3 other
+ A4 transport; steel 1.8 kgCO2e/kg (chat example; India's BF-BOF / EAF / DRI-induction mix NOT reflected); A4 distances assumed (30 km concrete, 500 km steel).
Formwork carbon excluded. Details and gaps: `docs/CARBON_DATA_AUDIT.md`.

## E. STAAD benchmark gaps (see `docs/BENCHMARK.md`)

Filled in after P0b.
