import { useData } from "../data";

export function GravityCaveat() {
  const { meta } = useData();
  return (
    <div className="rounded-md border border-amber-500 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
      <strong>Gravity-only caveat.</strong> {meta.gravity_only_caveat}
    </div>
  );
}

export function Finding({ level, text }: { level: "info" | "warn" | "bad"; text: string }) {
  const style =
    level === "bad"
      ? "border-red-600 bg-red-50 text-red-950 dark:bg-red-950/40 dark:text-red-100"
      : level === "warn"
        ? "border-amber-500 bg-amber-50 text-amber-950 dark:bg-amber-950/40 dark:text-amber-100"
        : "border-cyan-600 bg-cyan-50 text-cyan-950 dark:bg-cyan-950/40 dark:text-cyan-100";
  const icon = level === "bad" ? "✕" : level === "warn" ? "⚠" : "ℹ";
  return (
    <div className={`flex gap-2 rounded-md border-l-4 p-2.5 text-sm ${style}`}>
      <span aria-hidden>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {sub && <div className="mt-0.5 text-xs muted">{sub}</div>}
    </div>
  );
}
