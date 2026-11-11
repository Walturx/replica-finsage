import { useCallback, useRef, useState } from "react";

import type { PipelineEvent } from "../../contracts/events";
import { applyEvent, newAssistantTurn, type AssistantTurn, type Turn } from "./model";
import { streamEvents } from "./sse";

let counter = 0;
const nextId = () => `turn-${++counter}`;

/** Container logic for the chat: owns the turns and streams pipeline events into them. */
export function useChat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const runInto = useCallback(async (userText: string, url: string, init: RequestInit) => {
    const controller = new AbortController();
    abortRef.current = controller;
    const assistantId = nextId();
    setTurns((prev) => [...prev, { id: nextId(), role: "user", text: userText }, newAssistantTurn(assistantId)]);
    setBusy(true);

    const update = (fn: (t: AssistantTurn) => AssistantTurn) =>
      setTurns((prev) => prev.map((t) => (t.id === assistantId && t.role === "assistant" ? fn(t) : t)));
    const onEvent = (event: PipelineEvent) => update((t) => applyEvent(t, event));

    try {
      await streamEvents(url, { ...init, signal: controller.signal }, onEvent);
      update((t) => (t.status === "streaming" ? { ...t, status: "error", error: "The stream ended before the answer finished." } : t));
    } catch (err) {
      const stopped = controller.signal.aborted;
      update((t) => ({ ...t, status: "error", error: stopped ? "Stopped." : (err as Error).message }));
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }, []);

  const send = useCallback(
    (message: string) => {
      const history = turns.flatMap((t): { role: "user" | "assistant"; content: string }[] =>
        t.role === "user"
          ? [{ role: "user", content: t.text }]
          : t.status === "done"
            ? [{ role: "assistant", content: t.text }]
            : [],
      );
      return runInto(message, "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      });
    },
    [turns, runInto],
  );

  const replay = useCallback(
    (runId: string, question: string) => runInto(question, `/api/recordings/${encodeURIComponent(runId)}/replay`, { method: "GET" }),
    [runInto],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);
  const reset = useCallback(() => setTurns([]), []);

  return { turns, busy, send, replay, stop, reset };
}
