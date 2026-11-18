import { Gavel, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { splitCitations, type AssistantTurn, type CitationView } from "../chat/model";
import type { GradeResult, JudgeQuestion } from "./api";
import { pagesLabel, scoreLabel, verdictMeta, type Tone } from "./model";
import type { JudgePhase, OverviewState } from "./useJudge";

export interface JudgeViewProps {
  overview: OverviewState;
  selectedId: string | null;
  phase: JudgePhase;
  turn: AssistantTurn | null;
  grade: GradeResult | null;
  error: string | null;
  onSelect: (id: string) => void;
  onRun: () => void;
  onOpenCitation: (c: CitationView) => void;
  onOpenPage: (pageIndex: number) => void;
}

const TONES: Record<Tone, string> = {
  good: "border-good/30 bg-good/10 text-good",
  warn: "border-warn/30 bg-warn-soft text-warn",
  bad: "border-bad/30 bg-bad/10 text-bad",
  muted: "border-border bg-muted text-muted-foreground",
};

function VerdictChip({ verdict, large = false }: { verdict: string; large?: boolean }) {
  const meta = verdictMeta(verdict);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${TONES[meta.tone]} ${
        large ? "px-3 py-1 text-[14px]" : "px-2 py-0.5 text-[12px]"
      }`}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
      {meta.label}
    </span>
  );
}

function Column({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-card">
      <h3 className="m-0 text-[12px] font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      {children}
    </section>
  );
}

const BUTTON_LABEL: Record<JudgePhase, string> = {
  idle: "Answer and grade",
  answering: "Answering with FinSage…",
  grading: "Grading with Claude Opus…",
  done: "Answer and grade again",
  error: "Answer and grade",
};

function FinSageAnswer({ turn, onOpenCitation }: { turn: AssistantTurn; onOpenCitation: (c: CitationView) => void }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="whitespace-pre-wrap text-[13.5px] leading-[1.7] [overflow-wrap:anywhere]">
        {splitCitations(turn.text).map((part, i) =>
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
      {turn.done && (
        <p className="m-0 font-mono text-[11.5px] text-muted-foreground">
          {(turn.done.latency_ms / 1000).toFixed(1)} s · {turn.done.tokens_in + turn.done.tokens_out} tokens · US${turn.done.cost_usd.toFixed(4)}
        </p>
      )}
    </div>
  );
}

function LiveGrading(props: JudgeViewProps & { question: JudgeQuestion; available: boolean }) {
  const { question, available, phase, turn, grade, error, onRun, onOpenCitation, onOpenPage } = props;
  const working = phase === "answering" || phase === "grading";
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onRun}
          disabled={!available || working}
          className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-foreground px-4 py-2 text-[13px] font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-default disabled:opacity-50"
        >
          {working && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
          {BUTTON_LABEL[phase]}
        </button>
        {!available && (
          <p className="m-0 text-[12.5px] text-muted-foreground">
            Live grading needs the live backend and ANTHROPIC_API_KEY. The saved results below still work.
          </p>
        )}
      </div>

      {phase === "error" && error && (
        <p role="alert" className="m-0 rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-[12.5px] text-bad">
          {error}
        </p>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        <Column title="Official answer · FinanceBench">
          <p className="m-0 text-[13.5px] leading-[1.7]">{question.reference}</p>
          <div className="flex flex-wrap items-center gap-1.5 text-[12px] text-muted-foreground">
            Evidence:
            {question.evidence_pages.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onOpenPage(p)}
                aria-label={`Open evidence ${pagesLabel([p])}`}
                className="cursor-pointer rounded-md border border-border bg-card px-1.5 py-0.5 font-mono text-[11px] text-ink-2 transition-colors hover:border-accent hover:text-accent"
              >
                {pagesLabel([p])}
              </button>
            ))}
          </div>
        </Column>

        <Column title="FinSage · gpt-6-luna">
          {turn?.text ? (
            <FinSageAnswer turn={turn} onOpenCitation={onOpenCitation} />
          ) : (
            <p className="m-0 text-[13px] text-muted-foreground">
              {phase === "answering" ? "Searching the filing and writing the answer…" : "The answer appears here."}
            </p>
          )}
        </Column>

        <Column title="Verdict · Claude Opus">
          {grade ? (
            <div className="flex flex-col gap-3">
              <div>
                <VerdictChip verdict={grade.verdict} large />
              </div>
              <p className="m-0 text-[13.5px] leading-[1.7]">{grade.reason}</p>
              <p className="m-0 font-mono text-[11.5px] text-muted-foreground">
                {grade.model} · US${grade.cost_usd.toFixed(4)}
              </p>
            </div>
          ) : (
            <p className="m-0 text-[13px] text-muted-foreground">
              {phase === "grading" ? "Comparing the answer with the official one…" : "The verdict appears here."}
            </p>
          )}
        </Column>
      </div>
    </div>
  );
}

function SavedResults({ questions, scores }: { questions: JudgeQuestion[]; scores: { finsage: number; naive: number } }) {
  const graded = questions.filter((q) => q.saved);
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="m-0 text-[18px] font-medium">Saved experiment B results</h2>
        <p className="m-0 text-[13px] text-muted-foreground">
          Both systems use gpt-6-luna. Only the search changes. Open a row to read the judge's reasons. Showing these costs nothing.
        </p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="grid grid-cols-[minmax(0,1fr)_96px_96px] gap-3 border-b border-border px-4 py-2 text-[11.5px] font-medium uppercase tracking-wide text-muted-foreground sm:grid-cols-[minmax(0,1fr)_120px_120px]">
          <span>Question</span>
          <span>FinSage</span>
          <span>Naive RAG</span>
        </div>
        {graded.map((q) => (
          <details key={q.id} className="group border-b border-border last:border-b-0">
            <summary className="grid cursor-pointer list-none grid-cols-[minmax(0,1fr)_96px_96px] items-center gap-3 px-4 py-2.5 text-[13px] hover:bg-muted sm:grid-cols-[minmax(0,1fr)_120px_120px]">
              <span className="truncate" title={q.question}>
                {q.question}
              </span>
              <span>
                <VerdictChip verdict={q.saved!.finsage.verdict} />
              </span>
              <span>
                <VerdictChip verdict={q.saved!.naive.verdict} />
              </span>
            </summary>
            <div className="grid gap-3 bg-bg-alt px-4 py-3 text-[12.5px] leading-relaxed sm:grid-cols-2">
              <p className="m-0">
                <span className="font-medium">FinSage, cites {pagesLabel(q.saved!.finsage.cited_pages)}: </span>
                {q.saved!.finsage.reason}
              </p>
              <p className="m-0">
                <span className="font-medium">Naive RAG, cites {pagesLabel(q.saved!.naive.cited_pages)}: </span>
                {q.saved!.naive.reason}
              </p>
            </div>
          </details>
        ))}
        <div className="grid grid-cols-[minmax(0,1fr)_96px_96px] gap-3 border-t border-border bg-muted px-4 py-2.5 text-[13px] font-medium sm:grid-cols-[minmax(0,1fr)_120px_120px]">
          <span>Score</span>
          <span>{scoreLabel(scores.finsage, graded.length)}</span>
          <span>{scoreLabel(scores.naive, graded.length)}</span>
        </div>
      </div>
    </section>
  );
}

/** Judge tab: grade a benchmark answer live with Claude Opus, and browse the saved experiment B grades. */
export function JudgeView(props: JudgeViewProps) {
  const { overview, selectedId, onSelect } = props;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 pb-16 pt-8">
        <header className="flex flex-col gap-2">
          <h1 className="m-0 flex items-center gap-2 text-[24px] font-normal tracking-tight">
            <Gavel className="h-5 w-5 text-accent" aria-hidden />
            Judge · Claude Opus
          </h1>
          <p className="m-0 max-w-3xl text-[14px] text-muted-foreground text-balance">
            Claude Opus compares FinSage's answer with the official FinanceBench answer. It comes from a different model family than the
            generator, so no model grades its own answers. Only the benchmark questions have an official answer, so only those can be graded.
          </p>
        </header>

        {overview.status === "loading" && <p className="m-0 text-[13px] text-muted-foreground">Loading the benchmark questions…</p>}
        {overview.status === "error" && (
          <p role="alert" className="m-0 text-[13px] text-bad">
            Could not load the judge data: {overview.message}
          </p>
        )}

        {overview.status === "ready" && (() => {
          const { data } = overview;
          const question = data.questions.find((q) => q.id === selectedId) ?? data.questions[0];
          return (
            <>
              {question && (
                <div className="flex flex-col gap-4">
                  <label className="flex flex-col gap-1.5 text-[12px] font-medium uppercase tracking-wide text-muted-foreground">
                    Question
                    <select
                      id="judge-question"
                      value={question.id}
                      onChange={(e) => onSelect(e.target.value)}
                      className="w-full cursor-pointer rounded-xl border border-border bg-card px-3 py-2.5 text-[14px] font-normal normal-case tracking-normal text-foreground"
                    >
                      {data.questions.map((q) => (
                        <option key={q.id} value={q.id}>
                          {q.question}
                        </option>
                      ))}
                    </select>
                  </label>
                  <LiveGrading {...props} question={question} available={data.judge_available} />
                </div>
              )}
              {data.saved_scores && <SavedResults questions={data.questions} scores={data.saved_scores} />}
            </>
          );
        })()}
      </div>
    </div>
  );
}
