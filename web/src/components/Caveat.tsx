import { useData } from "../data";

export function GravityCaveat() {
  const { meta } = useData();
  return (
    <div className="flex gap-3 rounded-xl border p-3 text-sm" style={{ borderColor: "#e6d3a3", background: "#fbf5e6", color: "#5c4510" }}>
      <span aria-hidden className="text-base">⚠</span>
      <div>
        <strong>Gravity loads only.</strong> {meta.gravity_only_caveat}
      </div>
    </div>
  );
}

export function Finding({ level, text }: { level: "info" | "warn" | "bad"; text: string }) {
  const style =
    level === "bad"
      ? { borderColor: "var(--bad)", background: "#f8e7e5", color: "#6d241e" }
      : level === "warn"
        ? { borderColor: "var(--warn)", background: "#faf1dc", color: "#5c4510" }
        : { borderColor: "var(--accent)", background: "var(--accent-soft)", color: "#1d4f3a" };
  const icon = level === "bad" ? "✕" : level === "warn" ? "⚠" : "ℹ";
  return (
    <div className="flex gap-2 rounded-lg border-l-4 p-3 text-sm" style={style}>
      <span aria-hidden>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "good" | "warn" | "bad" }) {
  const color = tone === "good" ? "var(--good)" : tone === "warn" ? "var(--warn)" : tone === "bad" ? "var(--bad)" : "var(--fg)";
  return (
    <div className="card !p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wider muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold" style={{ color }}>{value}</div>
      {sub && <div className="mt-0.5 text-xs muted">{sub}</div>}
    </div>
  );
}
