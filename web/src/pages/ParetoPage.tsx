import { useCallback, useMemo, useState } from "react";
import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import DesignDetails from "../components/DesignDetails";
import FrontTable from "../components/FrontTable";
import PageHeader, { Section } from "../components/PageHeader";
import { GravityCaveat } from "../components/Caveat";
import { download, lakh, palette, tonnes } from "../format";
import { ZONE_COLORS, excess, zoneOf, zoneShapes, type Zone } from "../lib/zones";
import type { ParetoDesign } from "../types";

type ColorBy = "concrete" | "steel" | "cement" | "beamD" | "colB" | "zone" | "none";
const SYMBOLS: Record<string, string> = { A: "circle", A_margin: "diamond", B: "square", B_margin: "triangle-up", direct: "cross" };
const GRADES = ["M25", "M30", "M35", "M40"];
const CEMENTS = ["OPC", "PPC", "PSC"];
const ZONE_CODE: Record<Zone, number> = { bad: 0, good: 1, best: 2 };

const xy = (d: ParetoDesign, basis: "true" | "pred") =>
  basis === "true" && d.true_cost != null ? [d.true_cost / 1e5, (d.true_carbon as number) / 1000] : [d.pred_cost / 1e5, d.pred_carbon / 1000];

export default function ParetoPage() {
  const { pareto } = useData();
  const { dark } = useTheme();
  const names = Object.keys(pareto.variants);
  const [shown, setShown] = useState<string[]>(["B_margin", "direct"]);
  const [by, setBy] = useState<ColorBy>("zone");
  const [basis, setBasis] = useState<"true" | "pred">("true");
  const [cloud, setCloud] = useState(false);
  const [bestPct, setBestPct] = useState(4);
  const [goodPct, setGoodPct] = useState(10);
  const [sel, setSel] = useState<{ v: string; i: number } | null>(null);

  // best achievable values over every truly feasible design of every front (the corner the zones are measured from)
  const ideal = useMemo(() => {
    let c = Infinity, k = Infinity;
    for (const v of names) for (const d of pareto.variants[v]) if (d.feasible_true && d.true_cost != null) { c = Math.min(c, d.true_cost / 1e5); k = Math.min(k, (d.true_carbon as number) / 1000); }
    return { cost: c, carbon: k };
  }, [pareto, names]);

  const zoneFor = (d: ParetoDesign): Zone => {
    const [x, y] = xy(d, basis);
    return zoneOf(x, y, ideal, bestPct, goodPct);
  };

  const shownDesigns = useMemo(() => shown.flatMap((v) => pareto.variants[v].map((d) => ({ v, d }))), [shown, pareto]);
  const featured = useMemo(() => {
    const ok = shownDesigns.filter((s) => s.d.feasible_true && s.d.true_cost != null);
    if (!ok.length) return [];
    const byCost = [...ok].sort((a, b) => (a.d.true_cost as number) - (b.d.true_cost as number))[0];
    const byCarbon = [...ok].sort((a, b) => (a.d.true_carbon as number) - (b.d.true_carbon as number))[0];
    const bal = [...ok].sort((a, b) => excess(a.d.true_cost! / 1e5, a.d.true_carbon! / 1000, ideal) - excess(b.d.true_cost! / 1e5, b.d.true_carbon! / 1000, ideal))[0];
    return [
      { title: "Lowest cost", why: "Cheapest design that passes every check among the fronts shown.", ...byCost },
      { title: "Lowest carbon", why: "Smallest embodied carbon among the fronts shown.", ...byCarbon },
      { title: "Best balance", why: "Closest to the best cost and the best carbon at the same time (smallest worst-case excess).", ...bal },
    ];
  }, [shownDesigns, ideal]);

  const hover = (d: ParetoDesign, v: string) => {
    const z = zoneFor(d);
    const u = d.utilisation;
    const b = d.beams.map((x) => `beam g${x.group}: ${x.b_mm}×${x.D_mm}, bot ${x.bottom}, top ${x.top}`).join("<br>");
    const c = d.columns.map((x) => `column g${x.group}: ${x.b_mm}×${x.D_mm}, ${x.bars}`).join("<br>");
    return `<b>#${d.id} · ${pareto.labels[v] ?? v}</b><br>${d.concrete} · ${d.steel} · ${d.cement} cement<br>${b}<br>${c}` +
      (d.quantities ? `<br>concrete ${d.quantities.concrete_m3.toFixed(1)} m³ · steel ${(d.quantities.steel_kg / 1000).toFixed(1)} t · formwork ${d.quantities.formwork_m2.toFixed(0)} m²` : "") +
      (u ? `<br>checks: bending ${u.U_flex_max.toFixed(2)} · shear ${u.U_shear_max.toFixed(2)} · column ${u.U_col_max.toFixed(2)} · deflection ${u.deflection_ratio.toFixed(2)}` : "") +
      `<br>${d.feasible_true ? "✓ passes all checks" : "✕ FAILS a check"}${d.verification.verified ? (d.verification.passed ? " · verified ✓" : " · verification ✕") : ""}` +
      `<br>zone: <b>${ZONE_COLORS[z].label}</b>`;
  };

  const axisRange = useMemo(() => {
    if (cloud) return {};
    const span = Math.max(goodPct * 2.2, 8) / 100;
    return {
      xaxis: { title: "Construction cost (₹ lakh, provisional rates)", range: [ideal.cost * 0.995, ideal.cost * (1 + span)] },
      yaxis: { title: "Embodied carbon (t CO₂e)", range: [ideal.carbon * 0.995, ideal.carbon * (1 + span)] },
    };
  }, [cloud, goodPct, ideal]);

  const data = useMemo(() => {
    const traces: any[] = [];
    if (cloud)
      traces.push({ type: "scatter", mode: "markers", name: "analysed designs (sample)", x: pareto.cloud.map((c) => c.cost / 1e5), y: pareto.cloud.map((c) => c.carbon / 1000), marker: { size: 4, color: pareto.cloud.map((c) => (c.feasible ? "rgba(47,125,91,0.30)" : "rgba(150,160,155,0.25)")) }, hoverinfo: "skip" });
    const cb: Record<string, any> = {
      concrete: { colorscale: GRADES.map((g, i) => [i / 3, palette.grade[g]]), cmin: 0, cmax: 3, colorbar: { title: "concrete", tickvals: [0, 1, 2, 3], ticktext: GRADES } },
      steel: { colorscale: [[0, palette.steel.Fe415], [1, palette.steel.Fe500]], cmin: 0, cmax: 1, colorbar: { title: "steel", tickvals: [0, 1], ticktext: ["Fe415", "Fe500"] } },
      cement: { colorscale: [[0, "#b4443c"], [0.5, "#b7791f"], [1, "#2f7d5b"]], cmin: 0, cmax: 2, colorbar: { title: "cement", tickvals: [0, 1, 2], ticktext: CEMENTS } },
      zone: { colorscale: [[0, "#b4443c"], [0.5, "#d9a62e"], [1, "#2f7d5b"]], cmin: 0, cmax: 2, colorbar: { title: "zone", tickvals: [0, 1, 2], ticktext: ["bad", "good", "best"] } },
      beamD: { colorscale: "Viridis", colorbar: { title: "beam D (mm)" } },
      colB: { colorscale: "Viridis", colorbar: { title: "column b (mm)" } },
    };
    const code = (d: ParetoDesign, v: string) => {
      switch (by) {
        case "concrete": return GRADES.indexOf(d.concrete);
        case "steel": return d.steel === "Fe415" ? 0 : 1;
        case "cement": return CEMENTS.indexOf(d.cement);
        case "zone": return ZONE_CODE[zoneFor(d)];
        case "beamD": return d.beams[0].D_mm;
        case "colB": return d.columns[0].b_mm;
        default: return v === "direct" ? 0 : 1;
      }
    };
    for (const v of shown) {
      const ds = pareto.variants[v];
      traces.push({
        type: "scatter", mode: "markers", name: pareto.labels[v] ?? v, x: ds.map((d) => xy(d, basis)[0]), y: ds.map((d) => xy(d, basis)[1]),
        customdata: ds.map((d) => [v, d.id]), text: ds.map((d) => hover(d, v)), hovertemplate: "%{text}<extra></extra>",
        marker: { symbol: SYMBOLS[v] ?? "circle", size: 10, color: ds.map((d) => code(d, v)), ...(by === "none" ? { color: palette.fronts[v] } : cb[by]),
          line: { width: ds.map((d) => (d.feasible_true ? 0.8 : 2.5)), color: ds.map((d) => (d.feasible_true ? "rgba(30,40,35,0.55)" : "#7a1f19")) } },
      });
      const ver = ds.filter((d) => d.verification.verified);
      const okv = ver.filter((d) => d.verification.passed);
      const bad = ver.filter((d) => !d.verification.passed);
      if (okv.length) traces.push({ type: "scatter", mode: "markers", name: "✓ verified by FE re-run", showlegend: v === shown[0], x: okv.map((d) => xy(d, basis)[0]), y: okv.map((d) => xy(d, basis)[1]), hoverinfo: "skip", marker: { symbol: "circle-open", size: 19, color: "#1d5a40", line: { color: "#1d5a40", width: 2.5 } } });
      if (bad.length) traces.push({ type: "scatter", mode: "markers", name: "✕ verification failed", showlegend: v === shown[0], x: bad.map((d) => xy(d, basis)[0]), y: bad.map((d) => xy(d, basis)[1]), hoverinfo: "skip", marker: { symbol: "x-thin-open", size: 19, color: "#b4443c", line: { color: "#b4443c", width: 3 } } });
    }
    return traces;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown, by, basis, cloud, pareto, bestPct, goodPct, ideal]);

  const layout = useMemo(() => {
    const xr: number[] = (axisRange as any).xaxis?.range ?? [ideal.cost * 0.9, ideal.cost * 3];
    const yr: number[] = (axisRange as any).yaxis?.range ?? [ideal.carbon * 0.9, ideal.carbon * 3];
    return {
      ...axisRange,
      shapes: zoneShapes(ideal, bestPct, goodPct, Math.max(xr[1], ideal.cost * 4), Math.max(yr[1], ideal.carbon * 4)),
      hovermode: "closest", legend: { orientation: "h", y: -0.22 }, hoverlabel: { align: "left" },
      ...(cloud ? { xaxis: { title: "Construction cost (₹ lakh, provisional rates)" }, yaxis: { title: "Embodied carbon (t CO₂e)" } } : {}),
    };
  }, [axisRange, ideal, bestPct, goodPct, cloud]);

  const onClick = useCallback((pt: any) => { if (pt.customdata) setSel({ v: pt.customdata[0], i: pt.customdata[1] }); }, []);
  const toggle = (n: string) => setShown(shown.includes(n) ? shown.filter((x) => x !== n) : [...shown, n]);
  const chosen = sel ? pareto.variants[sel.v].find((d) => d.id === sel.i) : null;

  const counts = (v: string) => {
    const c = { best: 0, good: 0, bad: 0 };
    pareto.variants[v].forEach((d) => { c[zoneFor(d)]++; });
    return c;
  };
  const frontCsv = (v: string) =>
    ["id,concrete,steel,cement,beam0_b,beam0_D,beam1_b,beam1_D,col0_b,col0_D,col1_b,col1_D,cost_inr_true,carbon_kgco2e_true,passes_all_checks"]
      .concat(pareto.variants[v].map((d) => [d.id, d.concrete, d.steel, d.cement, d.beams[0].b_mm, d.beams[0].D_mm, d.beams[1]?.b_mm, d.beams[1]?.D_mm, d.columns[0].b_mm, d.columns[0].D_mm, d.columns[1]?.b_mm, d.columns[1]?.D_mm, d.true_cost, d.true_carbon, d.feasible_true].join(",")))
      .join("\n");

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Main result"
        title="Pareto explorer"
        lead="Each point is a complete, code-checked frame design. Cheaper designs sit to the left, lower-carbon designs sit lower on the chart; the best compromises are in the green corner."
        howTo={[
          "Green, yellow and red areas show how close a design is to the best achievable cost and carbon: green = within the “best” percentage on BOTH objectives, yellow = within the “good” percentage, red = beyond. Change the percentages with the sliders.",
          "Hover a point to see every property of that design. Click it to pin the full property sheet on the right.",
          "A red outline means the design fails an IS 456 check; a green ring means it was re-run through the finite-element model and passed; a red cross means that re-run failed.",
          "The cards under the chart describe the best designs for the fronts you have switched on.",
        ]}
      />
      <GravityCaveat />

      <div className="card">
        <div className="grid gap-x-8 gap-y-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="xl:col-span-2">
            <span className="label">Fronts to display</span>
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Fronts">
              {names.map((n) => (
                <button key={n} className={`btn ${shown.includes(n) ? "btn-on" : ""}`} onClick={() => toggle(n)} aria-pressed={shown.includes(n)}>
                  {pareto.labels[n] ?? n} <span className="opacity-70">({pareto.variants[n].length})</span>
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs muted">“B + safety margin” is the best-validated optimiser; “Direct FE” is the slow ground-truth baseline.</p>
          </div>
          <div>
            <label className="label">Colour points by</label>
            <select className="input" value={by} onChange={(e) => setBy(e.target.value as ColorBy)}>
              <option value="zone">bad / good / best zone</option>
              <option value="concrete">concrete grade</option>
              <option value="steel">steel grade</option>
              <option value="cement">cement type</option>
              <option value="beamD">beam depth</option>
              <option value="colB">column size</option>
              <option value="none">front</option>
            </select>
          </div>
          <div>
            <label className="label">Cost and carbon shown are</label>
            <select className="input" value={basis} onChange={(e) => setBasis(e.target.value as "true" | "pred")}>
              <option value="true">ground truth (FE re-evaluation)</option>
              <option value="pred">as the optimiser predicted</option>
            </select>
          </div>
          <div>
            <label className="label">“Best” zone: within {bestPct} % of the optimum</label>
            <input type="range" min={0.5} max={10} step={0.5} value={bestPct} onChange={(e) => { const v = +e.target.value; setBestPct(v); if (goodPct <= v) setGoodPct(v + 1); }} className="w-full accent-[color:var(--accent)]" />
          </div>
          <div>
            <label className="label">“Good” zone: within {goodPct} % of the optimum</label>
            <input type="range" min={1} max={40} step={1} value={goodPct} onChange={(e) => { const v = +e.target.value; setGoodPct(v); if (bestPct >= v) setBestPct(Math.max(0.5, v - 1)); }} className="w-full accent-[color:var(--accent)]" />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={cloud} onChange={(e) => setCloud(e.target.checked)} /> Zoom out to all analysed designs
            </label>
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="card xl:col-span-2">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
            {(["best", "good", "bad"] as Zone[]).map((z) => (
              <span key={z} className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1" style={{ borderColor: "var(--line)" }}>
                <span className="inline-block h-3 w-3 rounded-sm" style={{ background: ZONE_COLORS[z].line, opacity: 0.8 }} />
                <b>{ZONE_COLORS[z].label}</b>
                {z === "best" && <span className="muted">≤ {bestPct} % above the optimum on both</span>}
                {z === "good" && <span className="muted">≤ {goodPct} %</span>}
                {z === "bad" && <span className="muted">worse</span>}
              </span>
            ))}
            <span className="muted">Optimum corner: {ideal.cost.toFixed(2)} ₹ lakh · {ideal.carbon.toFixed(1)} t CO₂e</span>
          </div>
          <Plot data={data} dark={dark} height={540} onClick={onClick} layout={layout} />
          <p className="mt-2 text-xs muted">
            Symbols: ○ A, ◇ A + margin, □ B, △ B + margin, ＋ direct FE. The optimum corner is the best cost and the best carbon found, which no single design reaches exactly.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="t">
              <thead><tr><th>Front</th><th className="num">Designs</th><th className="num">Best zone</th><th className="num">Good zone</th><th className="num">Bad zone</th></tr></thead>
              <tbody>
                {shown.map((v) => { const c = counts(v); return (
                  <tr key={v}><td className="font-medium">{pareto.labels[v] ?? v}</td><td className="num">{pareto.variants[v].length}</td><td className="num">{c.best}</td><td className="num">{c.good}</td><td className="num">{c.bad}</td></tr>
                ); })}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:self-start xl:overflow-y-auto">
          {chosen && sel ? (
            <div>
              <DesignDetails d={chosen} label={pareto.labels[sel.v] ?? sel.v} />
              <button className="btn mt-3" onClick={() => setSel(null)}>Clear selection</button>
            </div>
          ) : (
            <div className="py-10 text-center">
              <div className="text-3xl" aria-hidden>👆</div>
              <div className="h2 mt-2">Pick a design</div>
              <p className="mt-1 text-sm muted">Click any point on the chart to see everything about that design here: materials, member sizes, reinforcement, quantities, cost, carbon and the code checks.</p>
            </div>
          )}
        </div>
      </div>

      <Section title="Best cases among the fronts shown" hint="Three designs worth looking at first. Each card lists the full specification so it can be taken to the drawing board; click “Show on chart” to locate it.">
        <div className="grid gap-4 lg:grid-cols-3">
          {featured.map((f) => (
            <div key={f.title} className="card-soft">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="eyebrow">{f.title}</div>
                  <div className="text-lg font-semibold">{lakh(f.d.true_cost)} · {tonnes(f.d.true_carbon)} CO₂e</div>
                  <p className="text-xs muted">{f.why}</p>
                </div>
                <button className="btn shrink-0" onClick={() => setSel({ v: f.v, i: f.d.id })}>Show on chart</button>
              </div>
              <div className="mt-2"><DesignDetails d={f.d} label={pareto.labels[f.v]} compact /></div>
            </div>
          ))}
          {!featured.length && <p className="text-sm muted">Switch on at least one front above.</p>}
        </div>
      </Section>

      <Section eyebrow="All points" title="Feature values of every design on the fronts shown" hint="The full data behind the chart: each row is one point with its materials, member sizes, reinforcement, quantities, cost, carbon and code checks. Click a row to pin its property sheet at the top of the page.">
        <FrontTable rows={shownDesigns} labels={pareto.labels} onPick={(r) => { setSel({ v: r.v, i: r.d.id }); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
      </Section>

      <div className="flex flex-wrap gap-2">
        {names.map((n) => (
          <button key={n} className="btn" onClick={() => download(`front_${n}.csv`, frontCsv(n), "text/csv")}>Download CSV: {pareto.labels[n] ?? n}</button>
        ))}
      </div>
    </div>
  );
}
