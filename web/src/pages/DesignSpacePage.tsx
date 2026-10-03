import { useData } from "../data";
import { sci } from "../format";

const GROUP_COLORS = ["#0ea5e9", "#f59e0b", "#10b981", "#a855f7"];

/** Elevation + plan sketch of the frame, coloured by optimisation group. */
function FrameSketch() {
  const { meta } = useData();
  const f = meta.frame;
  const xs = [0];
  f.bays_x_m.forEach((b) => xs.push(xs[xs.length - 1] + b));
  const zs = [0];
  f.bays_z_m.forEach((b) => zs.push(zs[zs.length - 1] + b));
  const ys = [0];
  f.storey_heights_m.forEach((h) => ys.push(ys[ys.length - 1] + h));
  const W = 360, H = 260, pad = 24;
  const sx = (W - 2 * pad) / xs[xs.length - 1];
  const sy = (H - 2 * pad - 20) / (ys[ys.length - 1] + f.stub_height_m);
  const X = (x: number) => pad + x * sx;
  const Y = (y: number) => H - pad - (y + f.stub_height_m) * sy;
  const bgOf = (lv: number) => f.beam_groups.findIndex((g) => g.includes(lv));
  const cgOf = (s: number) => f.column_groups.findIndex((g) => g.includes(s));
  const pw = 220, ph = (pw * zs[zs.length - 1]) / xs[xs.length - 1];
  const px = (x: number) => 10 + (x / xs[xs.length - 1]) * (pw - 20);
  const pz = (z: number) => 10 + (z / zs[zs.length - 1]) * (ph - 20);
  return (
    <div className="flex flex-wrap items-start gap-6">
      <figure>
        <svg width={W} height={H} role="img" aria-label="Frame elevation coloured by group">
          {ys.map((y, lv) => (
            <line key={`b${lv}`} x1={X(0)} x2={X(xs[xs.length - 1])} y1={Y(y)} y2={Y(y)} stroke={GROUP_COLORS[bgOf(lv) % 4]} strokeWidth={5} />
          ))}
          {xs.map((x, i) => (
            <g key={`c${i}`}>
              <line x1={X(x)} x2={X(x)} y1={Y(-f.stub_height_m)} y2={Y(0)} stroke={GROUP_COLORS[2 + (cgOf(0) % 2)]} strokeWidth={5} />
              {f.storey_heights_m.map((_, s) => (
                <line key={s} x1={X(x)} x2={X(x)} y1={Y(ys[s])} y2={Y(ys[s + 1])} stroke={GROUP_COLORS[2 + (cgOf(s) % 2)]} strokeWidth={5} />
              ))}
            </g>
          ))}
          {ys.map((y, lv) => (
            <text key={`t${lv}`} x={4} y={Y(y) + 4} fontSize={10} fill="currentColor">
              L{lv}
            </text>
          ))}
          <text x={W / 2 - 40} y={H - 4} fontSize={10} fill="currentColor">
            elevation (x-direction), fixed base
          </text>
        </svg>
        <figcaption className="text-xs muted">
          Beams: group B0 blue / B1 amber; columns (incl. stubs): group C0 green / C1 purple.
        </figcaption>
      </figure>
      <figure>
        <svg width={pw} height={ph + 20} role="img" aria-label="Plan">
          {xs.map((x) => (
            <line key={`px${x}`} x1={px(x)} x2={px(x)} y1={pz(0)} y2={pz(zs[zs.length - 1])} stroke="currentColor" strokeOpacity={0.5} />
          ))}
          {zs.map((z) => (
            <line key={`pz${z}`} y1={pz(z)} y2={pz(z)} x1={px(0)} x2={px(xs[xs.length - 1])} stroke="currentColor" strokeOpacity={0.5} />
          ))}
          {xs.flatMap((x) => zs.map((z) => <rect key={`${x}-${z}`} x={px(x) - 4} y={pz(z) - 4} width={8} height={8} fill={GROUP_COLORS[2]} />))}
        </svg>
        <figcaption className="text-xs muted">
          Plan: {f.bays_x_m.length} × {f.bays_z_m.length} bays of {f.bays_x_m[0]} m; storey {f.storey_heights_m[0]} m; D axis of columns along {f.column_D_axis.toUpperCase()}.
        </figcaption>
      </figure>
    </div>
  );
}

export default function DesignSpacePage() {
  const { space } = useData();
  const grouped = space.genes.filter((g) => !["fck", "fy"].includes(g.name));
  return (
    <div className="space-y-5">
      <h1 className="h1">Design space</h1>
      <p className="text-sm muted">
        {space.n_genes} integer genes → {sci(space.total_combinations)} combinations. Every gene is an index into an IS-standard option list; a deterministic repair snaps any candidate to the nearest buildable design (so no continuous relaxation is ever reported).
      </p>
      <section className="card">
        <h2 className="h2 mb-2">Frame (G+3, parsed from the owner's STAAD model)</h2>
        <FrameSketch />
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Variables and option lists</h2>
        <table className="t">
          <thead>
            <tr>
              <th>Gene</th>
              <th>Meaning</th>
              <th>Options</th>
            </tr>
          </thead>
          <tbody>
            {grouped.concat(space.genes.filter((g) => ["fck", "fy"].includes(g.name))).map((g) => (
              <tr key={g.name}>
                <td className="font-mono">{g.name}</td>
                <td className="text-xs">{describe(g.name)}</td>
                <td className="font-mono text-xs">{g.options.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card overflow-x-auto">
        <h2 className="h2 mb-2">Constraints (all must hold; IS 456:2000)</h2>
        <table className="t">
          <thead>
            <tr>
              <th>Check</th>
              <th>Rule</th>
              <th>Clause</th>
            </tr>
          </thead>
          <tbody>
            {space.constraints.map((c) => (
              <tr key={c.name}>
                <td className="font-medium">{c.name}</td>
                <td>{c.description}</td>
                <td className="text-xs muted">{c.clause}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs muted">
          Cover ({space.cover_mm.exposure} exposure): beams {space.cover_mm.beam} mm, columns {space.cover_mm.column} mm. Beam groups {JSON.stringify(space.beam_groups)} (levels), column groups {JSON.stringify(space.column_groups)} (storeys; stubs with storey 0).
        </p>
      </section>
    </div>
  );
}

function describe(name: string): string {
  const [g, what] = name.split("_");
  const grp = g.startsWith("B") ? `beam group ${g.slice(1)}` : `column group ${g.slice(1)}`;
  const m: Record<string, string> = {
    b: "width b (mm)", D: "depth D (mm)", bd: "bottom bar diameter (mm)", bn: "bottom bar count", td: "top bar diameter (mm)",
    tn: "top bar count", dia: "bar diameter (mm)", n: "bar count (symmetric perimeter layout)",
  };
  if (name === "fck") return "concrete grade (IS 456 Table 2)";
  if (name === "fy") return "reinforcement grade";
  return `${grp}: ${m[what] ?? what}`;
}
