// Mirror of contracts/pipeline-events.schema.json (generated from backend/src/finsage_replica/domain/events.py).
// Keep both in sync: the backend test `test_committed_contract_matches_the_event_models` guards the schema file.

export type Source = "live" | "recording" | "dev";
export type RetrievalPath = "bm25" | "dense" | "metadata" | "hyde";

export interface ChunkRef {
  chunk_id: string;
  doc_name: string;
  page_index: number;
  section: string;
  snippet: string;
  score: number;
}

interface EventBase {
  run_id: string;
  t_ms: number;
}

export interface RunStarted extends EventBase {
  type: "run_started";
  question: string;
  source: Source;
  model: string;
  recorded_at?: string | null;
}

export interface Rewrite extends EventBase {
  type: "rewrite";
  sub_questions: string[];
}

export interface Retrieval extends EventBase {
  type: "retrieval";
  sub_question: number;
  path: RetrievalPath;
  hits: ChunkRef[];
  hyde_text?: string | null;
}

export interface Rerank extends EventBase {
  type: "rerank";
  sub_question: number;
  top: ChunkRef[];
}

export interface AnswerDelta extends EventBase {
  type: "answer_delta";
  text: string;
}

export interface Citation extends EventBase {
  type: "citation";
  marker: number;
  chunk_id: string;
  doc_name: string;
  page_index: number;
}

export interface Done extends EventBase {
  type: "done";
  latency_ms: number;
  stages_ms: Record<string, number>;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
}

export interface RunError extends EventBase {
  type: "error";
  message: string;
}

export type PipelineEvent = RunStarted | Rewrite | Retrieval | Rerank | AnswerDelta | Citation | Done | RunError;
