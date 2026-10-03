export const lakh = (inr: number | null | undefined) => (inr == null ? "-" : `₹${(inr / 1e5).toFixed(2)} L`);
export const tonnes = (kg: number | null | undefined) => (kg == null ? "-" : `${(kg / 1000).toFixed(1)} t`);
export const num = (x: number | null | undefined, d = 3) => (x == null || !Number.isFinite(x) ? "-" : x.toFixed(d));
export const pct = (x: number | null | undefined, d = 1) => (x == null || !Number.isFinite(x) ? "-" : `${(100 * x).toFixed(d)} %`);
export const sci = (x: number) => x.toExponential(2);

export const isDark = () => document.documentElement.classList.contains("dark");
export const palette = {
  grade: { M20: "#94a3b8", M25: "#0ea5e9", M30: "#10b981", M35: "#f59e0b", M40: "#a855f7" } as Record<string, string>,
  steel: { Fe415: "#0ea5e9", Fe500: "#f97316" } as Record<string, string>,
  fronts: { A: "#0e7490", A_margin: "#6366f1", B: "#d97706", B_margin: "#be185d", direct: "#475569" } as Record<string, string>,
};
export const download = (name: string, text: string, mime = "text/plain") => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: mime }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
};
