import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduce) {
      node.textContent = format(value);
      return;
    }
    const controls = animate(value * 0.96, value, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => (node.textContent = format(v)),
    });
    return () => controls.stop();
  }, [value, format, reduce]);
  return <span ref={ref}>{format(value)}</span>;
}
