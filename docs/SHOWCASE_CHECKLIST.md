# Showcase checklist (do the technical part tonight, the demo tomorrow)

## Tonight (about 15 minutes of your time)
1. **Models present?** `models\surrogate_A.joblib` and `surrogate_B.joblib` must exist (they do on the main laptop). On another laptop: unzip `models.zip` into `models\`.
2. **Start the server once** and open the site:
   ```powershell
   .venv\Scripts\python.exe -m rcopt.cli serve
   ```
   open http://localhost:8000 and click through *Overview → Pareto explorer → Optimise with my prices → My design estimate*. The header must NOT show the "failed to render" message on any tab.
3. **Run the price demo once** (it takes about 1.5 minutes): *Optimise with my prices* → set **Cement PSC = 13** → *Optimise*. You should see two groups of designs (cheaper PPC, lower-carbon PSC) and several "trade-off points". This is the answer to "why is your Pareto front narrow?".
4. **Fallback if the laptop or Wi-Fi fails:** `web\dist\index.html` opens by double-click and shows every result (no live features). Keep a copy on a USB stick / phone.
5. **Link for the guide:** either enable GitHub Pages once (repository → Settings → Pages → Source: GitHub Actions; the site appears at `https://git-tejassh.github.io/rcOptimization/` after the next push finishes in the Actions tab) or share a temporary link from your laptop: `winget install Cloudflare.cloudflared`, then `cloudflared tunnel --url http://localhost:8000`.

## The 5-minute demo story
1. **Problem** (Overview): cheapest and greenest frame that still passes IS 456; 3 × 10¹⁷ combinations.
2. **Trust** (Data & assumptions → *IS 456 check*; Data → STAAD benchmark): code values checked against the printed IS 456; the model matches your STAAD results (reactions 0.001 %, column moments 0.12 %).
3. **Result** (Pareto explorer): green zone = best designs, click a dot for its full property sheet.
4. **Honesty** (Verification, Compute): surrogate B with a safety margin passes 27 of 30 exact re-checks; the fast model does not save time overall; the front is narrow at the placeholder prices.
5. **Your prices** (Optimise with my prices): change the cement price, press Optimise, a real trade-off appears.
6. **Your design** (My design estimate): upload a STAAD file → strength review → cost/carbon → suggested designs → report.

## Say these limitations before the guide asks
* Gravity loads only (no earthquake / wind): the designs are not complete code designs of the building.
* Unit prices are placeholders; carbon factors for cement and steel are secondary-source values; the cement content per grade is a typical mix, not a trial mix (`docs/CARBON_SOURCES_TO_CITE.md`).
* Where the project is stricter than IS 456 (`docs/IS456_VERIFICATION.md` section 3).
* 5-seed study = the reference result; the price page is a quick single-seed re-search, all of whose designs are re-checked exactly.
