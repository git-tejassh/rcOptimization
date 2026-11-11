# IS 456:2000 values checked against the printed code

**Date:** 2026-11-11. **Source used:** the owner's copy `is.456.2000.pdf` (BIS, IS 456:2000 with Amendment No. 1; 7 MB, kept out of git).
**How:** text extraction of the PDF for every clause, and the page *image* for Table 19 and Fig. 23 (the text layer garbles digits there). *Printed page* = the number printed on the page; PDF page = printed + 13.

**Result: every value that the code takes from IS 456 matched the printed standard. Nothing had to be changed.** The two places where the project is deliberately *more conservative* than the code are listed in section 3.

## 1. Values compared
| Item | Clause / table | Printed page | Printed value | Used in the project | Match |
|---|---|---|---|---|---|
| Design shear strength of concrete τc, 13 rows (pt 0.15 … 3.00) × M20, M25, M30, M35, M40 | Table 19 | 73 | e.g. M25: 0.29, 0.36, 0.49, 0.57, 0.64, 0.70, 0.74, 0.78, 0.82, 0.85, 0.88, 0.90, 0.92 | `table19` in `config/is456_tables.yaml` | ✔ all 65 cells (read from the page image) |
| Maximum shear stress τc,max | Table 20 | 73 | M20 2.8, M25 3.1, M30 3.5, M35 3.7, M40 4.0 | `table20` | ✔ |
| xu,max/d | Note to cl. 38.1 (Fig. 23) | 70 | Fe250 0.53, Fe415 0.48, Fe500 0.46 | `xu_max_over_d` | ✔ |
| Es | Fig. 23 | 70 | 200 000 N/mm² | `Es_MPa` | ✔ |
| Steel design curve | Fig. 23A | 70 | stress levels 0.80, 0.85, 0.90, 0.95, 0.975 fy (and fy); inelastic strains 0.0001, 0.0003, 0.0007, 0.001, 0.002; design stress fy/1.15 | `curve_stress_fraction`, `curve_inelastic_strain`, `partial_safety` 1.15 | ✔ |
| Concrete strain limits | cl. 38.1, 39.1 | 69-70 | 0.0035 in bending; 0.002 in axial compression; 0.0035 − 0.75 × (strain at least compressed fibre) | stress-block constants | ✔ |
| Minimum cement content / max w/c / min grade (reinforced concrete) | Table 5 | 20 | Mild 300 / 0.55 / M20; Moderate 300 / 0.50 / M25; Severe 320 / 0.45 / M30; Very severe 340 / 0.45 / M35; Extreme 360 / 0.40 / M40 | `exposure_requirements` in `config/design_space.yaml` | ✔ |
| Maximum cement content | cl. 8.2.4.2 | 19 | 450 kg/m³ (excluding fly ash / slag in excess) | `cement_content_kg_m3` of M40 = 450 (at the cap) | ✔ |
| Nominal cover | Table 16 | 47 | Mild 20, Moderate 30, Severe 45, Very severe 50, Extreme 75 mm | `cover_beam_mm` per exposure; project uses moderate = 30 mm | ✔ |
| Cover to column bars | cl. 26.4.2.1 | 46 | not less than 40 mm | `cover_mm.column` 40 | ✔ |
| Partial safety factors | Table 18 | 68 | 1.5 DL + 1.5 LL (collapse); 1.0 + 1.0 (serviceability) | `loads.yaml` | ✔ |
| Min / max tension steel | cl. 26.5.1.1 | 46 | As ≥ 0.85 bd / fy; As ≤ 0.04 bD | `beam_pt_max_percent` 4.0; min in `codes/beam.py` | ✔ |
| Shear reinforcement spacing / minimum | cl. 26.5.1.5-6, 40.4 | 47-48, 72 | sv ≤ 0.75 d or 300 mm; Asv / (b sv) ≥ 0.4 / (0.87 fy); fy of stirrups ≤ 415 | `min_stirrup_ratio_k` 0.4, `stirrup_fy_cap_MPa` 415 | ✔ |
| Column longitudinal steel | cl. 26.5.3.1 | 48 | 0.8 % ≤ pt ≤ 6 % (note: 6 % hard to place; 4 % recommended where bars overlap) | min 0.8, design cap 4.0, absolute 6.0 | ✔ |
| Ties | cl. 26.5.3.2 (c) + Amendment 1 | 49 | pitch ≤ least of least lateral dimension, 16 × smallest bar, 300 mm; diameter ≥ ¼ largest bar and not less than **6 mm** (amendment replaces 16 mm) | `tie_dia_min_mm` 8 (≥ 6), pitch rule in `quantities.py` | ✔ |
| Minimum eccentricity | cl. 25.4 | 42 | e ≥ l/500 + D/30, at least 20 mm | `min_eccentricity_mm` | ✔ (see 3.1) |
| Axial capacity Puz | cl. 39.6 | 71 | 0.45 fck Ac + 0.75 fy Asc | `puz_N` | ✔ |
| Biaxial interaction | cl. 39.6 | 71 | (Mux/Mux1)^αn + (Muy/Muy1)^αn ≤ 1; αn = 1.0 for Pu/Puz ≤ 0.2, 2.0 for ≥ 0.8, linear between | `alpha_n` | ✔ |
| Slender column additional moment | cl. 39.7.1 | 71 | Mux = Pu D / 2000 × (lex / D)² (and the same for y) | `codes/column.py` | ✔ |
| Moment of resistance, singly reinforced | Annex G-1.1 (b) | Annex G (end of the standard) | Mu = 0.87 fy Ast d (1 − Ast fy / (b d fck)) | `mu_singly_closed_form_Nmm` (test cross-check) | ✔ |
| Deflection limit | cl. 23.2 (a) | 37 | final deflection ≤ span / 250 | hard constraint from FE | ✔ (see 3.2) |

## 2. Not verifiable from the printed code (kept, flagged)
* **Fig. 4 / Fig. 5 span-to-depth modification factors** (cl. 23.2.1): the printed standard gives only the curves. The project uses a closed-form fit, **for a diagnostic only** (never a constraint). Owner: read two points off the printed Fig. 4 if you want to quote the diagnostic.
* **Effective length le = 1.2 × unsupported length** (a modelling choice for gravity-only frames; Annex E / Table 28 are not evaluated). See `docs/ASSUMPTIONS.md` B8.

## 3. Where the project is deliberately stricter than the code
1. **Minimum eccentricity about both axes at once.** cl. 25.4 says that for biaxial bending it is sufficient to ensure the eccentricity exceeds the minimum **about one axis at a time**; the project applies it about both axes at the same time (conservative, `docs/ASSUMPTIONS.md` F3).
2. **Deflection after partitions.** cl. 23.2 (b) also limits the deflection that occurs *after* partitions and finishes to span / 350 or 20 mm. The FE model cannot separate that part from the total, so only the total ≤ span / 250 is checked. State this in the report.
3. **Column steel cap of 4 %** instead of the code's 6 % (the code's own note recommends 4 % where bars overlap).
