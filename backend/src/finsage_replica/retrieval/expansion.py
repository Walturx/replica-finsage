"""Chunk bundling (FinSage MPR): grow each retrieved chunk with similar reading-order neighbours.

Paper settings: similarity threshold tau_exp = 0.85 and at most K = 5 chunks per bundle.
"""

from __future__ import annotations

import numpy as np


def expand_bundles(seeds: list[int], embeddings: np.ndarray, tau: float = 0.85, max_bundle: int = 5) -> list[int]:
    """Indices added by expansion (not already seeds), sorted in reading order.

    From each seed the bundle grows one neighbour at a time to the left or right, taking the more
    similar side, while that neighbour's cosine similarity to the adjacent bundle member is >= tau.
    """
    seed_set = set(seeds)
    added: set[int] = set()
    n = len(embeddings)

    def sim(a: int, b: int) -> float:
        return float(embeddings[a] @ embeddings[b])

    for seed in seeds:
        left, right, size = seed - 1, seed + 1, 1
        while size < max_bundle:
            options = []
            if left >= 0 and sim(left, left + 1) >= tau:
                options.append((sim(left, left + 1), "left"))
            if right < n and sim(right, right - 1) >= tau:
                options.append((sim(right, right - 1), "right"))
            if not options:
                break
            _, side = max(options)
            if side == "left":
                added.add(left)
                left -= 1
            else:
                added.add(right)
                right += 1
            size += 1
    return sorted(added - seed_set)
