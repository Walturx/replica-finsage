import { ChevronDown, FileSearch, Layers, ListOrdered, Sparkles, Split } from "lucide-react";
import { useEffect, useState } from "react";

import type { ChunkRef, RetrievalPath } from "../../contracts/events";
import type { AssistantTurn } from "../chat/model";

const PATHS: { key: RetrievalPath; label: string; hint: string }[] = [
  { key: "bm25", label: "BM25", hint: "exact words" },
  { key: "dense", label: "Dense", hint: "meaning, BGE-M3" },
  { key: "metadata", label: "Metadata", hint: "section summaries" },
  { key: "hyde", label: "HyDE", hint: "hypothetical answer" },
];

const docLabel = (c: { doc_name: string; page_index: number }) => `${c.doc_name.replaceAll("_", " ")} · p. ${c.page_index + 1}`;

function PageChip({ chunk, onOpen }: { chunk: ChunkRef; onOpen: (c: ChunkRef) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(chunk)}
      title={chunk.section}
      className="cursor-pointer rounded-md border border-border bg-card px-1.5 py-0.5 font-mono text-[10.5px] text-ink-2 transition-colors hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
    >
      {docLabel(chunk)}
    </button>
  );
}

function Elapsed({ running, ms }: { running: boolean; ms: number }) {
  const [now, setNow] = useState(() => Date.now());
  const [start] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [running]);
  const value = running ? now - start : ms;
  return <span className="tabular-nums">{(value / 1000).toFixed(1)} s</span>;
}

/** The "how I found it" panel: every pipeline stage of one answer, collapsible. */
export function TracePanel({ turn, onOpen }: { turn: AssistantTurn; onOpen: (c: ChunkRef) => void }) {
  const running = turn.status === "streaming";
  const [open, setOpen] = useState(true);
  const subCount = Math.max(turn.subQuestions.length, 1);
  const pathsDone = Object.values(turn.retrieval).reduce((n, r) => n + Object.keys(r).length, 0);
  const reranked = Object.values(turn.rerank).reduce((n, top) => n + top.length, 0);

  return (
    <div className="flex flex-col gap-2.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full cursor-pointer select-none items-center gap-1.5 rounded-sm border-b border-border pb-2 text-left text-[12.5px] text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-foreground"
      >
        <ChevronDown aria-hidden className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? "" : "-rotate-90"}`} />
        {running ? (
          <>
            <span aria-hidden className="pulse-dot h-1.5 w-1.5 rounded-full bg-foreground" />
            <span className="text-shimmer">Working for</span>
            <Elapsed running ms={0} />
          </>
        ) : (
          <>
            <span>Found in</span>
            <Elapsed running={false} ms={turn.done?.latency_ms ?? turn.lastEventMs} />
            <span className="tabular-nums text-muted-2">
              · {pathsDone} searches · top {reranked} kept
            </span>
          </>
        )}
      </button>

      {open && (
        <ol className="m-0 flex list-none flex-col gap-3 border-l border-border p-0 pl-3 text-[13px] text-muted-foreground">
          {turn.subQuestions.length > 0 && (
            <li className="animate-fade-in-up flex flex-col gap-1">
              <span className="flex items-center gap-2">
                <Split aria-hidden className="h-3.5 w-3.5" /> Rewrote the question into {turn.subQuestions.length} self-contained{" "}
                {turn.subQuestions.length === 1 ? "query" : "queries"}
              </span>
              {turn.subQuestions.map((q, i) => (
                <span key={i} className="pl-[22px] text-foreground">
                  <span className="font-mono text-muted-2">{i + 1}.</span> {q}
                </span>
              ))}
            </li>
          )}

          {Array.from({ length: subCount }, (_, sq) => {
            const paths = turn.retrieval[sq];
            if (!paths) return null;
            return (
              <li key={`r-${sq}`} className="animate-fade-in-up flex flex-col gap-1.5">
                <span className="flex items-center gap-2">
                  <FileSearch aria-hidden className="h-3.5 w-3.5" /> Searched {subCount > 1 ? `query ${sq + 1} ` : ""}by four paths
                </span>
                <div className="flex flex-col gap-1 pl-[22px]">
                  {PATHS.map(({ key, label, hint }) => {
                    const result = paths[key];
                    return (
                      <div key={key} className="flex flex-wrap items-center gap-1.5">
                        <span className="w-[74px] shrink-0 font-medium text-ink-2" title={hint}>
                          {label}
                        </span>
                        {result ? (
                          result.hits.length ? (
                            result.hits.map((c) => <PageChip key={c.chunk_id} chunk={c} onOpen={onOpen} />)
                          ) : (
                            <span className="text-muted-2">no hits</span>
                          )
                        ) : (
                          <span className="text-shimmer">searching</span>
                        )}
                        {result?.hyde_text && (
                          <span className="basis-full pl-[80px] italic text-muted-foreground">“{result.hyde_text}”</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </li>
            );
          })}

          {Object.entries(turn.rerank).map(([sq, top]) => (
            <li key={`k-${sq}`} className="animate-fade-in-up flex flex-col gap-1.5">
              <span className="flex items-center gap-2">
                <ListOrdered aria-hidden className="h-3.5 w-3.5" /> Reranked and kept the top {top.length}
              </span>
              <div className="flex flex-col gap-1 pl-[22px]">
                {top.map((c, i) => (
                  <div key={c.chunk_id} className="flex items-center gap-2">
                    <span className="w-4 font-mono text-muted-2">{i + 1}</span>
                    <span className="h-1 w-16 overflow-hidden rounded-full bg-muted">
                      <span className="block h-full rounded-full bg-accent" style={{ width: `${Math.round(Math.min(1, Math.max(0, c.score)) * 100)}%` }} />
                    </span>
                    <span className="w-9 font-mono tabular-nums text-muted-2">{c.score.toFixed(2)}</span>
                    <PageChip chunk={c} onOpen={onOpen} />
                  </div>
                ))}
              </div>
            </li>
          ))}

          {turn.done && (
            <li className="animate-fade-in-up flex items-center gap-2">
              {turn.source === "dev" ? <Layers aria-hidden className="h-3.5 w-3.5" /> : <Sparkles aria-hidden className="h-3.5 w-3.5" />}
              <span className="tabular-nums">
                {turn.model} · {(turn.done.latency_ms / 1000).toFixed(1)} s · {turn.done.tokens_in + turn.done.tokens_out} tokens · $
                {turn.done.cost_usd.toFixed(4)}
              </span>
            </li>
          )}
        </ol>
      )}
    </div>
  );
}
