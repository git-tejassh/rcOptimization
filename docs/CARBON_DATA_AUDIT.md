# Carbon data audit (Indian-context availability of embodied-carbon factors)

Scope: A1-A4 of frame materials (concrete, reinforcement). Updated 2026-10-04: the cement and steel factors were replaced by **Indian secondary-source values**
(web research; the ICE spreadsheet and manufacturer EPDs themselves were NOT opened, so these are `status: secondary_source`, not `sourced`). Cement content per grade, the other
concrete constituents and A4 transport are still `provisional`. The gap itself is a finding (Brief s4).

| Factor | Used | Source found (secondary) | India-specific? | Confidence | Gap / action for the owner |
|---|---|---|---|---|---|
| Cement PPC (default) | **0.507 kgCO2e/kg** | India PPC about 507 kg CO2/t cement, i.e. 31 % below OPC ([Indian OPC / blended-cement study](https://www.researchgate.net/publication/376684607_Study_on_energy_use_and_carbon_emission_from_manufacturing_of_OPC_and_blended_cements_in_India), reported via [CEEW](https://www.ceew.in/publications/how-can-india-decarbonise-for-net-zero-cement-industry)) | yes | medium | Replace by the EPD of the cement actually delivered (UltraTech / ACC / Ambuja ...) |
| Cement OPC | 0.92 kgCO2e/kg | India OPC 893-940 kg CO2/t cement over five zones (same study; mid-value) | yes | medium | as above |
| Indian cement-industry average (cross-check) | not used | 0.617-0.68 t CO2/t cement (2020-21), [NITI Aayog cement roadmap](https://niti.gov.in/sites/default/files/2026-01/Roadmap_for_Cement_Sector_Decarbonaisation.pdf) | yes | medium | PPC 0.507 and OPC 0.92 bracket this average, as expected for a blended-cement market |
| Reinforcement (Fe415 = Fe500) | **2.5 kgCO2e/kg** | India steel sector 2.55 tCO2/t crude steel ([CEEW](https://www.ceew.in/publications/how-can-india-decarbonise-for-net-zero-steel-industry)); major producers 2.53 and other producers 2.02 tCO2/t in 2023-24; electric-furnace TMT "over 2" ([Lodha](https://www.lodhagroup.com/blogs/sustainability/rebar-opportunity-decarbonising-backbone-of-india-construction)); scrap-EAF green TMT 0.592 (EPD) | yes | medium | The route (BF-BOF / DRI + induction / scrap-EAF) decides; 2.5 is the Indian average, not the factor of the mill you buy from. Obtain mill EPDs |
| Cement content per grade | 360 / 390 / 420 / 450 kg/m3 (M25-M40) | none found | no | low | Use the ready-mix plant's IS 10262 mix design; this is the main driver of the concrete term |
| Other concrete constituents | 12 kgCO2e/m3 | none found | no | low | aggregates, admixture, batching |
| Resulting concrete (M30, PPC) | about 195 kgCO2e/m3 | consistent with typical Indian ready-mix values quoted at roughly 200-300 kgCO2e/m3 (not verified) | partly | low | |
| A4 transport | 30 km concrete, 500 km steel, 0.11 kgCO2e/(t km) | none found | no | low | actual distances |
| Formwork carbon | excluded | n/a | n/a | n/a | out of scope, flagged |

## Consequences
* With these factors reinforcement carries about 0.036 kgCO2e per INR (2.5 per INR 70) and concrete only about 0.03 kgCO2e per INR (about 195 kgCO2e/m3 for INR 6000/m3, before formwork cost), so carbon is steel-dominated while cost is spread over concrete, formwork and steel. That mismatch is the realistic source of any cost-carbon trade-off (more concrete to save steel). `docs/REPORT_DRAFT.md` reports what the optimiser actually found.
* The cost rates remain provisional placeholders: the width of the front depends on the ratio of cost to carbon per material, so replacing the cost rates can change it as much as the carbon factors.
* Absolute kgCO2e must not be quoted as final until cement content, transport and the actual supplier EPDs replace the remaining assumptions.
