import { useEffect, useState } from "react";

export interface DocumentScope {
  doc_name: string;
  company: string;
  title: string;
  page_count: number | null;
  questions: { id: string; question: string }[];
}

export type ScopeState = { status: "loading" } | { status: "ready"; scope: DocumentScope } | { status: "error" };

/** The single FinanceBench document the replica works on, from GET /api/scope. */
export function useScope(): ScopeState {
  const [state, setState] = useState<ScopeState>({ status: "loading" });
  useEffect(() => {
    fetch("/api/scope")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(
        (scope: DocumentScope) => setState({ status: "ready", scope }),
        () => setState({ status: "error" }),
      );
  }, []);
  return state;
}
