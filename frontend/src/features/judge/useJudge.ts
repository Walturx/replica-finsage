import { useCallback, useEffect, useRef, useState } from "react";

import type { PipelineEvent } from "../../contracts/events";
import { applyEvent, newAssistantTurn, type AssistantTurn } from "../chat/model";
import { streamEvents } from "../chat/sse";
import { fetchOverview, postGrade, type GradeResult, type JudgeOverview } from "./api";

export type JudgePhase = "idle" | "answering" | "grading" | "done" | "error";
export type OverviewState = { status: "loading" } | { status: "ready"; data: JudgeOverview } | { status: "error"; message: string };

let counter = 0;

/** Container logic for the judge tab: FinSage answers live through /api/chat, then Claude Opus grades the answer. */
export function useJudge() {
  const [overview, setOverview] = useState<OverviewState>({ status: "loading" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<JudgePhase>("idle");
  const [turn, setTurn] = useState<AssistantTurn | null>(null);
  const [grade, setGrade] = useState<GradeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetchOverview().then(
      (data) => {
        setOverview({ status: "ready", data });
        setSelectedId((current) => current ?? data.questions[0]?.id ?? null);
      },
      (err: Error) => setOverview({ status: "error", message: err.message }),
    );
  }, []);

  const select = useCallback((id: string) => {
    abortRef.current?.abort();
    setSelectedId(id);
    setPhase("idle");
    setTurn(null);
    setGrade(null);
    setError(null);
  }, []);

  const run = useCallback(async () => {
    if (overview.status !== "ready" || !selectedId) return;
    const question = overview.data.questions.find((q) => q.id === selectedId);
    if (!question) return;
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    setGrade(null);
    setError(null);
    setPhase("answering");

    let current = newAssistantTurn(`judge-${++counter}`);
    setTurn(current);
    try {
      await streamEvents(
        "/api/chat",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: question.question, history: [] }),
          signal: controller.signal,
        },
        (event: PipelineEvent) => {
          current = applyEvent(current, event);
          setTurn(current);
        },
      );
      if (current.status !== "done") throw new Error(current.error ?? "The answer stopped before it finished.");
      setPhase("grading");
      setGrade(await postGrade(question.id, current.text, controller.signal));
      setPhase("done");
    } catch (err) {
      if (controller.signal.aborted) return;
      setError((err as Error).message);
      setPhase("error");
    }
  }, [overview, selectedId]);

  return { overview, selectedId, phase, turn, grade, error, select, run };
}
