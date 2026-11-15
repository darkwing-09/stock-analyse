import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState, type MouseEvent, type ReactNode } from "react";
import { EXPO, stagger } from "../lib/motion";

export interface Column<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  sort?: (row: T) => number | string;
  align?: "left" | "right";
}

function spotlight(e: MouseEvent<HTMLTableRowElement>) {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty("--x", `${e.clientX - r.left}px`);
}

export function DataTable<T>({
  rows, columns, rowKey, initialSort, caption, onRowClick, expanded, renderExpanded,
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  initialSort?: { key: string; dir: "asc" | "desc" };
  caption: string;
  onRowClick?: (row: T) => void;
  expanded?: string | null;
  renderExpanded?: (row: T) => ReactNode;
}) {
  const reduce = useReducedMotion();
  const [sort, setSort] = useState(initialSort);
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort?.key);
    if (!col?.sort || !sort) return rows;
    const get = col.sort;
    return [...rows].sort((a, b) => {
      const av = get(a), bv = get(b);
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === "asc" ? cmp : -cmp;
    });
  }, [rows, columns, sort]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0 text-[14px]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort?.key === c.key;
              return (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                  className={`sticky top-0 z-[1] border-b border-line bg-surface px-3 py-2.5 text-[12px] font-medium tracking-[0.01em] text-fg-3 ${c.align === "right" ? "text-right" : "text-left"}`}
                >
                  {c.sort ? (
                    <button
                      type="button"
                      onClick={() => setSort({ key: c.key, dir: active && sort!.dir === "desc" ? "asc" : "desc" })}
                      className={`inline-flex items-center gap-1 rounded transition-colors hover:text-fg ${active ? "text-fg" : ""}`}
                    >
                      {c.label}
                      {active && (sort!.dir === "desc" ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const key = rowKey(row);
            const open = expanded === key;
            return [
              <motion.tr
                key={key}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: EXPO, delay: stagger(i, 0.03) }}
                onMouseMove={spotlight}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                aria-expanded={renderExpanded ? open : undefined}
                className={`group [background:radial-gradient(320px_circle_at_var(--x,-400px)_50%,rgba(59,130,246,0.08),transparent_70%)] ${onRowClick ? "cursor-pointer" : ""}`}
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`border-b border-white/[0.05] px-3 py-2.5 transition-colors duration-200 group-hover:bg-white/[0.02] ${open ? "bg-white/[0.025]" : ""} ${c.align === "right" ? "text-right" : ""}`}
                  >
                    {c.render(row)}
                  </td>
                ))}
              </motion.tr>,
              renderExpanded ? (
                <tr key={`${key}-x`}>
                  <td colSpan={columns.length} className={`p-0 ${open ? "border-b border-white/[0.05]" : ""}`}>
                    <AnimatePresence initial={false}>
                      {open && (
                        <motion.div
                          initial={reduce ? false : { height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.32, ease: EXPO }}
                          className="overflow-hidden bg-white/[0.02]"
                        >
                          <div className="px-4 py-4">{renderExpanded(row)}</div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </td>
                </tr>
              ) : null,
            ];
          })}
        </tbody>
      </table>
    </div>
  );
}
