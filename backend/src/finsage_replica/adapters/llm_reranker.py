"""Reranker adapter that asks a language model to grade every candidate in one call.

FinSage's DRR is a decoder model fine-tuned with DPO, which was not released. The generic
cross-encoder (bge-reranker-v2-m3) ranked the AMD customer-concentration evidence 29th of 598,
because it matches wording rather than financial meaning. A decoder LLM grading relevance
zero-shot is the closer stand-in for the paper's reranker; the cross-encoder stays as baseline.
"""

from __future__ import annotations

import json
import re

from finsage_replica.ports.llm import Completion, LanguageModel

INSTRUCTIONS = (
    "You grade search results for a question about a company's SEC filing. For every numbered passage, give "
    "a score from 0 to 10: 10 means the passage contains the facts needed to answer the question, 5 means it "
    "is related context, 0 means it is useless. Judge financial meaning, not shared words: a passage saying one "
    "customer was 16% of revenue answers a question about customer concentration. Answer with one JSON object "
    'mapping every passage number to its score, like {"1": 3, "2": 10}, and nothing else.'
)


def parse_scores(text: str, n: int) -> list[float]:
    """Scores 0..1 in passage order. Missing or invalid entries score 0."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    scores = [0.0] * n
    for key, value in data.items() if isinstance(data, dict) else []:
        if str(key).isdigit() and 1 <= int(key) <= n and isinstance(value, (int, float)):
            scores[int(key) - 1] = min(max(float(value), 0.0), 10.0) / 10
    return scores


class LlmReranker:
    def __init__(self, llm: LanguageModel, max_passage_chars: int = 1200, max_output_tokens: int = 2500):
        self.llm = llm
        self.model = llm.model
        self._max_chars = max_passage_chars
        self._max_out = max_output_tokens
        self._usage: Completion | None = None

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        listing = "\n\n".join(f"[{i}] {p[: self._max_chars]}" for i, p in enumerate(passages, 1))
        completion = self.llm.complete(INSTRUCTIONS, f"Question: {query}\n\nPassages:\n{listing}", self._max_out)
        self._usage = completion
        return parse_scores(completion.text, len(passages))

    def take_usage(self) -> Completion | None:
        """Usage of the last call, returned once, so the pipeline can add it to the run cost."""
        usage, self._usage = self._usage, None
        return usage
