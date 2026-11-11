"""Near-duplicate removal (FinSage FFP, semantic enhancement step a).

The paper drops one of two chunks whose cosine similarity exceeds tau_dedup,
chosen at random. This replica keeps the first chunk in reading order so runs
are reproducible, and records which kept chunk stands in for each dropped one.
Financial filings repeat the same table in several sections, so the kept chunk
inherits the pages of its duplicates for page-level evaluation.
"""

from __future__ import annotations

import numpy as np


def representatives(embeddings: np.ndarray, threshold: float) -> list[int]:
    """For each chunk, the index of the kept chunk that represents it (itself when kept).

    Embeddings must be L2-normalized and in reading order. A chunk is dropped when its
    similarity to any already kept chunk reaches the threshold; it is then mapped to the
    most similar kept chunk.
    """
    if len(embeddings) == 0:
        return []
    similarity = embeddings @ embeddings.T
    kept: list[int] = []
    reps: list[int] = []
    for i in range(len(embeddings)):
        if kept:
            scores = similarity[i, kept]
            best = int(scores.argmax())
            if float(scores[best]) >= threshold:
                reps.append(kept[best])
                continue
        kept.append(i)
        reps.append(i)
    return reps


def inherited_pages(
    reps: list[int], page_indexes: list[int], n_tokens: list[int], min_tokens: int
) -> dict[int, list[int]]:
    """Pages each kept chunk stands in for, keyed by kept index.

    Only duplicates with at least `min_tokens` count, so short boilerplate such as a
    repeated "Table of Contents" line does not claim every page of the filing.
    """
    pages: dict[int, set[int]] = {i: set() for i, rep in enumerate(reps) if rep == i}
    for i, rep in enumerate(reps):
        if rep != i and n_tokens[i] >= min_tokens and page_indexes[i] != page_indexes[rep]:
            pages[rep].add(page_indexes[i])
    return {i: sorted(p) for i, p in pages.items()}


def deduplicate(embeddings: np.ndarray, threshold: float) -> list[int]:
    """Indices of the chunks to keep, given L2-normalized embeddings in reading order."""
    return [i for i, rep in enumerate(representatives(embeddings, threshold)) if rep == i]
