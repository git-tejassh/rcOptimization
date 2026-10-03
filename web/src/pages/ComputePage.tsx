import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import { Finding } from "../components/Caveat";
import { num, palette } from "../format";

export default function ComputePage() {
  const { compute: c, pareto } = useData();
  const { dark } = useTheme();
  const names = Object.keys(c.compute.configs);
  const cmp = c.compute;
  return (
    <div className="space-y-5">
      <h1 className="h1">Compute comparison: surrogate vs direct FE</h1>
      <Finding level={cmp.configs.A.speedup_vs_direct_incl_datagen_and_training > 1 ? "info" : "warn"} text={c.verdict} />
      <section className="card">
        <h2 className="h2 mb-2">Hypervolume vs evaluations (mean ± std over seeds)</h2>
        <Plot
          dark={dark}
          height={400}
          data={names.flatMap((n) => {
            const cv = c.optimization[n].convergence;
            const col = palette.fronts[n] ?? "#888";
            return [
              { type: "scatter", mode: "lines", name: pareto.labels[n] ?? n, x: cv.n_eval, y: cv.hv_mean, line: { color: col, width: 2 } },
              { type: "scatter", mode: "lines", showlegend: false, hoverinfo: "skip", x: cv.n_eval.concat([...cv.n_eval].reverse()), y: cv.hv_mean.map((m, i) => m + cv.hv_std[i]).concat(cv.hv_mean.map((m, i) => m - cv.hv_std[i]).reverse()), fill: "toself", fillcolor: `${col}22`, line: { width: 0 } },
            ];
          })}
          layout={{ xaxis: { title: "evaluations (population x generations)" }, yaxis: { title: "hypervolume of the feasible non-dominated set (normalised, fixed reference)" } }}
        />
        <p className="text-xs muted">Surrogate curves are hypervolume of the objectives as the optimiser saw them (surrogate-predicted feasibility); the "ground truth" column below re-evaluates the final fronts.</p>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Numbers</h2>
        <table className="t">
          <thead>
            <tr><th>Configuration</th><th>evaluations / seed</th><th>unique evals / seed</th><th>unique FE solves / seed</th><th>wall / seed (s)</th><th>HV (true, pooled)</th><th>HV ratio vs direct</th><th>speed-up (opt. only)</th><th>speed-up (incl. data gen + training)</th></tr>
          </thead>
          <tbody>
            {names.map((n) => {
              const x = cmp.configs[n];
              return (
                <tr key={n}>
                  <td className="font-medium">{pareto.labels[n] ?? n}</td>
                  <td>{num(x.evaluations_requested_per_seed, 0)}</td><td>{num(x.unique_evaluations_per_seed, 0)}</td><td>{num(x.unique_fe_solves_per_seed, 0)}</td>
                  <td>{num(x.wall_s_per_seed, 0)}</td><td>{num(x.hv_pooled_front_true, 4)}</td>
                  <td>{x.hv_ratio_true_vs_direct != null ? num(x.hv_ratio_true_vs_direct, 3) : "-"}</td>
                  <td>{x.speedup_optimisation_only != null ? `${num(x.speedup_optimisation_only, 1)}×` : "-"}</td>
                  <td>{x.speedup_vs_direct_incl_datagen_and_training != null ? `${num(x.speedup_vs_direct_incl_datagen_and_training, 2)}×` : "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="mt-2 text-xs muted">
          One cold OpenSees FE solve: {num(1e3 * cmp.mean_fe_solve_time_s_single_process, 0)} ms. One-time costs charged to every surrogate row: data generation {cmp.data_generation.fe_solves} FE solves ≈ {num(cmp.data_generation.serial_equivalent_s, 0)} s serial-equivalent ({num(cmp.data_generation.parallel_wall_s, 0)} s parallel wall) and training/tuning/active learning {num(cmp.surrogate_training_s, 0)} s. Direct FE caches solves by member sizes (the elastic response does not depend on reinforcement).
        </p>
      </section>
    </div>
  );
}
