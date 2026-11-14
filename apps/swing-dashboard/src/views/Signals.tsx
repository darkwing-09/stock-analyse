import { Check } from "lucide-react";
import { useMemo, useState } from "react";
import { useApi, type Candidate, type RankData } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { day, pct, sectorName, ticker } from "../format";

const COMPONENT_LABELS: Record<string, string> = {
  relative_strength: "Strength vs Nifty",
  trend_quality: "Trend smoothness",
  sector_strength: "Sector strength",
  near_high: "Near 52-week high",
  volume_trend: "Volume pick-up",
  low_volatility: "Calmness",
};

function Breakdown({ c }: { c: Candidate }) {
  return (
    <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.entries(c.components).map(([k, v]) => (
        <div key={k}>
          <div className="flex justify-between text-[13px]"><span className="text-fg-2">{COMPONENT_LABELS[k] ?? k}</span><span className="num">{Math.round(v)}</span></div>
          <div className="mt-1.5 h-1.5 rounded-full bg-ink-700"><div className="h-full rounded-full bg-marigold-deep" style={{ width: `${v}%` }} /></div>
        </div>
      ))}
      <p className="text-[13px] text-fg-3 sm:col-span-2 lg:col-span-3">
        Percentile vs other eligible stocks today. Stop {c.stop.toFixed(2)} is {(c.entry - c.stop).toFixed(2)} below entry ({(Math.round((c.entry - c.stop) / c.atr * 10) / 10)}× ATR). {c.setup === "breakout" ? "No prior high above: open-sky target at 3R." : "Target capped at the prior high."}
      </p>
    </div>
  );
}

export function SignalsView() {
  const res = useApi<RankData>("/api/signals");
  const [sector, setSector] = useState("all");
  const [planOnly, setPlanOnly] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const data = res.state === "ready" ? res.data : null;
  const plan = useMemo(() => new Set(data?.portfolio.map((p) => p.symbol)), [data]);
  const sectors = useMemo(() => [...new Set(data?.candidates.map((c) => c.sector))].sort(), [data]);
  const rows = useMemo(
    () => (data?.candidates ?? []).filter((c) => (sector === "all" || c.sector === sector) && (!planOnly || plan.has(c.symbol))),
    [data, sector, planOnly, plan],
  );

  if (res.state === "loading") return <Skeleton rows={8} />;
  if (res.state === "error") return <ErrorState message={res.message} />;
  if (res.state === "empty" || !data)
    return <EmptyState title="No ranking yet" command="python swing.py rank">Rank the Nifty 100 to see today's swing candidates.</EmptyState>;

  const columns: Column<Candidate>[] = [
    { key: "rank", label: "#", render: (c) => <span className="num text-fg-3">{data.candidates.indexOf(c) + 1}</span> },
    { key: "stock", label: "Stock", sort: (c) => c.symbol, render: (c) => (
      <div><div className="font-medium">{ticker(c.symbol)}</div><div className="max-w-[220px] truncate text-[12px] text-fg-3">{c.name}</div></div>) },
    { key: "sector", label: "Sector", sort: (c) => c.sector, render: (c) => <span className="text-fg-2">{sectorName(c.sector)}</span> },
    { key: "score", label: "Score", align: "right", sort: (c) => c.score, render: (c) => (
      <div className="flex items-center justify-end gap-2"><div className="h-1.5 w-16 rounded-full bg-ink-700"><div className="h-full rounded-full bg-marigold" style={{ width: `${c.score}%` }} /></div><span className="num w-8">{c.score.toFixed(0)}</span></div>) },
    { key: "setup", label: "Setup", render: (c) => <span className={`chip ${c.setup === "breakout" ? "text-marigold-soft ring-marigold/30" : "text-fg-2 ring-ink-600"}`}>{c.setup}</span> },
    { key: "entry", label: "Entry", align: "right", sort: (c) => c.entry, render: (c) => <span className="num">{c.entry.toFixed(2)}</span> },
    { key: "stop", label: "Stop", align: "right", sort: (c) => c.stop / c.entry, render: (c) => <span className="num">{c.stop.toFixed(2)} <span className="text-fg-3">{pct(c.stop / c.entry - 1)}</span></span> },
    { key: "target", label: "Target", align: "right", render: (c) => <span className="num">{c.target.toFixed(2)} <span className="text-fg-3">{pct(c.target / c.entry - 1)}</span></span> },
    { key: "rr", label: "R:R", align: "right", sort: (c) => c.reward_risk, render: (c) => <span className="num">{c.reward_risk.toFixed(1)}</span> },
    { key: "plan", label: "In plan", align: "right", render: (c) => (plan.has(c.symbol) ? <Check size={16} className="ml-auto text-marigold" aria-label="In suggested portfolio" /> : null) },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-semibold">Swing candidates</h1>
          <p className="mt-1 text-fg-2">{data.candidates.length} of {data.universe_size} Nifty 100 stocks pass every filter with ≥ 2:1 reward-to-risk · data to {day(data.as_of)}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-[13px] text-fg-2">
            Sector
            <select value={sector} onChange={(e) => setSector(e.target.value)} className="rounded-lg bg-ink-800 px-2.5 py-1.5 text-fg ring-1 ring-ink-600">
              <option value="all">All</option>
              {sectors.map((s) => <option key={s} value={s}>{sectorName(s)}</option>)}
            </select>
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-[13px] text-fg-2">
            <input type="checkbox" checked={planOnly} onChange={(e) => setPlanOnly(e.target.checked)} className="h-4 w-4 accent-[#f2b23e]" />
            Suggested only
          </label>
        </div>
      </div>
      <section className="panel p-3 sm:p-4">
        {rows.length ? (
          <DataTable rows={rows} columns={columns} rowKey={(c) => c.symbol} caption="Ranked swing candidates" initialSort={{ key: "score", dir: "desc" }}
            onRowClick={(c) => setOpen(open === c.symbol ? null : c.symbol)} expanded={open} renderExpanded={(c) => <Breakdown c={c} />} />
        ) : (
          <p className="p-4 text-fg-2">No candidates match these filters.</p>
        )}
      </section>
      <p className="text-[13px] text-fg-3">Click a row to see why it scored that way. Research only, not investment advice.</p>
    </div>
  );
}
