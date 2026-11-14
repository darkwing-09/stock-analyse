import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useCallback } from "react";
import { useApi, type Order, type PortfolioData, type Position, type Trade } from "../api";
import { CountUp } from "../components/CountUp";
import { DataTable, type Column } from "../components/DataTable";
import { EquityChart } from "../components/EquityChart";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { day, inr, pct, sectorName, ticker } from "../format";

function Delta({ value, money }: { value: number; money?: boolean }) {
  const up = value > 0, down = value < 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className="num inline-flex items-center gap-1">
      {(up || down) && <Icon size={14} className={up ? "text-good" : "text-bad"} aria-label={up ? "gain" : "loss"} />}
      {money ? `${up ? "+" : ""}${inr(value)}` : pct(value)}
    </span>
  );
}

function Stat({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="min-w-[120px]" title={hint}>
      <div className="label">{label}</div>
      <div className="mt-1 text-[17px] font-medium">{children}</div>
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
  const exitList = Object.entries(exits);
  return (
    <section className="panel p-5" aria-labelledby="next-h">
      <h2 id="next-h" className="text-[15px] font-semibold">Next session</h2>
      <p className="mt-1 text-[13px] text-fg-3">Simulated orders that fill at tomorrow's open.</p>
      {orders.length === 0 && exitList.length === 0 && <p className="mt-4 text-fg-2">Nothing queued. The strategy is waiting for a setup.</p>}
      <ul className="mt-4 space-y-2">
        {orders.map((o) => (
          <li key={o.symbol} className="flex items-center justify-between rounded-xl bg-ink-900/70 px-3 py-2.5 ring-1 ring-ink-700/70">
            <div>
              <div className="flex items-center gap-1.5 font-medium"><ArrowUpRight size={15} className="text-good" aria-hidden />Buy {ticker(o.symbol)}</div>
              <div className="num text-[12px] text-fg-3">stop {o.stop.toFixed(2)} · target {o.target.toFixed(2)}</div>
            </div>
            <span className="num text-fg-2">{o.qty} sh</span>
          </li>
        ))}
        {exitList.map(([s, why]) => (
          <li key={s} className="flex items-center justify-between rounded-xl bg-ink-900/70 px-3 py-2.5 ring-1 ring-ink-700/70">
            <div className="flex items-center gap-1.5 font-medium"><ArrowDownRight size={15} className="text-bad" aria-hidden />Sell {ticker(s)}</div>
            <span className="text-[13px] text-fg-3">{why} exit</span>
          </li>
        ))}
      </ul>
    </section>
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
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold">Paper portfolio</h1>
        <p className="mt-1 text-fg-2">Simulated {inr(d.capital)} · started {day(d.started_on)} · last session {day(d.last_session)}</p>
      </div>
      <section className="panel p-5 sm:p-6" aria-label="Equity">
        <div className="mb-5 flex flex-wrap gap-x-10 gap-y-4">
          <Stat label="Equity"><span className="num text-[26px] font-semibold"><CountUp value={d.equity} format={fmt} /></span></Stat>
          <Stat label="Return"><Delta value={d.total_return} /></Stat>
          {bench != null && <Stat label="Nifty 50, same period"><Delta value={bench} /></Stat>}
          <Stat label="Max drawdown"><span className="num">{pct(d.max_drawdown)}</span></Stat>
          <Stat label="Cash"><span className="num">{inr(d.cash)}</span></Stat>
          <Stat label="Open risk" hint="Loss if every position hit its stop"><span className="num">{inr(openRisk)}</span></Stat>
        </div>
        {curve.length >= 2 ? (
          <EquityChart data={curve} />
        ) : (
          <p className="rounded-xl bg-ink-900/70 p-4 text-fg-2 ring-1 ring-ink-700/70">
            The equity curve appears after the second session. Run <code className="num text-marigold-soft">python swing.py paper run</code> after each close.
          </p>
        )}
      </section>
      <div className="grid items-start gap-6 lg:grid-cols-3">
        <section className="panel p-5 lg:col-span-2" aria-labelledby="pos-h">
          <h2 id="pos-h" className="mb-3 text-[15px] font-semibold">Open positions <span className="text-fg-3">({d.positions.length})</span></h2>
          {d.positions.length ? (
            <DataTable rows={d.positions} columns={positionCols} rowKey={(p) => p.symbol} caption="Open positions" initialSort={{ key: "pnl", dir: "desc" }} />
          ) : (
            <p className="text-fg-2">No open positions yet. Queued buys fill at the next session's open.</p>
          )}
        </section>
        <NextSession orders={d.pending_orders} exits={d.pending_exits} />
      </div>
      <section className="panel p-5" aria-labelledby="tr-h">
        <h2 id="tr-h" className="mb-3 text-[15px] font-semibold">Closed trades <span className="text-fg-3">({d.trades.length}, win rate {Math.round(d.win_rate * 100)}%)</span></h2>
        {d.trades.length ? (
          <DataTable rows={[...d.trades].reverse()} columns={tradeCols} rowKey={(t) => `${t.symbol}-${t.entry_date}`} caption="Closed trades" />
        ) : (
          <p className="text-fg-2">No closed trades yet.</p>
        )}
      </section>
    </div>
  );
}
