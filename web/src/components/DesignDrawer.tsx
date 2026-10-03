import type { ParetoDesign } from "../types";
import { download, lakh, num, tonnes } from "../format";
import { GravityCaveat } from "./Caveat";

function Stacked({ parts, unit, fmt }: { parts: Record<string, number>; unit: string; fmt: (x: number) => string }) {
  const keys = Object.keys(parts).filter((k) => k !== "total");
  const total = parts.total ?? keys.reduce((s, k) => s + parts[k], 0);
  const colors = ["#0ea5e9", "#f97316", "#10b981", "#a855f7"];
  return (
    <div>
      <div className="flex h-5 w-full overflow-hidden rounded" role="img" aria-label={`${unit} breakdown`}>
        {keys.map((k, i) => (
          <div key={k} style={{ width: `${(100 * parts[k]) / total}%`, background: colors[i % 4] }} title={`${k}: ${fmt(parts[k])}`} />
        ))}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-3 text-xs">
        {keys.map((k, i) => (
          <span key={k}>
            <span className="mr-1 inline-block h-2 w-2 rounded-sm" style={{ background: colors[i % 4] }} />
            {k} {fmt(parts[k])} ({((100 * parts[k]) / total).toFixed(0)} %)
          </span>
        ))}
      </div>
    </div>
  );
}

const csvRow = (d: ParetoDesign) =>
  [d.concrete, d.steel, ...d.beams.flatMap((b) => [b.b_mm, b.D_mm, b.bottom, b.top]), ...d.columns.flatMap((c) => [c.b_mm, c.D_mm, c.bars]),
    d.true_cost ?? d.pred_cost, d.true_carbon ?? d.pred_carbon, d.feasible_true].join(",");

export default function DesignDrawer({ d, label, onClose }: { d: ParetoDesign; label: string; onClose: () => void }) {
  const u = d.utilisation;
  const v = d.verification;
  return (
    <aside className="fixed inset-y-0 right-0 z-20 w-full max-w-lg overflow-y-auto border-l p-4 shadow-xl" style={{ background: "var(--card)", borderColor: "var(--line)" }} aria-label="Design details">
      <div className="flex items-start justify-between">
        <div>
          <div className="h2">Design #{d.id}</div>
          <div className="text-xs muted">{label}</div>
        </div>
        <button className="btn" onClick={onClose} aria-label="Close">✕</button>
      </div>
      <div className="mt-3 space-y-3 text-sm">
        <GravityCaveat />
        <div className="flex flex-wrap gap-2">
          <span className={`tag ${d.feasible_true ? "bg-emerald-100 text-emerald-900" : "bg-red-100 text-red-900"}`}>
            {d.feasible_true ? "✓ truly feasible (FE + IS 456)" : "✕ truly infeasible"}
          </span>
          {v.verified ? (
            <span className={`tag ${v.passed ? "bg-emerald-100 text-emerald-900" : "bg-red-100 text-red-900"}`}>{v.passed ? "✓ verification passed" : "✕ verification failed"}{v.boundary_pick ? " (boundary pick)" : ""}</span>
          ) : (
            <span className="tag bg-slate-200 text-slate-800">not in the verified subset</span>
          )}
        </div>
        {v.verified && !v.passed && (
          <ul className="list-disc pl-5 text-red-700 dark:text-red-300">{v.reasons?.map((r, i) => <li key={i}>{r}</li>)}</ul>
        )}
        <table className="t">
          <tbody>
            <tr><td>Concrete / steel</td><td>{d.concrete} / {d.steel}</td></tr>
            {d.beams.map((b) => (
              <tr key={`b${b.group}`}><td>Beam group {b.group}</td><td>{b.b_mm} × {b.D_mm} mm · bottom {b.bottom} · top {b.top} · {b.stirrups}{d.stirrup_spacing_mm ? ` @ ${d.stirrup_spacing_mm[b.group]} mm` : ""}</td></tr>
            ))}
            {d.columns.map((c) => (
              <tr key={`c${c.group}`}><td>Column group {c.group}</td><td>{c.b_mm} × {c.D_mm} mm · {c.bars} (pt {num(c.pt_percent, 2)} %)</td></tr>
            ))}
            <tr><td>Cost (ground truth)</td><td>{lakh(d.true_cost)} <span className="muted">(surrogate: {lakh(d.pred_cost)})</span></td></tr>
            <tr><td>Embodied carbon</td><td>{tonnes(d.true_carbon)} CO₂e <span className="muted">(surrogate: {tonnes(d.pred_carbon)})</span></td></tr>
          </tbody>
        </table>
        {d.quantities && (
          <div>
            <div className="font-semibold">Quantities</div>
            <div className="text-xs">
              concrete {num(d.quantities.concrete_m3, 1)} m³ (beams {num(d.quantities.beam_concrete_m3, 1)}, columns {num(d.quantities.column_concrete_m3, 1)}) · steel {tonnes(d.quantities.steel_kg)} (beams {tonnes(d.quantities.beam_steel_kg)}, columns {tonnes(d.quantities.column_steel_kg)}) · formwork {num(d.quantities.formwork_m2, 0)} m²
            </div>
          </div>
        )}
        {d.cost_inr && (
          <div>
            <div className="mb-1 font-semibold">Cost breakdown (provisional rates)</div>
            <Stacked parts={d.cost_inr} unit="INR" fmt={lakh} />
          </div>
        )}
        {d.carbon_kgco2e && (
          <div>
            <div className="mb-1 font-semibold">Carbon breakdown (provisional factors, A1-A4)</div>
            <Stacked parts={d.carbon_kgco2e} unit="kgCO2e" fmt={tonnes} />
          </div>
        )}
        {u && (
          <div>
            <div className="mb-1 font-semibold">True utilisation ratios (≤ 1.0 required)</div>
            <table className="t">
              <tbody>
                {[
                  ["Beam flexure (max)", u.U_flex_max, d.pred_util?.U_flex_max],
                  ["Beam shear (max)", u.U_shear_max, d.pred_util?.U_shear_max],
                  ["Column interaction (max)", u.U_col_max, d.pred_util?.U_col_max],
                  ["Deflection / (L/250)", u.deflection_ratio, d.pred_util?.defl_ratio_max],
                ].map(([k, t, p]) => (
                  <tr key={k as string}>
                    <td>{k}</td>
                    <td className={(t as number) > 1 ? "font-semibold text-red-600" : ""}>{(t as number) > 1 ? "✕ " : "✓ "}{num(t as number, 3)}</td>
                    <td className="text-xs muted">{p != null ? `surrogate ${num(p as number, 3)}` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-xs muted">max service deflection {num(u.deflection_mm, 2)} mm</div>
          </div>
        )}
        <div className="flex gap-2">
          <button className="btn" onClick={() => download(`design_${d.id}.json`, JSON.stringify(d, null, 2), "application/json")}>Export JSON</button>
          <button className="btn" onClick={() => download(`design_${d.id}.csv`, csvRow(d))}>Export CSV row</button>
        </div>
      </div>
    </aside>
  );
}
