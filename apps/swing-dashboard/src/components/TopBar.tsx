import { motion } from "framer-motion";

export type Tab = "portfolio" | "signals" | "backtest" | "market";
const TABS: { id: Tab; label: string }[] = [
  { id: "portfolio", label: "Portfolio" },
  { id: "signals", label: "Signals" },
  { id: "backtest", label: "Backtest" },
  { id: "market", label: "Market" },
];

export function TopBar({ tab, onTab, riskOn, asOf }: { tab: Tab; onTab: (t: Tab) => void; riskOn: boolean | null; asOf?: string }) {
  return (
    <header className="sticky top-0 z-20 border-b border-ink-700/70 bg-ink-950/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
            <rect width="32" height="32" rx="8" fill="#182033" />
            <path d="M7 22l6-6 4 3 8-9" fill="none" stroke="#f2b23e" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-[15px] font-semibold tracking-tight">Stock Analyse</span>
        </div>
        <nav aria-label="Sections" className="order-3 -mx-1 flex w-full gap-1 sm:order-none sm:w-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={`relative rounded-lg px-3 py-1.5 text-[14px] font-medium transition-colors ${tab === t.id ? "text-ink-950" : "text-fg-2 hover:text-fg"}`}
            >
              {tab === t.id && (
                <motion.span layoutId="tab-pill" className="absolute inset-0 rounded-lg bg-marigold" transition={{ type: "spring", stiffness: 520, damping: 38 }} />
              )}
              <span className="relative">{t.label}</span>
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-[13px] text-fg-2">
          {riskOn != null && (
            <span className={`chip ${riskOn ? "bg-good/10 text-fg ring-good/30" : "bg-bad/10 text-fg ring-bad/30"}`} title="Nifty 50 vs its 200-day average">
              <span className="relative flex h-2 w-2">
                <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${riskOn ? "bg-good" : "bg-bad"}`} />
                <span className={`relative inline-flex h-2 w-2 rounded-full ${riskOn ? "bg-good" : "bg-bad"}`} />
              </span>
              <span className="sm:hidden">{riskOn ? "Risk-on" : "Risk-off"}</span>
              <span className="hidden sm:inline">{riskOn ? "Risk-on market" : "Risk-off market: no new buys"}</span>
            </span>
          )}
          {asOf && <span className="hidden md:inline">Data to {asOf}</span>}
        </div>
      </div>
    </header>
  );
}
