import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { pct } from "../format";

interface Row { year: string; strategy: number; benchmark: number | null }

function Tip({ active, payload, label }: { active?: boolean; payload?: { dataKey: string; value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl bg-ink-950/95 px-3 py-2 text-[13px] shadow-lift ring-1 ring-ink-600">
      <div className="mb-1 text-fg-3">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex gap-4">
          <span>{p.dataKey === "strategy" ? "Strategy" : "Nifty 50"}</span>
          <span className="num ml-auto">{pct(p.value)}</span>
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
          <CartesianGrid stroke="#232c42" vertical={false} />
          <XAxis dataKey="year" stroke="#7f8aa1" tickLine={false} axisLine={false} fontSize={12} />
          <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} stroke="#7f8aa1" tickLine={false} axisLine={false} fontSize={12} width={44} />
          <ReferenceLine y={0} stroke="#323d57" />
          <Tooltip content={<Tip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar dataKey="strategy" fill="#c98500" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Bar dataKey="benchmark" fill="#3987e5" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
