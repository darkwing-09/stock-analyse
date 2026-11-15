import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useApi, type RankData } from "./api";
import { Nav, TABS, type Tab } from "./components/Nav";
import { Spotlight } from "./components/Spotlight";
import { day } from "./format";
import { EXPO } from "./lib/motion";
import { BacktestView } from "./views/Backtest";
import { MarketView } from "./views/Market";
import { PortfolioView } from "./views/Portfolio";
import { SignalsView } from "./views/Signals";

const IDS = TABS.map((t) => t.id);

function initialTab(): Tab {
  const fromHash = window.location.hash.slice(1) as Tab;
  if (IDS.includes(fromHash)) return fromHash;
  try {
    const saved = localStorage.getItem("sa-tab") as Tab | null;
    if (saved && IDS.includes(saved)) return saved;
  } catch {
    /* storage unavailable: fall back to the default tab */
  }
  return "portfolio";
}

export default function App() {
  const [tab, setTab] = useState<Tab>(initialTab);
  const rank = useApi<RankData>("/api/signals");

  useEffect(() => {
    window.history.replaceState(null, "", `#${tab}`);
    try {
      localStorage.setItem("sa-tab", tab);
    } catch {
      /* ignore */
    }
  }, [tab]);

  const riskOn = rank.state === "ready" ? rank.data.risk_on : null;
  const asOf = rank.state === "ready" ? day(rank.data.as_of) : undefined;

  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
        <div className="dotgrid absolute inset-x-0 top-0 h-[560px]" />
        <Spotlight />
      </div>
      <div className="relative z-10">
        <Nav tab={tab} onTab={setTab} riskOn={riskOn} asOf={asOf} />
        <main className="mx-auto max-w-[1240px] px-4 pb-16 pt-10 sm:px-6 sm:pt-12">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -4, filter: "blur(4px)" }}
              transition={{ duration: 0.22, ease: EXPO }}
            >
              {tab === "portfolio" && <PortfolioView />}
              {tab === "signals" && <SignalsView />}
              {tab === "backtest" && <BacktestView />}
              {tab === "market" && <MarketView />}
            </motion.div>
          </AnimatePresence>
        </main>
        <footer className="mx-auto max-w-[1240px] px-4 pb-10 text-[12px] text-fg-3 sm:px-6">
          Research and paper trading only. Not investment advice. Live orders stay off unless you enable them.
        </footer>
      </div>
    </div>
  );
}
