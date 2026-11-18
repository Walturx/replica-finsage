"""Document re-ranking (FinSage DRR): keep the K most relevant candidates per sub-question (K = 5 in the paper)."""

from __future__ import annotations

from finsage_replica.ports.text import Reranker


def rerank(query: str, chunks: list[dict], reranker: Reranker, top_k: int = 5) -> list[tuple[dict, float]]:
    """Candidates sorted by reranker score, best first, cut to top_k. Ties keep retrieval order."""
    if not chunks:
        return []
    passages = [f"{c['section']}\n{c['text']}" for c in chunks]
    scores = reranker.score(query, passages)
    ranked = sorted(zip(chunks, scores), key=lambda pair: -pair[1])
    return ranked[:top_k]
