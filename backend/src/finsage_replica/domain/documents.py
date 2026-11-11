"""Document types shared by every FinSage module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """One parsed PDF page. `page_index` is 0-based, like FinanceBench `evidence_page_num`."""

    page_index: int
    markdown: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_name: str
    page_index: int
    section: str
    text: str
    n_tokens: int
