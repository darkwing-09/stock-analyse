import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { useMemo, useState } from "react";
import { useApi, type Candidate, type RankData } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import { GlowCard } from "../components/GlowCard";
import { Reveal } from "../components/Reveal";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { TextGenerate } from "../components/TextGenerate";
import { day, pct, sectorName, ticker } from "../format";
import { EXPO, knob, pill, stagger } from "../lib/motion";

const COMPONENT_LABELS: Record<string, string> = {
  relative_strength: "Strength vs Nifty",
  trend_quality: "Trend smoothness",
  sector_strength: "Sector strength",
  near_high: "Near 52-week high",
  volume_trend: "Volume pick-up",
  low_volatility: "Calmness",
};

function Bar({ value, delay = 0, className = "" }: { value: number; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <div className={`h-1.5 overflow-hidden rounded-full bg-white/[0.07] ${className}`}>
      <motion.div
        className="h-full origin-left rounded-full bg-accent shadow-[0_0_10px_rgba(59,130,246,0.55)]"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        initial={reduce ? false : { scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 0.8, ease: EXPO, delay }}
      />
    </div>
  );
}

function Breakdown({ c }: { c: Candidate }) {
  return (
    <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
      {Object.entries(c.components).map(([k, v], i) => (
        <div key={k}>
          <div className="flex justify-between text-[13px]"><span className="text-fg-2">{COMPONENT_LABELS[k] ?? k}</span><span className="num">{Math.round(v)}</span></div>
          <Bar value={v} delay={stagger(i, 0.05)} className="mt-1.5" />
        </div>
      ))}
      <p className="text-[13px] leading-relaxed text-fg-3 sm:col-span-2 lg:col-span-3">
        Percentile against the other eligible stocks today. Stop {c.stop.toFixed(2)} sits {(c.entry - c.stop).toFixed(2)} below entry ({Math.round(((c.entry - c.stop) / c.atr) * 10) / 10}× ATR). {c.setup === "breakout" ? "No prior high above: open-sky target at 3R." : "Target capped at the prior high."}
      </p>
    </div>
  );
}

function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer select-none items-center gap-2.5 text-[13px] text-fg-2">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-10 shrink-0 rounded-full ring-1 ring-inset transition-colors duration-300 ${checked ? "bg-accent ring-accent" : "bg-white/[0.06] ring-line-strong"}`}
      >
        <motion.span layout transition={knob} className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-md" style={{ left: checked ? "calc(100% - 22px)" : 2 }} />
      </button>
      {label}
    </label>
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
      <div className="flex items-center justify-end gap-2.5"><Bar value={c.score} className="w-16" delay={0.2} /><span className="num w-7 font-medium">{c.score.toFixed(0)}</span></div>) },
    { key: "setup", label: "Setup", render: (c) => (
      <span className={`chip ${c.setup === "breakout" ? "bg-accent/10 text-accent-pale ring-accent/30" : "text-fg-2 ring-line-strong"}`}>{c.setup}</span>) },
    { key: "entry", label: "Entry", align: "right", sort: (c) => c.entry, render: (c) => <span className="num">{c.entry.toFixed(2)}</span> },
    { key: "stop", label: "Stop", align: "right", sort: (c) => c.stop / c.entry, render: (c) => <span className="num">{c.stop.toFixed(2)} <span className="text-fg-3">{pct(c.stop / c.entry - 1)}</span></span> },
    { key: "target", label: "Target", align: "right", render: (c) => <span className="num">{c.target.toFixed(2)} <span className="text-fg-3">{pct(c.target / c.entry - 1)}</span></span> },
    { key: "rr", label: "R:R", align: "right", sort: (c) => c.reward_risk, render: (c) => <span className="num">{c.reward_risk.toFixed(1)}</span> },
    { key: "plan", label: "In plan", align: "right", render: (c) => (plan.has(c.symbol) ? <Check size={16} className="ml-auto text-accent-soft" aria-label="In suggested portfolio" /> : null) },
  ];

  const chips = [{ id: "all", label: "All sectors" }, ...sectors.map((s) => ({ id: s, label: sectorName(s) }))];

  return (
    <div className="space-y-5">
      <div>
        <TextGenerate text="Swing candidates" className="text-[32px] font-semibold leading-tight" />
        <Reveal delay={0.15}>
          <p className="mt-1.5 text-[15px] text-fg-2">
            {data.candidates.length} of {data.universe_size} Nifty 100 stocks pass every filter with ≥ 2:1 reward-to-risk · data to {day(data.as_of)}
          </p>
        </Reveal>
      </div>

      <Reveal delay={0.1}>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div role="radiogroup" aria-label="Sector" className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {chips.map((c) => {
              const active = sector === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setSector(c.id)}
                  className={`relative shrink-0 rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors duration-200 ${active ? "text-fg" : "text-fg-2 hover:text-fg"}`}
                >
                  {active && <motion.span layoutId="sector-pill" className="absolute inset-0 rounded-full bg-white/[0.09] ring-1 ring-inset ring-white/[0.08]" transition={pill} />}
                  <span className="relative">{c.label}</span>
                </button>
              );
            })}
          </div>
          <Switch checked={planOnly} onChange={setPlanOnly} label="Suggested portfolio only" />
        </div>
      </Reveal>

      <Reveal delay={0.18}>
        <GlowCard className="p-2 sm:p-3">
          {rows.length ? (
            <DataTable
              rows={rows}
              columns={columns}
              rowKey={(c) => c.symbol}
              caption="Ranked swing candidates"
              initialSort={{ key: "score", dir: "desc" }}
              onRowClick={(c) => setOpen(open === c.symbol ? null : c.symbol)}
              expanded={open}
              renderExpanded={(c) => <Breakdown c={c} />}
            />
          ) : (
            <p className="p-4 text-[14px] text-fg-2">No candidates match these filters.</p>
          )}
        </GlowCard>
      </Reveal>
      <Reveal delay={0.24}><p className="text-[13px] text-fg-3">Click a row to see why it scored that way. Research only, not investment advice.</p></Reveal>
    </div>
  );
}
