"""Data for the chatbot's judge tab: the benchmark questions with their reference answers and saved grades.

The reference answer only exists for FinanceBench questions, so only those can be graded (spec S7).
Saved grades come from experiment B (results/experiment_b/results.json) and cost nothing to show.
"""

from __future__ import annotations

import json
from pathlib import Path

SYSTEMS = ("finsage", "naive")
SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0, "unparsed": 0.0}


def load_saved_outputs(results_file: Path | None) -> dict | None:
    """Experiment B outputs keyed by question id, or None when the experiment has not been run."""
    if results_file is None or not results_file.is_file():
        return None
    return json.loads(results_file.read_text(encoding="utf-8")).get("outputs") or None


def _saved_entry(outputs: dict | None, question_id: str) -> dict | None:
    entry = (outputs or {}).get(question_id)
    if not entry or not all("grade" in entry.get(s, {}) for s in SYSTEMS):
        return None
    return {
        s: {"verdict": entry[s]["grade"]["verdict"], "reason": entry[s]["grade"]["reason"],
            "cited_pages": entry[s].get("cited_pages", [])}
        for s in SYSTEMS
    }


def judge_overview(questions: list[dict], outputs: dict | None, judge_model: str | None) -> dict:
    """Everything the judge tab shows before any live call. Page indexes stay 0-based, as in the events."""
    rows = [
        {"id": q["id"], "question": q["question"], "reference": q["answer"],
         "evidence_pages": q["evidence_pages"], "saved": _saved_entry(outputs, q["id"])}
        for q in questions
    ]
    graded = [r["saved"] for r in rows if r["saved"] is not None]
    scores = {s: sum(SCORE.get(g[s]["verdict"], 0.0) for g in graded) for s in SYSTEMS} if graded else None
    return {"judge_available": judge_model is not None, "judge_model": judge_model,
            "questions": rows, "saved_scores": scores}
