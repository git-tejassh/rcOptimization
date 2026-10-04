import { useEffect, useState } from "react";
import { useData } from "../data";
import PageHeader from "../components/PageHeader";
import { GravityCaveat } from "../components/Caveat";
import { lakh, num, tonnes } from "../format";

const API = (import.meta as any).env?.VITE_API_URL as string | undefined;

type Res = Record<string, any>;

export default function LivePage() {
  const { space, pareto } = useData();
  const [up, setUp] = useState<boolean | null>(null);
  const [genome, setGenome] = useState<number[]>(() => pareto.variants.A[Math.floor(pareto.variants.A.length / 2)]?.genome ?? space.genes.map(() => 0));
  const [sur, setSur] = useState<Res | null>(null);
  const [fe, setFe] = useState<Res | null>(null);
  const [busy, setBusy] = useState("");
  useEffect(() => {
    if (!API) return setUp(false);
    fetch(`${API}/health`).then((r) => setUp(r.ok)).catch(() => setUp(false));
  }, []);
  const post = async (path: string) => {
    setBusy(path);
    try {
      const r = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ genome }) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } finally {
      setBusy("");
    }
  };
  if (up === null) return <div className="muted">Checking for the local API…</div>;
  if (!up)
    return (
      <div className="space-y-3">
        <PageHeader eyebrow="Local tool" title="Live evaluator" lead="Pick any design and compare the surrogate prediction with the exact finite-element result. This tool needs the local API, so it is switched off on a static site." />
        <div className="card border-amber-500">
          <p className="text-sm">
            The live evaluator needs the local FastAPI server (surrogate models + OpenSees) which cannot run on a static / Vercel deployment. No API was found
            {API ? ` at ${API}` : " (VITE_API_URL is not set)"}.
          </p>
          <p className="mt-2 text-sm muted">Locally: <code>make api</code> in one terminal, then <code>VITE_API_URL=http://localhost:8000 npm run dev</code> in <code>web/</code>. Everything else in this dashboard works without it.</p>
        </div>
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
