import ReactMarkdown from "react-markdown";
import { useApi, type MarketData } from "../api";
import { EmptyState, ErrorState, Skeleton } from "../components/States";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold">India market review</h1>
        <p className="mt-1 text-fg-2">AI-written after the close · {day(date)}</p>
      </div>
      <article className="panel px-6 py-6 sm:px-10 sm:py-8">
        <div className="max-w-[72ch] text-[15px] leading-[1.7] text-fg-2">
          <ReactMarkdown
            components={{
              h1: () => null,
              h2: ({ children }) => <h2 className="mb-2 mt-0 text-[20px] font-semibold text-fg">{children}</h2>,
              h3: ({ children }) => <h3 className="mb-2 mt-8 text-[16px] font-semibold text-fg">{children}</h3>,
              h4: ({ children }) => <h4 className="mb-2 mt-6 text-[14px] font-semibold text-fg">{children}</h4>,
              p: ({ children }) => <p className="my-3">{children}</p>,
              ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-marigold">{children}</ul>,
              strong: ({ children }) => <strong className="font-semibold text-fg">{children}</strong>,
              table: ({ children }) => <div className="my-4 overflow-x-auto"><table className="num w-full text-[13px]">{children}</table></div>,
              th: ({ children }) => <th className="border-b border-ink-700 px-2 py-1.5 text-left font-medium text-fg-3">{children}</th>,
              td: ({ children }) => <td className="border-b border-ink-700/60 px-2 py-1.5">{children}</td>,
              hr: () => <hr className="my-6 border-ink-700" />,
            }}
          >
            {d.markdown}
          </ReactMarkdown>
        </div>
      </article>
    </div>
  );
}
