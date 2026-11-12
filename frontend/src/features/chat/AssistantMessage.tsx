import { AlertTriangle, Check, Copy } from "lucide-react";
import { useState } from "react";

import type { ChunkRef } from "../../contracts/events";
import { SourceBadge } from "../../shared/ui/SourceBadge";
import { TracePanel } from "../trace/TracePanel";
import { splitCitations, type AssistantTurn, type CitationView } from "./model";

interface Props {
  turn: AssistantTurn;
  onOpenCitation: (c: CitationView) => void;
  onOpenChunk: (c: ChunkRef) => void;
}

export function AssistantMessage({ turn, onOpenCitation, onOpenChunk }: Props) {
  const [copied, setCopied] = useState(false);
  const parts = splitCitations(turn.text);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(turn.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="animate-fade-in-up flex w-full min-w-0 flex-col gap-2.5">
      {turn.source && turn.source !== "live" && (
        <div className="flex items-center gap-2">
          <SourceBadge source={turn.source} />
          {turn.source === "recording" && turn.recordedAt && (
            <span className="font-mono text-[11px] text-muted-2">recorded {new Date(turn.recordedAt).toLocaleString()}</span>
          )}
        </div>
      )}
      {turn.source === "dev" && (
        <p className="m-0 rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-[12.5px] text-warn">
          Development fixture for building the interface. It is not output of the FinSage pipeline.
        </p>
      )}

      <TracePanel turn={turn} onOpen={onOpenChunk} />

      {turn.text && (
        <div className="whitespace-pre-wrap text-[13.5px] leading-[1.7] text-foreground [overflow-wrap:anywhere]">
          {parts.map((part, i) =>
            part.kind === "text" ? (
              <span key={i}>{part.value}</span>
            ) : (
              <button
                key={i}
                type="button"
                disabled={!turn.citations[part.marker]}
                onClick={() => turn.citations[part.marker] && onOpenCitation(turn.citations[part.marker])}
                className="mx-0.5 inline-flex h-[18px] min-w-[18px] cursor-pointer items-center justify-center rounded-full bg-accent-soft px-1 align-text-top font-mono text-[10.5px] font-medium text-accent transition-colors hover:bg-accent hover:text-background disabled:cursor-default disabled:opacity-60"
                aria-label={`Open source ${part.marker}`}
              >
                {part.marker}
              </button>
            ),
          )}
        </div>
      )}

      {Object.values(turn.citations).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.values(turn.citations).map((c) => (
            <button
              key={c.marker}
              type="button"
              onClick={() => onOpenCitation(c)}
              className="flex max-w-full cursor-pointer items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-left transition-colors hover:border-accent"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft font-mono text-[10.5px] text-accent">
                {c.marker}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[12.5px] font-medium">{c.doc_name.replaceAll("_", " ")}</span>
                <span className="block truncate text-[11.5px] text-muted-foreground">
                  Page {c.page_index + 1}
                  {c.section ? ` · ${c.section}` : ""}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}

      {turn.status === "error" && (
        <p role="alert" className="m-0 flex items-center gap-2 text-[12.5px] text-bad">
          <AlertTriangle aria-hidden className="h-3.5 w-3.5" /> {turn.error}
        </p>
      )}

      {turn.status === "done" && (
        <div className="flex items-center">
          <button
            type="button"
            onClick={copy}
            aria-label={copied ? "Copied" : "Copy answer"}
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-good" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      )}
    </div>
  );
}
