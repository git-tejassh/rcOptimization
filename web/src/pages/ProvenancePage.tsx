import { useState } from "react";
import { marked } from "marked";
import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { download } from "../format";

function Md({ text }: { text: string }) {
  return <div className="prose-md overflow-x-auto" dangerouslySetInnerHTML={{ __html: marked.parse(text, { async: false }) as string }} />;
}
const badge = (s: string) => (
  <span className={`tag ${s === "provisional" ? "bg-amber-200 text-amber-950" : s === "secondary_source" ? "bg-sky-200 text-sky-950" : "bg-emerald-200 text-emerald-950"}`}>
    {s === "provisional" ? "⚠ provisional" : s === "secondary_source" ? "◐ secondary source" : "✓ " + s}
  </span>
);

export default function ProvenancePage() {
  const { provenance: p, benchmark } = useData();
  const [tab, setTab] = useState<"assumptions" | "decisions" | "benchmark" | "carbon">("assumptions");
  const last = benchmark[Object.keys(benchmark).slice(-1)[0]];
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Where every number comes from"
        title={"Data provenance and assumptions"}
        lead="Every price, carbon factor and modelling assumption, with its source and how much to trust it."
        howTo={[
          "Amber tags are provisional placeholders; grey tags come from published secondary sources; neither is a verified quote or EPD.",
          "The tabs below hold the assumptions list, the decision log, the STAAD benchmark and the carbon-data audit.",
        ]}
      />
      <div className="rounded-md border border-amber-500 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
        Every value below marked ⚠ is a <strong>provisional placeholder</strong>. IS 456 tables: {p.is456_tables_status} (transcribed from memory; the owner must check them against the printed code). Replace the rates / factors in <code>config/*.yaml</code> and re-run to update everything.
      </div>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Cost rates (INR)</h2>
        <table className="t">
          <thead><tr><th>Item</th><th>Value</th><th>Unit</th><th>Source</th><th>Status</th></tr></thead>
          <tbody>{p.cost_rates.map((r) => <tr key={r.item}><td>{r.item}</td><td>{r.value}</td><td>{r.unit}</td><td className="text-xs">{r.source}</td><td>{badge(r.status)}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Embodied-carbon factors (A1-A4)</h2>
        <table className="t">
          <thead><tr><th>Item</th><th>Value</th><th>Unit</th><th>Source</th><th>Confidence</th><th>India-specific</th><th>Status</th></tr></thead>
          <tbody>{p.carbon_factors.map((r) => <tr key={r.item}><td>{r.item}</td><td>{String(r.value)}</td><td>{r.unit}</td><td className="text-xs">{r.source}</td><td>{r.confidence ?? "-"}</td><td>{r.india_specific == null ? "-" : r.india_specific ? "yes" : "no"}</td><td>{badge(r.status)}</td></tr>)}</tbody>
        </table>
      </section>
      <section className="card">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {(["assumptions", "decisions", "benchmark", "carbon"] as const).map((t) => (
            <button key={t} className={`btn ${tab === t ? "btn-on" : ""}`} onClick={() => setTab(t)}>
              {{ assumptions: "ASSUMPTIONS.md", decisions: "DECISIONS.md", benchmark: "STAAD benchmark", carbon: "Carbon data audit" }[t]}
            </button>
          ))}
          <button className="btn ml-auto" onClick={() => download("ASSUMPTIONS.md", p.assumptions_markdown)}>Download ASSUMPTIONS.md</button>
        </div>
        {tab === "assumptions" && <Md text={p.assumptions_markdown} />}
        {tab === "decisions" && <Md text={p.decisions_markdown} />}
        {tab === "benchmark" && (
          <>
            <p className="text-sm">Max reaction difference OpenSees vs STAAD: {(100 * last.reactions_Fy.DL.max_rel).toFixed(4)} %; column axial force {(100 * last.columns_Pu.max_rel).toFixed(4)} %.</p>
            <Md text={p.benchmark_markdown} />
          </>
        )}
        {tab === "carbon" && <Md text={p.carbon_audit_markdown || "_CARBON_DATA_AUDIT.md not generated._"} />}
      </section>
    </div>
  );
}
