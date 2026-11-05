"""PDF to per-page markdown. pymupdf4llm replaces MinerU from the paper (declared limitation)."""

from __future__ import annotations

from pathlib import Path

import pymupdf4llm

from finsage_replica.preprocessing.chunking import Page


def parse_pdf(path: Path) -> list[Page]:
    """Markdown per page, tables as markdown tables, 0-based page indexes."""
    pages = pymupdf4llm.to_markdown(str(path), page_chunks=True, show_progress=False)
    return [Page(page_index=p["metadata"]["page_number"] - 1, markdown=p["text"]) for p in pages]
