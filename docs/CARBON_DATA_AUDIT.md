# Carbon data audit (Indian-context availability of embodied-carbon factors)

Scope: A1-A4 of frame materials (concrete, reinforcement). **No value in `config/carbon_factors.yaml` is verified**; this audit records what
could be found (web search, secondary sources only; the ICE spreadsheet and Indian EPDs themselves were not opened) and what was assumed.
Everything stays `status: provisional`. The gap itself is a finding (Brief s4).

| Factor | Used (provisional) | What a quick search found (secondary, unverified) | India-specific? | Confidence | Gap / action for the owner |
|---|---|---|---|---|---|
| Cement OPC | 0.91 kgCO2e/kg | 0.91 (generic OPC, ICE-type); an Indian EPD-derived coefficient quoted as 0.996 | partly (0.996 is Indian) | medium | Obtain a current Indian OPC 43/53 EPD (e.g. UltraTech, ACC, Ambuja) |
| Cement PPC | 0.65 (assumed) | 0.71 quoted for Indian PPC | partly | low | Replace 0.65 by an EPD value; PPC is the common cement in Bhopal practice, so the OPC default is conservative |
| Cement content per grade | 330 / 360 / 390 / 420 / 450 kg/m3 (M20-M40) | none found | no | low | Use the mix designs of the ready-mix plant that will supply (IS 10262:2019) |
| Other concrete constituents | 12 kgCO2e/m3 | none found | no | low | Aggregates, admixture, batching energy |
| Concrete (resulting) | ~ 310-370 kgCO2e/m3 for M20-M40 | ICE v3 generic concrete about 0.10-0.16 kgCO2e/kg, i.e. ~ 250-390 kgCO2e/m3 at 2400 kg/m3 | no | low | Our M30 (about 367 kg/m3) lies above ICE C30/37 (about 247 kg/m3); the difference is the cement content assumption: this is the single biggest driver of the concrete term |
| Reinforcement | 1.8 kgCO2e/kg | search results span 0.43-2.46 kgCO2e/kg (EAF scrap 0.45, world-average 1.55, virgin BF-BOF 2.46; one source quotes 0.53-0.68 for rebar) | no | low | India's rebar mix (BF-BOF integrated, DRI + induction furnace, EAF) has no verified factor here; obtain mill EPDs (e.g. JSW, SAIL, Tata) |
| A4 transport | 30 km concrete, 500 km steel, 0.11 kgCO2e/(t km) | none found | no | low | Replace with actual distances |
| Formwork carbon | excluded | n/a | n/a | n/a | Out of scope, flagged |

## Consequences
* The cost-vs-carbon **shape** depends on the ratio steel-carbon : cement-carbon and on cement content per grade; the +/-20 % sensitivity study
  (`data/results/sensitivity.json`, dashboard page "Sensitivity") shows how much of the front survives, but it does not cover a 2x error such as the
  steel range above or a different cement content.
* Absolute kgCO2e must not be quoted from this project until the factors are replaced and `status: sourced` is set.

Sources consulted (secondary): [Climatiq rebar emission factor](https://www.climatiq.io/data/emission-factor/5cd03b14-6840-47e2-af28-4f363a4a856d);
[CIDB embodied carbon inventory template](https://www.cidb.gov.my/wp-content/uploads/2022/11/V4_EMBODIED-CARBON-INVENTORY-TEMPLATE-final-1.pdf);
[ASBP: updating the ICE database (v3.0)](https://asbp.org.uk/wp-content/uploads/2018/07/ASBP-TGR-01.11.18-Craig-Jones.pdf);
[SteelConstruction.info LCA data](https://www.steelconstruction.info/Life_cycle_assessment_and_embodied_carbon).
