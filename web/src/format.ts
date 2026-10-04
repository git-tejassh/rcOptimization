export const lakh = (inr: number | null | undefined) => (inr == null ? "-" : `₹${(inr / 1e5).toFixed(2)} L`);
export const tonnes = (kg: number | null | undefined) => (kg == null ? "-" : `${(kg / 1000).toFixed(1)} t`);
export const num = (x: number | null | undefined, d = 3) => (x == null || !Number.isFinite(x) ? "-" : x.toFixed(d));
export const pct = (x: number | null | undefined, d = 1) => (x == null || !Number.isFinite(x) ? "-" : `${(100 * x).toFixed(d)} %`);
export const sci = (x: number) => x.toExponential(2);

export const isDark = () => document.documentElement.classList.contains("dark");
export const palette = {
  grade: { M20: "#94a3b8", M25: "#9bc3ae", M30: "#4f9b78", M35: "#c9a24a", M40: "#7a5c2e" } as Record<string, string>,
  steel: { Fe415: "#7aa88f", Fe500: "#8a5a2b" } as Record<string, string>,
  fronts: { A: "#2f7d5b", A_margin: "#7aa88f", B: "#b7791f", B_margin: "#1d5a40", direct: "#566059" } as Record<string, string>,
};
export const download = (name: string, text: string, mime = "text/plain") => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: mime }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
};
