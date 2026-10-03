import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import { Finding } from "../components/Caveat";
import { num, pct } from "../format";

export default function SensitivityPage() {
  const { sensitivity: s } = useData();
  const { dark } = useTheme();
  if (!s) return <div className="card">Sensitivity results not available (run <code>rcopt sensitivity</code> and <code>rcopt export</code>).</div>;
  return (
    <div className="space-y-5">
      <h1 className="h1">Sensitivity to ±20 % of cost and carbon inputs</h1>
      <Finding level={s.verdict.includes("NOT") ? "warn" : "info"} text={s.verdict} />
      <p className="text-sm muted">
        Each scenario re-runs the headline optimisation (surrogate A, first two seeds) with one input scaled, re-evaluates the pooled front with ground-truth FE <em>under that scenario</em>, and compares it with the baseline front. All base values are provisional, so this page shows robustness of the <em>shape</em>, not of absolute values.
      </p>
      <section className="card">
        <Plot
          dark={dark}
          height={460}
          data={s.scenarios.map((x) => ({ type: "scatter", mode: "lines+markers", name: x.label, x: x.front.map((p) => p.cost / 1e5), y: x.front.map((p) => p.carbon / 1000), marker: { size: 5 }, line: { width: x.name === "baseline" ? 3 : 1.5 } }))}
          layout={{ xaxis: { title: "cost (₹ lakh) under each scenario" }, yaxis: { title: "embodied carbon (t CO₂e) under each scenario" } }}
        />
      </section>
      <section className="card overflow-x-auto">
        <table className="t">
          <thead><tr><th>Scenario</th><th>front size</th><th>baseline designs still non-dominated</th><th>rank corr. cost</th><th>rank corr. carbon</th><th>knee design</th><th>same grades as baseline knee</th></tr></thead>
          <tbody>
            {s.scenarios.map((x) => (
              <tr key={x.name}>
                <td className="font-medium">{x.label}</td><td>{x.front_size}</td><td>{pct(x.baseline_survival_fraction, 0)}</td>
                <td>{num(x.cost_rank_spearman, 3)}</td><td>{num(x.carbon_rank_spearman, 3)}</td>
                <td>₹{num(x.knee.cost / 1e5, 2)} L · {num(x.knee.carbon / 1000, 1)} t</td><td>{x.knee.same_knee_as_baseline ? "✓" : "✕ changes"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
