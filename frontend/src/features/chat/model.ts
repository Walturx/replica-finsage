import type { ChunkRef, Done, PipelineEvent, RetrievalPath, Source } from "../../contracts/events";

export type TurnStatus = "streaming" | "done" | "error";

export interface PathResult {
  hits: ChunkRef[];
  hyde_text?: string | null;
}

export interface CitationView {
  marker: number;
  chunk_id: string;
  doc_name: string;
  page_index: number;
  section?: string;
  snippet?: string;
}

export interface UserTurn {
  id: string;
  role: "user";
  text: string;
}

export interface AssistantTurn {
  id: string;
  role: "assistant";
  status: TurnStatus;
  runId?: string;
  source?: Source;
  model?: string;
  recordedAt?: string | null;
  subQuestions: string[];
  retrieval: Record<number, Partial<Record<RetrievalPath, PathResult>>>;
  rerank: Record<number, ChunkRef[]>;
  text: string;
  citations: Record<number, CitationView>;
  done?: Done;
  error?: string;
  lastEventMs: number;
}

export type Turn = UserTurn | AssistantTurn;

export function newAssistantTurn(id: string): AssistantTurn {
  return {
    id,
    role: "assistant",
    status: "streaming",
    subQuestions: [],
    retrieval: {},
    rerank: {},
    text: "",
    citations: {},
    lastEventMs: 0,
  };
}

function findChunk(turn: AssistantTurn, chunkId: string): ChunkRef | undefined {
  for (const top of Object.values(turn.rerank)) {
    const hit = top.find((c) => c.chunk_id === chunkId);
    if (hit) return hit;
  }
  return undefined;
}

/** Pure reducer: returns a new turn with the event applied. */
export function applyEvent(turn: AssistantTurn, event: PipelineEvent): AssistantTurn {
  const next: AssistantTurn = { ...turn, lastEventMs: event.t_ms };
  switch (event.type) {
    case "run_started":
      return {
        ...next,
        runId: event.run_id,
        source: event.source,
        model: event.model,
        recordedAt: event.recorded_at ?? null,
      };
    case "rewrite":
      return { ...next, subQuestions: event.sub_questions };
    case "retrieval":
      return {
        ...next,
        retrieval: {
          ...turn.retrieval,
          [event.sub_question]: {
            ...turn.retrieval[event.sub_question],
            [event.path]: { hits: event.hits, hyde_text: event.hyde_text },
          },
        },
      };
    case "rerank":
      return { ...next, rerank: { ...turn.rerank, [event.sub_question]: event.top } };
    case "answer_delta":
      return { ...next, text: turn.text + event.text };
    case "citation": {
      const chunk = findChunk(turn, event.chunk_id);
      return {
        ...next,
        citations: {
          ...turn.citations,
          [event.marker]: {
            marker: event.marker,
            chunk_id: event.chunk_id,
            doc_name: event.doc_name,
            page_index: event.page_index,
            section: chunk?.section,
            snippet: chunk?.snippet,
          },
        },
      };
    }
    case "done":
      return { ...next, status: "done", done: event };
    case "error":
      return { ...next, status: "error", error: event.message };
  }
}

export type AnswerPart = { kind: "text"; value: string } | { kind: "cite"; marker: number };

/** Split answer text on [n] markers so the UI can render them as citation chips. */
export function splitCitations(text: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  let last = 0;
  for (const match of text.matchAll(/\[(\d+)\]/g)) {
    const at = match.index ?? 0;
    if (at > last) parts.push({ kind: "text", value: text.slice(last, at) });
    parts.push({ kind: "cite", marker: Number(match[1]) });
    last = at + match[0].length;
  }
  if (last < text.length) parts.push({ kind: "text", value: text.slice(last) });
  return parts;
}
