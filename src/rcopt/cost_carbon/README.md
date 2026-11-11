# `cost_carbon/` — quantities, price and embodied carbon

**Plain words:** from a design we count how much concrete (m³), reinforcement steel (kg) and formwork (m²) the frame needs, then multiply by prices (INR)
and by carbon factors (kg CO₂-equivalent per kg or m³). Those two numbers are the two things the optimiser tries to reduce.

> All prices, the cement content per grade, transport distances and the "other constituents" carbon are **provisional** placeholders. Cement and steel
> carbon factors are Indian *secondary-source* values (PPC 0.507, OPC 0.92, PSC 0.312, rebar 2.5 kgCO₂e/kg) — not product EPDs. Sources: `docs/CARBON_DATA_AUDIT.md`.
> The absolute ₹ and kg figures are therefore indicative; the *ranking* of designs is more trustworthy than the totals.

| File | What it does |
|---|---|
| `quantities.py` | Counts concrete, steel and formwork. Rules: beams run clear between columns, columns take full height (joint counted once), slab excluded, lap/anchorage allowance, stirrups at the *designed* spacing, column ties around the perimeter (no cross-ties — flagged). Rules are in `config/quantities.yaml`. |
| `cost.py` | (Prices can be overridden per run via `scenario`, see `prices.py`.) Cost in INR = concrete + steel + formwork, and an adjustment for the cement type (concrete rates assume PPC; OPC/PSC pay the price difference × cement content). Rates from `config/cost_rates.yaml`. |
| `carbon.py` | Embodied carbon A1–A4 (cradle to site): concrete (cement content × cement factor + other constituents), steel, transport. Formwork carbon excluded (flagged). `recompute_dataset_objectives()` re-prices stored designs without re-running FE. |
| `prices.py` | **Editable unit prices.** Lists every price (concrete per grade, steel per grade, formwork, cement per type) with its placeholder default, reads/writes the CSV form (`item,value`), and validates input (unknown item, non-number, zero/negative price are rejected with a clear message). Used by `rcopt reoptimize`, the API and the template `config/prices_template.csv`. |
| `scenario.py` | A switch used by the sensitivity study: temporarily scale steel cost, cement carbon or steel carbon by ±20 % for every calculation in the process. |
| `sensitivity.py` | Re-runs the best optimisation under the ±20 % scenarios and reports how much the best designs move (result: not fully robust; optimum shifts ≤ 4.9 %). Output `data/results/sensitivity.json`. |
| `cement_tradeoff.py` | Cement-type study: because cement changes cost and carbon but not the structure, every truly feasible design is paired with every cement type and the price premium of low-carbon cement (PSC) is scanned to show when a real cost-vs-carbon trade-off appears. Output `data/results/cement_tradeoff.json`. |
| `__init__.py` | Marks the folder as a package. |

The website tab "My design estimate" repeats these formulas in TypeScript (`web/src/lib/estimate.ts`) so users can edit prices in the browser.
