import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type {
  ComputeData,
  DesignSpaceData,
  Meta,
  ParetoData,
  ProvenanceData,
  SensitivityData,
  SurrogateData,
  VerificationData,
} from "./types";

export interface AllData {
  meta: Meta;
  space: DesignSpaceData;
  pareto: ParetoData;
  surrogate: SurrogateData;
  verification: VerificationData;
  compute: ComputeData;
  sensitivity: SensitivityData | null;
  provenance: ProvenanceData;
  benchmark: Record<string, any>;
}

const Ctx = createContext<AllData | null>(null);
export const useData = () => {
  const d = useContext(Ctx);
  if (!d) throw new Error("data not loaded");
  return d;
};

async function get<T>(name: string, optional = false): Promise<T | null> {
  const r = await fetch(`data/${name}.json`);
  if (!r.ok) {
    if (optional) return null;
    throw new Error(`data/${name}.json: HTTP ${r.status} (run \`make export\`)`);
  }
  return (await r.json()) as T;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<AllData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const [meta, space, pareto, surrogate, verification, compute, sensitivity, provenance, benchmark] = await Promise.all([
          get<Meta>("meta"),
          get<DesignSpaceData>("design_space"),
          get<ParetoData>("pareto"),
          get<SurrogateData>("surrogate"),
          get<VerificationData>("verification"),
          get<ComputeData>("compute"),
          get<SensitivityData>("sensitivity", true),
          get<ProvenanceData>("provenance"),
          get<Record<string, any>>("benchmark"),
        ]);
        setData({
          meta: meta!, space: space!, pareto: pareto!, surrogate: surrogate!, verification: verification!,
          compute: compute!, sensitivity, provenance: provenance!, benchmark: benchmark!,
        });
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, []);
  if (err)
    return (
      <div className="mx-auto max-w-xl p-8">
        <div className="card border-red-500">
          <div className="h2 text-red-600">Could not load the result data</div>
          <p className="mt-2 text-sm">{err}</p>
          <p className="muted mt-2 text-sm">Run the pipeline and <code>make export</code> (or <code>rcopt export</code>) to create <code>web/public/data/*.json</code>.</p>
        </div>
      </div>
    );
  if (!data) return <div className="p-8 muted">Loading results…</div>;
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}
