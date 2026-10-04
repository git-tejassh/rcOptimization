// Cost / carbon / quantity arithmetic of the "My design" tab. It mirrors src/rcopt/cost_carbon/{cost,carbon,quantities}.py
// (same formulas, same constants from factors.json) so a design priced here matches the pipeline for the same quantities.

export interface RefDesign {
  cost: number;
  carbon: number;
  quantities?: Record<string, number>;
  concrete: string;
  steel: string;
  cement: string;
}

export interface Factors {
  grades: string[];
  steels: string[];
  cements: string[];
  cost: {
    concrete_per_m3: Record<string, number>;
    steel_per_kg: Record<string, number>;
    formwork_per_m2: number;
    cement_price_per_kg: Record<string, number>;
    cement_baseline: string;
    status: Record<string, string>;
  };
  carbon: {
    cement_per_kg: Record<string, number>;
    cement_content_kg_m3: Record<string, number>;
    concrete_other_per_m3: number;
    steel_per_kg: Record<string, number>;
    transport: Record<string, { distance_km: number; factor: number }>;
    concrete_density: number;
    status: Record<string, string>;
  };
  defaults: { beam_steel_kg_per_m3: number; column_steel_kg_per_m3: number; slab_thickness_mm: number; beam_side_formwork_net_of_slab: boolean; source: string };
  best_reference: { lowest_cost?: RefDesign; lowest_carbon?: RefDesign };
}

/** Everything the user may tweak (a deep copy of the project values, edited in place). */
export type Rates = Pick<Factors, "cost" | "carbon">;

export interface Quantities {
  concrete_m3: number;
  beam_concrete_m3: number;
  column_concrete_m3: number;
  steel_kg: number;
  beam_steel_kg: number;
  column_steel_kg: number;
  formwork_m2: number;
}
export interface Breakdown {
  cost: { concrete: number; steel: number; formwork: number; total: number };
  carbon: { concrete: number; steel: number; transport: number; total: number };
}

export const cloneRates = (f: Factors): Rates => JSON.parse(JSON.stringify({ cost: f.cost, carbon: f.carbon }));

export function estimate(q: Quantities, grade: string, steel: string, cement: string, r: Rates): Breakdown {
  const content = r.carbon.cement_content_kg_m3[grade];
  const adj = content * (r.cost.cement_price_per_kg[cement] - r.cost.cement_price_per_kg[r.cost.cement_baseline]);
  const c = q.concrete_m3 * (r.cost.concrete_per_m3[grade] + adj);
  const s = q.steel_kg * r.cost.steel_per_kg[steel];
  const f = q.formwork_m2 * r.cost.formwork_per_m2;
  const conc = q.concrete_m3 * (content * r.carbon.cement_per_kg[cement] + r.carbon.concrete_other_per_m3);
  const stl = q.steel_kg * r.carbon.steel_per_kg[steel];
  const tc = r.carbon.transport.concrete;
  const ts = r.carbon.transport.steel;
  const trans = ((q.concrete_m3 * r.carbon.concrete_density) / 1000) * tc.distance_km * tc.factor + (q.steel_kg / 1000) * ts.distance_km * ts.factor;
  return {
    cost: { concrete: c, steel: s, formwork: f, total: c + s + f },
    carbon: { concrete: conc, steel: stl, transport: trans, total: conc + stl + trans },
  };
}

export interface QuantityOptions {
  beamSteelKgM3: number;
  columnSteelKgM3: number;
  slabThicknessMm: number;
  deductColumnFromBeams: boolean;
  netSideFormwork: boolean;
}

export interface Group {
  kind: "beam" | "column";
  b_mm: number;
  D_mm: number;
  count: number;
  total_length_m: number;
}

/** Concrete / steel / formwork of member groups (same rules as quantities.py: beams clear between columns, columns full length). */
export function quantitiesFromGroups(groups: Group[], o: QuantityOptions): Quantities {
  const cols = groups.filter((g) => g.kind === "column" && g.total_length_m > 0);
  const nCols = cols.reduce((s, g) => s + g.count, 0);
  const meanCol = nCols ? cols.reduce((s, g) => s + g.count * (g.b_mm + g.D_mm) / 2, 0) / nCols / 1000 : 0;
  let bc = 0, cc = 0, form = 0;
  for (const g of groups) {
    if (!(g.total_length_m > 0) || !(g.b_mm > 0) || !(g.D_mm > 0)) continue;
    const b = g.b_mm / 1000, D = g.D_mm / 1000;
    if (g.kind === "beam") {
      const Lc = Math.max(g.total_length_m - (o.deductColumnFromBeams ? g.count * meanCol : 0), 0.1 * g.total_length_m);
      bc += b * D * Lc;
      const side = Math.max(D - (o.netSideFormwork ? o.slabThicknessMm / 1000 : 0), 0);
      form += (b + 2 * side) * Lc;
    } else {
      cc += b * D * g.total_length_m;
      form += 2 * (b + D) * g.total_length_m;
    }
  }
  const bs = bc * o.beamSteelKgM3, cs = cc * o.columnSteelKgM3;
  return { concrete_m3: bc + cc, beam_concrete_m3: bc, column_concrete_m3: cc, steel_kg: bs + cs, beam_steel_kg: bs, column_steel_kg: cs, formwork_m2: form };
}
