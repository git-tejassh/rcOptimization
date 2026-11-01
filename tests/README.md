# `tests/` — the safety net (77 automatic checks, all passing)

**Plain words:** each test asks the code a question whose correct answer is known independently (a textbook formula, a hand calculation, the STAAD result,
a physical law such as "forces in equilibrium"). If someone changes the code and breaks something, a test turns red. Run them with
`.venv\Scripts\python.exe -m pytest` (≈ 35 s; `-m "not slow"` skips the heavy ones). The code-style checker is `ruff check .` (currently clean).

| File | What it proves |
|---|---|
| `test_design_space.py` | All options are IS-standard sizes/bars/grades; a design encodes and decodes back to itself; the same seed gives the same result; geometry rules reject the right designs; the config fingerprint is stable and lists the provisional items. |
| `test_is456_anchors.py` | IS 456 code checks reproduce independent values: Mu,lim/bd², Table 19/20 spot values and interpolation, the SP 16 steel curve, beam capacity vs closed formula within 1 %, column interaction, **STAAD column 81 (Pu 775.8 kN, ratio 0.39)**, minimum eccentricity, steel limits, bar layouts, hand-calculation documents. |
| `test_fe_sanity.py` | The structural model is physically right: fixed-end beam moments wL²/12 and wL²/24 end-to-end through OpenSees, yield-line load totals, equilibrium (reactions = loads), symmetry, dead-load total 17,580 kN, results do not depend on reinforcement, bigger members lower the utilisation, every design yields one status row. |
| `test_benchmark.py` | The model matches the owner's STAAD results within tolerance (reactions, displacements, column forces/moments); the STAAD parser agrees with `config/geometry.yaml` and `loads.yaml`. *Skipped if the STAAD binaries are not on the machine.* |
| `test_sampling.py` | Latin-hypercube is stratified per gene, reproducible by seed, the biased sampler rejects undersized designs, no physically impossible rows in the design matrix. |
| `test_optimize.py` | Hypervolume has the right known value, spacing metric, the repair operator keeps genomes integer and buildable, evaluators memoise and count FE solves, a tiny NSGA-II run works, cost/carbon scenarios scale correctly. |
| `test_api.py` | Server smoke tests: `/health`, input validation, exact-FE and cost-carbon endpoints, surrogate close to truth (skipped without models), results endpoints, **strength review passes the sample frame and fails an undersized-column frame**. |

Not covered by automatic tests: the website (it is checked by building it, `npm run build`, and by hand in a browser).
