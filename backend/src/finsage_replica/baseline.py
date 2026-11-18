"""Naive dense RAG baseline for experiment B.

One dense search on the raw question, top k chunks, one answer with the same generator, prompt and
citation format as FinSage. No rewriting, BM25, metadata, HyDE, expansion or reranking.
"""

from __future__ import annotations

from dataclasses import dataclass

from finsage_replica.answering.generate import ANSWER_INSTRUCTIONS, answer_prompt, build_sources, extract_citations
from finsage_replica.ports.llm import Completion, LanguageModel
from finsage_replica.ports.text import Embedder


@dataclass
class BaselineResult:
    text: str
    retrieved: list[dict]
    cited: list[dict]
    completion: Completion


def naive_answer(question: str, index, embedder: Embedder, llm: LanguageModel, k: int = 5) -> BaselineResult:
    query_vector = embedder.encode([question])[0]
    retrieved = [index.chunks[i] for i, _ in index.dense(query_vector, k)]
    sources = build_sources([retrieved])
    completion = llm.complete(ANSWER_INSTRUCTIONS, answer_prompt(question, sources), 1500)
    cited = [s.chunk for s in extract_citations(completion.text, sources)]
    return BaselineResult(text=completion.text, retrieved=retrieved, cited=cited, completion=completion)
