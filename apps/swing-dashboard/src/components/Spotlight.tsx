import { motion, useReducedMotion } from "framer-motion";

// Twin beams that drift slowly across the top of the page. Ambient light for the
// whole desk; the only moving thing that isn't tied to data or state.
const FIRST = "radial-gradient(68.54% 68.72% at 55.02% 31.46%, hsla(210, 100%, 85%, .08) 0, hsla(210, 100%, 55%, .02) 50%, hsla(210, 100%, 45%, 0) 80%)";
const SECOND = "radial-gradient(50% 50% at 50% 50%, hsla(210, 100%, 85%, .06) 0, hsla(210, 100%, 55%, .02) 80%, transparent 100%)";
const THIRD = "radial-gradient(50% 50% at 50% 50%, hsla(210, 100%, 85%, .04) 0, hsla(210, 100%, 45%, .02) 80%, transparent 100%)";

const WIDTH = 560, SMALL = 240, HEIGHT = 1380, Y = -350, X = 100, DURATION = 9;

function Beams({ side }: { side: "left" | "right" }) {
  const reduce = useReducedMotion();
  const sign = side === "left" ? 1 : -1;
  const rot = side === "left" ? -45 : 45;
  const anchor = side === "left" ? "left-0 origin-top-left" : "right-0 origin-top-right";
  return (
    <motion.div
      animate={reduce ? undefined : { x: [0, sign * X, 0] }}
      transition={{ duration: DURATION, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      className={`absolute top-0 h-screen w-screen ${side === "left" ? "left-0" : "right-0"}`}
    >
      <div className={`absolute top-0 ${side === "left" ? "left-0" : "right-0"}`} style={{ transform: `translateY(${Y}px) rotate(${rot}deg)`, background: FIRST, width: WIDTH, height: HEIGHT }} />
      <div className={`absolute top-0 ${anchor}`} style={{ transform: `rotate(${rot}deg) translate(${sign * 5}%, -50%)`, background: SECOND, width: SMALL, height: HEIGHT }} />
      <div className={`absolute top-0 ${anchor}`} style={{ transform: `rotate(${rot}deg) translate(${sign * -180}%, -70%)`, background: THIRD, width: SMALL, height: HEIGHT }} />
    </motion.div>
  );
}

export function Spotlight() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1.6 }} className="pointer-events-none absolute inset-0" aria-hidden>
      <Beams side="left" />
      <Beams side="right" />
    </motion.div>
  );
}
