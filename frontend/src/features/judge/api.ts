/** Wire types of the judge tab endpoints (GET /api/judge, POST /api/judge/grade). Page indexes are 0-based. */

export interface SavedSystemGrade {
  verdict: string;
  reason: string;
  cited_pages: number[];
}

export interface JudgeQuestion {
  id: string;
  question: string;
  reference: string;
  evidence_pages: number[];
  saved: { finsage: SavedSystemGrade; naive: SavedSystemGrade } | null;
}

export interface JudgeOverview {
  judge_available: boolean;
  judge_model: string | null;
  questions: JudgeQuestion[];
  saved_scores: { finsage: number; naive: number } | null;
}

export interface GradeResult {
  question_id: string;
  verdict: string;
  reason: string;
  model: string;
  cost_usd: number;
}

async function detail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* fall through to the status */
  }
  return `The server answered ${response.status}.`;
}

export async function fetchOverview(): Promise<JudgeOverview> {
  const response = await fetch("/api/judge");
  if (!response.ok) throw new Error(await detail(response));
  return response.json();
}

export async function postGrade(questionId: string, answer: string, signal?: AbortSignal): Promise<GradeResult> {
  const response = await fetch("/api/judge/grade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer }),
    signal,
  });
  if (!response.ok) throw new Error(await detail(response));
  return response.json();
}
