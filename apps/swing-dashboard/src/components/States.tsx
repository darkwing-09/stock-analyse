import { AlertTriangle, Check, Copy, Terminal } from "lucide-react";
import { useState, type ReactNode } from "react";
import { GlowCard } from "./GlowCard";

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <div className="shimmer h-9 w-64 rounded-xl" />
      <div className="shimmer h-5 w-96 max-w-full rounded-lg" />
      <div className="panel mt-6 p-5">
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="shimmer h-10 rounded-xl" style={{ opacity: 1 - i * 0.12 }} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function Command({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable: the text is still selectable */
    }
  }
  return (
    <div className="mono inline-flex max-w-full items-center gap-3 rounded-xl bg-ground px-3.5 py-2.5 text-[13px] text-fg ring-1 ring-inset ring-line">
      <Terminal size={14} className="shrink-0 text-accent-soft" aria-hidden />
      <code className="truncate">{children}</code>
      <button type="button" onClick={copy} aria-label={copied ? "Copied" : "Copy command"} className="ml-1 rounded-md p-1 text-fg-3 transition-colors hover:bg-white/[0.06] hover:text-fg">
        {copied ? <Check size={14} className="text-good" /> : <Copy size={14} />}
      </button>
    </div>
  );
}

export function EmptyState({ title, children, command }: { title: string; children: ReactNode; command?: string }) {
  return (
    <GlowCard className="p-7 sm:p-9">
      <h2 className="text-[20px] font-semibold">{title}</h2>
      <p className="mt-2 max-w-[62ch] text-[15px] leading-relaxed text-fg-2">{children}</p>
      {command && <div className="mt-5"><Command>{command}</Command></div>}
    </GlowCard>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="panel flex items-start gap-3 p-6">
      <AlertTriangle className="mt-0.5 shrink-0 text-bad" size={18} aria-hidden />
      <div>
        <p className="font-medium">Couldn't reach the dashboard server.</p>
        <p className="mt-1 text-fg-2">
          {message}. Start it with <code className="mono text-accent-soft">python swing.py serve</code> and reload.
        </p>
      </div>
    </div>
  );
}
