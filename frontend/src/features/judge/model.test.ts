import { describe, expect, it } from "vitest";

import { pagesLabel, scoreLabel, verdictMeta } from "./model";

describe("verdictMeta", () => {
  it("maps each judge verdict to a label and a tone", () => {
    expect(verdictMeta("correct")).toEqual({ label: "Correct", tone: "good" });
    expect(verdictMeta("partially_correct")).toEqual({ label: "Partial", tone: "warn" });
    expect(verdictMeta("incorrect")).toEqual({ label: "Incorrect", tone: "bad" });
  });

  it("treats unknown or unparsed output as not graded", () => {
    expect(verdictMeta("unparsed")).toEqual({ label: "Not graded", tone: "muted" });
    expect(verdictMeta("something else")).toEqual({ label: "Not graded", tone: "muted" });
  });
});

describe("pagesLabel", () => {
  it("shows 0-based page indexes as 1-based page numbers", () => {
    expect(pagesLabel([11])).toBe("p. 12");
    expect(pagesLabel([42, 3])).toBe("pp. 4, 43");
    expect(pagesLabel([])).toBe("none");
  });
});

describe("scoreLabel", () => {
  it("prints whole and half scores out of the question count", () => {
    expect(scoreLabel(7, 7)).toBe("7 of 7");
    expect(scoreLabel(3.5, 7)).toBe("3.5 of 7");
  });
});
