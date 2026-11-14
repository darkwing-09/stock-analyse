import { motion, useReducedMotion } from "framer-motion";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurvePoint } from "../api";
import { day, inr, shortDay } from "../format";

const STRATEGY = "#c98500";
const NIFTY = "#3987e5";

const compact = (v: number) => (v >= 1e7 ? `₹${(v / 1e7).toFixed(1)}Cr` : `₹${(v / 1e5).toFixed(1)}L`);

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: CurvePoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-xl bg-ink-950/95 px-3 py-2 text-[13px] shadow-lift ring-1 ring-ink-600">
      <div className="mb-1 text-fg-3">{day(p.date)}</div>
      <div className="flex items-center gap-2">
        <span className="h-0.5 w-3 rounded" style={{ background: STRATEGY }} /> Strategy
        <span className="num ml-auto pl-4">{inr(p.equity)}</span>
      </div>
      {p.benchmark != null && (
        <div className="flex items-center gap-2">
          <span className="h-0.5 w-3 rounded" style={{ background: NIFTY }} /> Nifty 50
          <span className="num ml-auto pl-4">{inr(p.benchmark)}</span>
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
      <div className="mb-3 flex items-center gap-5 text-[13px] text-fg-2" aria-label="Legend">
        <span className="flex items-center gap-2"><span className="h-0.5 w-4 rounded" style={{ background: STRATEGY }} />Strategy</span>
        {hasBench && <span className="flex items-center gap-2"><span className="h-0.5 w-4 rounded" style={{ background: NIFTY }} />Nifty 50 (same start)</span>}
      </div>
      <motion.div
        initial={reduce ? false : { clipPath: "inset(0 100% 0 0)" }}
        animate={{ clipPath: "inset(0 0% 0 0)" }}
        transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        style={{ height }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={STRATEGY} stopOpacity={0.22} />
                <stop offset="100%" stopColor={STRATEGY} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#232c42" vertical={false} />
            <XAxis dataKey="date" ticks={ticks} tickFormatter={shortDay} stroke="#7f8aa1" tickLine={false} axisLine={false} fontSize={12} minTickGap={24} />
            <YAxis tickFormatter={compact} stroke="#7f8aa1" tickLine={false} axisLine={false} fontSize={12} width={56} domain={["auto", "auto"]} />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#7f8aa1", strokeWidth: 1 }} />
            <Area type="monotone" dataKey="equity" stroke="none" fill="url(#eqFill)" isAnimationActive={false} />
            {hasBench && <Line type="monotone" dataKey="benchmark" stroke={NIFTY} strokeWidth={2} dot={false} isAnimationActive={false} activeDot={{ r: 4, stroke: "#121826", strokeWidth: 2 }} />}
            <Line type="monotone" dataKey="equity" stroke={STRATEGY} strokeWidth={2} dot={false} isAnimationActive={false} activeDot={{ r: 5, stroke: "#121826", strokeWidth: 2 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
}
