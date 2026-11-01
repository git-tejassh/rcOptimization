# `review/` — check and reinforce a user's own STAAD frame

**Plain words:** this powers the website tab "My design estimate → Strength review". A user uploads a STAAD `.std` file; this code recognises a regular grid
frame, analyses it for gravity loads with the same OpenSees model, and then designs the **cheapest standard reinforcement** that satisfies IS 456 for
every group of beams and columns. The answer is PASS or FAIL with reasons, and the *designed* steel quantity replaces the assumed steel in the cost/carbon estimate.

| File | What it does |
|---|---|
| `frame_review.py` | `review_staad()` does the whole job: `derive_frame()` checks the file is a complete regular grid (columns at every grid node, beams on every grid line, one section per level/storey) or raises a readable `ReviewError`; `design_beam_group()` and `design_column_group()` search bar arrangements (least steel first) that pass bending, shear, steel limits, column interaction; the report includes demands, utilisations, deflection and the list of limits of the review. |
| `__init__.py` | One-line package description. |

**Limits (stated in every report):** gravity loads only (project IS 875 defaults, not the STAAD load cases), regular rectangular grid frames only, no
detailing checks (development length, curtailment, torsion), no seismic. Exposed through `POST /review/staad` of the API ([`../../../api/README.md`](../../../api/README.md)); needs the server (`python -m rcopt.cli serve`), not a static website.
