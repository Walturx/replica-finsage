import { useEffect, useRef } from "react";

import type { ChunkRef } from "../../contracts/events";
import { AssistantMessage } from "./AssistantMessage";
import { Composer } from "./Composer";
import type { CitationView, Turn } from "./model";

// Real FinanceBench open-source questions (financebench_id 03029, 00591, 01935, 00995).
const EXAMPLES = [
  "What is the FY2018 capital expenditure amount (in USD millions) for 3M? Give a response to the question by relying on the details shown in the cash flow statement.",
  "Does Adobe have an improving Free cashflow conversion as of FY2022?",
  "What was the key agenda of the AMCOR's 8k filing dated 1st July 2022?",
  "What are the major products and services that AMD sells as of FY22?",
];

interface Props {
  turns: Turn[];
  busy: boolean;
  composerDisabled?: boolean;
  composerNote?: string;
  onSend: (text: string) => void;
  onStop: () => void;
  onOpenCitation: (c: CitationView) => void;
  onOpenChunk: (c: ChunkRef) => void;
}

export function ChatView({ turns, busy, composerDisabled, composerNote, onSend, onStop, onOpenCitation, onOpenChunk }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const last = turns[turns.length - 1];
  const lastLength = last?.role === "assistant" ? last.text.length + last.lastEventMs : 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns.length, lastLength]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 pb-56 pt-8">
          {turns.length === 0 ? (
            <div className="flex flex-col items-center gap-6 pt-[12vh] text-center">
              <div className="flex flex-col gap-1.5">
                <h1 className="m-0 text-[30px] font-normal tracking-tight text-balance">Questions about financial filings</h1>
                <p className="m-0 text-[16px] text-muted-foreground">
                  A replication of FinSage over 84 FinanceBench documents. Every answer shows how it was found.
                </p>
              </div>
              <div className="grid w-full gap-2 sm:grid-cols-2">
                {EXAMPLES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    disabled={busy || composerDisabled}
                    onClick={() => onSend(q)}
                    className="cursor-pointer rounded-xl border border-border bg-card px-4 py-3 text-left text-[13px] leading-snug text-ink-2 transition-colors hover:border-border-strong hover:bg-bg-alt disabled:cursor-default disabled:opacity-50"
                  >
                    <span className="line-clamp-3">{q}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            turns.map((turn) =>
              turn.role === "user" ? (
                <div key={turn.id} className="animate-fade-in-up flex justify-end">
                  <div className="max-w-[80%] whitespace-pre-wrap rounded-[28px] bg-muted px-5 py-2.5 text-[14px] leading-relaxed [overflow-wrap:anywhere]">
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

      <div className="pointer-events-none absolute inset-x-0 bottom-0 px-4 pb-6 pt-2 sm:px-6">
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-44 bg-gradient-to-t from-background from-50% to-transparent" />
        <div className="pointer-events-auto relative mx-auto w-full max-w-3xl">
          <Composer busy={busy} disabled={composerDisabled} onSend={onSend} onStop={onStop} />
          <p className="m-0 mt-2.5 text-center text-[12px] text-muted-foreground">
            {composerNote ?? "Answers come from the documents and can be wrong. Check the cited page before relying on a number."}
          </p>
        </div>
      </div>
    </div>
  );
}
