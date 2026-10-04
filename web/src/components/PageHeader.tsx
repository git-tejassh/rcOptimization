import type { ReactNode } from "react";

/** Every page opens with the same block: what it is, why it matters, how to read it. */
export default function PageHeader({
  eyebrow,
  title,
  lead,
  howTo,
  children,
}: {
  eyebrow?: string;
  title: string;
  lead: string;
  howTo?: string[];
  children?: ReactNode;
}) {
  return (
    <header className="mb-1 space-y-3">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="h1 mt-0.5">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm muted">{lead}</p>
      </div>
      {howTo && howTo.length > 0 && (
        <details className="card-soft max-w-3xl" open>
          <summary>How to read this page</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {howTo.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </details>
      )}
      {children}
    </header>
  );
}

/** A titled card section with a one-line explanation of what it shows. */
export function Section({ title, hint, children, className = "" }: { title: string; hint?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      <h2 className="h2">{title}</h2>
      {hint && <p className="mb-3 mt-0.5 text-sm muted">{hint}</p>}
      {!hint && <div className="mb-2" />}
      {children}
    </section>
  );
}
