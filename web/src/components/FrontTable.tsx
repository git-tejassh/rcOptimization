import { useMemo, useState } from "react";
import type { ParetoDesign } from "../types";
import { download } from "../format";

export interface Row {
  v: string;
  d: ParetoDesign;
}

/** One column of the table: how to read a value out of a design (used for display, sorting and CSV export). */
interface Col {
  key: string;
  head: string;
  unit?: string;
  get: (r: Row) => string | number;
  fmt?: (x: any) => string;
  group: "Result" | "Materials" | "Beams" | "Columns" | "Quantities" | "Code checks" | "Status";
}

const f = (x: number, d = 2) => (Number.isFinite(x) ? x.toFixed(d) : "-");

function columns(nB: number, nC: number, labels: Record<string, string>): Col[] {
  const c: Col[] = [
    { key: "front", head: "Front", group: "Result", get: (r) => labels[r.v] ?? r.v },
    { key: "id", head: "#", group: "Result", get: (r) => r.d.id },
    { key: "cost", head: "Cost", unit: "₹ lakh", group: "Result", get: (r) => (r.d.true_cost ?? r.d.pred_cost) / 1e5, fmt: (x) => f(x, 2) },
    { key: "carbon", head: "Carbon", unit: "t CO₂e", group: "Result", get: (r) => (r.d.true_carbon ?? r.d.pred_carbon) / 1000, fmt: (x) => f(x, 1) },
    { key: "conc", head: "Concrete", group: "Materials", get: (r) => r.d.concrete },
    { key: "steel", head: "Steel", group: "Materials", get: (r) => r.d.steel },
    { key: "cement", head: "Cement", group: "Materials", get: (r) => r.d.cement },
  ];
  for (let g = 0; g < nB; g++) {
    c.push({ key: `bs${g}`, head: `Beam g${g} size`, unit: "b × D mm", group: "Beams", get: (r) => (r.d.beams[g] ? `${r.d.beams[g].b_mm} × ${r.d.beams[g].D_mm}` : "-") });
    c.push({ key: `bb${g}`, head: `Beam g${g} bottom`, group: "Beams", get: (r) => r.d.beams[g]?.bottom ?? "-" });
    c.push({ key: `bt${g}`, head: `Beam g${g} top`, group: "Beams", get: (r) => r.d.beams[g]?.top ?? "-" });
    c.push({ key: `sv${g}`, head: `Stirrup g${g}`, unit: "mm c/c", group: "Beams", get: (r) => r.d.stirrup_spacing_mm?.[g] ?? "-" });
  }
  for (let g = 0; g < nC; g++) {
    c.push({ key: `cs${g}`, head: `Column g${g} size`, unit: "b × D mm", group: "Columns", get: (r) => (r.d.columns[g] ? `${r.d.columns[g].b_mm} × ${r.d.columns[g].D_mm}` : "-") });
    c.push({ key: `cb${g}`, head: `Column g${g} bars`, group: "Columns", get: (r) => r.d.columns[g]?.bars ?? "-" });
    c.push({ key: `cp${g}`, head: `Column g${g} steel`, unit: "%", group: "Columns", get: (r) => r.d.columns[g]?.pt_percent ?? NaN, fmt: (x) => f(x, 2) });
  }
  c.push(
    { key: "vc", head: "Concrete", unit: "m³", group: "Quantities", get: (r) => r.d.quantities?.concrete_m3 ?? NaN, fmt: (x) => f(x, 1) },
    { key: "vs", head: "Steel", unit: "t", group: "Quantities", get: (r) => (r.d.quantities?.steel_kg ?? NaN) / 1000, fmt: (x) => f(x, 1) },
    { key: "vf", head: "Formwork", unit: "m²", group: "Quantities", get: (r) => r.d.quantities?.formwork_m2 ?? NaN, fmt: (x) => f(x, 0) },
    { key: "u1", head: "Beam bending", unit: "≤ 1", group: "Code checks", get: (r) => r.d.utilisation?.U_flex_max ?? NaN, fmt: (x) => f(x, 2) },
    { key: "u2", head: "Beam shear", unit: "≤ 1", group: "Code checks", get: (r) => r.d.utilisation?.U_shear_max ?? NaN, fmt: (x) => f(x, 2) },
    { key: "u3", head: "Column", unit: "≤ 1", group: "Code checks", get: (r) => r.d.utilisation?.U_col_max ?? NaN, fmt: (x) => f(x, 2) },
    { key: "u4", head: "Deflection", unit: "≤ 1", group: "Code checks", get: (r) => r.d.utilisation?.deflection_ratio ?? NaN, fmt: (x) => f(x, 2) },
    { key: "ok", head: "Passes all checks", group: "Status", get: (r) => (r.d.feasible_true ? "yes" : "NO") },
    { key: "ver", head: "FE re-run", group: "Status", get: (r) => (r.d.verification.verified ? (r.d.verification.passed ? "passed" : "failed") : "-") },
  );
  return c;
}

/** Every point of the chosen fronts with every feature value, sortable, with CSV download. */
export default function FrontTable({ rows, labels, onPick }: { rows: Row[]; labels: Record<string, string>; onPick?: (r: Row) => void }) {
  const nB = Math.max(1, ...rows.map((r) => r.d.beams.length));
  const nC = Math.max(1, ...rows.map((r) => r.d.columns.length));
  const cols = useMemo(() => columns(nB, nC, labels), [nB, nC, labels]);
  const [sort, setSort] = useState<{ key: string; asc: boolean }>({ key: "cost", asc: true });
  const sorted = useMemo(() => {
    const c = cols.find((x) => x.key === sort.key) ?? cols[0];
    return [...rows].sort((a, b) => {
      const x = c.get(a), y = c.get(b);
      const cmp = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), undefined, { numeric: true });
      return sort.asc ? cmp : -cmp;
    });
  }, [rows, cols, sort]);
  const groups = cols.reduce<{ g: string; n: number }[]>((acc, c) => { const l = acc[acc.length - 1]; if (l && l.g === c.group) l.n++; else acc.push({ g: c.group, n: 1 }); return acc; }, []);
  const csv = () => {
    const head = cols.map((c) => (c.unit ? `${c.head} (${c.unit})` : c.head));
    const lines = sorted.map((r) => cols.map((c) => { const v = c.get(r); return typeof v === "number" ? (Number.isFinite(v) ? v : "") : `"${v}"`; }).join(","));
    download("pareto_front_features.csv", [head.join(","), ...lines].join("\n"), "text/csv");
  };
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="muted">{rows.length} designs · click a column title to sort{onPick ? " · click a row for its full property sheet" : ""}. “g0”, “g1” are the member groups (beam levels / column storeys sharing one section).</span>
        <button className="btn" onClick={csv}>Download this table (CSV)</button>
      </div>
      <div className="table-wrap" style={{ maxHeight: 560 }}>
        <table className="t" style={{ minWidth: 1500 }}>
          <thead>
            <tr>
              {groups.map((g) => (
                <th key={g.g} colSpan={g.n} className="!text-center" style={{ position: "sticky", top: 0, background: "var(--accent-soft)", color: "var(--accent-strong)" }}>{g.g}</th>
              ))}
            </tr>
            <tr>
              {cols.map((c) => (
                <th key={c.key} style={{ top: 31 }} className={`cursor-pointer ${typeof c.get(rows[0] ?? ({} as Row)) === "number" ? "num" : ""}`} onClick={() => setSort({ key: c.key, asc: sort.key === c.key ? !sort.asc : true })}>
                  {c.head}{c.unit && <span className="block text-[10px] font-normal normal-case tracking-normal">{c.unit}</span>}{sort.key === c.key ? (sort.asc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={`${r.v}-${r.d.id}`} className={onPick ? "cursor-pointer" : ""} onClick={() => onPick?.(r)}>
                {cols.map((c) => {
                  const v = c.get(r);
                  const txt = c.fmt && typeof v === "number" ? c.fmt(v) : String(v);
                  const bad = (c.group === "Code checks" && typeof v === "number" && v > 1) || (c.key === "ok" && v === "NO") || (c.key === "ver" && v === "failed");
                  return <td key={c.key} className={typeof v === "number" ? "num" : ""} style={bad ? { color: "var(--bad)", fontWeight: 600 } : undefined}>{txt}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
