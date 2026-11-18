"""Answer generation with page citations (FinSage answering and answer merging).

Each sub-question is answered from its reranked chunks. With several sub-questions the partial answers
are merged into one, as in the paper. Sources are numbered once across sub-questions so every [n] marker
in the final text points to one chunk and one page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ANSWER_INSTRUCTIONS = (
    "You answer questions about a company's SEC filing using only the numbered sources you are given. "
    "Cite every fact with the number of its source in square brackets, like [2]. When you compute a figure, "
    "show the inputs and the calculation. If the sources do not contain the answer, say that the provided "
    "excerpts of the filing do not answer it. Be concise: at most five sentences. Plain text."
)
MERGE_INSTRUCTIONS = (
    "Combine the partial answers into one answer to the original question. Use only what the partial answers "
    "and sources say, keep every citation number exactly as written, and do not add new facts. At most six "
    "sentences. Plain text."
)


@dataclass(frozen=True)
class Source:
    marker: int
    chunk: dict


def build_sources(per_subquestion: list[list[dict]]) -> list[Source]:
    """Number chunks 1..n in order of first appearance across sub-questions."""
    seen: dict[str, Source] = {}
    for chunks in per_subquestion:
        for chunk in chunks:
            if chunk["chunk_id"] not in seen:
                seen[chunk["chunk_id"]] = Source(len(seen) + 1, chunk)
    return list(seen.values())


def _render(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[{s.marker}] {s.chunk['doc_name'].replace('_', ' ')}, page {s.chunk['page_index'] + 1}, "
        f"section \"{s.chunk['section']}\":\n{s.chunk['text']}"
        for s in sources
    )


def answer_prompt(question: str, sources: list[Source]) -> str:
    return f"Sources:\n{_render(sources)}\n\nQuestion: {question}"


def merge_prompt(question: str, subquestions: list[str], partial_answers: list[str], sources: list[Source]) -> str:
    partials = "\n".join(f"- {q}\n  {a}" for q, a in zip(subquestions, partial_answers))
    return f"Sources:\n{_render(sources)}\n\nOriginal question: {question}\n\nPartial answers:\n{partials}"


def extract_citations(text: str, sources: list[Source]) -> list[Source]:
    """Sources cited in the text, in order of first use. Markers without a source are ignored."""
    by_marker = {s.marker: s for s in sources}
    cited: list[Source] = []
    for number in re.findall(r"\[(\d+)\]", text):
        source = by_marker.get(int(number))
        if source and source not in cited:
            cited.append(source)
    return cited
