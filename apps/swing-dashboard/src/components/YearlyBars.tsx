import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { pct } from "../format";
import { NIFTY, STRATEGY } from "./EquityChart";

interface Row { year: string; strategy: number; benchmark: number | null }

function Tip({ active, payload, label }: { active?: boolean; payload?: { dataKey: string; value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl bg-[#0c0c0c]/95 px-3 py-2 text-[13px] shadow-lift ring-1 ring-inset ring-line-strong backdrop-blur-xl">
      <div className="mb-1.5 text-fg-3">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-sm" style={{ background: p.dataKey === "strategy" ? STRATEGY : NIFTY }} />
          <span>{p.dataKey === "strategy" ? "Strategy" : "Nifty 50"}</span>
          <span className="num ml-auto pl-5 font-medium">{pct(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function YearlyBars({ rows }: { rows: Row[] }) {
  return (
    <div style={{ height: 240 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} barGap={2} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="year" stroke="#8b8b8b" tickLine={false} axisLine={false} fontSize={11} />
          <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} stroke="#8b8b8b" tickLine={false} axisLine={false} fontSize={11} width={44} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.18)" />
          <Tooltip content={<Tip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="strategy" fill={STRATEGY} maxBarSize={22} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="benchmark" fill={NIFTY} maxBarSize={22} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
