import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useApi, type RankData } from "./api";
import { TopBar, type Tab } from "./components/TopBar";
import { day } from "./format";
import { BacktestView } from "./views/Backtest";
import { MarketView } from "./views/Market";
import { PortfolioView } from "./views/Portfolio";
import { SignalsView } from "./views/Signals";

const TABS: Tab[] = ["portfolio", "signals", "backtest", "market"];

function initialTab(): Tab {
  const fromHash = window.location.hash.slice(1) as Tab;
  if (TABS.includes(fromHash)) return fromHash;
  try {
    const saved = localStorage.getItem("sa-tab") as Tab | null;
    if (saved && TABS.includes(saved)) return saved;
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
    <div className="min-h-screen">
      <TopBar tab={tab} onTab={setTab} riskOn={riskOn} asOf={asOf} />
      <main className="mx-auto max-w-[1240px] px-4 pb-16 pt-8 sm:px-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, filter: "blur(6px)", y: 6 }}
            animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
            exit={{ opacity: 0, filter: "blur(4px)" }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
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
  );
}
