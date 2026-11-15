import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useApi, type MarketData } from "../api";
import { GlowCard } from "../components/GlowCard";
import { Reveal } from "../components/Reveal";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
import { TextGenerate } from "../components/TextGenerate";
import { day } from "../format";

export function MarketView() {
  const res = useApi<MarketData>("/api/market");
  if (res.state === "loading") return <Skeleton rows={8} />;
  if (res.state === "error") return <ErrorState message={res.message} />;
  if (res.state === "empty")
    return <EmptyState title="No market review yet" command="python main.py --market-review">The AI writes an India market review (Nifty, Sensex, Bank Nifty, India VIX, sector rotation) after the close.</EmptyState>;
  const d = res.data;
  const date = `${d.date.slice(0, 4)}-${d.date.slice(4, 6)}-${d.date.slice(6, 8)}`;
  return (
    <div className="space-y-5">
      <div>
        <TextGenerate text="India market review" className="text-[32px] font-semibold leading-tight" />
        <Reveal delay={0.15}><p className="mt-1.5 text-[15px] text-fg-2">Written by the AI after the close · {day(date)}</p></Reveal>
      </div>
      <Reveal delay={0.1}>
        <GlowCard className="px-6 py-7 sm:px-10 sm:py-9">
          <article className="max-w-[72ch] text-[15px] leading-[1.75] text-fg-2">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: () => null,
                h2: ({ children }) => <h2 className="mb-3 mt-0 text-[22px] font-semibold text-fg">{children}</h2>,
                h3: ({ children }) => <h3 className="mb-2 mt-8 border-t border-line pt-5 text-[16px] font-semibold text-fg first:mt-0 first:border-0 first:pt-0">{children}</h3>,
                h4: ({ children }) => <h4 className="mb-2 mt-6 text-[14px] font-semibold text-fg">{children}</h4>,
                p: ({ children }) => <p className="my-3">{children}</p>,
                ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-accent-soft">{children}</ul>,
                ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5 marker:text-fg-3">{children}</ol>,
                strong: ({ children }) => <strong className="font-semibold text-fg">{children}</strong>,
                a: ({ children, href }) => <a href={href} className="text-accent-soft underline decoration-accent/40 hover:decoration-accent" target="_blank" rel="noreferrer">{children}</a>,
                code: ({ children }) => <code className="mono rounded bg-white/[0.06] px-1.5 py-0.5 text-[13px] text-fg">{children}</code>,
                table: ({ children }) => <div className="my-5 overflow-x-auto rounded-xl ring-1 ring-inset ring-line"><table className="num w-full text-[13px]">{children}</table></div>,
                th: ({ children }) => <th className="whitespace-nowrap border-b border-line bg-white/[0.03] px-3 py-2 text-left text-[12px] font-medium text-fg-3">{children}</th>,
                td: ({ children }) => <td className="whitespace-nowrap border-b border-white/[0.05] px-3 py-2 text-fg">{children}</td>,
                hr: () => <hr className="my-6 border-line" />,
                blockquote: ({ children }) => <blockquote className="my-4 border-l border-line-strong pl-4 text-fg-3">{children}</blockquote>,
              }}
            >
              {d.markdown}
            </ReactMarkdown>
          </article>
        </GlowCard>
      </Reveal>
    </div>
  );
}
