import { Component, createContext, useContext, useEffect, useState, type ReactNode } from "react";
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
      <div className="card border-red-500">
        <div className="h2 text-red-600">This page failed to render</div>
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

function readHash() {
  const h = window.location.hash.replace("#/", "").replace("#", "");
  return PAGES.some((p) => p.id === h) ? h : "overview";
}

function initialDark(): boolean {
  try {
    const s = localStorage.getItem("theme");
    if (s) return s === "dark";
  } catch {
    /* storage unavailable: fall back to the OS preference */
  }
  return false;   // light, neutral business look by default; the toggle remembers the choice
}

export default function App() {
  const { meta } = useData();
  const [page, setPage] = useState(readHash());
  const [dark, setDark] = useState(initialDark());
  useEffect(() => {
    const on = () => setPage(readHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }, [dark]);
  const Page = PAGES.find((p) => p.id === page)!.el;
  return (
    <ThemeCtx.Provider value={{ dark }}>
      {meta.provisional && (
        <div role="alert" className="px-4 py-1.5 text-center text-xs font-medium" style={{ background: "#f3e7c4", color: "#5c4510" }}>
          Provisional data: cost rates, several carbon inputs and the IS 456 table transcriptions are unverified placeholders, so absolute ₹ and kgCO₂e values are indicative.
          <a className="ml-2 underline" href="#/provenance">See details</a>
        </div>
      )}
      <header className="border-b" style={{ borderColor: "var(--line)", background: "var(--card)" }}>
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg text-white" style={{ background: "var(--accent)" }} aria-hidden>▤</div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">RC Frame Optimiser</div>
              <div className="text-xs muted">Cost vs embodied carbon · IS 456 · gravity loads</div>
            </div>
          </div>
          <nav className="flex flex-1 flex-wrap items-center gap-1" aria-label="Pages">
            {PAGES.map((p) => (
              <a
                key={p.id}
                href={`#/${p.id}`}
                aria-current={p.id === page ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${p.id === page ? "text-white" : p.id === "mine" ? "border" : ""}`}
                style={p.id === page ? { background: "var(--accent)" } : p.id === "mine" ? { borderColor: "var(--accent)", color: "var(--accent-strong)" } : { color: "var(--muted)" }}
              >
                {p.id === "mine" ? "＋ " : ""}{p.label}
              </a>
            ))}
          </nav>
          <button className="btn" onClick={() => setDark(!dark)} aria-label="Toggle dark mode">
            {dark ? "☀ Light" : "☾ Dark"}
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Boundary page={page}>
          <Page />
        </Boundary>
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-2 text-xs muted">
        Gravity-only (IS 456:2000) · generated {meta.generated} · config {meta.config_hash} · not a final design
      </footer>
    </ThemeCtx.Provider>
  );
}
