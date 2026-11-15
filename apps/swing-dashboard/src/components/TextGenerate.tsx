import { motion, useReducedMotion } from "framer-motion";
import { EXPO } from "../lib/motion";

// Heading whose words resolve out of a blur, one after another. Under 600 ms
// for a five-word title; plain text under reduced motion.
export function TextGenerate({ text, className, as = "h1" }: { text: string; className?: string; as?: "h1" | "h2" | "p" }) {
  const reduce = useReducedMotion();
  const Tag = as;
  if (reduce) return <Tag className={className}>{text}</Tag>;
  const words = text.split(" ");
  return (
    <Tag className={className} aria-label={text}>
      {words.map((w, i) => (
        <motion.span
          key={`${w}-${i}`}
          aria-hidden
          className="inline-block"
          initial={{ opacity: 0, filter: "blur(10px)", y: 6 }}
          animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
          transition={{ duration: 0.5, ease: EXPO, delay: 0.06 * i }}
        >
          {w}
          {i < words.length - 1 ? " " : ""}
        </motion.span>
      ))}
    </Tag>
  );
}
