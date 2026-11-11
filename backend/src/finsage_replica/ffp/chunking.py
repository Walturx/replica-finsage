"""Split parsed filing pages into token-bounded chunks (FinSage FFP, textual encoding step).

Rules:
- Chunks follow reading order and never cross a page, so every chunk maps to one
  0-based page index, the same convention as FinanceBench `evidence_page_num`.
- A markdown heading starts a new chunk and becomes the `section` of the chunks
  that follow it, across pages, until the next heading.
- A table that does not fit in one chunk is split by rows, and every piece repeats
  the table header so numbers keep their column labels.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from finsage_replica.domain.documents import Chunk, Page

__all__ = ["Chunk", "Page", "chunk_pages", "clean_heading"]

CountTokens = Callable[[str], int]

_HEADING = re.compile(r"^\s*#{1,6}\s+(.*)$")
_TABLE_SEPARATOR = re.compile(r"^\|[\s:|-]+\|?\s*$")
_MARKUP = re.compile(r"\*\*|__|</?u>|(?<!\w)_|_(?!\w)")


def clean_heading(line: str) -> str:
    match = _HEADING.match(line)
    text = match.group(1) if match else line
    return " ".join(_MARKUP.sub("", text).split())


def _blocks(markdown: str) -> list[tuple[str, str]]:
    """Group lines into ('heading' | 'table' | 'text', content) blocks in reading order."""
    blocks: list[tuple[str, str]] = []
    current: list[str] = []
    kind = ""

    def flush() -> None:
        nonlocal current, kind
        if current:
            blocks.append((kind, "\n".join(current)))
        current, kind = [], ""

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
        elif _HEADING.match(line):
            flush()
            blocks.append(("heading", clean_heading(line)))
        else:
            line_kind = "table" if line.lstrip().startswith("|") else "text"
            if line_kind != kind:
                flush()
                kind = line_kind
            current.append(line)
    flush()
    return [(k, c) for k, c in blocks if c.strip()]


def _split_words(text: str, max_tokens: int, count_tokens: CountTokens) -> list[str]:
    pieces: list[str] = []
    current: list[str] = []
    for word in text.split():
        candidate = current + [word]
        if current and count_tokens(" ".join(candidate)) > max_tokens:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current = candidate
    if current:
        pieces.append(" ".join(current))
    return pieces


def _split_table(table: str, max_tokens: int, count_tokens: CountTokens) -> list[str]:
    lines = table.splitlines()
    has_header = len(lines) >= 2 and bool(_TABLE_SEPARATOR.match(lines[1]))
    header = lines[:2] if has_header else []
    pieces: list[str] = []
    rows: list[str] = []
    for row in lines[len(header):]:
        candidate = "\n".join(header + rows + [row])
        if rows and count_tokens(candidate) > max_tokens:
            pieces.append("\n".join(header + rows))
            rows = [row]
        else:
            rows.append(row)
    if rows:
        pieces.append("\n".join(header + rows))

    result: list[str] = []
    for piece in pieces:
        if count_tokens(piece) <= max_tokens:
            result.append(piece)
        else:  # a single row wider than the limit
            result.extend(_split_words(piece, max_tokens, count_tokens))
    return result


def chunk_pages(
    doc_name: str,
    pages: list[Page],
    max_tokens: int,
    count_tokens: CountTokens,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    section = ""

    for page in pages:
        seq = 0
        current: list[str] = []
        current_section = section

        def emit(text: str) -> None:
            nonlocal seq
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_name}:{page.page_index}:{seq}",
                    doc_name=doc_name,
                    page_index=page.page_index,
                    section=current_section,
                    text=text,
                    n_tokens=count_tokens(text),
                )
            )
            seq += 1

        def flush() -> None:
            nonlocal current
            if current:
                emit("\n\n".join(current))
            current = []

        for kind, content in _blocks(page.markdown):
            if kind == "heading":
                flush()
                section = content
                current_section = section
                current = [content]
                continue

            if count_tokens("\n\n".join(current + [content])) <= max_tokens:
                current.append(content)
                continue

            flush()
            if count_tokens(content) <= max_tokens:
                current = [content]
            elif kind == "table":
                for piece in _split_table(content, max_tokens, count_tokens):
                    emit(piece)
            else:
                *full, remainder = _split_words(content, max_tokens, count_tokens)
                for piece in full:
                    emit(piece)
                current = [remainder]
        flush()

    return chunks
