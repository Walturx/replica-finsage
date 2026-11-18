"""Port for grading an answer against a reference answer. The API and experiment B depend on this, never on an SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Grade:
    verdict: str  # correct, partially_correct, incorrect or unparsed
    reason: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class Judge(Protocol):
    model: str

    def grade(self, question: str, reference: str, answer: str) -> Grade:
        """Verdict on the candidate answer compared with the reference answer."""
        ...
