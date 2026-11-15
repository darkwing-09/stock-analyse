import clsx from "clsx";
import { motion, useAnimationFrame, useMotionTemplate, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useRef, type ReactNode } from "react";

// A pill whose 1px edge carries a travelling point of light: the "live" marker
// for the market regime chip. Still under reduced motion.
export function MovingBorderChip({ children, color = "#3b82f6", duration = 4500, className, title }: { children: ReactNode; color?: string; duration?: number; className?: string; title?: string }) {
  const reduce = useReducedMotion();
  const pathRef = useRef<SVGRectElement>(null);
  const progress = useMotionValue(0);

  useAnimationFrame((time) => {
    if (reduce) return;
    const length = pathRef.current?.getTotalLength();
    if (length) progress.set((time * (length / duration)) % length);
  });
  const x = useTransform(progress, (v) => pathRef.current?.getPointAtLength(v).x ?? 0);
  const y = useTransform(progress, (v) => pathRef.current?.getPointAtLength(v).y ?? 0);
  const transform = useMotionTemplate`translateX(${x}px) translateY(${y}px) translateX(-50%) translateY(-50%)`;

  return (
    <span className={clsx("relative inline-flex overflow-hidden rounded-full p-px", className)} title={title}>
      <span className="absolute inset-0 rounded-full bg-white/10" aria-hidden />
      {!reduce && (
        <span className="absolute inset-0" aria-hidden>
          <svg className="absolute h-full w-full" preserveAspectRatio="none" width="100%" height="100%">
            <rect ref={pathRef} fill="none" width="100%" height="100%" rx="30%" ry="30%" />
          </svg>
          <motion.span className="absolute left-0 top-0 h-10 w-10 rounded-full" style={{ transform, background: `radial-gradient(${color} 25%, transparent 65%)` }} />
        </span>
      )}
      <span className="relative inline-flex items-center gap-1.5 rounded-full bg-[#0c0c0c]/90 px-3 py-1.5 text-[12px] font-medium text-fg backdrop-blur-xl">{children}</span>
    </span>
  );
}
