import { motion } from "framer-motion";
import { useState } from "react";
import { pill } from "../lib/motion";
import { MovingBorderChip } from "./MovingBorder";

export type Tab = "portfolio" | "signals" | "backtest" | "market";
export const TABS: { id: Tab; label: string }[] = [
  { id: "portfolio", label: "Portfolio" },
  { id: "signals", label: "Signals" },
  { id: "backtest", label: "Backtest" },
  { id: "market", label: "Market" },
];

function Mark() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="9" fill="#111111" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="8.5" fill="none" stroke="rgba(255,255,255,0.12)" />
      <path d="M7 22l6-6 4 3 8-9" fill="none" stroke="#3b82f6" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="25" cy="10" r="2" fill="#93c5fd" />
    </svg>
  );
}

function Tabs({ tab, onTab, className }: { tab: Tab; onTab: (t: Tab) => void; className?: string }) {
  const [hover, setHover] = useState<Tab | null>(null);
  return (
    <nav role="tablist" aria-label="Sections" className={className} onMouseLeave={() => setHover(null)}>
      {TABS.map((t) => {
        const active = tab === t.id;
        return (
          <button
            key={t.id}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onTab(t.id)}
            onMouseEnter={() => setHover(t.id)}
            onFocus={() => setHover(t.id)}
            className={`relative flex-1 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors duration-200 sm:flex-none ${active ? "text-fg" : "text-fg-2 hover:text-fg"}`}
          >
            {hover === t.id && !active && (
              <motion.span layoutId="tab-hover" className="absolute inset-0 rounded-full bg-white/[0.05]" transition={{ type: "spring", stiffness: 650, damping: 48 }} />
            )}
            {active && (
              <motion.span layoutId="tab-active" className="absolute inset-0 rounded-full bg-white/[0.09] ring-1 ring-inset ring-white/[0.08]" transition={pill} />
            )}
            <span className="relative">{t.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export function Nav({ tab, onTab, riskOn, asOf }: { tab: Tab; onTab: (t: Tab) => void; riskOn: boolean | null; asOf?: string }) {
  return (
    <header className="sticky top-0 z-30 pt-3">
      <div className="mx-auto max-w-[1240px] px-4 sm:px-6">
        <div className="flex items-center gap-3 rounded-2xl border border-line bg-[#0a0a0a]/75 px-3 py-2 shadow-bar backdrop-blur-xl sm:gap-5 sm:px-4">
          <a href="#portfolio" className="flex items-center gap-2.5 rounded-lg" onClick={(e) => { e.preventDefault(); onTab("portfolio"); }}>
            <Mark />
            <span className="text-[15px] font-semibold tracking-tight">Stock Analyse</span>
          </a>
          <Tabs tab={tab} onTab={onTab} className="hidden items-center gap-0.5 rounded-full bg-white/[0.03] p-1 ring-1 ring-inset ring-white/[0.06] sm:flex" />
          <div className="ml-auto flex items-center gap-3 text-[12px] text-fg-3">
            {riskOn != null && (
              <MovingBorderChip title="Nifty 50 compared with its 200-day average" color={riskOn ? "#3b82f6" : "#d03b3b"}>
                <span className="relative flex h-2 w-2">
                  <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${riskOn ? "bg-good" : "bg-bad"}`} />
                  <span className={`relative inline-flex h-2 w-2 rounded-full ${riskOn ? "bg-good" : "bg-bad"}`} />
                </span>
                <span>{riskOn ? "Risk-on" : "Risk-off"}</span>
                <span className="hidden text-fg-3 lg:inline">{riskOn ? "· buys allowed" : "· no new buys"}</span>
              </MovingBorderChip>
            )}
            {asOf && <span className="hidden whitespace-nowrap md:inline">Data to {asOf}</span>}
          </div>
        </div>
        <Tabs tab={tab} onTab={onTab} className="mt-2 flex items-center gap-0.5 rounded-full border border-line bg-[#0a0a0a]/75 p-1 backdrop-blur-xl sm:hidden" />
      </div>
    </header>
  );
}
