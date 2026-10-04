import { useCallback, useMemo, useState } from "react";
import { useData } from "../data";
import { useTheme } from "../App";
import Plot from "../components/Plot";
import DesignDrawer from "../components/DesignDrawer";
import { GravityCaveat } from "../components/Caveat";
import { download, palette } from "../format";
import type { ParetoDesign } from "../types";

type ColorBy = "concrete" | "steel" | "cement" | "beamD" | "colB" | "none";
const SYMBOLS: Record<string, string> = { A: "circle", A_margin: "diamond", B: "square", B_margin: "triangle-up", direct: "cross" };
const GRADES = ["M20", "M25", "M30", "M35", "M40"];

function colorOf(d: ParetoDesign, by: ColorBy): number {
  switch (by) {
    case "concrete": return GRADES.indexOf(d.concrete);
    case "steel": return d.steel === "Fe415" ? 0 : 1;
    case "cement": return ["OPC", "PPC", "PSC"].indexOf(d.cement);
    case "beamD": return d.beams[0].D_mm;
    case "colB": return d.columns[0].b_mm;
    default: return 0;
  }
}

export default function ParetoPage() {
  const { pareto, meta } = useData();
  const { dark } = useTheme();
  const names = Object.keys(pareto.variants);
  const [shown, setShown] = useState<string[]>(["A", "direct"]);
  const [by, setBy] = useState<ColorBy>("concrete");
  const [basis, setBasis] = useState<"true" | "pred">("true");
  const [cloud, setCloud] = useState(true);
  const [sel, setSel] = useState<{ v: string; i: number } | null>(null);

  const xy = (d: ParetoDesign) =>
    basis === "true" && d.true_cost != null ? [d.true_cost / 1e5, (d.true_carbon as number) / 1000] : [d.pred_cost / 1e5, d.pred_carbon / 1000];

  const data = useMemo(() => {
    const traces: any[] = [];
    if (cloud)
      traces.push({
        type: "scatter", mode: "markers", name: "dataset designs (FE, sample)", x: pareto.cloud.map((c) => c.cost / 1e5), y: pareto.cloud.map((c) => c.carbon / 1000),
        marker: { size: 4, color: pareto.cloud.map((c) => (c.feasible ? "rgba(16,185,129,0.35)" : "rgba(148,163,184,0.25)")) }, hoverinfo: "skip",
      });
    const cb = by === "none" ? {} : (() => {
      if (by === "concrete") return { colorscale: GRADES.map((g, i) => [i / 4, palette.grade[g]]), cmin: 0, cmax: 4, colorbar: { title: "concrete", tickvals: [0, 1, 2, 3, 4], ticktext: GRADES } };
      if (by === "cement") return { colorscale: [[0, "#dc2626"], [0.5, "#0ea5e9"], [1, "#16a34a"]], cmin: 0, cmax: 2, colorbar: { title: "cement", tickvals: [0, 1, 2], ticktext: ["OPC", "PPC", "PSC"] } };
      if (by === "steel") return { colorscale: [[0, palette.steel.Fe415], [1, palette.steel.Fe500]], cmin: 0, cmax: 1, colorbar: { title: "steel", tickvals: [0, 1], ticktext: ["Fe415", "Fe500"] } };
      return { colorscale: "Viridis", colorbar: { title: by === "beamD" ? "beam D (mm), group 0" : "column b (mm), group 0" } };
    })();
    for (const v of shown) {
      const ds = pareto.variants[v];
      traces.push({
        type: "scatter", mode: "markers", name: pareto.labels[v] ?? v,
        x: ds.map((d) => xy(d)[0]), y: ds.map((d) => xy(d)[1]),
        customdata: ds.map((d) => [v, d.id]),
        text: ds.map((d) => `#${d.id} ${d.concrete}/${d.steel}/${d.cement}<br>beam ${d.beams[0].b_mm}×${d.beams[0].D_mm}, col ${d.columns[0].b_mm}×${d.columns[0].D_mm}<br>${d.feasible_true ? "✓ feasible" : "✕ INFEASIBLE"}${d.verification.verified ? (d.verification.passed ? " · verified ✓" : " · verification ✕") : ""}`),
        hovertemplate: "%{text}<br>cost %{x:.2f} lakh · carbon %{y:.1f} t<extra></extra>",
        marker: {
          symbol: SYMBOLS[v] ?? "circle", size: 9, color: ds.map((d) => colorOf(d, by)), ...(by === "none" ? { color: palette.fronts[v] } : cb),
          line: { width: ds.map((d) => (d.feasible_true ? 0.5 : 2.5)), color: ds.map((d) => (d.feasible_true ? "rgba(0,0,0,0.4)" : "#dc2626")) },
        },
      });
      // verification overlays: green ring (passed) / red cross (failed)
      const ver = ds.filter((d) => d.verification.verified);
      const ok = ver.filter((d) => d.verification.passed);
      const bad = ver.filter((d) => !d.verification.passed);
      if (ok.length) traces.push({ type: "scatter", mode: "markers", name: `✓ verified (${pareto.labels[v] ?? v})`, x: ok.map((d) => xy(d)[0]), y: ok.map((d) => xy(d)[1]), hoverinfo: "skip", marker: { symbol: "circle-open", size: 17, line: { color: "#16a34a", width: 2.5 } } });
      if (bad.length) traces.push({ type: "scatter", mode: "markers", name: `✕ verification failed (${pareto.labels[v] ?? v})`, x: bad.map((d) => xy(d)[0]), y: bad.map((d) => xy(d)[1]), hoverinfo: "skip", marker: { symbol: "x-thin-open", size: 18, line: { color: "#dc2626", width: 3 } } });
    }
    return traces;
  }, [shown, by, basis, cloud, pareto]);

  const onClick = useCallback((pt: any) => {
    if (pt.customdata) setSel({ v: pt.customdata[0], i: pt.customdata[1] });
  }, []);
  const toggle = (n: string) => setShown(shown.includes(n) ? shown.filter((x) => x !== n) : [...shown, n]);
  const chosen = sel ? pareto.variants[sel.v].find((d) => d.id === sel.i) : null;

  const frontCsv = (v: string) =>
    ["id,concrete,steel,beam0_b,beam0_D,beam1_b,beam1_D,col0_b,col0_D,col1_b,col1_D,cost_inr_true,carbon_kgco2e_true,feasible_true"]
      .concat(pareto.variants[v].map((d) => [d.id, d.concrete, d.steel, d.beams[0].b_mm, d.beams[0].D_mm, d.beams[1]?.b_mm, d.beams[1]?.D_mm, d.columns[0].b_mm, d.columns[0].D_mm, d.columns[1]?.b_mm, d.columns[1]?.D_mm, d.true_cost, d.true_carbon, d.feasible_true].join(",")))
      .join("\n");

  return (
    <div className="space-y-4">
      <h1 className="h1">Pareto explorer</h1>
      <GravityCaveat />
      <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Fronts">
          <span className="muted mr-1">Fronts:</span>
          {names.map((n) => (
            <button key={n} className={`btn ${shown.includes(n) ? "btn-on" : ""}`} onClick={() => toggle(n)} aria-pressed={shown.includes(n)}>
              {pareto.labels[n] ?? n} ({pareto.variants[n].length})
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1">
          Colour by
          <select className="btn" value={by} onChange={(e) => setBy(e.target.value as ColorBy)}>
            <option value="concrete">concrete grade</option>
            <option value="steel">steel grade</option>
            <option value="cement">cement type</option>
            <option value="beamD">beam depth</option>
            <option value="colB">column size</option>
            <option value="none">front</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          Objectives
          <select className="btn" value={basis} onChange={(e) => setBasis(e.target.value as "true" | "pred")}>
            <option value="true">ground truth (FE re-evaluation)</option>
            <option value="pred">as the optimiser saw them</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={cloud} onChange={(e) => setCloud(e.target.checked)} /> dataset cloud
        </label>
      </div>
      <div className="card">
        <Plot
          data={data}
          dark={dark}
          height={520}
          onClick={onClick}
          layout={{ xaxis: { title: "Construction cost (₹ lakh, provisional rates)" }, yaxis: { title: "Embodied carbon (t CO₂e, provisional factors)" }, hovermode: "closest", legend: { orientation: "h", y: -0.25 } }}
        />
        <p className="text-xs muted">
          Symbols: ○ A, ◇ A+margin, □ B, △ B+margin, + direct FE. Red outline = truly infeasible; green ring ✓ = verified and passed; red ✕ = verification failed. Click a point for the design drawer.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {names.map((n) => (
          <button key={n} className="btn" onClick={() => download(`front_${n}.csv`, frontCsv(n), "text/csv")}>
            Download front CSV: {pareto.labels[n] ?? n}
          </button>
        ))}
      </div>
      {chosen && sel && <DesignDrawer d={chosen} label={pareto.labels[sel.v] ?? sel.v} onClose={() => setSel(null)} />}
      <span className="sr-only">{meta.generated}</span>
    </div>
  );
}
