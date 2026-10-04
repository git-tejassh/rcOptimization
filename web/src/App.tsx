import { Component, createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useData } from "./data";
import Overview from "./pages/Overview";
import DesignSpacePage from "./pages/DesignSpacePage";
import ParetoPage from "./pages/ParetoPage";
import SurrogatePage from "./pages/SurrogatePage";
import VerificationPage from "./pages/VerificationPage";
import ComputePage from "./pages/ComputePage";
import SensitivityPage from "./pages/SensitivityPage";
import ProvenancePage from "./pages/ProvenancePage";
import LivePage from "./pages/LivePage";
import AboutPage from "./pages/AboutPage";
import MyDesignPage from "./pages/MyDesignPage";

/** A render error on one page must show a message, never a blank screen. */
class Boundary extends Component<{ children: ReactNode; page: string }, { err: string | null }> {
  state = { err: null as string | null };
  static getDerivedStateFromError(e: Error) {
    return { err: String(e) };
  }
  componentDidUpdate(prev: { page: string }) {
    if (prev.page !== this.props.page && this.state.err) this.setState({ err: null });
  }
  render() {
    return this.state.err ? (
      <div className="card" style={{ borderColor: "var(--bad)" }}>
        <div className="h2" style={{ color: "var(--bad)" }}>This page failed to render</div>
        <p className="mt-1 text-sm">{this.state.err}</p>
      </div>
    ) : (
      this.props.children
    );
  }
}

export const ThemeCtx = createContext<{ dark: boolean }>({ dark: false });
export const useTheme = () => useContext(ThemeCtx);

const PAGES: { id: string; label: string; el: () => JSX.Element }[] = [
  { id: "overview", label: "Overview", el: Overview },
  { id: "space", label: "Design space", el: DesignSpacePage },
  { id: "pareto", label: "Pareto explorer", el: ParetoPage },
  { id: "surrogate", label: "Surrogate performance", el: SurrogatePage },
  { id: "verification", label: "Verification", el: VerificationPage },
  { id: "compute", label: "Compute comparison", el: ComputePage },
  { id: "sensitivity", label: "Sensitivity", el: SensitivityPage },
  { id: "provenance", label: "Data & assumptions", el: ProvenancePage },
  { id: "live", label: "Live evaluator", el: LivePage },
  { id: "about", label: "About", el: AboutPage },
  { id: "mine", label: "My design estimate", el: MyDesignPage },
];
const label = (id: string) => PAGES.find((p) => p.id === id)!.label;

/** Top navigation: a few headers, each opening its own pages (same pattern as the reference site). */
const NAV: { title: string; items: { id: string; hint: string }[] }[] = [
  { title: "Overview", items: [{ id: "overview", hint: "Project summary and headline numbers" }] },
  { title: "Designs", items: [
    { id: "pareto", hint: "Browse the cost vs carbon designs" },
    { id: "verification", hint: "Were the predictions confirmed by the exact model?" },
  ] },
  { title: "Method", items: [
    { id: "space", hint: "What the optimiser may choose and the code limits" },
    { id: "surrogate", hint: "How accurate the fast predictors are" },
    { id: "compute", hint: "Was the shortcut worth it?" },
    { id: "sensitivity", hint: "What if prices or factors are wrong?" },
  ] },
  { title: "Data", items: [
    { id: "provenance", hint: "Sources, assumptions, decisions, benchmark" },
    { id: "about", hint: "Scope, limits, deviations from the brief" },
  ] },
  { title: "Live evaluator", items: [{ id: "live", hint: "Local tool: exact check of any design" }] },
];

function readHash() {
  const h = window.location.hash.replace("#/", "").replace("#", "");
  return PAGES.some((p) => p.id === h) ? h : "overview";
}

function initialDark(): boolean {
  try {
    const s = localStorage.getItem("theme");
    if (s) return s === "dark";
  } catch {
    /* storage unavailable: fall back to the light default */
  }
  return false;
}

export default function App() {
  const { meta } = useData();
  const [page, setPage] = useState(readHash());
  const [dark, setDark] = useState(initialDark());
  const [open, setOpen] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const navRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const on = () => { setPage(readHash()); setOpen(null); setMenu(false); window.scrollTo({ top: 0 }); };
    window.addEventListener("hashchange", on);
    const close = (e: MouseEvent) => { if (navRef.current && !navRef.current.contains(e.target as Node)) setOpen(null); };
    document.addEventListener("click", close);
    return () => { window.removeEventListener("hashchange", on); document.removeEventListener("click", close); };
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);
  const Page = PAGES.find((p) => p.id === page)!.el;
  const groupOf = (g: (typeof NAV)[number]) => g.items.some((i) => i.id === page);

  return (
    <ThemeCtx.Provider value={{ dark }}>
      {meta.provisional && (
        <div role="alert" className="px-4 py-1.5 text-center text-xs font-medium" style={{ background: "#f3e7c4", color: "#5c4510" }}>
          Provisional data: cost rates, several carbon inputs and the IS 456 table transcriptions are unverified placeholders, so absolute ₹ and kgCO₂e values are indicative.
          <a className="ml-2 underline" href="#/provenance">See details</a>
        </div>
      )}
      <header className="sticky top-0 z-40" style={{ background: "#1d1e1c" }}>
        <div ref={navRef} className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2.5">
          <a href="#/overview" className="flex items-center gap-2.5 text-white" aria-label="RC Frame Optimiser, home">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg text-lg font-semibold text-white" style={{ background: "var(--accent)" }} aria-hidden>▤</span>
            <span className="leading-tight">
              <span className="block text-sm font-semibold tracking-wide">RC Frame Optimiser</span>
              <span className="block text-[11px] text-white/60">Cost vs embodied carbon</span>
            </span>
          </a>
          <button className="ml-auto rounded-lg border border-white/30 px-3 py-1.5 text-sm text-white md:hidden" onClick={() => setMenu(!menu)} aria-expanded={menu} aria-label="Menu">☰ Menu</button>
          <nav className={`${menu ? "flex" : "hidden"} absolute left-0 right-0 top-full flex-col gap-1 bg-[#1d1e1c] px-4 pb-4 md:static md:flex md:flex-1 md:flex-row md:items-center md:justify-end md:gap-1 md:bg-transparent md:p-0`} aria-label="Main">
            {NAV.map((g) => {
              const on = groupOf(g);
              if (g.items.length === 1) {
                const it = g.items[0];
                return <a key={g.title} href={`#/${it.id}`} aria-current={page === it.id ? "page" : undefined} className={`navlink ${on ? "navlink-on" : ""}`}>{g.title}</a>;
              }
              return (
                <div key={g.title} className="relative" onMouseEnter={() => window.innerWidth >= 768 && setOpen(g.title)} onMouseLeave={() => setOpen(null)}>
                  <button className={`navlink ${on ? "navlink-on" : ""}`} aria-haspopup="true" aria-expanded={open === g.title} onClick={(e) => { e.stopPropagation(); setOpen(open === g.title ? null : g.title); }}>
                    {g.title} <span aria-hidden className="text-[10px]">▾</span>
                  </button>
                  {open === g.title && (
                    <div className="dropdown" role="menu">
                      {g.items.map((it) => (
                        <a key={it.id} href={`#/${it.id}`} role="menuitem" aria-current={page === it.id ? "page" : undefined}>
                          <span className="block">{label(it.id)}</span>
                          <span className="block text-xs font-normal muted">{it.hint}</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            <a href="#/mine" aria-current={page === "mine" ? "page" : undefined} className="btn-primary md:ml-2">My design estimate <span aria-hidden>→</span></a>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <Boundary page={page}>
          <Page />
        </Boundary>
      </main>

      <footer className="mt-10" style={{ background: "#1d1e1c", color: "rgba(255,255,255,0.8)" }}>
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-3">
          <div>
            <div className="flex items-center gap-2 text-white"><span className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: "var(--accent)" }} aria-hidden>▤</span><b>RC Frame Optimiser</b></div>
            <p className="mt-3 text-sm text-white/60">Surrogate-assisted multi-objective optimisation of an RC frame for cost and embodied carbon. B.Tech Civil major project, MANIT Bhopal.</p>
          </div>
          <div>
            <div className="eyebrow">Pages</div>
            <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              {PAGES.map((p) => <li key={p.id}><a className="hover:text-[color:var(--accent)]" href={`#/${p.id}`}>{p.label}</a></li>)}
            </ul>
          </div>
          <div className="text-sm">
            <div className="eyebrow">Read before quoting a number</div>
            <ul className="mt-3 space-y-1.5 text-white/70">
              <li>Gravity loads only (IS 456:2000); no seismic or wind design.</li>
              <li>Prices and several carbon inputs are provisional.</li>
              <li>Generated {meta.generated} · config {meta.config_hash}</li>
            </ul>
            <button className="mt-4 rounded-full border border-white/30 px-3 py-1 text-xs text-white" onClick={() => setDark(!dark)}>{dark ? "☀ Light page" : "☾ Dark page"}</button>
          </div>
        </div>
        <div className="border-t border-white/10 px-4 py-3 text-center text-xs text-white/50">Layout inspired by eggentaler-bau.com; no third-party text or images are used.</div>
      </footer>
    </ThemeCtx.Provider>
  );
}
