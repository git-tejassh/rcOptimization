// Builds the standalone HTML of the "final report" of the My design estimate tab (downloadable, printable).
import type { ReviewReport } from "./api";
import type { Breakdown, Quantities } from "./estimate";

const e = (s: unknown) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const lakh = (x: number) => `₹${(x / 1e5).toFixed(2)} lakh`;
const t = (kg: number) => `${(kg / 1000).toFixed(2)} t`;

export interface ReportInput {
  source: string;
  grade: string;
  steel: string;
  cement: string;
  q: Quantities;
  est: Breakdown;
  steelBasis: string;
  review: ReviewReport | null;
  zone: string | null;
  reference: { cost: number; carbon: number } | null;
  suggestions: { tag: string; front: string; cost: number; carbon: number; materials: string; beams: string; columns: string }[];
  changedRates: string[];
  provisionalNote: string;
}

export function reportHtml(r: ReportInput): string {
  const row = (a: string, b: string, c = "") => `<tr><td>${e(a)}</td><td>${e(b)}</td><td>${e(c)}</td></tr>`;
  const rev = r.review;
  const strength = rev
    ? `<p class="${rev.verdict === "PASS" ? "ok" : "bad"}"><b>${rev.verdict === "PASS" ? "PASS" : "FAIL"}</b>${rev.verdict === "PASS" ? ": the member sizes are adequate with the designed reinforcement." : ": the member sizes are not adequate."}</p>` +
      (rev.failures.length ? `<ul>${rev.failures.map((f) => `<li class="bad">${e(f)}</li>`).join("")}</ul>` : "") +
      `<h3>Beams</h3><table><tr><th>Group (levels)</th><th>Size (mm)</th><th>Designed bars</th><th>Demand sag / hog / shear</th><th>Bending</th><th>Shear</th></tr>` +
      rev.beams.map((b) => `<tr><td>${b.group} (${b.levels.join(", ")})</td><td>${b.b_mm} × ${b.D_mm}</td><td>bottom ${e(b.bottom)}, top ${e(b.top)}, ${e(b.stirrups)}</td><td>${b.demand.Msag_kNm.toFixed(1)} / ${b.demand.Mhog_kNm.toFixed(1)} kN·m / ${b.demand.Vu_kN.toFixed(1)} kN</td><td>${Math.max(b.U_sag, b.U_hog).toFixed(2)}</td><td>${b.U_shear.toFixed(2)}</td></tr>`).join("") +
      `</table><h3>Columns</h3><table><tr><th>Group</th><th>Size (mm)</th><th>Designed bars</th><th>Governing Pu / M</th><th>Interaction</th></tr>` +
      rev.columns.map((c) => `<tr><td>${c.group}${c.is_base_group ? " (incl. base)" : ""}</td><td>${c.b_mm} × ${c.D_mm}</td><td>${e(c.bars)} (${c.pt_percent.toFixed(2)} %)</td><td>${c.governing.Pu_kN.toFixed(0)} kN / ${c.governing.MD_kNm.toFixed(1)}, ${c.governing.Mb_kNm.toFixed(1)} kN·m</td><td>${c.U.toFixed(2)}</td></tr>`).join("") +
      `</table><p>Deflection ${rev.deflection.ratio_to_L_over_250.toFixed(2)} × the L/250 limit (largest ${rev.deflection.max_mm.toFixed(1)} mm). Limits of this review: ${rev.assumptions.map(e).join(" ")}</p>`
    : `<p>No strength review was run. It needs a STAAD input of a regular frame and the local Python server (<code>python -m rcopt.cli serve</code>); reinforcement quantities below are therefore ASSUMED, not designed.</p>`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Design review report</title><style>
body{font-family:Outfit,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;color:#1d1e1c;line-height:1.5}
h1{font-weight:500;border-bottom:4px solid #53ac35;padding-bottom:8px}h2{margin-top:28px;font-weight:600}h3{margin-top:16px}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}th,td{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}th{background:#f1f5ee}
.ok{color:#2c5e1b}.bad{color:#b4443c}.note{background:#fbf5e6;border:1px solid #e6d3a3;padding:10px;border-radius:8px;font-size:13px}
</style></head><body>
<h1>Design review report</h1><p>Generated ${new Date().toLocaleString()} · source: ${e(r.source)} · ${e(r.grade)} / ${e(r.steel)} / ${e(r.cement)} cement</p>
<h2>1. Strength review (IS 456, gravity loads)</h2>${strength}
<h2>2. Quantities</h2><table><tr><th>Item</th><th>Value</th><th>Note</th></tr>
${row("Concrete", `${r.q.concrete_m3.toFixed(1)} m³`, `beams ${r.q.beam_concrete_m3.toFixed(1)}, columns ${r.q.column_concrete_m3.toFixed(1)}`)}
${row("Reinforcement", t(r.q.steel_kg), r.steelBasis)}${row("Formwork", `${r.q.formwork_m2.toFixed(0)} m²`)}</table>
<h2>3. Cost and embodied carbon</h2><table><tr><th>Item</th><th>Cost</th><th>Carbon</th></tr>
<tr><td>Concrete</td><td>${lakh(r.est.cost.concrete)}</td><td>${t(r.est.carbon.concrete)} CO₂e</td></tr>
<tr><td>Reinforcement</td><td>${lakh(r.est.cost.steel)}</td><td>${t(r.est.carbon.steel)} CO₂e</td></tr>
<tr><td>Formwork / transport</td><td>${lakh(r.est.cost.formwork)}</td><td>${t(r.est.carbon.transport)} CO₂e</td></tr>
<tr><th>Total</th><th>${lakh(r.est.cost.total)}</th><th>${t(r.est.carbon.total)} CO₂e</th></tr></table>
${r.zone ? `<p>Position against the optimiser’s best: <b>${e(r.zone)} zone</b>.</p>` : ""}
${r.reference ? `<p>Best optimised design of the project frame: ${lakh(r.reference.cost)} and ${t(r.reference.carbon)} CO₂e.</p>` : ""}
<h2>4. Suggested optimised designs</h2><table><tr><th>Suggestion</th><th>Cost</th><th>Carbon</th><th>Materials</th><th>Beams</th><th>Columns</th></tr>
${r.suggestions.map((s) => `<tr><td>${e(s.tag)} (${e(s.front)})</td><td>${lakh(s.cost)}</td><td>${t(s.carbon)}</td><td>${e(s.materials)}</td><td>${e(s.beams)}</td><td>${e(s.columns)}</td></tr>`).join("")}</table>
<h2>5. Assumptions and limits</h2><div class="note">${e(r.provisionalNote)}</div>
<ul><li>Frame concrete, reinforcement and formwork only (no slab, foundations, finishes).</li><li>Gravity loads only; no seismic or wind design.</li><li>${r.changedRates.length ? `Prices / factors edited by the user: ${r.changedRates.map(e).join("; ")}.` : "All prices and factors are the project values."}</li></ul>
</body></html>`;
}
