import { useEffect, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";

type Props = {
  data: any[];
  layout?: Record<string, any>;
  height?: number;
  onClick?: (pt: any) => void;
  dark?: boolean;
};

/** Thin Plotly wrapper (basic bundle: scatter / bar / histogram). Theme-aware, responsive. */
export default function Plot({ data, layout = {}, height = 420, onClick, dark }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const isDark = dark ?? document.documentElement.classList.contains("dark");
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const fg = isDark ? "#e2e8f0" : "#0f172a";
    const grid = isDark ? "#24314d" : "#e2e8f0";
    const lay = {
      height,
      margin: { l: 60, r: 20, t: 30, b: 50 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: fg, size: 12 },
      legend: { orientation: "h", y: -0.2 },
      ...layout,
      xaxis: { gridcolor: grid, zerolinecolor: grid, ...(layout.xaxis || {}) },
      yaxis: { gridcolor: grid, zerolinecolor: grid, ...(layout.yaxis || {}) },
    };
    Plotly.react(el, data, lay as any, { responsive: true, displaylogo: false });
    const anyEl = el as any;
    if (onClick) {
      anyEl.removeAllListeners?.("plotly_click");
      anyEl.on?.("plotly_click", (ev: any) => ev.points?.length && onClick(ev.points[0]));
    }
  }, [data, layout, height, onClick, isDark]);
  useEffect(() => {
    const el = ref.current;
    return () => {
      if (el) Plotly.purge(el);
    };
  }, []);
  return <div ref={ref} className="w-full" role="img" aria-label="chart" />;
}
