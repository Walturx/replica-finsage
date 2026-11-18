export type Tone = "good" | "warn" | "bad" | "muted";

const VERDICTS: Record<string, { label: string; tone: Tone }> = {
  correct: { label: "Correct", tone: "good" },
  partially_correct: { label: "Partial", tone: "warn" },
  incorrect: { label: "Incorrect", tone: "bad" },
};

/** Label and color tone for a judge verdict; anything else reads as not graded. */
export function verdictMeta(verdict: string): { label: string; tone: Tone } {
  return VERDICTS[verdict] ?? { label: "Not graded", tone: "muted" };
}

/** 0-based page indexes as the 1-based page numbers printed on the filing. */
export function pagesLabel(pageIndexes: number[]): string {
  if (pageIndexes.length === 0) return "none";
  const pages = [...pageIndexes].sort((a, b) => a - b).map((p) => p + 1);
  return pages.length === 1 ? `p. ${pages[0]}` : `pp. ${pages.join(", ")}`;
}

export function scoreLabel(score: number, count: number): string {
  return `${Number.isInteger(score) ? score : score.toFixed(1)} of ${count}`;
}
