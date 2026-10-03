import { useData } from "../data";
import { GravityCaveat } from "../components/Caveat";

export default function AboutPage() {
  const { meta } = useData();
  return (
    <div className="space-y-5">
      <h1 className="h1">About, limits and deviations from the brief</h1>
      <GravityCaveat />
      <section className="card">
        <h2 className="h2">Honest novelty</h2>
        <p className="mt-1 text-sm">{meta.honest_novelty}</p>
      </section>
      <section className="card">
        <h2 className="h2">Method in one paragraph</h2>
        <p className="mt-1 text-sm">
          The owner's G+3 STAAD model supplies geometry and loads. An OpenSeesPy 3D elastic frame (validated against the STAAD results to a fraction of a percent) is analysed for 1.5 (DL + LL) and the IS 456:2000 beam / column checks are applied to discrete designs. A discrete-aware Latin-hypercube sample plus a feasibility-biased stratum is analysed (every run kept, with a status flag), two surrogates are trained (direct utilisation regression, and a demand regression with exact analytic capacity), one active-learning round targets the feasibility boundary, and constrained NSGA-II minimises cost and embodied carbon with the surrogates and, as a baseline, with live FE. Pareto designs are re-verified with ground truth and the whole front is re-evaluated.
        </p>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Deviations from the brief</h2>
        <table className="t">
          <thead><tr><th>ID</th><th>Brief says</th><th>This project does</th><th>Reason</th></tr></thead>
          <tbody>{meta.deviations.map((d) => <tr key={d.id}><td className="font-mono">{d.id}</td><td>{d.brief}</td><td>{d.spec}</td><td>{d.reason}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="card">
        <h2 className="h2">Out of scope</h2>
        <ul className="mt-1 list-disc pl-5 text-sm">
          <li>Seismic (IS 1893 / IS 13920) and wind design: gravity only. A seismic hook (interfaces only) exists in <code>rcopt/seismic</code>; no seismic results are claimed.</li>
          <li>Foundations, construction-sequence and operational carbon, slab design, steel (IS 800) members, other building typologies.</li>
          <li>Formwork carbon is excluded; formwork cost is included at a provisional rate.</li>
          <li>The cost rates, emission factors and IS table transcriptions are provisional until the owner verifies them.</li>
        </ul>
      </section>
      <section className="card text-sm">
        <h2 className="h2">Reproduce</h2>
        <pre className="mt-1 overflow-x-auto rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">{`make setup && make all     # or .\\make.ps1 setup; .\\make.ps1 all
make web-dev               # this dashboard (data from web/public/data/*.json)
make api                   # optional local API for the live evaluator`}</pre>
      </section>
    </div>
  );
}
