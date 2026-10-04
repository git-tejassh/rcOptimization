// "Bad / good / best" regions of the cost-carbon plane, measured against the best achievable values.
export interface Ideal {
  cost: number;
  carbon: number;
}
export type Zone = "best" | "good" | "bad";

/** Relative excess over the best value on the worse of the two objectives (0 = as good as the best on both). */
export const excess = (cost: number, carbon: number, ideal: Ideal) => Math.max(cost / ideal.cost - 1, carbon / ideal.carbon - 1);

export const zoneOf = (cost: number, carbon: number, ideal: Ideal, bestPct: number, goodPct: number): Zone => {
  const e = excess(cost, carbon, ideal);
  return e <= bestPct / 100 ? "best" : e <= goodPct / 100 ? "good" : "bad";
};

export const ZONE_COLORS = {
  best: { fill: "rgba(47,125,91,0.20)", line: "#2f7d5b", label: "Best" },
  good: { fill: "rgba(222,176,60,0.22)", line: "#b7791f", label: "Good" },
  bad: { fill: "rgba(196,80,70,0.13)", line: "#b4443c", label: "Bad" },
};

/** Plotly rectangles anchored at the ideal corner: red (everything), yellow (within goodPct), green (within bestPct). */
export function zoneShapes(ideal: Ideal, bestPct: number, goodPct: number, xMax: number, yMax: number) {
  const x0 = 0, y0 = 0; // paper-wide rectangles in data space start at the axis origin of the visible range
  const rect = (x1: number, y1: number, fill: string) => ({ type: "rect", xref: "x", yref: "y", x0, x1, y0, y1, fillcolor: fill, line: { width: 0 }, layer: "below" });
  return [
    rect(xMax, yMax, ZONE_COLORS.bad.fill),
    rect(ideal.cost * (1 + goodPct / 100), ideal.carbon * (1 + goodPct / 100), ZONE_COLORS.good.fill),
    rect(ideal.cost * (1 + bestPct / 100), ideal.carbon * (1 + bestPct / 100), ZONE_COLORS.best.fill),
  ];
}
