// Browser-side reader for the subset of the STAAD.Pro input language needed for a quantity estimate:
// UNIT, JOINT COORDINATES, MEMBER INCIDENCES, MEMBER PROPERTY (PRISMATIC YD / ZD). Everything else is skipped.
// It reads only geometry and section sizes: reinforcement is NOT in a STAAD input and is assumed by the estimator.

export interface StaadMember {
  id: number;
  n1: number;
  n2: number;
  length_m: number;
  kind: "beam" | "column";
  b_mm: number;
  D_mm: number;
  hasSection: boolean;
}
export interface StaadGroup {
  key: string;
  kind: "beam" | "column";
  b_mm: number;
  D_mm: number;
  count: number;
  total_length_m: number;
}
export interface StaadModel {
  joints: number;
  members: StaadMember[];
  groups: StaadGroup[];
  warnings: string[];
  verticalAxis: "y" | "z";
  lengthUnit: string;
}

const UNIT_TO_M: Record<string, number> = {
  METER: 1, METRE: 1, MET: 1, MTR: 1, M: 1, CM: 0.01, MMS: 0.001, MM: 0.001, INCH: 0.0254, INCHES: 0.0254, IN: 0.0254,
  FEET: 0.3048, FT: 0.3048, KIP_PLACEHOLDER: 1,
};

function expandIds(tokens: string[]): number[] {
  const out: number[] = [];
  for (let i = 0; i < tokens.length; i++) {
    if (i + 2 < tokens.length && tokens[i + 1].toUpperCase() === "TO") {
      const a = parseInt(tokens[i], 10);
      const b = parseInt(tokens[i + 2], 10);
      for (let k = a; k <= b; k++) out.push(k);
      i += 2;
    } else if (/^\d+$/.test(tokens[i])) out.push(parseInt(tokens[i], 10));
  }
  return out;
}

function logicalLines(text: string): string[] {
  const lines: string[] = [];
  let buf = "";
  for (const raw of text.split(/\r?\n/)) {
    const s = raw.trim();
    if (!s || s.startsWith("<!") || s.startsWith("*")) continue;
    if (s.endsWith("-")) {
      buf += s.slice(0, -1) + " ";
      continue;
    }
    lines.push((buf + s).trim());
    buf = "";
  }
  return lines;
}

export function parseStaad(text: string): StaadModel {
  const warnings: string[] = [];
  const verticalAxis: "y" | "z" = /SET\s+Z\s+UP/i.test(text) ? "z" : "y";
  let unitM = 1;
  let unitName = "METER";
  const joints = new Map<number, [number, number, number]>();
  const inc = new Map<number, [number, number]>();
  const sect = new Map<number, [number, number]>(); // member -> [width b, depth D] in mm
  let block = "";
  const circular = new Set<number>();

  for (const line of logicalLines(text)) {
    const up = line.toUpperCase();
    const mu = up.match(/^UNIT\s+(\w+)/);
    if (mu && UNIT_TO_M[mu[1]] !== undefined) {
      unitM = UNIT_TO_M[mu[1]];
      unitName = mu[1];
      continue;
    }
    if (up.startsWith("JOINT COORDINATES")) { block = "joints"; continue; }
    if (up.startsWith("MEMBER INCIDENCES")) { block = "inc"; continue; }
    if (up.startsWith("MEMBER PROPERTY")) { block = "prop"; continue; }
    if (/^(DEFINE|CONSTANTS|SUPPORTS|LOAD|PERFORM|START|FINISH|MEMBER (LOAD|WEIGHT)|SELFWEIGHT|FLOOR|CHECK|PRINT)/.test(up)) { block = ""; continue; }
    if (block === "joints") {
      for (const stmt of line.split(";")) {
        const t = stmt.trim().split(/\s+/);
        if (t.length >= 4 && /^\d+$/.test(t[0])) joints.set(+t[0], [+t[1] * unitM, +t[2] * unitM, +t[3] * unitM]);
      }
    } else if (block === "inc") {
      for (const stmt of line.split(";")) {
        const t = stmt.trim().split(/\s+/);
        if (t.length >= 3 && /^\d+$/.test(t[0])) inc.set(+t[0], [+t[1], +t[2]]);
      }
    } else if (block === "prop") {
      const m = line.match(/^(.*?)\bPRIS(?:MATIC)?\b(.*)$/i);
      if (!m) {
        if (/\b(TABLE|TAPERED|GENERAL)\b/i.test(line)) warnings.push("A non-prismatic / catalogue section was ignored (only PRISMATIC YD ZD is read).");
        continue;
      }
      const ids = expandIds(m[1].trim().split(/\s+/));
      const yd = m[2].match(/\bYD\s+([\d.eE+-]+)/i);
      const zd = m[2].match(/\bZD\s+([\d.eE+-]+)/i);
      if (!yd) continue;
      const depth = +yd[1] * unitM * 1000;
      const width = zd ? +zd[1] * unitM * 1000 : depth;
      for (const id of ids) {
        sect.set(id, [width, depth]);
        if (!zd) circular.add(id);
      }
    }
  }
  if (joints.size === 0 || inc.size === 0) warnings.push("No JOINT COORDINATES / MEMBER INCIDENCES were found: is this a STAAD input (.std) text file?");
  if (circular.size) warnings.push(`${circular.size} circular section(s) (PRIS YD only) were treated as a square of equal area.`);

  const members: StaadMember[] = [];
  let missing = 0;
  for (const [id, [a, b]] of inc) {
    const p = joints.get(a);
    const q = joints.get(b);
    if (!p || !q) continue;
    const d = [q[0] - p[0], q[1] - p[1], q[2] - p[2]];
    const L = Math.hypot(d[0], d[1], d[2]);
    if (L < 1e-9) continue;
    const dv = Math.abs(verticalAxis === "y" ? d[1] : d[2]);
    const kind = dv >= 0.7 * L ? "column" : "beam";
    let s = sect.get(id);
    const has = !!s;
    if (!s) { s = [0, 0]; missing++; }
    let [bw, dd] = s;
    if (circular.has(id)) { const side = bw * Math.sqrt(Math.PI) / 2; bw = dd = side; }
    if (kind === "column" && bw > dd) [bw, dd] = [dd, bw];
    members.push({ id, n1: a, n2: b, length_m: L, kind, b_mm: bw, D_mm: dd, hasSection: has });
  }
  if (missing) warnings.push(`${missing} member(s) have no section property and are excluded from the quantities.`);

  const groups = new Map<string, StaadGroup>();
  for (const m of members.filter((x) => x.hasSection)) {
    const key = `${m.kind}-${Math.round(m.b_mm)}x${Math.round(m.D_mm)}`;
    const g = groups.get(key) ?? { key, kind: m.kind, b_mm: Math.round(m.b_mm), D_mm: Math.round(m.D_mm), count: 0, total_length_m: 0 };
    g.count += 1;
    g.total_length_m += m.length_m;
    groups.set(key, g);
  }
  return {
    joints: joints.size,
    members,
    groups: [...groups.values()].sort((a, b) => (a.kind === b.kind ? b.total_length_m - a.total_length_m : a.kind === "beam" ? -1 : 1)),
    warnings,
    verticalAxis,
    lengthUnit: unitName,
  };
}
