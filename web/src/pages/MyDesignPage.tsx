import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import PageHeader, { Section } from "../components/PageHeader";
import FrontTable from "../components/FrontTable";
import DesignDetails from "../components/DesignDetails";
import StrengthReview from "../components/StrengthReview";
import Suggestions, { pickSuggestions } from "../components/Suggestions";
import { reportHtml } from "../lib/report";
import type { ReviewReport } from "../lib/api";
import { Finding, Stat } from "../components/Caveat";
import { download, lakh, num, pct, tonnes } from "../format";
import { cloneRates, estimate, quantitiesFromGroups, type Group, type Quantities, type Rates } from "../lib/estimate";
import { parseStaad, type StaadModel } from "../lib/staad";
import { ZONE_COLORS, zoneOf, zoneShapes } from "../lib/zones";
import type { ParetoDesign } from "../types";

const STORE = "rcopt_user_rates_v2";
type Mode = "staad" | "design" | "manual";

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs muted">{hint}</p>}
    </div>
  );
}

/** Number input that turns green when it differs from the project value and offers a one-click reset. */
function Rate({ label, unit, value, base, onChange, step = 0.1 }: { label: string; unit: string; value: number; base: number; onChange: (v: number) => void; step?: number }) {
  const changed = Math.abs(value - base) > 1e-9;
  return (
    <div>
      <label className="label">{label} <span className="font-normal">({unit})</span></label>
      <div className="flex items-center gap-1">
        <input className="input" type="number" step={step} min={0} value={Number.isFinite(value) ? value : ""} onChange={(e) => onChange(parseFloat(e.target.value))}
          style={changed ? { borderColor: "var(--accent)", background: "var(--accent-soft)" } : undefined} />
        <button className="btn !px-2" title={`Reset to project value ${base}`} disabled={!changed} onClick={() => onChange(base)} aria-label="Reset">↺</button>
      </div>
      {changed && <p className="mt-0.5 text-[11px] muted">project value {base}</p>}
    </div>
  );
}

const statusTag = (s?: string) =>
  s === "provisional" ? <span className="tag tag-warn">provisional</span> : s === "secondary_source" ? <span className="tag tag-neutral">secondary source</span> : null;

export default function MyDesignPage() {
  const { factors, pareto, sample } = useData();
  const { dark } = useTheme();
  const base: Rates = useMemo(() => cloneRates(factors), [factors]);

  const [rates, setRates] = useState<Rates>(() => {
    try {
      const s = localStorage.getItem(STORE);
      if (s) {
        const r = JSON.parse(s) as Rates;
        if (r.cost?.concrete_per_m3 && r.carbon?.cement_per_kg && Object.keys(r.cost.concrete_per_m3).join() === factors.grades.join()) return r;
      }
    } catch { /* storage unavailable: use project values */ }
    return cloneRates(factors);
  });
  useEffect(() => {
    try { localStorage.setItem(STORE, JSON.stringify(rates)); } catch { /* ignore */ }
  }, [rates]);
  const setCost = (f: (c: Rates["cost"]) => void) => setRates((r) => { const n = JSON.parse(JSON.stringify(r)) as Rates; f(n.cost); return n; });
  const setCarbon = (f: (c: Rates["carbon"]) => void) => setRates((r) => { const n = JSON.parse(JSON.stringify(r)) as Rates; f(n.carbon); return n; });
  const nChanged = JSON.stringify(rates) !== JSON.stringify(base);

  const [mode, setMode] = useState<Mode>("staad");
  const [model, setModel] = useState<StaadModel | null>(null);
  const [staadText, setStaadText] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewReport | null>(null);
  const [reviewKey, setReviewKey] = useState("");
  const [picked, setPicked] = useState<{ v: string; d: ParetoDesign } | null>(null);
  const [tableFronts, setTableFronts] = useState<string[]>(["B_margin", "direct"]);
  const [fileName, setFileName] = useState("");
  const [manual, setManual] = useState<Group[]>([
    { kind: "beam", b_mm: 300, D_mm: 450, count: 155, total_length_m: 775 },
    { kind: "column", b_mm: 450, D_mm: 450, count: 100, total_length_m: 260 },
  ]);
  const optimal = useMemo(() => [...pareto.variants.B_margin, ...pareto.variants.direct].filter((d) => d.feasible_true && d.quantities).sort((a, b) => (a.true_cost as number) - (b.true_cost as number)), [pareto]);
  const [designIdx, setDesignIdx] = useState(0);
  const chosen: ParetoDesign | undefined = optimal[designIdx];

  const [grade, setGrade] = useState("M30");
  const [steel, setSteel] = useState("Fe500");
  const [cement, setCement] = useState("PPC");
  const [beamSteel, setBeamSteel] = useState(factors.defaults.beam_steel_kg_per_m3);
  const [colSteel, setColSteel] = useState(factors.defaults.column_steel_kg_per_m3);
  const [slabT, setSlabT] = useState(factors.defaults.slab_thickness_mm);
  const [deduct, setDeduct] = useState(true);

  const loadText = (text: string, name: string) => {
    setStaadText(text);
    setReview(null);
    setModel(parseStaad(text));
    setFileName(name);
    setMode("staad");
  };
  const onFile = async (f: File | undefined) => { if (f) loadText(await f.text(), f.name); };
  const pickDesign = (i: number) => {
    setDesignIdx(i);
    const d = optimal[i];
    if (d) { setGrade(d.concrete); setSteel(d.steel); setCement(d.cement); }
  };

  const currentKey = `${grade}|${steel}|${cement}`;
  const reviewStale = !!review && reviewKey !== currentKey;
  const q: Quantities | null = useMemo(() => {
    if (mode === "design") {
      const x = chosen?.quantities;
      return x ? { concrete_m3: x.concrete_m3, beam_concrete_m3: x.beam_concrete_m3, column_concrete_m3: x.column_concrete_m3, steel_kg: x.steel_kg, beam_steel_kg: x.beam_steel_kg, column_steel_kg: x.column_steel_kg, formwork_m2: x.formwork_m2 } : null;
    }
    if (mode === "staad" && review && !reviewStale) return review.quantities as unknown as Quantities;   // designed bars replace the assumed steel
    if (mode === "staad" && review && !reviewStale) return review.quantities as unknown as Quantities;   // designed bars replace the assumed steel
    const groups: Group[] = mode === "staad" ? (model?.groups ?? []) : manual;
    if (!groups.length) return null;
    return quantitiesFromGroups(groups, { beamSteelKgM3: beamSteel, columnSteelKgM3: colSteel, slabThicknessMm: slabT, deductColumnFromBeams: deduct, netSideFormwork: factors.defaults.beam_side_formwork_net_of_slab });
  }, [mode, chosen, model, manual, beamSteel, colSteel, slabT, deduct, factors, review, reviewStale]);

  const est = useMemo(() => (q ? estimate(q, grade, steel, cement, rates) : null), [q, grade, steel, cement, rates]);

  // zones are measured against the best designs of the optimiser (same definition as the Pareto explorer)
  const ideal = useMemo(() => {
    let c = Infinity, k = Infinity;
    for (const v of Object.keys(pareto.variants)) for (const d of pareto.variants[v]) if (d.feasible_true && d.true_cost != null) { c = Math.min(c, d.true_cost / 1e5); k = Math.min(k, (d.true_carbon as number) / 1000); }
    return { cost: c, carbon: k };
  }, [pareto]);
  const BEST = 4, GOOD = 10;
  const me = est ? { x: est.cost.total / 1e5, y: est.carbon.total / 1000 } : null;
  const zone = me ? zoneOf(me.x, me.y, ideal, BEST, GOOD) : null;
  const comparable = !!me && me.x < ideal.cost * 2.5 && me.x > ideal.cost * 0.4;

  const ref = factors.best_reference.lowest_cost;
  const refQ = ref?.quantities;
  const delta = (a: number, b: number) => (b ? a / b - 1 : NaN);
  const intens = est && q ? { costPerM3: est.cost.total / q.concrete_m3, carbonPerM3: est.carbon.total / q.concrete_m3, steelPerM3: q.steel_kg / q.concrete_m3 } : null;
  const refIntens = ref && refQ ? { costPerM3: ref.cost / refQ.concrete_m3, carbonPerM3: ref.carbon / refQ.concrete_m3, steelPerM3: refQ.steel_kg / refQ.concrete_m3 } : null;

  const exportCsv = () => {
    if (!q || !est) return;
    const rows = [["item", "value", "unit"], ["source", mode === "staad" ? fileName || "STAAD file" : mode === "design" ? `optimiser design #${chosen?.id}` : "manual", ""],
      ["concrete grade", grade, ""], ["steel grade", steel, ""], ["cement type", cement, ""], ["concrete", q.concrete_m3.toFixed(2), "m3"], ["reinforcement", q.steel_kg.toFixed(0), "kg"],
      ["formwork", q.formwork_m2.toFixed(0), "m2"], ["cost concrete", est.cost.concrete.toFixed(0), "INR"], ["cost steel", est.cost.steel.toFixed(0), "INR"], ["cost formwork", est.cost.formwork.toFixed(0), "INR"],
      ["cost total", est.cost.total.toFixed(0), "INR"], ["carbon concrete", est.carbon.concrete.toFixed(0), "kgCO2e"], ["carbon steel", est.carbon.steel.toFixed(0), "kgCO2e"],
      ["carbon transport", est.carbon.transport.toFixed(0), "kgCO2e"], ["carbon total", est.carbon.total.toFixed(0), "kgCO2e"]];
    download("my_design_estimate.csv", rows.map((r) => r.join(",")).join("\n"), "text/csv");
  };

  const plotData = useMemo(() => {
    const pts = [...pareto.variants.B_margin, ...pareto.variants.direct].filter((d) => d.feasible_true && d.true_cost != null);
    const t: any[] = [{ type: "scatter", mode: "markers", name: "optimised designs (all pass IS 456 checks)", x: pts.map((d) => d.true_cost! / 1e5), y: pts.map((d) => d.true_carbon! / 1000), marker: { size: 8, color: "#2f7d5b", opacity: 0.55 }, hoverinfo: "skip" }];
    if (me) t.push({ type: "scatter", mode: "markers+text", name: "your design", x: [me.x], y: [me.y], text: ["your design"], textposition: "top center", marker: { symbol: "star", size: 20, color: "#1d2723", line: { color: "#fff", width: 1.5 } } });
    return t;
  }, [pareto, me]);
  const plotLayout = useMemo(() => {
    const xmax = Math.max(ideal.cost * 1.18, (me?.x ?? 0) * 1.06);
    const ymax = Math.max(ideal.carbon * 1.18, (me?.y ?? 0) * 1.06);
    return {
      xaxis: { title: "Cost (₹ lakh)", range: [ideal.cost * 0.97, xmax] }, yaxis: { title: "Carbon (t CO₂e)", range: [ideal.carbon * 0.97, ymax] },
      shapes: zoneShapes(ideal, BEST, GOOD, xmax * 2, ymax * 2), legend: { orientation: "h", y: -0.25 },
    };
  }, [ideal, me]);

  const suggestions = useMemo(() => {
    const rows = [
      ...pareto.variants.B_margin.map((d) => ({ v: "B_margin", d })),
      ...pareto.variants.direct.map((d) => ({ v: "direct", d })),
      ...pareto.variants.B.map((d) => ({ v: "B", d })),
    ];
    return pickSuggestions(rows, ideal, 8);
  }, [pareto, ideal]);
  const html = () => reportHtml({
    source: mode === "staad" ? fileName || "STAAD file" : mode === "design" ? `optimiser design #${chosen?.id}` : "manual member totals",
    grade, steel, cement, q: q!, est: est!,
    steelBasis: mode === "design" ? "from the optimiser (designed bars)" : review && !reviewStale ? "designed by the strength review (IS 456)" : `ASSUMED ${num(beamSteel, 0)} kg/m3 (beams), ${num(colSteel, 0)} kg/m3 (columns)`,
    review: review && !reviewStale ? review : null, zone: zone ? ZONE_COLORS[zone].label : null, reference: ref ? { cost: ref.cost, carbon: ref.carbon } : null,
    suggestions: suggestions.map((s) => ({ tag: s.tag, front: pareto.labels[s.v] ?? s.v, cost: s.d.true_cost!, carbon: s.d.true_carbon!, materials: `${s.d.concrete}/${s.d.steel}/${s.d.cement}`,
      beams: s.d.beams.map((b) => `${b.b_mm}x${b.D_mm} (${b.bottom} / ${b.top})`).join("; "), columns: s.d.columns.map((c) => `${c.b_mm}x${c.D_mm} (${c.bars})`).join("; ") })),
    changedRates: nChanged ? ["see the green price and factor fields in the app"] : [],
    provisionalNote: "Prices, cement content, transport and several carbon inputs are provisional placeholders; absolute INR and kgCO2e are indicative. Gravity loads only.",
  });
  const groupsShown: Group[] = mode === "staad" ? (model?.groups ?? []) : mode === "manual" ? manual : [];
  const needsAssumptions = mode !== "design";

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Your own design"
        title="My design estimate"
        lead="Bring a frame of your own and get its concrete, steel and formwork quantities, its cost and its embodied carbon, then compare it with the optimised designs. Every price and factor can be changed and the answer updates immediately."
        howTo={[
          "Step 1: choose where your design comes from: upload a STAAD input file (.std), try the sample file, start from one of the optimised designs, or type member totals by hand.",
          "Step 2: confirm the materials (concrete grade, steel grade, cement type) and the reinforcement assumption. A STAAD file contains member sizes but no reinforcement, so a steel quantity per m³ of concrete is assumed; the default is the median of the optimised designs.",
          "Step 3: for a STAAD file, run the strength review (it needs the local server, see the panel): it checks your member sizes against IS 456, designs the reinforcement and says so if the sizes are inadequate.",
          "Step 4: change any price or carbon factor (green fields differ from the project values; ↺ resets one, “Reset all” resets everything). Your changes are remembered in this browser only.",
          "The results panel on the right is live. It shows quantities, cost, carbon, how you compare with the best optimised design, and where you sit on the bad / good / best map.",
          "Important: this is a quantity, cost and carbon estimate. It does NOT check strength; the optimised designs are the ones that were checked against IS 456 (gravity loads only).",
        ]}
      />

      <div className="grid gap-5 xl:grid-cols-5">
        {/* ------------------------------------------------------------------ inputs */}
        <div className="space-y-5 xl:col-span-3">
          <section className="card">
            <div className="eyebrow">Step 1</div>
            <h2 className="h2">Choose your starting point</h2>
            <div className="mt-3 grid gap-2 md:grid-cols-3" role="tablist">
              {([
                ["staad", "Upload a STAAD file", "Reads geometry and section sizes from a STAAD.Pro .std input (text)."],
                ["design", "Start from an optimised design", "Use a design from the optimiser (reinforcement known) and change prices or materials."],
                ["manual", "Type member totals", "No file: enter section sizes and total member lengths yourself."],
              ] as [Mode, string, string][]).map(([m, t, d]) => (
                <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`rounded-xl border p-3 text-left transition-colors ${mode === m ? "border-[color:var(--accent)] bg-[color:var(--accent-soft)]" : ""}`} style={mode === m ? undefined : { borderColor: "var(--line)" }}>
                  <div className="text-sm font-semibold">{t}</div>
                  <div className="mt-0.5 text-xs muted">{d}</div>
                </button>
              ))}
            </div>

            {mode === "staad" && (
              <div className="mt-4 space-y-3">
                <div className="flex flex-wrap items-end gap-3">
                  <Field label="STAAD input file (.std / .STD text)">
                    <input className="input" type="file" accept=".std,.STD,.txt,text/plain" onChange={(e) => onFile(e.target.files?.[0])} />
                  </Field>
                  {sample && <button className="btn" onClick={() => loadText(sample.text, sample.name)}>Load the sample (project’s G+3 model)</button>}
                </div>
                {!model && <p className="text-sm muted">No file loaded yet. Your file never leaves your computer: it is read in the browser.</p>}
                {model && (
                  <div className="space-y-2">
                    <div className="text-sm"><b>{fileName}</b>: {model.joints} joints, {model.members.length} members, vertical axis {model.verticalAxis.toUpperCase()}, length unit {model.lengthUnit}.</div>
                    {model.warnings.map((w, i) => <Finding key={i} level="warn" text={w} />)}
                  </div>
                )}
              </div>
            )}

            {mode === "design" && (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <Field label="Optimised design" hint="Sorted from cheapest to dearest; every one passes all IS 456 checks (gravity only).">
                  <select className="input" value={designIdx} onChange={(e) => pickDesign(+e.target.value)}>
                    {optimal.map((d, i) => <option key={`${d.id}-${i}`} value={i}>{`#${d.id} · ${lakh(d.true_cost)} · ${tonnes(d.true_carbon)} CO₂e · ${d.concrete}/${d.steel}/${d.cement}`}</option>)}
                  </select>
                </Field>
                {chosen && <div className="card-soft text-sm">Beams {chosen.beams.map((b) => `${b.b_mm}×${b.D_mm}`).join(" / ")} mm · columns {chosen.columns.map((c) => `${c.b_mm}×${c.D_mm}`).join(" / ")} mm · reinforcement from the optimiser.</div>}
              </div>
            )}

            {mode === "manual" && (
              <div className="mt-4 space-y-2">
                <div className="table-wrap">
                  <table className="t">
                    <thead><tr><th>Member type</th><th>Width b (mm)</th><th>Depth D (mm)</th><th>Number</th><th>Total length (m)</th><th /></tr></thead>
                    <tbody>
                      {manual.map((g, i) => (
                        <tr key={i}>
                          <td><select className="input" value={g.kind} onChange={(e) => setManual(manual.map((x, k) => (k === i ? { ...x, kind: e.target.value as Group["kind"] } : x)))}><option value="beam">beam</option><option value="column">column</option></select></td>
                          {(["b_mm", "D_mm", "count", "total_length_m"] as const).map((f) => (
                            <td key={f}><input className="input" type="number" min={0} value={g[f]} onChange={(e) => setManual(manual.map((x, k) => (k === i ? { ...x, [f]: parseFloat(e.target.value) || 0 } : x)))} /></td>
                          ))}
                          <td><button className="btn" onClick={() => setManual(manual.filter((_, k) => k !== i))} aria-label="Remove row">✕</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button className="btn" onClick={() => setManual([...manual, { kind: "beam", b_mm: 300, D_mm: 450, count: 1, total_length_m: 10 }])}>+ Add a row</button>
                <p className="text-xs muted">Pre-filled with the project frame (155 beams, 775 m; 100 columns, 260 m). Use centre-line lengths.</p>
              </div>
            )}

            {groupsShown.length > 0 && mode === "staad" && (
              <div className="mt-4">
                <div className="label">Member groups found in the file</div>
                <div className="table-wrap" style={{ maxHeight: 260 }}>
                  <table className="t">
                    <thead><tr><th>Type</th><th className="num">Size b × D (mm)</th><th className="num">Members</th><th className="num">Total length (m)</th></tr></thead>
                    <tbody>{groupsShown.map((g) => <tr key={`${g.kind}${g.b_mm}${g.D_mm}`}><td className="capitalize">{g.kind}</td><td className="num">{g.b_mm} × {g.D_mm}</td><td className="num">{g.count}</td><td className="num">{num(g.total_length_m, 1)}</td></tr>)}</tbody>
                  </table>
                </div>
                <p className="mt-1 text-xs muted">Members are classed as columns when they are close to vertical, otherwise beams. STAAD “YD” is read as the depth and “ZD” as the width of beams; for columns the smaller side is the width.</p>
              </div>
            )}
          </section>

          <section className="card">
            <div className="eyebrow">Step 2</div>
            <h2 className="h2">Materials and assumptions</h2>
            <div className="mt-3 grid gap-4 md:grid-cols-3">
              <Field label="Concrete grade" hint="IS 456 Table 5: M25 is the minimum for moderate exposure.">
                <select className="input" value={grade} onChange={(e) => setGrade(e.target.value)}>{factors.grades.map((g) => <option key={g}>{g}</option>)}</select>
              </Field>
              <Field label="Reinforcement grade">
                <select className="input" value={steel} onChange={(e) => setSteel(e.target.value)}>{factors.steels.map((g) => <option key={g}>{g}</option>)}</select>
              </Field>
              <Field label="Cement type" hint="OPC, PPC (fly-ash blend) or PSC (slag blend): changes cost and carbon only.">
                <select className="input" value={cement} onChange={(e) => setCement(e.target.value)}>{factors.cements.map((g) => <option key={g}>{g}</option>)}</select>
              </Field>
            </div>
            {needsAssumptions && review && !reviewStale ? (
              <p className="mt-3 text-sm muted">Reinforcement comes from the strength review (designed bars), so the steel-per-m³ assumption is not used.</p>
            ) : needsAssumptions ? (
              <div className="mt-4 grid gap-4 md:grid-cols-4">
                <Field label="Beam steel (kg per m³ of beam concrete)" hint={`Default ${num(factors.defaults.beam_steel_kg_per_m3, 0)}: median of the optimised designs.`}>
                  <input className="input" type="number" min={0} value={beamSteel} onChange={(e) => setBeamSteel(parseFloat(e.target.value) || 0)} />
                </Field>
                <Field label="Column steel (kg per m³ of column concrete)" hint={`Default ${num(factors.defaults.column_steel_kg_per_m3, 0)}.`}>
                  <input className="input" type="number" min={0} value={colSteel} onChange={(e) => setColSteel(parseFloat(e.target.value) || 0)} />
                </Field>
                <Field label="Slab thickness for beam formwork (mm)" hint="Beam side formwork is the depth below the slab.">
                  <input className="input" type="number" min={0} value={slabT} onChange={(e) => setSlabT(parseFloat(e.target.value) || 0)} />
                </Field>
                <Field label="Beam length" hint="Subtract the column width from each beam (clear span), as the optimiser does.">
                  <label className="flex items-center gap-2 pt-1 text-sm"><input type="checkbox" checked={deduct} onChange={(e) => setDeduct(e.target.checked)} /> clear span between columns</label>
                </Field>
              </div>
            ) : (
              <p className="mt-3 text-xs muted">Reinforcement and formwork of an optimised design are known exactly, so no assumption is needed. Changing the grade, steel or cement here is a what-if (strength is not re-checked).</p>
            )}
          </section>

          {mode === "staad" ? (
            <StrengthReview staadText={staadText} grade={grade} steel={steel} cement={cement} report={review} stale={reviewStale}
              onReport={(r) => { setReview(r); setReviewKey(currentKey); }} />
          ) : (
            <section className="card">
              <div className="eyebrow">Step 3</div>
              <h2 className="h2">Strength review</h2>
              <p className="mt-1 text-sm muted">{mode === "design" ? "Optimised designs were already checked against IS 456 with the finite-element model (see the Pareto explorer), so no further review is needed." : "The strength review runs on a STAAD input of a regular frame: choose “Upload a STAAD file” in Step 1."}</p>
            </section>
          )}

          <section className="card">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="eyebrow">Step 4</div>
                <h2 className="h2">Prices and carbon factors (editable)</h2>
                <p className="mt-0.5 text-sm muted">Green fields differ from the project values. Prices are placeholders, so replace them with your own quotes (to re-run the optimiser with them use “Optimise with my prices”).</p>
              </div>
              <button className="btn" disabled={!nChanged} onClick={() => setRates(cloneRates(factors))}>Reset all to project values</button>
            </div>
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold">Cost {statusTag(factors.cost.status.concrete)}</div>
                <div className="grid grid-cols-2 gap-3">
                  {factors.grades.map((g) => <Rate key={g} label={`Concrete ${g}`} unit="₹/m³" step={50} value={rates.cost.concrete_per_m3[g]} base={base.cost.concrete_per_m3[g]} onChange={(v) => setCost((c) => { c.concrete_per_m3[g] = v; })} />)}
                  {factors.steels.map((g) => <Rate key={g} label={`Reinforcement ${g}`} unit="₹/kg" value={rates.cost.steel_per_kg[g]} base={base.cost.steel_per_kg[g]} onChange={(v) => setCost((c) => { c.steel_per_kg[g] = v; })} />)}
                  <Rate label="Formwork" unit="₹/m²" step={10} value={rates.cost.formwork_per_m2} base={base.cost.formwork_per_m2} onChange={(v) => setCost((c) => { c.formwork_per_m2 = v; })} />
                  {factors.cements.map((g) => <Rate key={g} label={`Cement ${g}`} unit="₹/kg" value={rates.cost.cement_price_per_kg[g]} base={base.cost.cement_price_per_kg[g]} onChange={(v) => setCost((c) => { c.cement_price_per_kg[g] = v; })} />)}
                </div>
                <p className="mt-2 text-xs muted">Concrete rates are taken to include the {factors.cost.cement_baseline} baseline cement; another cement type adds (its price − {factors.cost.cement_baseline} price) × the cement content of the grade.</p>
              </div>
              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold">Embodied carbon {statusTag(factors.carbon.status.cement)} <span className="font-normal muted">cement and steel from Indian secondary sources</span></div>
                <div className="grid grid-cols-2 gap-3">
                  {factors.cements.map((g) => <Rate key={g} label={`Cement ${g}`} unit="kgCO₂e/kg" step={0.01} value={rates.carbon.cement_per_kg[g]} base={base.carbon.cement_per_kg[g]} onChange={(v) => setCarbon((c) => { c.cement_per_kg[g] = v; })} />)}
                  {factors.steels.map((g) => <Rate key={g} label={`Reinforcement ${g}`} unit="kgCO₂e/kg" step={0.05} value={rates.carbon.steel_per_kg[g]} base={base.carbon.steel_per_kg[g]} onChange={(v) => setCarbon((c) => { c.steel_per_kg[g] = v; })} />)}
                  {factors.grades.map((g) => <Rate key={g} label={`Cement content ${g}`} unit="kg/m³" step={5} value={rates.carbon.cement_content_kg_m3[g]} base={base.carbon.cement_content_kg_m3[g]} onChange={(v) => setCarbon((c) => { c.cement_content_kg_m3[g] = v; })} />)}
                  <Rate label="Other concrete constituents" unit="kgCO₂e/m³" step={1} value={rates.carbon.concrete_other_per_m3} base={base.carbon.concrete_other_per_m3} onChange={(v) => setCarbon((c) => { c.concrete_other_per_m3 = v; })} />
                  <Rate label="Concrete transport distance" unit="km" step={5} value={rates.carbon.transport.concrete.distance_km} base={base.carbon.transport.concrete.distance_km} onChange={(v) => setCarbon((c) => { c.transport.concrete.distance_km = v; })} />
                  <Rate label="Steel transport distance" unit="km" step={25} value={rates.carbon.transport.steel.distance_km} base={base.carbon.transport.steel.distance_km} onChange={(v) => setCarbon((c) => { c.transport.steel.distance_km = v; })} />
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* ------------------------------------------------------------------ results */}
        <div className="space-y-5 xl:col-span-2">
          <div className="xl:sticky xl:top-4 space-y-5">
            {!q || !est ? (
              <section className="card py-10 text-center">
                <div className="text-3xl" aria-hidden>📐</div>
                <div className="h2 mt-2">Your estimate appears here</div>
                <p className="mt-1 text-sm muted">Load a STAAD file, pick an optimised design or enter member totals in Step 1.</p>
              </section>
            ) : (
              <>
                <section className="card">
                  <div className="eyebrow">Your estimate</div>
                  <div className="mt-2 grid grid-cols-2 gap-3">
                    <Stat label="Cost" value={lakh(est.cost.total)} sub={`concrete ${lakh(est.cost.concrete)} · steel ${lakh(est.cost.steel)} · formwork ${lakh(est.cost.formwork)}`} />
                    <Stat label="Embodied carbon" value={`${tonnes(est.carbon.total)} CO₂e`} sub={`concrete ${tonnes(est.carbon.concrete)} · steel ${tonnes(est.carbon.steel)} · transport ${tonnes(est.carbon.transport)}`} />
                    <Stat label="Concrete" value={`${num(q.concrete_m3, 1)} m³`} sub={`beams ${num(q.beam_concrete_m3, 1)} · columns ${num(q.column_concrete_m3, 1)}`} />
                    <Stat label="Reinforcement" value={tonnes(q.steel_kg)} sub={`${num(q.steel_kg / q.concrete_m3, 0)} kg per m³ of concrete · formwork ${num(q.formwork_m2, 0)} m²`} />
                  </div>
                  {zone && comparable && (
                    <div className="mt-3 flex items-center gap-2 text-sm">
                      <span className={`tag ${zone === "best" ? "tag-good" : zone === "good" ? "tag-warn" : "tag-bad"}`}>{ZONE_COLORS[zone].label} zone</span>
                      <span className="muted">{zone === "best" ? `within ${BEST} % of the optimiser’s best cost and carbon` : zone === "good" ? `within ${GOOD} % of the optimiser’s best` : `more than ${GOOD} % above the optimiser’s best on cost or carbon`}</span>
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className="btn" onClick={exportCsv}>Download CSV</button>
                    <button className="btn" onClick={() => window.print()}>Print</button>
                  </div>
                </section>

                <section className="card">
                  <h2 className="h2">Compared with the best optimised design</h2>
                  <p className="mb-2 mt-0.5 text-sm muted">The reference is the cheapest design that passes every IS 456 check, for the project’s 4 × 3 bay G+3 frame.</p>
                  {ref && refIntens && intens ? (
                    <div className="table-wrap" style={{ maxHeight: "none" }}>
                      <table className="t">
                        <thead><tr><th>Measure</th><th className="num">Yours</th><th className="num">Reference</th><th className="num">Difference</th></tr></thead>
                        <tbody>
                          <tr><td>Total cost</td><td className="num">{lakh(est.cost.total)}</td><td className="num">{lakh(ref.cost)}</td><td className="num">{pct(delta(est.cost.total, ref.cost))}</td></tr>
                          <tr><td>Total carbon</td><td className="num">{tonnes(est.carbon.total)}</td><td className="num">{tonnes(ref.carbon)}</td><td className="num">{pct(delta(est.carbon.total, ref.carbon))}</td></tr>
                          <tr><td>Cost per m³ of concrete</td><td className="num">₹{num(intens.costPerM3, 0)}</td><td className="num">₹{num(refIntens.costPerM3, 0)}</td><td className="num">{pct(delta(intens.costPerM3, refIntens.costPerM3))}</td></tr>
                          <tr><td>Carbon per m³ of concrete</td><td className="num">{num(intens.carbonPerM3, 0)} kg</td><td className="num">{num(refIntens.carbonPerM3, 0)} kg</td><td className="num">{pct(delta(intens.carbonPerM3, refIntens.carbonPerM3))}</td></tr>
                          <tr><td>Steel per m³ of concrete</td><td className="num">{num(intens.steelPerM3, 0)} kg</td><td className="num">{num(refIntens.steelPerM3, 0)} kg</td><td className="num">{pct(delta(intens.steelPerM3, refIntens.steelPerM3))}</td></tr>
                        </tbody>
                      </table>
                    </div>
                  ) : <p className="text-sm muted">Reference not available.</p>}
                  <p className="mt-2 text-xs muted">Totals are only comparable for a frame of similar size; the per-m³ rows are comparable for any frame. The reference uses the project rates, not your edited ones; your figures use your edits. The reference is designed for gravity loads only, whereas a real design may also be sized for seismic or wind, so a higher cost is not necessarily a flaw.</p>
                </section>

                <section className="card">
                  <h2 className="h2">Where you sit on the map</h2>
                  {comparable ? (
                    <>
                      <Plot data={plotData} dark={dark} height={330} layout={plotLayout} />
                      <p className="text-xs muted">Green = within {BEST} % of the best cost and carbon, yellow = within {GOOD} %, red = worse. The dots are optimised designs.</p>
                    </>
                  ) : <p className="text-sm muted">Your frame is much larger or smaller than the reference frame, so its position on the cost-carbon map is not meaningful. Compare the per-m³ rows instead.</p>}
                </section>

                <section className="card">
                  <h2 className="h2">What if…?</h2>
                  <p className="mb-2 mt-0.5 text-sm muted">Same quantities, different materials (strength is not re-checked).</p>
                  <div className="table-wrap" style={{ maxHeight: "none" }}>
                    <table className="t">
                      <thead><tr><th>Change</th><th className="num">Cost</th><th className="num">Carbon</th><th className="num">Cost Δ</th><th className="num">Carbon Δ</th></tr></thead>
                      <tbody>
                        {factors.cements.map((c) => { const e = estimate(q, grade, steel, c, rates); return (
                          <tr key={c} style={c === cement ? { background: "var(--accent-soft)" } : undefined}><td>Cement {c}{c === cement ? " (current)" : ""}</td><td className="num">{lakh(e.cost.total)}</td><td className="num">{tonnes(e.carbon.total)}</td><td className="num">{pct(delta(e.cost.total, est.cost.total))}</td><td className="num">{pct(delta(e.carbon.total, est.carbon.total))}</td></tr>
                        ); })}
                        {factors.grades.map((g) => { const e = estimate(q, g, steel, cement, rates); return (
                          <tr key={g} style={g === grade ? { background: "var(--accent-soft)" } : undefined}><td>Concrete {g}{g === grade ? " (current)" : ""}</td><td className="num">{lakh(e.cost.total)}</td><td className="num">{tonnes(e.carbon.total)}</td><td className="num">{pct(delta(e.cost.total, est.cost.total))}</td><td className="num">{pct(delta(e.carbon.total, est.carbon.total))}</td></tr>
                        ); })}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            )}
            <Finding level="warn" text="Estimate only: frame concrete, reinforcement and formwork (no slab, foundations or finishes), gravity-load design basis. Strength and serviceability of your own design are NOT checked here. Prices and several carbon inputs are provisional until you replace them." />
          </div>
        </div>
      </div>

      <Section eyebrow="Suggestions" title="Optimised designs you could use instead" hint="Several designs that pass every IS 456 check: the cheapest, the lowest-carbon, the best compromise, an FE-verified one, and designs spread along the front. Click a row for its full specification.">
        <Suggestions items={suggestions} mine={me ? { cost: me.x * 1e5, carbon: me.y * 1000 } : null} labels={pareto.labels}
          onUse={(d) => { setMode("design"); const i = optimal.findIndex((o) => o.id === d.id && o.true_cost === d.true_cost); pickDesign(i >= 0 ? i : 0); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
      </Section>

      <Section eyebrow="Reference data" title="Every design on the Pareto front and its feature values" hint="All points of the fronts you select, with every feature the optimiser chose or computed: materials, member sizes, reinforcement, stirrups, quantities, cost, carbon and the four code checks.">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {Object.keys(pareto.variants).map((n) => (
            <button key={n} className={`btn ${tableFronts.includes(n) ? "btn-on" : ""}`} onClick={() => setTableFronts(tableFronts.includes(n) ? tableFronts.filter((x) => x !== n) : [...tableFronts, n])}>{pareto.labels[n] ?? n} ({pareto.variants[n].length})</button>
          ))}
        </div>
        <FrontTable rows={tableFronts.flatMap((v) => pareto.variants[v].map((d) => ({ v, d })))} labels={pareto.labels} onPick={(r) => setPicked(r)} />
        {picked && (
          <div className="card-soft mt-4">
            <div className="mb-2 flex items-center justify-between"><span className="eyebrow">Selected row</span><button className="btn" onClick={() => setPicked(null)}>Close</button></div>
            <DesignDetails d={picked.d} label={pareto.labels[picked.v]} />
          </div>
        )}
      </Section>

      {q && est && (
        <Section eyebrow="Final report" title="Design review report" hint="Everything above in one document: strength review, quantities, cost and carbon, suggested designs and the assumptions. Download it as an HTML file or print it (choose Save as PDF in the print dialog).">
          <div className="grid gap-3 md:grid-cols-4">
            <Stat label="Strength" value={review && !reviewStale ? review.verdict : mode === "design" ? "PASS" : "not run"} tone={review && !reviewStale ? (review.verdict === "PASS" ? "good" : "bad") : mode === "design" ? "good" : "warn"}
              sub={mode === "design" ? "optimised designs pass all IS 456 checks" : review && !reviewStale ? "IS 456, gravity loads, designed bars" : "needs a STAAD file and the local server"} />
            <Stat label="Cost" value={lakh(est.cost.total)} sub={`${num(q.concrete_m3, 1)} m³ concrete · ${tonnes(q.steel_kg)} steel`} />
            <Stat label="Carbon" value={`${tonnes(est.carbon.total)} CO₂e`} sub={zone ? `${ZONE_COLORS[zone].label} zone vs the optimiser` : "zone n/a"} />
            <Stat label="Suggestions" value={`${suggestions.length}`} sub="optimised designs listed above" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn-primary" onClick={() => download("design_review_report.html", html(), "text/html")}>Download the report (HTML)</button>
            <button className="btn" onClick={() => { const w = window.open("", "_blank"); if (w) { w.document.write(html()); w.document.close(); w.focus(); w.print(); } }}>Print / save as PDF</button>
          </div>
        </Section>
      )}
    </div>
  );
}
