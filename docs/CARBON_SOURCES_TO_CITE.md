# Carbon numbers: which standards and sources to cite (hand-off for the team)

**Short answer.** No Indian Standard (IS code) publishes embodied-carbon factors. IS codes define the *materials and the mix* (what to count); the carbon *numbers* must come from product **EPDs** (Environmental Product Declarations, made under ISO 14025 / EN 15804) or a published Indian database. Below: what to cite for each input in `config/carbon_factors.yaml`, in the order of how much it moves the result. Search date: 2026-11-11; items marked **not verified** were visible only as search snippets.

## 1. IS codes to cite (these define the material, not its carbon)
| What | Cite | Used in this project for |
|---|---|---|
| Reinforced concrete design, min cement content / max water-cement ratio / min grade by exposure | **IS 456:2000, Table 5** and cl. 8.2.4.2 (cement content not above 450 kg/m³): *checked in your PDF* (`docs/IS456_VERIFICATION.md`) | exposure rules, M40 cement content = 450 |
| Concrete mix proportioning (how cement content per m³ is computed from water content and w/c ratio) | **IS 10262:2019** | `cement_content_kg_m3` per grade. Method: cement = water content ÷ (w/c ratio), then check ≥ the Table 5 minimum and ≤ 450 kg/m³. Typical worked M25 results quoted in secondary sources are 372–413 kg/m³ (not verified against the standard) |
| Ordinary Portland Cement | **IS 269:2015** | cement type OPC |
| Portland Pozzolana Cement (fly-ash based) | **IS 1489 (Part 1):2015** | cement type PPC |
| Portland Slag Cement | **IS 455:2015** | cement type PSC |
| Reinforcement bars (Fe415, Fe500, Fe500D …) | **IS 1786:2008** | steel grade and the steel carbon factor |
| Aggregates | IS 383:2016 | not used (the "other constituents" term) |

## 2. Standards for the method of the carbon number (cite once in the report)
* **ISO 14040 / ISO 14044**: life-cycle assessment principles and requirements.
* **ISO 14025** and **EN 15804:2012+A2:2019**: how an EPD is made; modules **A1–A3** (raw material, transport to factory, manufacture) = the "cradle-to-gate" figure this project uses; **A4** = transport to site (also used here).
* **EN 16908**: product category rules for cement (cited by the Indian cement EPD below).

## 3. Where to get the numbers, per input
| Input in `carbon_factors.yaml` | Current value (status) | Best source to replace it with | How to cite |
|---|---|---|---|
| Cement GWP A1–A3 (OPC, PPC, PSC) | 0.92 / 0.507 / 0.312 kgCO₂e/kg (secondary source) | **UltraTech Cement EPD** covering OPC, PPC, PSC (and PCC): ISO 14025 + EN 15804:2012+A2:2019 + EN 16908, valid to 2027-08-01, in the EPD International library (environdec.com). *The per-product GWP table was not readable in my search: open the PDF.* Alternative: **IIT Madras primary LCI of Indian cement plants** (Mendeley Data, "Primary Life Cycle Inventory Data for Cement Production – Indian Cases"). | "UltraTech Cement Ltd., EPD of OPC / PPC / PSC, registered at EPD International, valid to 2027-08-01" |
| Concrete (if you prefer a ready-mix value per m³ instead of cement content × factor) | not used | **JSW Cement ready-mix concrete EPD** (India, reference period Apr 2021 – Mar 2022, ISO 14025 / EN 15804) | EPD number from environdec.com |
| Reinforcement steel | 2.5 kgCO₂e/kg (secondary source) | **EPD of the mill that supplies your TMT bar** (Tata Steel, JSW, SAIL and others publish them; I did not find one in my search: check each mill's website and environdec.com). Fallback: an India-specific database below | mill EPD number, or database + table |
| India-specific database | – | **India Construction Materials Database of Embodied Energy and Global Warming Potential**, IFC / thinkstep, v1.0, 30 Nov 2017 (Eco-cities in India programme). Copies I found are marked DRAFT / "not for public distribution": **get the official version** before citing; numbers not read | "IFC (2017), India Construction Materials Database …, version 1.0" |
| Generic fallback | – | ICE Database (University of Bath) or Ökobaudat, which Indian studies use when nothing local exists | database version and table |
| Transport A4 (30 km concrete, 500 km steel, 0.11 kgCO₂e per tonne-km) | placeholder | Any published fuel-based freight factor for road transport (India GHG Program, DEFRA, GLEC) matched to your real distances; no IS code | publication and year |

## 4. Warning: published Indian cement factors disagree
A Lodha Group sustainability note quotes **0.996 kgCO₂e/kg for OPC and 0.71 for PPC** (citing an EPD; **not verified**), against our **0.92 and 0.507** (Indian blended-cement study via CEEW/GCCA). A 40 % spread on PPC changes the carbon axis noticeably. **Pick one source for all three cements, use its numbers together (same system boundary), and write the reference next to them.** Do not mix cement values from different sources.

## 5. What to do, step by step
1. Choose the sources above (cement: EPD of the cement brand you assume; steel: your supplier's mill EPD).
2. Edit `config/carbon_factors.yaml`: the `value`, a short `source:` text, `confidence`, and set `status: sourced` (or `secondary_source`). Also revise `cement_content_kg_m3` per grade using IS 10262:2019 and Table 5.
3. Re-run from the optimisation onwards (the FE data and trained models do **not** need to be redone, because only prices and carbon changed): `python -m rcopt.cli all` (a few minutes for phases 0–3 because they are cached, about an hour for phases 4–5).
4. Rebuild the website: `cd web; npm run build`.

## 6. Sources used for this note
* Search results on India embodied-carbon data and the lack of an India-specific database: [SACE 2025 proceedings paper](https://www.atlantis-press.com/proceedings/sace-25/126020489), [IFC India Construction Materials Database (methodology report copy)](https://edgebuildings.com/ifc-india-construction-materials-database-methodology-report/).
* [IIT Madras primary LCI data for Indian cement](https://data.mendeley.com/datasets/hk9yfsdhh9).
* UltraTech cement EPD (OPC, PPC, PSC, PCC) and JSW Cement ready-mix EPD, listed in the EPD International library: [environdec.com](https://www.environdec.com/library).
* Mix-design content summaries (secondary, not the standard text): [infralens IS 10262:2019](https://infralens.in/code/IS-10262-2019).
