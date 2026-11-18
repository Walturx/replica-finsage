"""LLM-as-judge grading for experiment B, kept free of any SDK so it can be tested offline.

The judge compares a system answer with the FinanceBench reference answer. It must belong to a
different model family than the generator (spec S4) to avoid self-preference bias.
"""

from __future__ import annotations

import json
import re

VERDICTS = ("correct", "partially_correct", "incorrect")

JUDGE_INSTRUCTIONS = (
    "You grade answers to financial questions about one company filing. Compare the candidate answer "
    "with the reference answer written by a financial analyst. Judge the financial substance: figures, "
    "direction of change, and conclusions. Wording, extra correct detail and rounding differences do not "
    "matter. Use 'correct' when the candidate states the reference's key facts and conclusion, "
    "'partially_correct' when it gets part of them or hedges without a clear conclusion, and 'incorrect' "
    "when it contradicts the reference, misses the key facts or says it cannot answer. "
    'Reply with one JSON object only: {"verdict": "correct" | "partially_correct" | "incorrect", '
    '"reason": "<one sentence>"}'
)


def judge_prompt(question: str, reference: str, answer: str) -> str:
    return f"Question:\n{question}\n\nReference answer:\n{reference}\n\nCandidate answer:\n{answer}"


def parse_verdict(text: str) -> tuple[str, str]:
    """(verdict, reason); verdict is 'unparsed' when the judge output has no valid verdict."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return "unparsed", text.strip()
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "unparsed", text.strip()
    verdict = str(data.get("verdict", "")).strip().lower()
    return (verdict if verdict in VERDICTS else "unparsed"), str(data.get("reason", "")).strip()


def cited_page_hit(cited_pages: list[int], evidence_pages: list[int]) -> bool | None:
    """True when a cited page is an evidence page; None when the answer cites nothing."""
    if not cited_pages:
        return None
    return bool(set(cited_pages) & set(evidence_pages))
