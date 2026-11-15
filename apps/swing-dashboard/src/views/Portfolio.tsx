import { motion, useReducedMotion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useCallback, type ReactNode } from "react";
import { useApi, type Order, type PortfolioData, type Position, type Trade } from "../api";
import { CountUp } from "../components/CountUp";
import { DataTable, type Column } from "../components/DataTable";
import { EquityChart } from "../components/EquityChart";
import { GlowCard } from "../components/GlowCard";
import { Reveal } from "../components/Reveal";
import { Command, EmptyState, ErrorState, Skeleton } from "../components/States";
import { TextGenerate } from "../components/TextGenerate";
import { day, inr, pct, sectorName, ticker } from "../format";
import { EXPO, stagger } from "../lib/motion";

export function Delta({ value, money, className = "" }: { value: number; money?: boolean; className?: string }) {
  const up = value > 0, down = value < 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`num inline-flex items-center gap-1 ${className}`}>
      {(up || down) && <Icon size={14} className={up ? "text-good" : "text-bad"} aria-label={up ? "gain" : "loss"} />}
      {money ? `${up ? "+" : ""}${inr(value)}` : pct(value)}
    </span>
  );
}

function Stat({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div title={hint}>
      <div className="label">{label}</div>
      <div className="num mt-1 text-[15px] font-medium">{children}</div>
    </div>
  );
}

const positionCols: Column<Position>[] = [
  { key: "symbol", label: "Stock", sort: (p) => p.symbol, render: (p) => (
    <div><div className="font-medium">{ticker(p.symbol)}</div><div className="text-[12px] text-fg-3">{sectorName(p.sector)}</div></div>) },
  { key: "qty", label: "Qty", align: "right", sort: (p) => p.qty, render: (p) => <span className="num">{p.qty}</span> },
  { key: "entry", label: "Entry", align: "right", render: (p) => <span className="num">{p.entry_price.toFixed(2)}</span> },
  { key: "last", label: "Last", align: "right", render: (p) => <span className="num">{p.last_price.toFixed(2)}</span> },
  { key: "stop", label: "Trailing stop", align: "right", sort: (p) => p.last_price / p.stop - 1, render: (p) => (
    <span className="num">{p.stop.toFixed(2)} <span className="text-fg-3">({pct(p.stop / p.last_price - 1)})</span></span>) },
  { key: "pnl", label: "P&L", align: "right", sort: (p) => p.unrealized_pnl, render: (p) => (
    <div><Delta value={p.unrealized_pnl} money /><div className="text-[12px] text-fg-3"><Delta value={p.unrealized_pct} /></div></div>) },
  { key: "days", label: "Days", align: "right", sort: (p) => p.bars_held, render: (p) => <span className="num">{p.bars_held}</span> },
];

const tradeCols: Column<Trade>[] = [
  { key: "symbol", label: "Stock", sort: (t) => t.symbol, render: (t) => <span className="font-medium">{ticker(t.symbol)}</span> },
  { key: "in", label: "Bought", sort: (t) => t.entry_date, render: (t) => <span className="num text-fg-2">{day(t.entry_date)}</span> },
  { key: "out", label: "Sold", sort: (t) => t.exit_date, render: (t) => <span className="num text-fg-2">{day(t.exit_date)}</span> },
  { key: "why", label: "Exit", render: (t) => <span className="text-fg-2">{t.exit_reason}</span> },
  { key: "r", label: "R", align: "right", sort: (t) => t.r_multiple, render: (t) => <span className="num">{t.r_multiple >= 0 ? "+" : ""}{t.r_multiple.toFixed(2)}R</span> },
  { key: "pnl", label: "Net P&L", align: "right", sort: (t) => t.net_pnl, render: (t) => <Delta value={t.net_pnl} money /> },
];

function NextSession({ orders, exits }: { orders: Order[]; exits: Record<string, string> }) {
  const reduce = useReducedMotion();
  const exitList = Object.entries(exits);
  const items = [
    ...orders.map((o) => ({ key: `b-${o.symbol}`, side: "buy" as const, symbol: o.symbol, qty: o.qty as number | null, meta: `stop ${o.stop.toFixed(2)} · target ${o.target.toFixed(2)}` })),
    ...exitList.map(([s, why]) => ({ key: `s-${s}`, side: "sell" as const, symbol: s, qty: null as number | null, meta: `${why} exit` })),
  ];
  return (
    <GlowCard className="p-5" aria-labelledby="next-h">
      <div className="flex items-baseline justify-between">
        <h2 id="next-h" className="text-[15px] font-semibold">Next session</h2>
        <span className="text-[12px] text-fg-3">{items.length} order{items.length === 1 ? "" : "s"}</span>
      </div>
      <p className="mt-1 text-[13px] text-fg-3">Simulated orders that fill at tomorrow's open.</p>
      {items.length === 0 && <p className="mt-5 text-[14px] text-fg-2">Nothing queued. The strategy is waiting for a setup.</p>}
      <ul className="mt-4 space-y-1.5">
        {items.map((it, i) => (
          <motion.li
            key={it.key}
            initial={reduce ? false : { opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, ease: EXPO, delay: 0.2 + stagger(i, 0.05) }}
            className="flex items-center justify-between gap-3 rounded-xl px-3 py-2 ring-1 ring-inset ring-white/[0.05] transition-colors hover:bg-white/[0.03]"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 text-[14px] font-medium">
                {it.side === "buy" ? <ArrowUpRight size={15} className="text-good" aria-hidden /> : <ArrowDownRight size={15} className="text-bad" aria-hidden />}
                {it.side === "buy" ? "Buy" : "Sell"} {ticker(it.symbol)}
              </div>
              <div className="num truncate text-[12px] text-fg-3">{it.meta}</div>
            </div>
            {it.qty != null && <span className="num shrink-0 text-[13px] text-fg-2">{it.qty} sh</span>}
          </motion.li>
        ))}
      </ul>
    </GlowCard>
  );
}

export function PortfolioView() {
  const res = useApi<PortfolioData>("/api/portfolio");
  const fmt = useCallback((v: number) => inr(v), []);
  if (res.state === "loading") return <Skeleton rows={6} />;
  if (res.state === "error") return <ErrorState message={res.message} />;
  if (res.state === "empty")
    return (
      <EmptyState title="The paper portfolio hasn't started" command="python swing.py paper run">
        Run this after the 15:30 close. It ranks the Nifty 100, queues simulated buys for the next open and tracks them like real trades.
      </EmptyState>
    );
  const d = res.data;
  const curve = d.equity_curve;
  const bench = curve.length && curve[curve.length - 1].benchmark != null ? curve[curve.length - 1].benchmark! / d.capital - 1 : null;
  const openRisk = d.positions.reduce((s, p) => s + Math.max(0, p.qty * (p.last_price - p.stop)), 0);

  return (
    <div className="space-y-5">
      <div>
        <TextGenerate text="Paper portfolio" className="text-[32px] font-semibold leading-tight" />
        <Reveal delay={0.15}><p className="mt-1.5 text-[15px] text-fg-2">Simulated {inr(d.capital)} · started {day(d.started_on)} · last session {day(d.last_session)}</p></Reveal>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-12">
        <div className="space-y-5 lg:col-span-8">
        <Reveal delay={0.08}>
          <GlowCard className="p-5 sm:p-6" aria-label="Equity">
            <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
              <div>
                <div className="label">Equity</div>
                <div className="num mt-1 text-[36px] font-semibold leading-none tracking-tight sm:text-[40px]"><CountUp value={d.equity} format={fmt} /></div>
              </div>
              <div className="flex items-center gap-2 pb-1">
                <Delta value={d.total_return} className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[13px] font-medium ring-1 ring-inset ring-white/[0.06]" />
                {bench != null && <span className="num text-[13px] text-fg-3">Nifty {pct(bench)}</span>}
              </div>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 border-t border-line pt-4 sm:grid-cols-4">
              {bench != null && <Stat label="Nifty 50, same period"><Delta value={bench} /></Stat>}
              <Stat label="Max drawdown">{pct(d.max_drawdown)}</Stat>
              <Stat label="Cash">{inr(d.cash)}</Stat>
              <Stat label="Open risk" hint="Loss if every position hit its stop">{inr(openRisk)}</Stat>
            </div>
            <div className="mt-5">
              {curve.length >= 2 ? (
                <EquityChart data={curve} />
              ) : (
                <div className="flex flex-col gap-3 rounded-xl bg-ground/60 p-4 text-[14px] text-fg-2 ring-1 ring-inset ring-line sm:flex-row sm:items-center sm:justify-between">
                  <span>The equity curve appears after the second session. Run this after each close:</span>
                  <Command>python swing.py paper run</Command>
                </div>
              )}
            </div>
          </GlowCard>
        </Reveal>
        <Reveal delay={0.2}>
          <GlowCard className="p-5" aria-labelledby="pos-h">
            <h2 id="pos-h" className="mb-3 text-[15px] font-semibold">Open positions <span className="font-normal text-fg-3">· {d.positions.length}</span></h2>
            {d.positions.length ? (
              <DataTable rows={d.positions} columns={positionCols} rowKey={(p) => p.symbol} caption="Open positions" initialSort={{ key: "pnl", dir: "desc" }} />
            ) : (
              <p className="text-[14px] text-fg-2">No open positions yet. Queued buys fill at the next session's open.</p>
            )}
          </GlowCard>
        </Reveal>
        </div>
        <Reveal delay={0.14} className="lg:col-span-4">
          <NextSession orders={d.pending_orders} exits={d.pending_exits} />
        </Reveal>
      </div>

      <Reveal delay={0.28}>
        <GlowCard className="p-5" aria-labelledby="tr-h">
          <h2 id="tr-h" className="mb-3 text-[15px] font-semibold">
            Closed trades <span className="font-normal text-fg-3">· {d.trades.length}{d.trades.length ? `, win rate ${Math.round(d.win_rate * 100)}%` : ""}</span>
          </h2>
          {d.trades.length ? (
            <DataTable rows={[...d.trades].reverse()} columns={tradeCols} rowKey={(t) => `${t.symbol}-${t.entry_date}`} caption="Closed trades" />
          ) : (
            <p className="text-[14px] text-fg-2">No closed trades yet.</p>
          )}
        </GlowCard>
      </Reveal>
    </div>
  );
}
