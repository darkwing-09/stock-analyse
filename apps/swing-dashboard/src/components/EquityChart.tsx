import { motion, useReducedMotion } from "framer-motion";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurvePoint } from "../api";
import { compactInr, day, inr, shortDay } from "../format";

export const STRATEGY = "#3b82f6";
export const NIFTY = "#d95926";

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: CurvePoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-xl bg-[#0c0c0c]/95 px-3 py-2 text-[13px] shadow-lift ring-1 ring-inset ring-line-strong backdrop-blur-xl">
      <div className="mb-1.5 text-fg-3">{day(p.date)}</div>
      <div className="flex items-center gap-2">
        <span className="h-0.5 w-3 rounded" style={{ background: STRATEGY }} /> Strategy
        <span className="num ml-auto pl-5 font-medium">{inr(p.equity)}</span>
      </div>
      {p.benchmark != null && (
        <div className="mt-0.5 flex items-center gap-2">
          <span className="h-0.5 w-3 rounded" style={{ background: NIFTY }} /> Nifty 50
          <span className="num ml-auto pl-5 font-medium">{inr(p.benchmark)}</span>
        </div>
      )}
    </div>
  );
}

export function EquityChart({ data, height = 300 }: { data: CurvePoint[]; height?: number }) {
  const reduce = useReducedMotion();
  const hasBench = data.some((d) => d.benchmark != null);
  const ticks = data.length > 6 ? data.filter((_, i) => i % Math.ceil(data.length / 6) === 0).map((d) => d.date) : undefined;
  return (
    <div>
      <div className="mb-3 flex items-center gap-5 text-[12px] text-fg-2" aria-label="Legend">
        <span className="flex items-center gap-2"><span className="h-0.5 w-4 rounded" style={{ background: STRATEGY }} />Strategy</span>
        {hasBench && <span className="flex items-center gap-2"><span className="w-4 border-t border-dashed" style={{ borderColor: NIFTY }} />Nifty 50, same start</span>}
      </div>
      <motion.div
        initial={reduce ? false : { clipPath: "inset(0 100% 0 0)" }}
        animate={{ clipPath: "inset(0 0% 0 0)" }}
        transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        style={{ height }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={STRATEGY} stopOpacity={0.26} />
                <stop offset="100%" stopColor={STRATEGY} stopOpacity={0} />
              </linearGradient>
              <filter id="eqGlow" x="-10%" y="-40%" width="120%" height="180%">
                <feGaussianBlur stdDeviation="3" result="b" />
                <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={shortDay} stroke="#8b8b8b" tickLine={false} axisLine={false} fontSize={11} minTickGap={24} />
            <YAxis tickFormatter={compactInr} stroke="#8b8b8b" tickLine={false} axisLine={false} fontSize={11} width={56} domain={["auto", "auto"]} />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(255,255,255,0.25)", strokeWidth: 1 }} />
            <Area type="monotone" dataKey="equity" stroke="none" fill="url(#eqFill)" isAnimationActive={false} />
            {hasBench && <Line type="monotone" dataKey="benchmark" stroke={NIFTY} strokeWidth={1.5} strokeDasharray="4 4" dot={false} isAnimationActive={false} activeDot={{ r: 4, stroke: "#0f0f0f", strokeWidth: 2 }} />}
            <Line className="eq-strategy" type="monotone" dataKey="equity" stroke={STRATEGY} strokeWidth={2} dot={false} isAnimationActive={false} activeDot={{ r: 5, stroke: "#0f0f0f", strokeWidth: 2 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
}
