import { useEffect, useState } from "react";
import { defaultBase, health, reviewStaad, saveBase, type Health, type ReviewReport } from "../lib/api";
import { Finding } from "./Caveat";
import { num } from "../format";

const u = (x: number) => (
  <span style={{ color: x > 1 ? "var(--bad)" : undefined, fontWeight: x > 1 ? 600 : undefined }}>{x > 1 ? "✕ " : "✓ "}{num(x, 2)}</span>
);

/** Strength review of the uploaded frame (needs the local API): designs the reinforcement and reports every IS 456 check. */
export default function StrengthReview({
  staadText, grade, steel, cement, report, stale, onReport,
}: {
  staadText: string | null;
  grade: string;
  steel: string;
  cement: string;
  report: ReviewReport | null;
  stale: boolean;
  onReport: (r: ReviewReport | null) => void;
}) {
  const [base, setBase] = useState(defaultBase());
  const [h, setH] = useState<Health | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => { health(base).then(setH); }, [base]);

  const run = async () => {
    if (!staadText) return;
    setBusy(true);
    setErr("");
    try { onReport(await reviewStaad(base, staadText, grade, steel, cement)); }
    catch (e) { setErr(String((e as Error).message)); onReport(null); }
    finally { setBusy(false); }
  };

  return (
    <section className="card">
      <div className="eyebrow">Step 3</div>
      <h2 className="h2">Strength review and reinforcement design (IS 456)</h2>
      <p className="mb-3 mt-1 max-w-3xl text-sm muted">
        Your frame is analysed with the project’s finite-element model under gravity loads (1.5 × (dead + live), project IS 875 loads), and the cheapest standard reinforcement that satisfies
        every IS 456 check is designed for each group of members. If the sizes themselves are too small, the check that fails is named. This replaces the assumed steel per m³ with real bars.
      </p>
      {h === undefined && <p className="text-sm muted">Looking for the local API…</p>}
      {h === null && (
        <div className="space-y-2">
          <Finding level="warn" text="The strength review needs the local Python server, which is not reachable here (a static website cannot run the finite-element model)." />
          <div className="card-soft text-sm">
            Start it on your computer with <code>python -m rcopt.cli serve</code> and open <b>http://localhost:8000</b> (this dashboard is then served together with the API), or type the API address if it runs elsewhere:
            <div className="mt-2 flex max-w-md gap-2">
              <input className="input" value={base} placeholder="http://localhost:8000" onChange={(e) => setBase(e.target.value)} />
              <button className="btn" onClick={() => { saveBase(base); health(base).then(setH); }}>Connect</button>
            </div>
          </div>
        </div>
      )}
      {h && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn-primary disabled:opacity-50" disabled={!staadText || busy} onClick={run}>{busy ? "Analysing…" : report ? "Re-run the strength review" : "Check strength and design the reinforcement"}</button>
            {!staadText && <span className="text-sm muted">Load a STAAD file in Step 1 first (the review works on STAAD input of a regular frame).</span>}
            {report && stale && <span className="tag tag-warn">materials changed since this review: run it again</span>}
            <span className="tag tag-good">API connected</span>
          </div>
          {err && <Finding level="bad" text={err} />}
        </div>
      )}

      {report && (
        <div className="mt-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`tag ${report.verdict === "PASS" ? "tag-good" : "tag-bad"} !text-sm`}>{report.verdict === "PASS" ? "✓ PASS: the sizes are adequate with the reinforcement below" : "✕ FAIL: the sizes are not adequate"}</span>
            <span className="text-sm muted">{report.materials.concrete} · {report.materials.steel} · {report.frame.bays_x_m.length} × {report.frame.bays_z_m.length} bays, {report.frame.storey_heights_m.length} storeys</span>
          </div>
          {report.failures.length > 0 && <div className="space-y-1.5">{report.failures.map((f, i) => <Finding key={i} level="bad" text={f} />)}</div>}
          {report.notes.map((n, i) => <Finding key={i} level="info" text={n} />)}

          <div>
            <div className="label">Beams</div>
            <div className="table-wrap" style={{ maxHeight: "none" }}>
              <table className="t">
                <thead><tr><th>Group (levels)</th><th>Size b × D (mm)</th><th>Designed bars</th><th className="num">Demand: sag / hog (kN·m), shear (kN)</th><th className="num">Capacity sag / hog (kN·m)</th><th className="num">Bending</th><th className="num">Shear</th><th>Result</th></tr></thead>
                <tbody>
                  {report.beams.map((b) => (
                    <tr key={b.group}>
                      <td>{b.group} ({b.levels.join(", ")})</td><td>{b.b_mm} × {b.D_mm}</td>
                      <td>bottom {b.bottom}<br />top {b.top}<br /><span className="muted">{b.stirrups}</span></td>
                      <td className="num">{num(b.demand.Msag_kNm, 1)} / {num(b.demand.Mhog_kNm, 1)}, {num(b.demand.Vu_kN, 1)}</td>
                      <td className="num">{num(b.Mu_sag_kNm, 1)} / {num(b.Mu_hog_kNm, 1)}</td>
                      <td className="num">{u(Math.max(b.U_sag, b.U_hog))}</td><td className="num">{u(b.U_shear)}</td>
                      <td>{b.pass ? <span className="tag tag-good">✓ ok</span> : <span className="tag tag-bad">✕ fails</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div>
            <div className="label">Columns (the most heavily loaded column of each group is shown)</div>
            <div className="table-wrap" style={{ maxHeight: "none" }}>
              <table className="t">
                <thead><tr><th>Group (storeys)</th><th>Size b × D (mm)</th><th>Designed bars</th><th className="num">Governing load: Pu (kN), M (kN·m)</th><th className="num">Capacity M at that Pu (kN·m)</th><th className="num">Interaction</th><th>Result</th></tr></thead>
                <tbody>
                  {report.columns.map((c) => (
                    <tr key={c.group}>
                      <td>{c.group} {c.is_base_group ? "(incl. base columns)" : ""} {c.storeys.length ? `(${c.storeys.join(", ")})` : ""}</td><td>{c.b_mm} × {c.D_mm}</td>
                      <td>{c.bars}<br /><span className="muted">{num(c.pt_percent, 2)} % steel</span></td>
                      <td className="num">{num(c.governing.Pu_kN, 0)}, {num(c.governing.MD_kNm, 1)} / {num(c.governing.Mb_kNm, 1)}</td>
                      <td className="num">{num(c.MuD1_kNm, 1)} / {num(c.Mub1_kNm, 1)}</td>
                      <td className="num">{u(c.U)}</td>
                      <td>{c.pass ? <span className="tag tag-good">✓ ok</span> : <span className="tag tag-bad">✕ fails</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="text-sm">
            Deflection: {u(report.deflection.ratio_to_L_over_250)} of the L/250 limit (largest {num(report.deflection.max_mm, 1)} mm).
            Revised steel: <b>{num(report.quantities.steel_kg / 1000, 2)} t</b> ({num(report.quantities.steel_kg / report.quantities.concrete_m3, 0)} kg/m³): the estimate on the right uses these bars.
          </div>
        </div>
      )}
    </section>
  );
}
