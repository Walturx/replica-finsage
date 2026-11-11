"""PdfParser adapter. pymupdf4llm replaces MinerU from the paper (declared limitation)."""

from __future__ import annotations

from pathlib import Path

from finsage_replica.domain.documents import Page


class Pymupdf4llmParser:
    def parse(self, path: Path) -> list[Page]:
        """Markdown per page, tables as markdown tables, 0-based page indexes."""
        import pymupdf4llm

        pages = pymupdf4llm.to_markdown(str(path), page_chunks=True, show_progress=False)
        return [Page(page_index=p["metadata"]["page_number"] - 1, markdown=p["text"]) for p in pages]
