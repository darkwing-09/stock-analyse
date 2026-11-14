import { Info } from "lucide-react";
import { useApi, type BacktestData, type Trade } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import { EquityChart } from "../components/EquityChart";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { YearlyBars } from "../components/YearlyBars";
import { day, inr, pct, ticker } from "../format";

// Reference palette slots 1-3 (validated all-pairs on the dark surface); anything else folds to neutral.
const EXIT_COLORS: Record<string, string> = { stop: "#d95926", trend: "#3987e5", time: "#199e70" };
const EXIT_LABELS: Record<string, string> = { stop: "Stop hit", trend: "Fell below 50-day avg", time: "Time limit", target: "Target hit" };

function Versus({ label, mine, theirs }: { label: string; mine: number; theirs: number }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="num text-[22px] font-semibold">{pct(mine)}</span>
        <span className="num text-[13px] text-fg-3">Nifty {pct(theirs)}</span>
      </div>
    </div>
  );
}

const tradeCols: Column<Trade>[] = [
  { key: "symbol", label: "Stock", sort: (t) => t.symbol, render: (t) => <span className="font-medium">{ticker(t.symbol)}</span> },
  { key: "in", label: "Bought", sort: (t) => t.entry_date, render: (t) => <span className="num text-fg-2">{day(t.entry_date)}</span> },
  { key: "days", label: "Days", align: "right", sort: (t) => t.bars_held, render: (t) => <span className="num">{t.bars_held}</span> },
  { key: "why", label: "Exit", render: (t) => <span className="text-fg-2">{EXIT_LABELS[t.exit_reason] ?? t.exit_reason}</span> },
  { key: "r", label: "R", align: "right", sort: (t) => t.r_multiple, render: (t) => <span className="num">{t.r_multiple >= 0 ? "+" : ""}{t.r_multiple.toFixed(2)}R</span> },
  { key: "costs", label: "Costs", align: "right", sort: (t) => t.costs, render: (t) => <span className="num text-fg-2">{inr(t.costs)}</span> },
  { key: "pnl", label: "Net P&L", align: "right", sort: (t) => t.net_pnl, render: (t) => <span className="num">{t.net_pnl >= 0 ? "+" : ""}{inr(t.net_pnl)}</span> },
];

export function BacktestView() {
  const res = useApi<BacktestData>("/api/backtest");
  if (res.state === "loading") return <Skeleton rows={6} />;
  if (res.state === "error") return <ErrorState message={res.message} />;
  if (res.state === "empty")
    return <EmptyState title="No backtest yet" command="python swing.py backtest --years 10">Replay the strategy over past years with every Indian charge and tax included.</EmptyState>;

  const { summary: s, equity, trades } = res.data;
  const yearly = Object.entries(s.yearly).map(([year, r]) => ({ year, strategy: r.strategy, benchmark: r.benchmark }));
  const exits = Object.entries(s.exit_reasons);
  const totalExits = exits.reduce((a, [, n]) => a + n, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold">Backtest</h1>
        <p className="mt-1 text-fg-2">{day(s.start)} to {day(s.end)} · {inr(s.initial_capital)} start · Fyers delivery charges, 0.10% slippage, 20% short-term gains tax</p>
      </div>
      <section className="panel p-5 sm:p-6" aria-label="Results">
        <div className="mb-6 grid grid-cols-2 gap-x-8 gap-y-5 md:grid-cols-4">
          <Versus label="Yearly growth (CAGR)" mine={s.cagr} theirs={s.benchmark_cagr} />
          <Versus label="Worst drawdown" mine={s.max_drawdown} theirs={s.benchmark_max_drawdown} />
          <div><div className="label">After tax</div><div className="num mt-1 text-[22px] font-semibold">{inr(s.post_tax_final_equity)}</div></div>
          <div><div className="label">Trades · win rate · profit factor</div><div className="num mt-1 text-[22px] font-semibold">{s.trades} · {Math.round(s.win_rate * 100)}% · {s.profit_factor.toFixed(2)}</div></div>
        </div>
        <EquityChart data={equity} height={320} />
      </section>
      <div className="grid gap-6 lg:grid-cols-5">
        <section className="panel p-5 lg:col-span-3" aria-labelledby="yr-h">
          <h2 id="yr-h" className="text-[15px] font-semibold">Year by year</h2>
          <div className="mb-3 mt-1 flex gap-5 text-[13px] text-fg-2">
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm bg-marigold-deep" />Strategy</span>
            <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm bg-nifty" />Nifty 50</span>
          </div>
          <YearlyBars rows={yearly} />
        </section>
        <section className="panel p-5 lg:col-span-2" aria-labelledby="ex-h">
          <h2 id="ex-h" className="text-[15px] font-semibold">How trades ended</h2>
          <div className="mt-4 flex h-3 gap-[2px] overflow-hidden rounded-full" role="img" aria-label="Exit reasons share">
            {exits.map(([k, n]) => <div key={k} style={{ width: `${(n / totalExits) * 100}%`, background: EXIT_COLORS[k] ?? "#7f8aa1" }} />)}
          </div>
          <ul className="mt-4 space-y-2 text-[14px]">
            {exits.map(([k, n]) => (
              <li key={k} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: EXIT_COLORS[k] ?? "#7f8aa1" }} />
                <span className="text-fg-2">{EXIT_LABELS[k] ?? k}</span>
                <span className="num ml-auto">{n} <span className="text-fg-3">({Math.round((n / totalExits) * 100)}%)</span></span>
              </li>
            ))}
          </ul>
          <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-ink-700 pt-4 text-[14px]">
            <div><dt className="label">Average win</dt><dd className="num mt-0.5">{inr(s.avg_win)}</dd></div>
            <div><dt className="label">Average loss</dt><dd className="num mt-0.5">{inr(s.avg_loss)}</dd></div>
            <div><dt className="label">Charges paid</dt><dd className="num mt-0.5">{inr(s.total_costs)}</dd></div>
            <div><dt className="label">Sharpe (vs 6.5%)</dt><dd className="num mt-0.5">{s.sharpe.toFixed(2)}</dd></div>
          </dl>
        </section>
      </div>
      {s.in_sample && s.out_of_sample && (
        <section className="panel flex gap-3 p-5" aria-label="Robustness">
          <Info size={18} className="mt-0.5 shrink-0 text-marigold" aria-hidden />
          <div className="text-[14px] leading-relaxed text-fg-2">
            <p className="text-fg">First 70% of the period: CAGR {pct(s.in_sample.cagr)} vs Nifty {pct(s.in_sample.benchmark_cagr)}. Last 30%: CAGR {pct(s.out_of_sample.cagr)} vs Nifty {pct(s.out_of_sample.benchmark_cagr)}.</p>
            <p className="mt-1">Today's Nifty 100 members are used for the whole period (survivorship bias), so these results are likely optimistic. Past results do not predict future returns.</p>
          </div>
        </section>
      )}
      <section className="panel p-5" aria-labelledby="bt-h">
        <h2 id="bt-h" className="mb-3 text-[15px] font-semibold">Most recent 150 trades</h2>
        <div className="max-h-[520px] overflow-y-auto">
          <DataTable rows={trades.slice(-150).reverse()} columns={tradeCols} rowKey={(t) => `${t.symbol}-${t.entry_date}`} caption="Backtest trades" />
        </div>
      </section>
    </div>
  );
}
