import clsx from "clsx";
import { useReducedMotion } from "framer-motion";
import { useRef, type HTMLAttributes, type PointerEvent, type ReactNode } from "react";

// A panel whose edge lights up where the pointer is. The highlight angle is
// measured from the card centre, so the glow travels around the border as the
// pointer circles the card. Static (plain hairline) under reduced motion.
export function GlowCard({ className, children, ...rest }: { className?: string; children: ReactNode } & HTMLAttributes<HTMLElement>) {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();

  function onMove(e: PointerEvent<HTMLElement>) {
    const el = ref.current;
    if (!el || e.pointerType === "touch") return;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    const angle = (Math.atan2(y - r.height / 2, x - r.width / 2) * 180) / Math.PI + 90;
    el.style.setProperty("--gx", `${x}px`);
    el.style.setProperty("--gy", `${y}px`);
    el.style.setProperty("--gs", angle.toFixed(1));
    el.style.setProperty("--ga", "1");
  }
  function onLeave() {
    ref.current?.style.setProperty("--ga", "0");
  }

  return (
    <section ref={ref} onPointerMove={reduce ? undefined : onMove} onPointerLeave={onLeave} className={clsx("panel glow", className)} {...rest}>
      <div className="relative">{children}</div>
    </section>
  );
}
