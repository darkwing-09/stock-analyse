import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState, type MouseEvent, type ReactNode } from "react";

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
                  className={`sticky top-0 border-b border-ink-700 bg-ink-850 px-3 py-2.5 font-medium text-fg-3 ${c.align === "right" ? "text-right" : "text-left"}`}
                >
                  {c.sort ? (
                    <button
                      type="button"
                      onClick={() => setSort({ key: c.key, dir: active && sort!.dir === "desc" ? "asc" : "desc" })}
                      className={`inline-flex items-center gap-1 rounded hover:text-fg ${active ? "text-fg" : ""}`}
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
          {sorted.map((row) => {
            const key = rowKey(row);
            return [
              <tr
                key={key}
                onMouseMove={spotlight}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`group transition-colors [background:radial-gradient(260px_circle_at_var(--x,-300px)_50%,rgba(242,178,62,0.07),transparent_70%)] ${onRowClick ? "cursor-pointer" : ""}`}
              >
                {columns.map((c) => (
                  <td key={c.key} className={`border-b border-ink-700/60 px-3 py-2.5 group-hover:bg-white/[0.015] ${c.align === "right" ? "text-right" : ""}`}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>,
              expanded === key && renderExpanded ? (
                <tr key={`${key}-x`}>
                  <td colSpan={columns.length} className="border-b border-ink-700/60 bg-ink-900/60 px-3 py-4">
                    {renderExpanded(row)}
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
