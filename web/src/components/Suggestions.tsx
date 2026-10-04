import { useMemo, useState } from "react";
import type { ParetoDesign } from "../types";
import { lakh, pct, tonnes } from "../format";
import DesignDetails from "./DesignDetails";
import { excess } from "../lib/zones";

export interface Suggestion {
  tag: string;
  v: string;
  d: ParetoDesign;
}

/** Pick several diverse optimised designs: three anchors plus designs spread along the cost range. */
export function pickSuggestions(rows: { v: string; d: ParetoDesign }[], ideal: { cost: number; carbon: number }, n = 8): Suggestion[] {
  const ok = rows.filter((r) => r.d.feasible_true && r.d.true_cost != null);
  const seen = new Set<string>();
  const out: Suggestion[] = [];
  const add = (r: { v: string; d: ParetoDesign } | undefined, tag: string) => {
    if (!r) return;
    const k = `${r.d.concrete}${r.d.steel}${r.d.cement}${r.d.beams.map((b) => `${b.b_mm}x${b.D_mm}${b.bottom}${b.top}`).join()}${r.d.columns.map((c) => `${c.b_mm}x${c.D_mm}${c.bars}`).join()}`;
    if (seen.has(k)) return;
    seen.add(k);
    out.push({ tag, v: r.v, d: r.d });
  };
  const byCost = [...ok].sort((a, b) => a.d.true_cost! - b.d.true_cost!);
  const byCarbon = [...ok].sort((a, b) => a.d.true_carbon! - b.d.true_carbon!);
  const bal = [...ok].sort((a, b) => excess(a.d.true_cost! / 1e5, a.d.true_carbon! / 1000, ideal) - excess(b.d.true_cost! / 1e5, b.d.true_carbon! / 1000, ideal));
  add(byCost[0], "Lowest cost");
  add(byCarbon[0], "Lowest carbon");
  add(bal[0], "Best balance");
  const verified = ok.filter((r) => r.d.verification.verified && r.d.verification.passed);
  add([...verified].sort((a, b) => excess(a.d.true_cost! / 1e5, a.d.true_carbon! / 1000, ideal) - excess(b.d.true_cost! / 1e5, b.d.true_carbon! / 1000, ideal))[0], "Best balance, FE-verified");
  for (let i = 1; out.length < n && i < 40; i++) {
    const idx = Math.floor((i / 12) * (byCost.length - 1));
    add(byCost[Math.min(idx, byCost.length - 1)], "Along the front");
  }
  return out.slice(0, n);
}

/** Several optimised designs side by side with the user's estimate; each can be expanded to its full property sheet. */
export default function Suggestions({
  items, mine, labels, onUse,
}: {
  items: Suggestion[];
  mine: { cost: number; carbon: number } | null;
  labels: Record<string, string>;
  onUse: (d: ParetoDesign) => void;
}) {
  const [open, setOpen] = useState<number | null>(0);
  const rows = useMemo(() => items, [items]);
  const dl = (a: number, b: number | undefined) => (b ? pct(a / b - 1) : "-");
  return (
    <div className="space-y-3">
      <div className="table-wrap" style={{ maxHeight: "none" }}>
        <table className="t">
          <thead>
            <tr><th>Suggestion</th><th className="num">Cost</th><th className="num">vs yours</th><th className="num">Carbon</th><th className="num">vs yours</th><th>Materials</th><th>Beams</th><th>Columns</th><th /></tr>
          </thead>
          <tbody>
            {rows.map((s, i) => (
              <tr key={i} className="cursor-pointer" onClick={() => setOpen(open === i ? null : i)} style={open === i ? { background: "var(--accent-soft)" } : undefined}>
                <td><b>{s.tag}</b><br /><span className="text-xs muted">{labels[s.v] ?? s.v} · #{s.d.id}</span></td>
                <td className="num">{lakh(s.d.true_cost)}</td>
                <td className="num" style={{ color: mine && s.d.true_cost! < mine.cost ? "var(--good)" : undefined }}>{mine ? dl(s.d.true_cost!, mine.cost) : "-"}</td>
                <td className="num">{tonnes(s.d.true_carbon)}</td>
                <td className="num" style={{ color: mine && s.d.true_carbon! < mine.carbon ? "var(--good)" : undefined }}>{mine ? dl(s.d.true_carbon!, mine.carbon) : "-"}</td>
                <td>{s.d.concrete} · {s.d.steel} · {s.d.cement}</td>
                <td>{s.d.beams.map((b) => `${b.b_mm}×${b.D_mm}`).join(" / ")}</td>
                <td>{s.d.columns.map((c) => `${c.b_mm}×${c.D_mm}`).join(" / ")}</td>
                <td><button className="btn" onClick={(e) => { e.stopPropagation(); onUse(s.d); }}>Use as my design</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open != null && rows[open] && (
        <div className="card-soft">
          <div className="eyebrow mb-2">Full specification: {rows[open].tag}</div>
          <DesignDetails d={rows[open].d} label={labels[rows[open].v]} />
        </div>
      )}
      <p className="text-xs muted">Every suggestion passes all IS 456 checks (gravity loads) and was re-evaluated with the finite-element model. “vs yours” compares total cost and carbon of the project frame; it is only meaningful when your frame has the same size as the project frame (4 × 3 bays of 5 m, G+3).</p>
    </div>
  );
}
