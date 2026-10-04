import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { Finding, GravityCaveat, Stat } from "../components/Caveat";
import { num, pct } from "../format";

export default function Overview() {
  const { meta } = useData();
  const h = meta.headline as Record<string, number>;
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Project summary"
        title="Optimising an RC frame for cost and embodied carbon"
        lead={`${meta.project}. A reproducible tool that searches for RC frame designs that are cheap and low in embodied carbon while passing the IS 456 checks, and measures how far a machine-learning shortcut can be trusted.`}
        howTo={[
          "The cards give the headline numbers: data analysed, designs found, how well they were verified, and the speed-up.",
          "“What the results say” lists the findings in plain words, including the unfavourable ones.",
          "Open the Pareto explorer to browse the designs, or My design estimate to price your own frame.",
        ]}
      />
      <GravityCaveat />
      <section aria-label="Headline numbers" className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="FE dataset" value={`${h.dataset_rows_ok}`} sub={`${h.dataset_feasible} truly feasible · all runs kept`} />
        <Stat label="Pareto front (headline A)" value={`${h.front_size_A} pts`} sub={`direct-FE front: ${h.front_size_direct} pts`} />
        <Stat
          label="Verification pass rate, headline A"
          value={pct(h.verification_pass_rate_A, 0)}
          sub={`${h.verification_n_A} designs re-run through FE + IS 456 (target 90 %)`}
        />
        <Stat
          label="Best-validated configuration"
          value={pct(h.verification_best_rate, 0)}
          sub={`${String(meta.headline.verification_best_variant)}: pass rate of its ${h.verification_n_A} verified designs`}
        />
        <Stat
          label="Surrogate speed-up"
          value={`${num(h.speedup_A_incl_costs, 2)}×`}
          sub={`${num(h.speedup_A_opt_only, 1)}× optimisation only; includes data-gen + training in the first number`}
        />
        <Stat label="Surrogate A, U_flex MAE" value={num(h.surrogate_A_Uflex_MAE, 4)} sub={`boundary feasibility agreement ${pct(h.surrogate_A_boundary_feas_agree, 1)}`} />
        <Stat label="Surrogate B, U_flex MAE" value={num(h.surrogate_B_Uflex_MAE, 4)} sub={`boundary feasibility agreement ${pct(h.surrogate_B_boundary_feas_agree, 1)}`} />
        <Stat label="Mean FE solve" value={`${num(h.mean_fe_time_ms, 0)} ms`} sub="one OpenSees solve, single process" />
        <Stat label="STAAD benchmark" value={`${num(100 * h.benchmark_max_rel_reaction, 3)} %`} sub="max reaction difference vs the owner's STAAD model" />
      </section>
      <section aria-label="Findings" className="space-y-2">
        <h2 className="h2">What the results say (including the unfavourable ones)</h2>
        {meta.findings.map((f, i) => (
          <Finding key={i} level={f.level} text={f.text} />
        ))}
      </section>
      <section className="card">
        <h2 className="h2">Honest novelty statement</h2>
        <p className="mt-1 text-sm">{meta.honest_novelty}</p>
      </section>
    </div>
  );
}
