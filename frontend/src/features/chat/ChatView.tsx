import { useEffect, useRef } from "react";

import type { ChunkRef } from "../../contracts/events";
import { AssistantMessage } from "./AssistantMessage";
import { Composer } from "./Composer";
import type { CitationView, Turn } from "./model";

interface Props {
  turns: Turn[];
  busy: boolean;
  docTitle?: string;
  examples: string[];
  composerDisabled?: boolean;
  composerNote?: string;
  onSend: (text: string) => void;
  onStop: () => void;
  onOpenCitation: (c: CitationView) => void;
  onOpenChunk: (c: ChunkRef) => void;
}

export function ChatView({
  turns,
  busy,
  docTitle,
  examples,
  composerDisabled,
  composerNote,
  onSend,
  onStop,
  onOpenCitation,
  onOpenChunk,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const last = turns[turns.length - 1];
  const progress = last?.role === "assistant" ? last.text.length + last.lastEventMs + Object.keys(last.citations).length : 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns.length, progress]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 pb-60 pt-8">
          {turns.length === 0 ? (
            <div className="flex flex-col items-center gap-7 pt-[14vh] text-center">
              <div className="flex flex-col items-center gap-1.5">
                <h1 className="m-0 text-[32px] font-normal tracking-tight text-balance">
                  {docTitle ? `Ask the ${docTitle}` : "Ask a financial filing"}
                </h1>
                <p className="m-0 text-[18px] text-muted-foreground text-balance">Every answer shows how it was found and cites the page.</p>
              </div>
              {examples.length > 0 && (
                <div className="grid w-full gap-2 sm:grid-cols-2">
                  {examples.map((q) => (
                    <button
                      key={q}
                      type="button"
                      disabled={busy || composerDisabled}
                      onClick={() => onSend(q)}
                      className="cursor-pointer rounded-2xl border border-border bg-card px-4 py-3 text-left text-[13px] leading-snug text-ink-2 shadow-card transition-colors hover:border-border-strong disabled:cursor-default disabled:opacity-50"
                    >
                      <span className="line-clamp-3">{q}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            turns.map((turn) =>
              turn.role === "user" ? (
                <div key={turn.id} className="animate-fade-in-up flex justify-end">
                  <div className="max-w-[80%] whitespace-pre-wrap rounded-[36px] bg-user-bubble px-6 py-3 text-[13px] leading-relaxed [overflow-wrap:anywhere]">
                    {turn.text}
                  </div>
                </div>
              ) : (
                <AssistantMessage key={turn.id} turn={turn} onOpenCitation={onOpenCitation} onOpenChunk={onOpenChunk} />
              ),
            )
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 px-4 pb-7 pt-2 sm:px-6">
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-background from-50% to-transparent" />
        <div className="pointer-events-auto relative mx-auto w-full max-w-3xl">
          <Composer
            busy={busy}
            disabled={composerDisabled}
            placeholder={docTitle ? `Ask about the ${docTitle}` : undefined}
            onSend={onSend}
            onStop={onStop}
          />
          <p className="m-0 mt-3 text-center text-[13px] text-muted-foreground">
            {composerNote ?? "FinSage answers from the filing and can be wrong. Check the cited page before relying on a number."}
          </p>
        </div>
      </div>
    </div>
  );
}
