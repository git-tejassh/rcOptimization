// Talks to the local Python API (live evaluator + strength review). Same origin when served by `rcopt serve`,
// otherwise the address the user typed (default http://localhost:8000). Static hosting has no API: callers must handle that.
const KEY = "rcopt_api_base";
export const defaultBase = (): string => {
  const env = (import.meta as any).env?.VITE_API_URL as string | undefined;
  if (env) return env.replace(/\/$/, "");
  try {
    const s = localStorage.getItem(KEY);
    if (s) return s;
  } catch { /* ignore */ }
  return window.location.protocol === "file:" ? "http://localhost:8000" : "";
};
export const saveBase = (b: string) => { try { localStorage.setItem(KEY, b); } catch { /* ignore */ } };

export interface Health {
  status: string;
  service?: string;
  strength_review?: boolean;
  live_evaluator_ready?: boolean;
  price_optimiser?: boolean;
  surrogates?: Record<string, boolean>;
}

export async function health(base: string): Promise<Health | null> {
  try {
    const r = await fetch(`${base}/health`);
    if (!r.ok || !(r.headers.get("content-type") ?? "").includes("json")) return null;
    const j = (await r.json()) as Health;
    return j.service === "rcopt" ? j : null;
  } catch {
    return null;
  }
}

export interface ReviewReport {
  verdict: "PASS" | "FAIL";
  failures: string[];
  frame: { bays_x_m: number[]; bays_z_m: number[]; storey_heights_m: number[]; base_to_first_beam_level_m: number; n_members: number; n_joints: number };
  materials: { concrete: string; steel: string; cement: string; fck_MPa: number; fy_MPa: number };
  beams: {
    group: number; levels: number[]; b_mm: number; D_mm: number; demand: { Msag_kNm: number; Mhog_kNm: number; Vu_kN: number };
    bottom: string; top: string; stirrups: string; Mu_sag_kNm: number; Mu_hog_kNm: number; U_sag: number; U_hog: number; U_shear: number;
    tau_v: number; tau_c: number; pt_bot: number; pt_top: number; pass: boolean; reasons: string[];
  }[];
  columns: {
    group: number; storeys: number[]; is_base_group: boolean; b_mm: number; D_mm: number; bars: string; pt_percent: number;
    governing: { Pu_kN: number; MD_kNm: number; Mb_kNm: number; l_mm: number }; MuD1_kNm: number; Mub1_kNm: number; alpha_n: number;
    Puz_kN: number; U: number; slender: boolean; pass: boolean; reasons: string[];
  }[];
  deflection: { ratio_to_L_over_250: number; max_mm: number; pass: boolean };
  quantities: { concrete_m3: number; beam_concrete_m3: number; column_concrete_m3: number; steel_kg: number; beam_steel_kg: number; column_steel_kg: number; formwork_m2: number };
  notes: string[];
  assumptions: string[];
}

export async function reviewStaad(base: string, text: string, concrete: string, steel: string, cement: string): Promise<ReviewReport> {
  const r = await fetch(`${base}/review/staad`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, concrete, steel, cement }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : `HTTP ${r.status}`);
  return j as ReviewReport;
}

/** One editable unit price (keys match src/rcopt/cost_carbon/prices.py). */
export interface PriceItem { key: string; label: string; unit: string; group: string; default: number }

export interface OptimiseResult {
  prices: Record<string, number>;
  defaults: Record<string, number>;
  changed: Record<string, number>;
  mode: string;
  engine: string;
  pop_size: number;
  n_gen: number;
  evaluations: number | null;
  wall_s: number;
  n_candidates: number;
  n_feasible_true: number;
  rejected: number;
  designs: import("../types").ParetoDesign[] & { pareto_true?: boolean }[];
  baseline_repriced: Record<string, { cost_old_prices: number; cost_new_prices: number; carbon: number; concrete: string; steel: string; cement: string }>;
  note: string;
}
export interface Job {
  job_id: string;
  status: "running" | "done" | "failed";
  elapsed_s: number;
  progress: { stage?: string; gen?: number; n_gen?: number; feasible?: number; n_candidates?: number };
  result?: OptimiseResult;
  error?: string;
}

async function asJson(r: Response) {
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : `HTTP ${r.status}`);
  return j;
}
export const startOptimise = (base: string, prices: Record<string, number>, mode: string): Promise<{ job_id: string }> =>
  fetch(`${base}/optimize/prices`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prices, mode }) }).then(asJson);
export const jobStatus = (base: string, id: string): Promise<Job> => fetch(`${base}/optimize/jobs/${id}`).then(asJson);
