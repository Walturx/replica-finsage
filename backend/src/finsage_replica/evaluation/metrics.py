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


def evidence_precision(retrieved: list[dict], evidence_pages: list[int]) -> float:
    """Share of retrieved chunks that cover an evidence page."""
    if not retrieved:
        return 0.0
    wanted = set(evidence_pages)
    return sum(1 for c in retrieved if _pages(c) & wanted) / len(retrieved)
