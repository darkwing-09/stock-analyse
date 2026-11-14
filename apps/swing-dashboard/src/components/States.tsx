import { AlertTriangle, Terminal } from "lucide-react";
import type { ReactNode } from "react";

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-xl bg-ink-800" style={{ opacity: 1 - i * 0.15 }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children, command }: { title: string; children: ReactNode; command?: string }) {
  return (
    <div className="panel flex flex-col items-start gap-3 p-8">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-[62ch] text-fg-2">{children}</p>
      {command && (
        <code className="num flex items-center gap-2 rounded-lg bg-ink-950 px-3 py-2 text-[13px] text-marigold-soft ring-1 ring-ink-700">
          <Terminal size={14} aria-hidden /> {command}
        </code>
      )}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="panel flex items-start gap-3 p-6">
      <AlertTriangle className="mt-0.5 shrink-0 text-bad" size={18} aria-hidden />
      <div>
        <p className="font-medium">Couldn't reach the dashboard server.</p>
        <p className="text-fg-2">
          {message}. Start it with <code className="num text-marigold-soft">python swing.py serve</code> and reload.
        </p>
      </div>
    </div>
  );
}
