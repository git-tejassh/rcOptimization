import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import { Finding } from "../components/Caveat";
import { num, pct } from "../format";

export default function SensitivityPage() {
  const { sensitivity: s, cement } = useData();
  const { dark } = useTheme();
  if (!s) return <div className="card">Sensitivity results not available (run <code>rcopt sensitivity</code> and <code>rcopt export</code>).</div>;
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="What if the inputs are wrong?"
        title={"Sensitivity to ±20 % of cost and carbon inputs"}
        lead="How much the best designs change when prices and carbon factors move by ±20 %, and what the cement type would do."
        howTo={[
          "Each line is a front re-computed with one input changed; lines close to the baseline mean the result is robust.",
          "The cement section scans the price premium of a low-carbon cement to show when a real cost-carbon trade-off appears.",
        ]}
      />
      <Finding level={s.verdict.includes("NOT") ? "warn" : "info"} text={s.verdict} />
      <p className="max-w-3xl text-sm muted">
        Each scenario re-runs the best-validated optimisation (surrogate B + safety margin, first two seeds) with one input scaled, re-evaluates the pooled front with ground-truth FE <em>under that scenario</em>, and compares it with the baseline front. All base values are provisional, so this page shows robustness of the <em>shape</em>, not of absolute values.
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
      {cement && (
        <section className="card overflow-x-auto">
          <h2 className="h2 mb-1">Cement type as a design variable: when does a low-carbon cement create a trade-off?</h2>
          <p className="mb-2 text-sm muted">
            Cement type (OPC / PPC / PSC) changes cost and carbon but not the structural response, so every truly feasible design ({cement.n_structural_designs}) was paired with every cement type and the
            non-dominated set scanned over the price premium of PSC over PPC. At the market prices of the config PSC is both cheaper and lower-carbon and simply dominates; a front appears only when low-carbon cement costs more. All prices are provisional.
          </p>
          <Plot
            dark={dark}
            height={380}
            data={cement.scenarios.map((x) => ({ type: "scatter", mode: "lines+markers", name: x.psc_premium_inr_per_kg == null ? "market prices" : `PSC +${x.psc_premium_inr_per_kg} INR/kg`, x: x.front.map((p) => p.cost / 1e5), y: x.front.map((p) => p.carbon / 1000), marker: { size: 5 } }))}
            layout={{ xaxis: { title: "cost (₹ lakh)" }, yaxis: { title: "embodied carbon (t CO₂e)" } }}
          />
          <table className="t mt-2">
            <thead><tr><th>PSC price premium over PPC</th><th>PSC price (₹/kg)</th><th>front size</th><th>cost span</th><th>carbon span</th><th>cements on the front</th></tr></thead>
            <tbody>
              {cement.scenarios.map((x, i) => (
                <tr key={i}>
                  <td>{x.psc_premium_inr_per_kg == null ? "market (config)" : `+${x.psc_premium_inr_per_kg} ₹/kg`}</td><td>{num(x.psc_price_inr_per_kg, 2)}</td><td>{x.front_size}</td>
                  <td>{num(x.cost_span_pct, 1)} %</td><td>{num(x.carbon_span_pct, 1)} %</td><td>{Object.entries(x.cement_types_on_front).filter(([, n]) => n > 0).map(([k, n]) => `${k}: ${n}`).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
