import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useData } from "../data";
import { useTheme } from "../App";
import PageHeader, { Section } from "../components/PageHeader";
import { GravityCaveat, Stat } from "../components/Caveat";
import Plot from "../components/Plot";
import FrontTable from "../components/FrontTable";
import DesignDetails from "../components/DesignDetails";
import { defaultBase, health, jobStatus, saveBase, startOptimise, type Health, type Job, type OptimiseResult, type PriceItem } from "../lib/api";
import { download, lakh, num, tonnes } from "../format";
import type { ParetoDesign } from "../types";

const CEMENT_COLOR: Record<string, string> = { OPC: "#b4443c", PPC: "#b7791f", PSC: "#2f7d5b" };

/** Price items in the same order and with the same keys as src/rcopt/cost_carbon/prices.py (defaults come from the exported factors). */
function itemsFrom(f: { cost: { concrete_per_m3: Record<string, number>; steel_per_kg: Record<string, number>; formwork_per_m2: number; cement_price_per_kg: Record<string, number>; cement_baseline: string } }): PriceItem[] {
  const out: PriceItem[] = [];
  for (const [g, v] of Object.entries(f.cost.concrete_per_m3)) out.push({ key: `concrete_${g}`, label: `Concrete ${g} (placed)`, unit: "₹/m³", group: "Concrete", default: v });
  for (const [s, v] of Object.entries(f.cost.steel_per_kg)) out.push({ key: `steel_${s}`, label: `Reinforcement ${s}`, unit: "₹/kg", group: "Steel", default: v });
  out.push({ key: "formwork_m2", label: "Formwork (contact area)", unit: "₹/m²", group: "Formwork", default: f.cost.formwork_per_m2 });
  for (const c of ["OPC", "PPC", "PSC"]) out.push({ key: `cement_${c}`, label: `Cement ${c}${c === f.cost.cement_baseline ? " (baseline of the concrete rates)" : ""}`, unit: "₹/kg", group: "Cement", default: f.cost.cement_price_per_kg[c] });
  return out;
}

const toCsv = (items: PriceItem[], vals: Record<string, number>) =>
  "# Unit prices in INR. Every default is a PLACEHOLDER (not a verified market rate): replace with current local rates.\nitem,value,unit,label\n" +
  items.map((i) => `${i.key},${vals[i.key]},${i.unit.replace("₹", "INR").replace("³", "3").replace("²", "2")},"${i.label}"`).join("\n") + "\n";

function parseCsv(text: string, items: PriceItem[]): { values: Record<string, number>; error?: string } {
  const keys = new Set(items.map((i) => i.key));
  const values: Record<string, number> = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const cells = line.split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
    if (cells[0].toLowerCase() === "item") continue;
    if (!keys.has(cells[0])) return { values, error: `Unknown item "${cells[0]}". Valid items: ${[...keys].join(", ")}` };
    const v = Number(cells[1]);
    if (!Number.isFinite(v) || v <= 0) return { values, error: `Price of "${cells[0]}" must be a positive number (got "${cells[1]}")` };
    values[cells[0]] = v;
  }
  if (!Object.keys(values).length) return { values, error: "The file has no price rows (expected lines like  steel_Fe500,70 )" };
  return { values };
}

export default function OptimisePage() {
  const { factors } = useData();
  const { dark } = useTheme();
  const items = useMemo(() => itemsFrom(factors as any), [factors]);
  const defaults = useMemo(() => Object.fromEntries(items.map((i) => [i.key, i.default])) as Record<string, number>, [items]);
  const [vals, setVals] = useState<Record<string, number>>(defaults);
  const [msg, setMsg] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [base, setBase] = useState(defaultBase());
  const [h, setH] = useState<Health | null | undefined>(undefined);
  const [mode, setMode] = useState<"quick" | "standard">("quick");
  const [job, setJob] = useState<Job | null>(null);
  const [err, setErr] = useState("");
  const [picked, setPicked] = useState<ParetoDesign | null>(null);
  const timer = useRef<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { health(base).then(setH); }, [base]);
  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current); }, []);

  const changed = items.filter((i) => Math.abs(vals[i.key] - i.default) > 1e-9);
  const ready = !!h?.price_optimiser;
  const running = job?.status === "running";
  const result: OptimiseResult | undefined = job?.status === "done" ? job.result : undefined;

  const run = useCallback(async () => {
    setErr(""); setPicked(null); setJob(null);
    try {
      const { job_id } = await startOptimise(base, vals, mode);
      const poll = async () => {
        try {
          const j = await jobStatus(base, job_id);
          setJob(j);
          if (j.status !== "running" && timer.current) { window.clearInterval(timer.current); timer.current = null; }
        } catch (e) { setErr(String(e)); if (timer.current) window.clearInterval(timer.current); }
      };
      await poll();
      timer.current = window.setInterval(poll, 1500);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }, [base, vals, mode]);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    const r = parseCsv(await f.text(), items);
    if (r.error) setMsg({ tone: "bad", text: r.error });
    else { setVals({ ...defaults, ...r.values }); setMsg({ tone: "good", text: `Loaded ${Object.keys(r.values).length} price(s) from ${f.name}; prices not in the file keep their placeholder value.` }); }
    if (fileRef.current) fileRef.current.value = "";
  };

  const designs = (result?.designs ?? []) as ParetoDesign[];
  const best = designs.length ? [...designs].sort((a, b) => a.true_cost! - b.true_cost!)[0] : null;
  const green = designs.length ? [...designs].sort((a, b) => a.true_carbon! - b.true_carbon!)[0] : null;
  const front = designs.filter((d: any) => d.pareto_true);

  const traces = useMemo(() => {
    if (!result) return [];
    const t: any[] = ["OPC", "PPC", "PSC"].map((c) => {
      const ds = designs.filter((d) => d.cement === c);
      return { type: "scatter", mode: "markers", name: `${c} cement`, x: ds.map((d) => d.true_cost! / 1e5), y: ds.map((d) => d.true_carbon! / 1000),
        customdata: ds.map((d) => d.id), text: ds.map((d) => `#${d.id} ${d.concrete}/${d.steel}/${d.cement}<br>₹${(d.true_cost! / 1e5).toFixed(2)} lakh, ${(d.true_carbon! / 1000).toFixed(1)} t CO₂e`),
        hovertemplate: "%{text}<extra></extra>", marker: { size: 11, color: CEMENT_COLOR[c], line: { width: ds.map((d: any) => (d.pareto_true ? 2.5 : 0.6)), color: ds.map((d: any) => (d.pareto_true ? "#111" : "rgba(30,40,35,.5)")) } } };
    }).filter((x) => x.x.length);
    const bl = Object.entries(result.baseline_repriced);
    if (bl.length) t.push({ type: "scatter", mode: "markers", name: "earlier optimum, priced with your prices", x: bl.map(([, v]) => v.cost_new_prices / 1e5), y: bl.map(([, v]) => v.carbon / 1000),
      text: bl.map(([k, v]) => `Earlier ${k.replace("_", " ")} design (${v.concrete}/${v.steel}/${v.cement})<br>₹${(v.cost_old_prices / 1e5).toFixed(2)} lakh with placeholder prices, ₹${(v.cost_new_prices / 1e5).toFixed(2)} lakh with yours`),
      hovertemplate: "%{text}<extra></extra>", marker: { symbol: "diamond-open", size: 15, color: "#111", line: { width: 2.5, color: "#111" } } });
    return t;
  }, [result, designs]);

  const layout = useMemo(() => ({ xaxis: { title: "Construction cost with your prices (₹ lakh)" }, yaxis: { title: "Embodied carbon (t CO₂e)" }, hovermode: "closest" }), []);
  const onClick = useCallback((pt: any) => { const d = designs.find((x) => x.id === pt.customdata); if (d) setPicked(d); }, [designs]);

  const groups = [...new Set(items.map((i) => i.group))];
  const pg = job?.progress;
  const frac = !pg || !pg.n_gen ? 0 : pg.stage === "verifying" ? 0.95 : Math.min(0.92, (pg.gen ?? 0) / pg.n_gen);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Change prices, then optimise"
        title="Optimise with your own prices"
        lead="Every price in this project is a placeholder. Type your local rates, move a slider or load a CSV file, then run the optimiser again: the best designs are re-searched with your prices and re-checked with the exact IS 456 model."
        howTo={[
          "Step 1: set the unit prices. A price you change turns green; “reset” returns it to the placeholder value.",
          "Step 2: press Optimise. It needs the local server (python -m rcopt.cli serve); on a static website you can still edit and download the prices as CSV and run the command shown below.",
          "Step 3: read the results. Every listed design passes all IS 456 checks (gravity loads) with the exact finite-element model.",
        ]}
      />
      <GravityCaveat />

      <Section eyebrow="Step 1" title="Set the unit prices" hint="All default values are placeholders, not verified market rates. Slider range: half to twice the placeholder.">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <input ref={fileRef} type="file" accept=".csv,text/csv,text/plain" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          <button className="btn" onClick={() => fileRef.current?.click()}>Load prices from a CSV file</button>
          <button className="btn" onClick={() => download("prices.csv", toCsv(items, vals), "text/csv")}>Download these prices (CSV)</button>
          <button className="btn" onClick={() => { setVals(defaults); setMsg(null); }} disabled={!changed.length}>Reset all to placeholders</button>
          <span className="text-sm muted">{changed.length ? `${changed.length} price(s) changed` : "all prices are the placeholder defaults"}</span>
        </div>
        {msg && <div className="mb-3 text-sm" style={{ color: msg.tone === "good" ? "var(--good)" : "var(--bad)" }}>{msg.text}</div>}
        <div className="grid gap-4 md:grid-cols-2">
          {groups.map((g) => (
            <div key={g} className="card-soft">
              <div className="eyebrow mb-2">{g}</div>
              <div className="space-y-3">
                {items.filter((i) => i.group === g).map((i) => {
                  const diff = Math.abs(vals[i.key] - i.default) > 1e-9;
                  return (
                    <div key={i.key}>
                      <div className="flex items-center justify-between gap-2 text-sm">
                        <label htmlFor={i.key}>{i.label} <span className="tag tag-warn ml-1">placeholder</span></label>
                        <div className="flex items-center gap-1">
                          <input id={i.key} type="number" min={0} step="any" className="input !w-28 text-right" style={diff ? { borderColor: "var(--good)", background: "#eef7e9" } : undefined}
                            value={vals[i.key]} onChange={(e) => { const x = Number(e.target.value); if (Number.isFinite(x)) setVals({ ...vals, [i.key]: x }); }} />
                          <span className="w-12 text-xs muted">{i.unit}</span>
                        </div>
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <input type="range" aria-label={`${i.label} slider`} className="w-full accent-[#53ac35]" min={i.default * 0.5} max={i.default * 2} step={i.default / 100}
                          value={Math.min(Math.max(vals[i.key], i.default * 0.5), i.default * 2)} onChange={(e) => setVals({ ...vals, [i.key]: Number(Number(e.target.value).toPrecision(5)) })} />
                        <button className="text-xs underline muted" disabled={!diff} onClick={() => setVals({ ...vals, [i.key]: i.default })}>reset</button>
                      </div>
                      <div className="text-[11px] muted">placeholder: {i.default} {i.unit}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs muted">Concrete rates are taken to include the baseline cement (PPC); a design that uses another cement pays (price − baseline price) × the cement content of its grade. Carbon factors are not editable here (they come from <code>config/carbon_factors.yaml</code>).</p>
      </Section>

      <Section eyebrow="Step 2" title="Optimise with these prices" hint="Quick: about 1.5 minutes. Thorough: about 5 minutes. Both use the validated surrogate with a safety margin, then re-check every design exactly.">
        <div className="card">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm">Effort&nbsp;
              <select className="input !w-auto" value={mode} onChange={(e) => setMode(e.target.value as "quick" | "standard")} disabled={running}>
                <option value="quick">Quick (population 100 × 60 generations)</option>
                <option value="standard">Thorough (population 200 × 150 generations)</option>
              </select>
            </label>
            <button className="btn-primary" disabled={!ready || running} onClick={run}>{running ? "Optimising…" : "Optimise with these prices"}</button>
            {running && <span className="text-sm muted">{pg?.stage === "verifying" ? "re-checking the best designs with the exact model…" : pg?.stage === "loading" || !pg?.gen ? "loading the models…" : `generation ${pg.gen} of ${pg.n_gen}`} · {num(job?.elapsed_s, 0)} s</span>}
          </div>
          {running && <div className="mt-3 h-2 w-full overflow-hidden rounded-full" style={{ background: "var(--accent-soft)" }}><div className="h-full" style={{ width: `${Math.round(frac * 100)}%`, background: "var(--accent)", transition: "width .6s" }} /></div>}
          {!ready && (
            <div className="mt-3 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--warn)", background: "#fbf5e6" }}>
              {h === undefined ? "Looking for the local server…" : h === null
                ? <>The local server is not reachable, so this page can only prepare the prices. Download them above and run <code>python -m rcopt.cli reoptimize --prices prices.csv</code>, or start everything with <code>python -m rcopt.cli serve</code>.</>
                : <>The server is running but the trained surrogate models are missing (<code>models/</code>): run <code>python -m rcopt.cli phase3</code> or unzip <code>models.zip</code>.</>}
              <div className="mt-2 flex gap-2">
                <input className="input max-w-xs" value={base} placeholder="http://192.168.1.20:8000" onChange={(e) => setBase(e.target.value)} />
                <button className="btn" onClick={() => { saveBase(base); health(base).then(setH); }}>Connect</button>
              </div>
            </div>
          )}
          {(err || job?.status === "failed") && <div className="mt-3 text-sm" style={{ color: "var(--bad)" }}>The optimisation failed: {err || job?.error}</div>}
        </div>
      </Section>

      {result && best && green && (
        <Section eyebrow="Step 3" title="Results with your prices" hint="Black outline = non-dominated among the checked designs (the cost-carbon trade-off front). Open diamonds: the designs that were optimal with the placeholder prices, priced with yours.">
          <div className="grid gap-3 md:grid-cols-4">
            <Stat label="Designs found" value={`${result.n_feasible_true}`} sub={`all pass IS 456 (exact model); ${result.rejected} rejected on re-check`} tone="good" />
            <Stat label="Lowest cost" value={lakh(best.true_cost)} sub={`${best.concrete} · ${best.steel} · ${best.cement} · ${num((best.true_carbon ?? 0) / 1000, 1)} t CO₂e`} />
            <Stat label="Lowest carbon" value={`${tonnes(green.true_carbon)} CO₂e`} sub={`${green.concrete} · ${green.steel} · ${green.cement} · ${lakh(green.true_cost)}`} />
            <Stat label="Trade-off points" value={`${front.length}`} sub={front.length < 3 ? "cost and carbon still move together with these prices" : "designs where cost and carbon pull apart"} tone={front.length < 3 ? "warn" : "good"} />
          </div>
          <div className="card mt-4"><Plot data={traces} dark={dark} height={460} layout={layout} onClick={onClick} /></div>
          {Object.keys(result.changed).length > 0 && Object.keys(result.baseline_repriced).length > 0 && (
            <p className="mt-2 text-sm">
              The design that was cheapest with the placeholder prices costs {lakh(result.baseline_repriced.lowest_cost?.cost_new_prices)} with yours
              (it was {lakh(result.baseline_repriced.lowest_cost?.cost_old_prices)}); the cheapest design found now costs {lakh(best.true_cost)}.
            </p>
          )}
          <div className="mt-4"><FrontTable rows={designs.map((d) => ({ v: "custom", d }))} labels={{ custom: "Your prices" }} onPick={(r) => setPicked(r.d)} /></div>
          {picked && (
            <div className="card-soft mt-4">
              <div className="mb-2 flex items-center justify-between"><span className="eyebrow">Selected design #{picked.id}</span><button className="btn" onClick={() => setPicked(null)}>Close</button></div>
              <DesignDetails d={picked} label="Your-price optimisation" />
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn" onClick={() => download("optimised_designs_your_prices.json", JSON.stringify(result, null, 1), "application/json")}>Download the results (JSON)</button>
            <button className="btn" onClick={() => download("prices_used.csv", toCsv(items, result.prices), "text/csv")}>Download the prices used (CSV)</button>
          </div>
          <p className="mt-3 text-xs muted">{result.note} Run: {result.mode}, population {result.pop_size} × {result.n_gen} generations, {num(result.wall_s, 0)} s. The five-seed study of the Pareto explorer stays the reference result; this run is a quick re-search for your prices.</p>
        </Section>
      )}
    </div>
  );
}
