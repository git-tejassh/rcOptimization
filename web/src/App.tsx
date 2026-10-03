import { createContext, useContext, useEffect, useState } from "react";
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
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
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
        <div role="alert" className="bg-amber-500 px-4 py-2 text-center text-sm font-semibold text-black">
          ⚠ PROVISIONAL DATA - cost rates, emission factors and IS 456 table transcriptions are unverified placeholders; absolute ₹ and kgCO₂e values are indicative only.
          <a className="ml-2 underline" href="#/provenance">Details</a>
        </div>
      )}
      <header className="border-b" style={{ borderColor: "var(--line)" }}>
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="mr-2 text-base font-semibold">RC frame · cost vs embodied carbon</div>
          <nav className="flex flex-wrap gap-1" aria-label="Pages">
            {PAGES.map((p) => (
              <a key={p.id} href={`#/${p.id}`} className={`btn ${p.id === page ? "btn-on" : ""}`} aria-current={p.id === page ? "page" : undefined}>
                {p.label}
              </a>
            ))}
          </nav>
          <button className="btn ml-auto" onClick={() => setDark(!dark)} aria-label="Toggle dark mode">
            {dark ? "☀ Light" : "☾ Dark"}
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">
        <Page />
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-2 text-xs muted">
        Gravity-only (IS 456:2000) · generated {meta.generated} · config {meta.config_hash} · not a final design
      </footer>
    </ThemeCtx.Provider>
  );
}
