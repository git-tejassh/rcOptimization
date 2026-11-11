import type { ReactNode } from "react";

interface Action {
  label: string;
  href: string;
  primary?: boolean;
}

/** Default hero buttons per page (hash route -> [primary, secondary]), so every hero offers a next step. */
const ACTIONS: Record<string, Action[]> = {
  overview: [{ label: "Explore the designs", href: "#/pareto", primary: true }, { label: "Estimate my design", href: "#/mine" }],
  space: [{ label: "Browse the designs", href: "#/pareto", primary: true }, { label: "Read the assumptions", href: "#/provenance" }],
  pareto: [{ label: "Estimate my own design", href: "#/mine", primary: true }, { label: "How it was verified", href: "#/verification" }],
  optimise: [{ label: "Estimate my own design", href: "#/mine", primary: true }, { label: "Pareto explorer", href: "#/pareto" }],
  surrogate: [{ label: "See the verification", href: "#/verification", primary: true }, { label: "Compute comparison", href: "#/compute" }],
  verification: [{ label: "Open the Pareto explorer", href: "#/pareto", primary: true }, { label: "Surrogate performance", href: "#/surrogate" }],
  compute: [{ label: "Sensitivity of the result", href: "#/sensitivity", primary: true }, { label: "Back to the overview", href: "#/overview" }],
  sensitivity: [{ label: "Estimate my design", href: "#/mine", primary: true }, { label: "Data and assumptions", href: "#/provenance" }],
  provenance: [{ label: "Open the sensitivity study", href: "#/sensitivity", primary: true }, { label: "About the project", href: "#/about" }],
  live: [{ label: "Pareto explorer", href: "#/pareto", primary: true }, { label: "Overview", href: "#/overview" }],
  about: [{ label: "Explore the designs", href: "#/pareto", primary: true }, { label: "Data and assumptions", href: "#/provenance" }],
  mine: [{ label: "Compare on the Pareto map", href: "#/pareto", primary: true }, { label: "Data and assumptions", href: "#/provenance" }],
};

const FRAME = (
  // a stylised 4-bay, 4-storey frame elevation: the structure the project optimises
  <svg viewBox="0 0 420 300" className="absolute bottom-0 right-0 hidden h-full max-h-[22rem] w-auto opacity-30 md:block" aria-hidden>
    {[0, 1, 2, 3, 4].map((y) => <line key={`b${y}`} x1="20" x2="400" y1={270 - y * 62} y2={270 - y * 62} stroke="#53ac35" strokeWidth="5" />)}
    {[0, 1, 2, 3, 4].map((x) => <line key={`c${x}`} x1={20 + x * 95} x2={20 + x * 95} y1="270" y2={270 - 4 * 62} stroke="#53ac35" strokeWidth="7" />)}
    {[0, 1, 2, 3, 4].map((x) => <rect key={`f${x}`} x={8 + x * 95} y="270" width="24" height="12" fill="#53ac35" />)}
  </svg>
);

/** The single hero of a page: one H1, a one-sentence purpose, and next-step buttons. */
export default function PageHeader({
  eyebrow,
  title,
  lead,
  howTo,
  actions,
}: {
  eyebrow?: string;
  title: string;
  lead: string;
  howTo?: string[];
  actions?: Action[];
}) {
  const page = (window.location.hash.replace("#/", "").replace("#", "") || "overview").split("?")[0];
  const buttons = actions ?? ACTIONS[page] ?? [];
  return (
    <>
      <header className="hero -mt-6 mb-8">
        <div className="relative mx-auto flex min-h-[19rem] max-w-7xl flex-col justify-center px-4 py-12">
          {FRAME}
          <div className="relative max-w-3xl">
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <h1 className="hero-title mt-2">{title}</h1>
            <p className="mt-4 max-w-2xl text-base text-white/80">{lead}</p>
            {buttons.length > 0 && (
              <div className="mt-6 flex flex-wrap gap-3">
                {buttons.map((b) => (
                  <a key={b.href} href={b.href} className={b.primary ? "btn-hero" : "btn-hero-outline"}>{b.label} {b.primary && <span aria-hidden>→</span>}</a>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>
      {howTo && howTo.length > 0 && (
        <details className="card-soft mb-6 max-w-4xl" open>
          <summary>How to read this page</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {howTo.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        </details>
      )}
    </>
  );
}

/** A section: small green label, a semibold heading, and a one-line explanation. Not an H1: the hero owns that. */
export function Section({ title, hint, eyebrow, children, className = "" }: { title: string; hint?: string; eyebrow?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
      <h2 className="h2">{title}</h2>
      {hint && <p className="mb-4 mt-1 max-w-3xl text-sm muted">{hint}</p>}
      {!hint && <div className="mb-3" />}
      {children}
    </section>
  );
}
