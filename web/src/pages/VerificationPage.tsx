import { useState } from "react";
import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import { Finding } from "../components/Caveat";
import { num, pct } from "../format";

export default function VerificationPage() {
  const { verification: v, pareto } = useData();
  const { dark } = useTheme();
  const names = Object.keys(v.variants);
  const [name, setName] = useState("A");
  const r = v.variants[name];
  const ff = v.full_front[name];
  return (
    <div className="space-y-5">
      <h1 className="h1">Verification of Pareto designs</h1>
      <p className="text-sm muted">
        {v.selection.n_designs} designs per front (cost-quantile picks plus the {v.selection.n_boundary} with the smallest predicted constraint slack) were re-run through OpenSees + the IS 456 checks. A design passes only if it is <em>truly feasible</em> and the surrogate's utilisations are within ±{v.tolerance.util_abs} (absolute) and its deflection within ±{pct(v.tolerance.defl_rel, 0)} (relative) of the truth. The selection rule was fixed before the results; the 90 % target is reported against, not engineered toward.
      </p>
      <div className="flex flex-wrap gap-1" role="group" aria-label="Front variant">
        {names.map((n) => <button key={n} className={`btn ${n === name ? "btn-on" : ""}`} onClick={() => setName(n)}>{pareto.labels[n] ?? n}</button>)}
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <div className="card">
          <div className="text-xs uppercase muted">Pass rate</div>
          <div className="mt-1 flex items-end gap-2">
            <div className={`text-3xl font-semibold ${r.target_met ? "text-emerald-600" : "text-red-600"}`}>{r.target_met ? "✓" : "✕"} {pct(r.pass_rate, 0)}</div>
            <div className="text-xs muted">{r.n_pass} / {r.n_verified}</div>
          </div>
          <div className="mt-2 h-2 w-full rounded bg-slate-200 dark:bg-slate-700" role="img" aria-label={`pass rate ${pct(r.pass_rate, 0)} against target ${pct(r.pass_target, 0)}`}>
            <div className={`h-2 rounded ${r.target_met ? "bg-emerald-500" : "bg-red-500"}`} style={{ width: `${100 * r.pass_rate}%` }} />
          </div>
          <div className="mt-1 text-xs muted">target {pct(r.pass_target, 0)} (shown as measured)</div>
        </div>
        <div className="card"><div className="text-xs uppercase muted">Truly feasible</div><div className="mt-1 text-2xl font-semibold">{r.n_truly_feasible} / {r.n_verified}</div></div>
        <div className="card"><div className="text-xs uppercase muted">Within tolerance</div><div className="mt-1 text-2xl font-semibold">{r.n_within_tolerance} / {r.n_verified}</div></div>
        <div className="card"><div className="text-xs uppercase muted">Boundary picks passing</div><div className="mt-1 text-2xl font-semibold">{r.boundary_picks.n_pass} / {r.boundary_picks.n}</div><div className="text-xs muted">where surrogates are weakest</div></div>
      </div>
      {r.failures.length > 0 ? (
        <section className="space-y-2">
          <h2 className="h2">Failures ({r.failures.length}) - not hidden</h2>
          {r.failures.map((f) => <Finding key={f.index} level="bad" text={`Design #${f.index}${f.boundary_pick ? " (boundary pick)" : ""}: ${f.reasons.join(" · ")}`} />)}
        </section>
      ) : <Finding level="info" text="No failures in the verified subset." />}
      {ff && (
        <div className="card text-sm">
          <h2 className="h2 mb-1">Whole pooled front re-evaluated (extra finding)</h2>
          {ff.front_size} designs: {pct(ff.truly_feasible_fraction, 1)} truly feasible · largest true constraint violation {num(ff.max_true_utilisation_violation, 3)} · hypervolume gap predicted vs true front {pct(ff.hv_gap_relative, 1)} · mean cost error {pct(ff.cost_rel_err_mean, 2)}, carbon error {pct(ff.carbon_rel_err_mean, 2)}.
        </div>
      )}
      <section className="card">
        <h2 className="h2 mb-2">Predicted vs true utilisation of the verified designs</h2>
        <Plot
          dark={dark}
          height={380}
          data={[
            ...["U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max"].map((t) => ({
              type: "scatter", mode: "markers", name: t,
              x: r.designs.filter((d) => d.status === "OK").map((d) => d[`true_${t}`] as number), y: r.designs.filter((d) => d.status === "OK").map((d) => d[`pred_${t}`] as number),
              marker: { size: 8, symbol: r.designs.filter((d) => d.status === "OK").map((d) => (d.passed ? "circle" : "x")) },
            })),
            { type: "scatter", mode: "lines", x: [0, 1.3], y: [0, 1.3], name: "ideal", line: { dash: "dash", color: "gray" } },
          ]}
          layout={{ xaxis: { title: "true" }, yaxis: { title: "predicted" } }}
        />
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">All verified designs</h2>
        <table className="t">
          <thead><tr><th>#</th><th></th><th>Cost pred → true (₹ L)</th><th>U flex</th><th>U shear</th><th>U col</th><th>defl</th><th>Result</th></tr></thead>
          <tbody>
            {r.designs.map((d) => (
              <tr key={d.index} className={d.passed ? "" : "bg-red-50 dark:bg-red-950/30"}>
                <td>{d.index}</td>
                <td className="text-xs">{d.boundary_pick ? "boundary" : ""}</td>
                <td>{num(d.pred_cost / 1e5, 2)} → {d.true_cost != null ? num((d.true_cost as number) / 1e5, 2) : "-"}</td>
                {["U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max"].map((t) => (
                  <td key={t} className={(d[`true_${t}`] as number) > 1 ? "font-semibold text-red-600" : ""}>{d.status === "OK" ? `${num(d[`pred_${t}`] as number, 2)} → ${num(d[`true_${t}`] as number, 2)}` : "-"}</td>
                ))}
                <td>{d.passed ? "✓ pass" : `✕ ${d.reasons.join("; ")}`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
