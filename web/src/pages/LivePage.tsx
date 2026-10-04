import { useEffect, useState } from "react";
import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { GravityCaveat } from "../components/Caveat";
import { lakh, num, tonnes } from "../format";

import { defaultBase, health, saveBase, type Health } from "../lib/api";

type Res = Record<string, any>;

export default function LivePage() {
  const { space, pareto } = useData();
  const [base, setBase] = useState(defaultBase());
  const [h, setH] = useState<Health | null | undefined>(undefined);
  const [genome, setGenome] = useState<number[]>(() => pareto.variants.A[Math.floor(pareto.variants.A.length / 2)]?.genome ?? space.genes.map(() => 0));
  const [sur, setSur] = useState<Res | null>(null);
  const [fe, setFe] = useState<Res | null>(null);
  const [busy, setBusy] = useState("");
  useEffect(() => { health(base).then(setH); }, [base]);
  const post = async (path: string) => {
    setBusy(path);
    try {
      const r = await fetch(`${base}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ genome }) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } finally {
      setBusy("");
    }
  };
  if (h === undefined) return <div className="muted">Checking for the local API…</div>;
  if (h === null || !h.live_evaluator_ready)
    return (
      <div className="space-y-5">
        <PageHeader eyebrow="Local tool" title="Live evaluator" lead="Pick any design and compare the surrogate prediction with the exact finite-element result. It needs the Python server, so it is switched off on a static website." />
        <section className="card">
          <h2 className="h2">What the live evaluator needs</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
            <li>The Python environment of the project (<code>make setup</code> or <code>pip install -r requirements.txt</code>): OpenSeesPy runs the exact analysis.</li>
            <li>The trained surrogate models <code>models/surrogate_A.joblib</code> and <code>surrogate_B.joblib</code>: created by <code>python -m rcopt.cli phase3</code> or copied from the shared Google Drive folder into <code>models/</code>.</li>
            <li>The dashboard built once (<code>cd web && npm run build</code>) so one server can host it.</li>
            <li>Then start everything with <code>python -m rcopt.cli serve</code> and open <b>http://localhost:8000</b>. This tab and the strength review in “My design estimate” switch on automatically.</li>
          </ol>
          <div className="mt-4">
            <Status ok={!!h} label="API reachable" />
            <Status ok={!!h?.live_evaluator_ready} label="Surrogate models present" />
          </div>
          <div className="card-soft mt-4 max-w-xl text-sm">
            If the server runs on another address (for example a teammate’s computer), type it here:
            <div className="mt-2 flex gap-2">
              <input className="input" value={base} placeholder="http://192.168.1.20:8000" onChange={(e) => setBase(e.target.value)} />
              <button className="btn" onClick={() => { saveBase(base); health(base).then(setH); }}>Connect</button>
            </div>
          </div>
        </section>
      </div>
    );
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Local tool"
        title={"Live evaluator"}
        lead="Pick any design and compare the surrogate prediction with the exact finite-element result (needs the local API)."
        howTo={[
          "Choose a value for each variable, then run the surrogate (instant) or the ground-truth check (about 50 ms).",
        ]}
      />
      <GravityCaveat />
      <div className="card grid grid-cols-2 gap-2 md:grid-cols-4">
        {space.genes.map((g, i) => (
          <label key={g.name} className="text-xs">
            <span className="font-mono">{g.name}</span>
            <select className="btn mt-0.5 w-full" value={genome[i]} onChange={(e) => setGenome(genome.map((v, k) => (k === i ? Number(e.target.value) : v)))}>
              {g.options.map((o, k) => <option key={k} value={k}>{String(o)}</option>)}
            </select>
          </label>
        ))}
      </div>
      <div className="flex gap-2">
        <button className="btn btn-on" disabled={!!busy} onClick={async () => setSur(await post("/evaluate/surrogate"))}>Surrogate prediction (A and B)</button>
        <button className="btn" disabled={!!busy} onClick={async () => setFe(await post("/evaluate/fe"))}>Ground truth: OpenSees FE + IS 456</button>
        {busy && <span className="muted self-center text-sm">running…</span>}
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {sur && (["A", "B"] as const).map((m) => (
          <div key={m} className="card text-sm">
            <div className="font-semibold">Surrogate {m}</div>
            <table className="t"><tbody>
              {["U_flex_max", "U_shear_max", "U_col_max", "defl_ratio_max"].map((k) => <tr key={k}><td>{k}</td><td>{num(sur[m][k], 3)}</td></tr>)}
              <tr><td>cost</td><td>{lakh(sur[m].cost)}</td></tr><tr><td>carbon</td><td>{tonnes(sur[m].carbon)}</td></tr>
              <tr><td>predicted feasible</td><td>{sur[m].feasible ? "✓" : "✕"}</td></tr>
            </tbody></table>
          </div>
        ))}
        {fe && (
          <div className="card text-sm">
            <div className="font-semibold">Ground truth</div>
            {fe.utilisation ? (
              <table className="t"><tbody>
                <tr><td>U_flex_max</td><td>{num(fe.utilisation.U_flex_max, 3)}</td></tr><tr><td>U_shear_max</td><td>{num(fe.utilisation.U_shear_max, 3)}</td></tr>
                <tr><td>U_col_max</td><td>{num(fe.utilisation.U_col_max, 3)}</td></tr><tr><td>deflection ratio</td><td>{num(fe.utilisation.deflection_ratio, 3)}</td></tr>
                <tr><td>cost</td><td>{lakh(fe.cost_inr?.total)}</td></tr><tr><td>carbon</td><td>{tonnes(fe.carbon_kgco2e?.total)}</td></tr>
                <tr><td>feasible</td><td>{fe.feasible ? "✓" : "✕ " + JSON.stringify(fe.violations)}</td></tr>
              </tbody></table>
            ) : <p>Status {fe.status}: {fe.geometry_reasons}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function Status({ ok, label }: { ok: boolean; label: string }) {
  return <div className="text-sm"><span className={`tag ${ok ? "tag-good" : "tag-bad"} mr-2`}>{ok ? "✓" : "✕"}</span>{label}</div>;
}
