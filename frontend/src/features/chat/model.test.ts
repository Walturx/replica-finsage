import { describe, expect, it } from "vitest";

import type { ChunkRef, PipelineEvent } from "../../contracts/events";
import { applyEvent, newAssistantTurn, splitCitations } from "./model";
import { createSseParser } from "./sse";

const chunk: ChunkRef = {
  chunk_id: "3M_2018_10K:59:3",
  doc_name: "3M_2018_10K",
  page_index: 59,
  section: "Cash Flows",
  snippet: "capex",
  score: 0.9,
};

function run(events: PipelineEvent[]) {
  return events.reduce(applyEvent, newAssistantTurn("t1"));
}

describe("createSseParser", () => {
  it("emits complete events even when they arrive split across chunks", () => {
    const out: PipelineEvent[] = [];
    const feed = createSseParser((e) => out.push(e));
    const line = JSON.stringify({ type: "answer_delta", run_id: "r", t_ms: 1, text: "hi" });

    feed(`data: ${line.slice(0, 10)}`);
    feed(`${line.slice(10)}\n\n`);
    feed(`data: ${line}\n\ndata: ${line}`);
    feed("\n\n");

    expect(out).toHaveLength(3);
    expect(out[0]).toMatchObject({ type: "answer_delta", text: "hi" });
  });

  it("ignores lines that are not data lines", () => {
    const out: PipelineEvent[] = [];
    createSseParser((e) => out.push(e))(": keep-alive\n\n");

    expect(out).toEqual([]);
  });
});

describe("applyEvent", () => {
  it("builds the assistant turn from a full run", () => {
    const turn = run([
      { type: "run_started", run_id: "r", t_ms: 0, question: "q", source: "live", model: "m" },
      { type: "rewrite", run_id: "r", t_ms: 1, sub_questions: ["q1", "q2"] },
      { type: "retrieval", run_id: "r", t_ms: 2, sub_question: 1, path: "hyde", hits: [chunk], hyde_text: "guess" },
      { type: "rerank", run_id: "r", t_ms: 3, sub_question: 1, top: [chunk] },
      { type: "answer_delta", run_id: "r", t_ms: 4, text: "Capex was " },
      { type: "answer_delta", run_id: "r", t_ms: 5, text: "$1,577 million [1]." },
      { type: "citation", run_id: "r", t_ms: 6, marker: 1, chunk_id: chunk.chunk_id, doc_name: "3M_2018_10K", page_index: 59 },
      { type: "done", run_id: "r", t_ms: 7, latency_ms: 7, stages_ms: {}, tokens_in: 10, tokens_out: 5, cost_usd: 0.001 },
    ]);

    expect(turn.status).toBe("done");
    expect(turn.source).toBe("live");
    expect(turn.subQuestions).toEqual(["q1", "q2"]);
    expect(turn.retrieval[1].hyde).toMatchObject({ hits: [chunk], hyde_text: "guess" });
    expect(turn.rerank[1]).toEqual([chunk]);
    expect(turn.text).toBe("Capex was $1,577 million [1].");
    expect(turn.citations[1]).toMatchObject({ doc_name: "3M_2018_10K", page_index: 59, snippet: "capex" });
    expect(turn.done?.cost_usd).toBe(0.001);
  });

  it("marks the turn as failed on an error event and keeps the partial answer", () => {
    const turn = run([
      { type: "run_started", run_id: "r", t_ms: 0, question: "q", source: "live", model: "m" },
      { type: "answer_delta", run_id: "r", t_ms: 1, text: "partial" },
      { type: "error", run_id: "r", t_ms: 2, message: "boom" },
    ]);

    expect(turn.status).toBe("error");
    expect(turn.error).toBe("boom");
    expect(turn.text).toBe("partial");
  });

  it("does not mutate the previous turn", () => {
    const before = newAssistantTurn("t1");
    applyEvent(before, { type: "answer_delta", run_id: "r", t_ms: 1, text: "x" });

    expect(before.text).toBe("");
  });
});

describe("splitCitations", () => {
  it("splits answer text into text parts and citation markers", () => {
    expect(splitCitations("A [1] and B [12].")).toEqual([
      { kind: "text", value: "A " },
      { kind: "cite", marker: 1 },
      { kind: "text", value: " and B " },
      { kind: "cite", marker: 12 },
      { kind: "text", value: "." },
    ]);
  });

  it("returns plain text when there are no markers", () => {
    expect(splitCitations("no refs")).toEqual([{ kind: "text", value: "no refs" }]);
  });
});
