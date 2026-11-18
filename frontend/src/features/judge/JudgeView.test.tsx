import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { newAssistantTurn } from "../chat/model";
import type { JudgeOverview } from "./api";
import { JudgeView, type JudgeViewProps } from "./JudgeView";

afterEach(cleanup);

const overview: JudgeOverview = {
  judge_available: true,
  judge_model: "claude-opus-5-5",
  saved_scores: { finsage: 1, naive: 0.5 },
  questions: [
    {
      id: "q1",
      question: "Did AMD report customer concentration in FY22?",
      reference: "Yes, one customer accounted for 16% of net revenue.",
      evidence_pages: [11],
      saved: {
        finsage: { verdict: "correct", reason: "States the 16% customer.", cited_pages: [11] },
        naive: { verdict: "partially_correct", reason: "Hedges without the figure.", cited_pages: [] },
      },
    },
  ],
};

function props(overrides: Partial<JudgeViewProps> = {}): JudgeViewProps {
  return {
    overview: { status: "ready", data: overview },
    selectedId: "q1",
    phase: "idle",
    turn: null,
    grade: null,
    error: null,
    onSelect: vi.fn(),
    onRun: vi.fn(),
    onOpenCitation: vi.fn(),
    onOpenPage: vi.fn(),
    ...overrides,
  };
}

describe("JudgeView", () => {
  it("shows the official answer with its evidence page before any run", () => {
    render(<JudgeView {...props()} />);

    expect(screen.getByText("Yes, one customer accounted for 16% of net revenue.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Open evidence p. 12" }));
  });

  it("starts a run from the answer and grade button", () => {
    const onRun = vi.fn();
    render(<JudgeView {...props({ onRun })} />);

    fireEvent.click(screen.getByRole("button", { name: "Answer and grade" }));
    expect(onRun).toHaveBeenCalledOnce();
  });

  it("names the step in progress and disables the button", () => {
    render(<JudgeView {...props({ phase: "grading", turn: { ...newAssistantTurn("t"), text: "Yes." } })} />);

    const button = screen.getByRole("button", { name: "Grading with Claude Opus…" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("shows the verdict and the judge reason after grading", () => {
    render(
      <JudgeView
        {...props({
          phase: "done",
          turn: { ...newAssistantTurn("t"), status: "done", text: "Yes. One customer was 16% [1]." },
          grade: { question_id: "q1", verdict: "correct", reason: "Matches the 16% figure.", model: "claude-opus-5-5", cost_usd: 0.0068 },
        })}
      />,
    );

    expect(screen.getAllByText("Correct").length).toBeGreaterThan(0);
    expect(screen.getByText("Matches the 16% figure.")).toBeTruthy();
    expect(screen.getByText(/US\$0\.0068/)).toBeTruthy();
  });

  it("lists the saved experiment B grades with their totals", () => {
    render(<JudgeView {...props()} />);

    expect(screen.getByText("Saved experiment B results")).toBeTruthy();
    expect(screen.getByText("1 of 1")).toBeTruthy();
    expect(screen.getByText("0.5 of 1")).toBeTruthy();
    expect(screen.getByText("Hedges without the figure.")).toBeTruthy();
  });

  it("explains why grading is off when the judge is not available", () => {
    const data = { ...overview, judge_available: false, judge_model: null };
    render(<JudgeView {...props({ overview: { status: "ready", data } })} />);

    const button = screen.getByRole("button", { name: "Answer and grade" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(screen.getByText(/ANTHROPIC_API_KEY/)).toBeTruthy();
  });

  it("shows the error message when a run fails", () => {
    render(<JudgeView {...props({ phase: "error", error: "The judge failed: 401" })} />);

    expect(screen.getByRole("alert").textContent).toContain("The judge failed: 401");
  });
});
