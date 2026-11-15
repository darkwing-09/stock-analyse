import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { EXPO, rise } from "../lib/motion";

// Section arrival: rise 12px out of a slight blur. Sections on a page use
// increasing delays so the page settles top to bottom within ~400 ms.
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} initial={reduce ? false : rise.initial} animate={rise.animate} transition={{ duration: 0.55, ease: EXPO, delay }}>
      {children}
    </motion.div>
  );
}
