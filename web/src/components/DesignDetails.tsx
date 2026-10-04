import type { ParetoDesign } from "../types";
import { download, lakh, num, tonnes } from "../format";

function Bar({ parts, fmt }: { parts: Record<string, number>; fmt: (x: number) => string }) {
  const keys = Object.keys(parts).filter((k) => k !== "total");
  const total = parts.total ?? keys.reduce((s, k) => s + parts[k], 0);
  const colors = ["#2f7d5b", "#7aa88f", "#c9a24a", "#9aa6a0"];
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full" role="img" aria-label="breakdown">
        {keys.map((k, i) => (
          <div key={k} style={{ width: `${(100 * parts[k]) / total}%`, background: colors[i % 4] }} title={`${k}: ${fmt(parts[k])}`} />
        ))}
      </div>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
        {keys.map((k, i) => (
          <span key={k}>
            <span className="mr-1 inline-block h-2 w-2 rounded-sm" style={{ background: colors[i % 4] }} />
            <span className="capitalize">{k}</span> {fmt(parts[k])} <span className="muted">({((100 * parts[k]) / total).toFixed(0)} %)</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function Row({ k, v, hint }: { k: string; v: React.ReactNode; hint?: string }) {
  return (
    <div className="flex justify-between gap-4 border-b py-1.5 text-sm" style={{ borderColor: "var(--line)" }}>
      <dt className="muted" title={hint}>{k}</dt>
      <dd className="text-right font-medium">{v}</dd>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow mb-1 mt-4">{title}</div>
      {children}
    </div>
  );
}

const csvRow = (d: ParetoDesign) =>
  [d.concrete, d.steel, d.cement, ...d.beams.flatMap((b) => [b.b_mm, b.D_mm, b.bottom, b.top]), ...d.columns.flatMap((c) => [c.b_mm, c.D_mm, c.bars]),
    d.true_cost ?? d.pred_cost, d.true_carbon ?? d.pred_carbon, d.feasible_true].join(",");

/** Every property of one design in plain words: materials, members, quantities, cost, carbon, checks, verification. */
export default function DesignDetails({ d, label, compact = false }: { d: ParetoDesign; label?: string; compact?: boolean }) {
  const u = d.utilisation;
  const v = d.verification;
  const util = (name: string, val: number, pred?: number, hint?: string) => (
    <Row
      key={name}
      k={name}
      hint={hint}
      v={
        <span className={val > 1 ? "text-[color:var(--bad)]" : ""}>
          {val > 1 ? "✕ " : "✓ "}{num(val, 3)}
          {pred != null && <span className="ml-2 text-xs font-normal muted">surrogate {num(pred, 3)}</span>}
        </span>
      }
    />
  );
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="h2">Design #{d.id}</span>
        {label && <span className="tag tag-neutral">{label}</span>}
        <span className={`tag ${d.feasible_true ? "tag-good" : "tag-bad"}`}>{d.feasible_true ? "✓ passes every IS 456 check" : "✕ fails a check"}</span>
        {v.verified ? (
          <span className={`tag ${v.passed ? "tag-good" : "tag-bad"}`}>{v.passed ? "✓ verified by FE re-run" : "✕ verification failed"}{v.boundary_pick ? " · boundary pick" : ""}</span>
        ) : (
          <span className="tag tag-neutral">not in the verified sample</span>
        )}
      </div>
      {v.verified && !v.passed && <ul className="mt-2 list-disc pl-5 text-sm text-[color:var(--bad)]">{v.reasons?.map((r, i) => <li key={i}>{r}</li>)}</ul>}

      <Block title="Headline">
        <dl>
          <Row k="Construction cost" v={lakh(d.true_cost)} hint="Frame concrete, reinforcement and formwork at the provisional rates" />
          <Row k="Embodied carbon (A1-A4)" v={`${tonnes(d.true_carbon)} CO₂e`} hint="Cradle-to-site carbon of concrete and steel" />
        </dl>
      </Block>

      <Block title="Materials">
        <dl>
          <Row k="Concrete grade" v={d.concrete} hint="IS 456 Table 2; Table 5 minimum for the exposure is M25" />
          <Row k="Reinforcement grade" v={d.steel} />
          <Row k="Cement type" v={d.cement} hint="OPC (IS 269), PPC (IS 1489-1), PSC (IS 455)" />
        </dl>
      </Block>

      <Block title="Beams (width × depth, bars)">
        <dl>
          {d.beams.map((b) => (
            <Row key={b.group} k={`Beam group ${b.group}`} v={<span>{b.b_mm} × {b.D_mm} mm<br /><span className="text-xs font-normal muted">bottom {b.bottom} · top {b.top} · stirrups {b.stirrups}{d.stirrup_spacing_mm ? ` @ ${d.stirrup_spacing_mm[b.group]} mm` : ""}</span></span>} />
          ))}
        </dl>
      </Block>
      <Block title="Columns (width × depth, bars)">
        <dl>
          {d.columns.map((c) => (
            <Row key={c.group} k={`Column group ${c.group}`} v={<span>{c.b_mm} × {c.D_mm} mm<br /><span className="text-xs font-normal muted">{c.bars} · steel ratio {num(c.pt_percent, 2)} %</span></span>} />
          ))}
        </dl>
      </Block>

      {d.quantities && (
        <Block title="Quantities">
          <dl>
            <Row k="Concrete" v={`${num(d.quantities.concrete_m3, 1)} m³`} hint={`beams ${num(d.quantities.beam_concrete_m3, 1)} · columns ${num(d.quantities.column_concrete_m3, 1)}`} />
            <Row k="Reinforcement" v={tonnes(d.quantities.steel_kg)} hint={`beams ${tonnes(d.quantities.beam_steel_kg)} · columns ${tonnes(d.quantities.column_steel_kg)}`} />
            <Row k="Formwork" v={`${num(d.quantities.formwork_m2, 0)} m²`} />
          </dl>
        </Block>
      )}
      {!compact && d.cost_inr && (
        <Block title="Cost breakdown">
          <Bar parts={d.cost_inr} fmt={lakh} />
        </Block>
      )}
      {!compact && d.carbon_kgco2e && (
        <Block title="Carbon breakdown">
          <Bar parts={d.carbon_kgco2e} fmt={tonnes} />
        </Block>
      )}
      {u && (
        <Block title="Code checks (utilisation must be ≤ 1.0)">
          <dl>
            {util("Beam bending", u.U_flex_max, d.pred_util?.U_flex_max, "Moment demand / moment capacity, worst beam section")}
            {util("Beam shear", u.U_shear_max, d.pred_util?.U_shear_max, "Shear stress / maximum permitted shear stress")}
            {util("Column (axial + bending)", u.U_col_max, d.pred_util?.U_col_max, "IS 456 biaxial interaction ratio, worst column")}
            {util("Deflection", u.deflection_ratio, d.pred_util?.defl_ratio_max, "Service deflection divided by span/250")}
          </dl>
          <div className="mt-1 text-xs muted">Largest service deflection {num(u.deflection_mm, 2)} mm.</div>
        </Block>
      )}
      {!compact && (
        <div className="mt-4 flex gap-2">
          <button className="btn" onClick={() => download(`design_${d.id}.json`, JSON.stringify(d, null, 2), "application/json")}>Download JSON</button>
          <button className="btn" onClick={() => download(`design_${d.id}.csv`, csvRow(d))}>Download CSV row</button>
        </div>
      )}
    </div>
  );
}
