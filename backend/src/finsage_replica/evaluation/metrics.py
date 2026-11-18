"""Page-level retrieval metrics against FinanceBench evidence pages (0-based `evidence_page_num`).

A chunk counts for a page when it lives on that page or stands in for a duplicate on it
(`also_on_pages`, see ffp/dedup.py).
"""

from __future__ import annotations


def _pages(chunk: dict) -> set[int]:
    return {chunk["page_index"], *chunk.get("also_on_pages", [])}


def evidence_page_hit(retrieved: list[dict], evidence_pages: list[int]) -> bool:
    """True when at least one retrieved chunk covers an evidence page."""
    wanted = set(evidence_pages)
    return any(_pages(c) & wanted for c in retrieved)


def first_evidence_rank(ranked: list[dict], evidence_pages: list[int]) -> int | None:
    """1-based position of the first chunk covering an evidence page, or None."""
    wanted = set(evidence_pages)
    for position, chunk in enumerate(ranked, 1):
        if _pages(chunk) & wanted:
            return position
    return None


def hits_at_k(ranked: list[dict], evidence_pages: list[int], k: int) -> bool:
    rank = first_evidence_rank(ranked, evidence_pages)
    return rank is not None and rank <= k


def evidence_precision(retrieved: list[dict], evidence_pages: list[int]) -> float:
    """Share of retrieved chunks that cover an evidence page."""
    if not retrieved:
        return 0.0
    wanted = set(evidence_pages)
    return sum(1 for c in retrieved if _pages(c) & wanted) / len(retrieved)
