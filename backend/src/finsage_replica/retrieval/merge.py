"""Union of the retrieval paths (FinSage MPR): one candidate list, each chunk tagged with the paths that found it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    index: int
    paths: tuple[str, ...]
    best_rank: int  # best 0-based rank across the paths that found it


def merge_paths(per_path: dict[str, list[tuple[int, float]]]) -> list[Candidate]:
    """Deduplicate by chunk. Order: found by more paths first, then by best rank. Order is only for display;
    the reranker decides the final order."""
    found: dict[int, list[str]] = {}
    rank: dict[int, int] = {}
    for path, hits in per_path.items():
        for position, (index, _score) in enumerate(hits):
            found.setdefault(index, []).append(path)
            rank[index] = min(rank.get(index, position), position)
    candidates = [Candidate(i, tuple(paths), rank[i]) for i, paths in found.items()]
    return sorted(candidates, key=lambda c: (-len(c.paths), c.best_rank))
