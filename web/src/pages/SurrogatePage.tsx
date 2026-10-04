import { useState } from "react";
import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import { Finding } from "../components/Caveat";
import { num, pct } from "../format";
import type { ModelEval } from "../types";

const OUTS = ["U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max"];
const NAMES: Record<string, string> = { U_flex_max: "U flexure", U_shear_max: "U shear", U_col_max: "U column", defl_ratio_max: "deflection ratio" };

function MetricTable({ rows }: { rows: { label: string; ev: ModelEval }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="t">
        <thead>
          <tr>
            <th>Model / round</th>
            <th>Output</th>
            <th>Hold-out MAE</th>
            <th>R²</th>
            <th>p95 |err|</th>
            <th>max |err|</th>
            <th>Boundary MAE</th>
            <th>Boundary p95</th>
          </tr>
        </thead>
        <tbody>
          {rows.flatMap((r) =>
            OUTS.map((o, k) => (
              <tr key={r.label + o}>
                <td className="font-medium">{k === 0 ? r.label : ""}</td>
                <td>{NAMES[o]}</td>
                <td>{num(r.ev.overall[o].MAE, 4)}</td>
                <td>{num(r.ev.overall[o].R2, 4)}</td>
                <td>{num(r.ev.overall[o].p95_abs_err, 3)}</td>
                <td>{num(r.ev.overall[o].max_abs_err, 2)}</td>
                <td>{num(r.ev.boundary[o].MAE, 4)}</td>
                <td>{num(r.ev.boundary[o].p95_abs_err, 3)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}

function Confusion({ title, c }: { title: string; c: Record<string, number> }) {
  return (
    <div className="card">
      <div className="font-semibold">{title}</div>
      <table className="t mt-1">
        <thead>
          <tr><th></th><th>predicted feasible</th><th>predicted infeasible</th></tr>
        </thead>
        <tbody>
          <tr><td>truly feasible</td><td>{c.TP}</td><td className={c.FN_pred_infeasible_but_truly_feasible ? "text-amber-600" : ""}>{c.FN_pred_infeasible_but_truly_feasible}</td></tr>
          <tr><td>truly infeasible</td><td className={c.FP_pred_feasible_but_truly_infeasible ? "font-semibold text-red-600" : ""}>{c.FP_pred_feasible_but_truly_infeasible}</td><td>{c.TN}</td></tr>
        </tbody>
      </table>
      <div className="text-xs muted">agreement {pct(c.agreement, 1)} · red = designs the optimiser would wrongly accept</div>
    </div>
  );
}

export default function SurrogatePage() {
  const { surrogate: s } = useData();
  const { dark } = useTheme();
  const [model, setModel] = useState<"A" | "B">("A");
  const [round, setRound] = useState<"before" | "after">("after");
  const [out, setOut] = useState("U_flex_max");
  const pts = (round === "before" ? s.parity_points_before : s.parity_points_after)[model] as any;
  const t = pts[out] as { true: number[]; pred: number[] };
  const nb = pts.near_boundary as boolean[];
  const lim = Math.max(1.6, ...t.true.map((x) => Math.min(x, 3)));
  const trace = (flag: boolean, name: string, color: string) => ({
    type: "scatter", mode: "markers", name,
    x: t.true.filter((_, i) => nb[i] === flag), y: t.pred.filter((_, i) => nb[i] === flag), marker: { size: 5, color, opacity: 0.6 },
  });
  const al = s.active_learning as Record<string, any>;
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Trusting the shortcut"
        title={"Surrogate performance"}
        lead="How closely the fast machine-learning predictors reproduce the slow, exact finite-element results, overall and near the code limit where mistakes matter most."
        howTo={[
          "Surrogate A predicts the checks directly; Surrogate B predicts only the forces and then applies the exact IS 456 formulas.",
          "Smaller errors (MAE) are better; the “boundary” columns cover designs close to the limit (a ratio between 0.85 and 1.15), the hard case.",
          "The confusion tables count how often a model says “passes” when the design truly fails (the dangerous mistake).",
        ]}
      />
      <p className="max-w-3xl text-sm muted">
        Hold-out = {s.n_test} designs (grouped by identical sizes, never used for tuning or training); {s.n_test_boundary} of them lie near the feasibility boundary (any ratio in [0.85, 1.15]). Hyper-parameters: 5-fold group CV on the training portion only. Surrogate A = brief (direct utilisation regression, bootstrap XGBoost ensemble); Surrogate B = demand regression + exact IS 456 capacity.
      </p>
      <Finding level="info" text={`Safety margins (95th-percentile boundary abs. error of the worst utilisation): A ${num(s.margin_q95.A, 3)}, B ${num(s.margin_q95.B, 3)} - used by the "+ margin" optimisation runs.`} />
      <section className="card">
        <h2 className="h2 mb-2">Metrics (before vs after the active-learning round)</h2>
        <MetricTable
          rows={[
            { label: "A before AL", ev: s.before_AL.A }, { label: "A after AL", ev: s.after_AL.A },
            { label: "B before AL", ev: s.before_AL.B }, { label: "B after AL", ev: s.after_AL.B },
            { label: "Random forest (A inputs), before AL", ev: s.baseline_random_forest_A_before_AL },
          ]}
        />
        <p className="mt-2 text-xs muted">
          Active learning: {al.n_selected} designs near the predicted boundary / with high ensemble disagreement were run through FE ({al.n_ok} OK; {al.feasible_among_selected} truly feasible; {al.near_boundary_among_selected} near the boundary) and added to the training set; one round only.
        </p>
      </section>
      <section className="grid gap-3 md:grid-cols-2">
        <Confusion title="Surrogate A, near the boundary (after AL)" c={s.after_AL.A.feasibility_boundary} />
        <Confusion title="Surrogate B, near the boundary (after AL)" c={s.after_AL.B.feasibility_boundary} />
        <Confusion title="Surrogate A, all hold-out (after AL)" c={s.after_AL.A.feasibility_overall} />
        <Confusion title="Surrogate B, all hold-out (after AL)" c={s.after_AL.B.feasibility_overall} />
      </section>
      <section className="card">
        <div className="mb-2 flex flex-wrap items-center gap-3 text-sm">
          <h2 className="h2">Parity plot</h2>
          {(["A", "B"] as const).map((m) => <button key={m} className={`btn ${model === m ? "btn-on" : ""}`} onClick={() => setModel(m)}>Surrogate {m}</button>)}
          {(["before", "after"] as const).map((r) => <button key={r} className={`btn ${round === r ? "btn-on" : ""}`} onClick={() => setRound(r)}>{r} AL</button>)}
          <select className="btn" value={out} onChange={(e) => setOut(e.target.value)}>{OUTS.map((o) => <option key={o} value={o}>{NAMES[o]}</option>)}</select>
        </div>
        <Plot
          dark={dark}
          height={420}
          data={[
            trace(false, "hold-out", "#0ea5e9"), trace(true, "near boundary", "#dc2626"),
            { type: "scatter", mode: "lines", x: [0, lim], y: [0, lim], name: "ideal", line: { dash: "dash", color: "gray" } },
          ]}
          layout={{ xaxis: { title: "FE + IS 456 (true)", range: [0, lim] }, yaxis: { title: "surrogate", range: [0, lim] }, shapes: [{ type: "line", x0: 1, x1: 1, y0: 0, y1: lim, line: { color: "gray", width: 0.5 } }, { type: "line", y0: 1, y1: 1, x0: 0, x1: lim, line: { color: "gray", width: 0.5 } }] }}
        />
        <p className="text-xs muted">500 random hold-out points shown. Grey lines mark the constraint limit 1.0.</p>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Surrogate B: demand regression quality (after AL)</h2>
        <table className="t">
          <thead><tr><th>Demand</th><th>R²</th><th>MAE</th><th>mean |value|</th></tr></thead>
          <tbody>
            {Object.entries(s.after_AL.B.demands ?? {}).map(([k, m]) => (
              <tr key={k}><td className="font-mono">{k}</td><td>{num(m.R2, 4)}</td><td>{num(m.MAE, 3)}</td><td>{num(m.mean_abs_value, 2)}</td></tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs muted">
          Column demands are regressed per position class (storey level x position in plan), which is smooth in the sizes; utilisation errors above already include any residual error.
        </p>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Top feature importances</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(s.feature_importance_top).map(([k, imp]) => (
            <div key={k}>
              <div className="font-mono text-sm">{k}</div>
              <table className="t"><tbody>{Object.entries(imp).slice(0, 8).map(([f, v]) => <tr key={f}><td>{f}</td><td>{num(v, 3)}</td></tr>)}</tbody></table>
            </div>
          ))}
        </div>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Hyper-parameter search (5-fold group CV, training portion only)</h2>
        <table className="t">
          <thead><tr><th>max_depth</th><th>n_estimators</th><th>learning rate</th><th>CV mean log-MAE</th><th>± std</th></tr></thead>
          <tbody>{s.tuning.map((r, i) => <tr key={i}><td>{r.params.max_depth}</td><td>{r.params.n_estimators}</td><td>{r.params.learning_rate}</td><td>{num(r.cv_mean_log_mae, 4)}</td><td>{num(r.cv_std, 4)}</td></tr>)}</tbody>
        </table>
      </section>
    </div>
  );
}
