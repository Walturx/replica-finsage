import numpy as np

from finsage_replica.preprocessing.dedup import deduplicate, inherited_pages, representatives


def _unit(*vectors: list[float]) -> np.ndarray:
    m = np.array(vectors, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_keeps_first_occurrence_and_drops_later_near_duplicates():
    emb = _unit([1, 0, 0], [0, 1, 0], [1, 0.01, 0], [0, 0, 1])

    assert deduplicate(emb, threshold=0.98) == [0, 1, 3]


def test_keeps_everything_below_the_threshold():
    emb = _unit([1, 0], [1, 1], [0, 1])

    assert deduplicate(emb, threshold=0.98) == [0, 1, 2]


def test_compares_against_kept_chunks_only():
    # 1 duplicates 0 and is dropped. 2 is close to 1 but not to 0, so it stays.
    emb = _unit([1, 0], [1, 0.15], [1, 0.32])

    assert deduplicate(emb, threshold=0.985) == [0, 2]


def test_empty_input():
    assert deduplicate(np.zeros((0, 4), dtype=np.float32), threshold=0.98) == []
    assert representatives(np.zeros((0, 4), dtype=np.float32), threshold=0.98) == []


def test_representatives_map_each_dropped_chunk_to_its_most_similar_kept_chunk():
    # 2 duplicates 0, 3 duplicates 1 (closer to 1 than to 0).
    emb = _unit([1, 0, 0], [0, 1, 0], [1, 0.01, 0], [0.01, 1, 0])

    assert representatives(emb, threshold=0.98) == [0, 1, 0, 1]


def test_kept_chunk_inherits_pages_of_substantive_duplicates_only():
    pages = [0, 62, 85, 90, 91]
    tokens = [8, 200, 200, 8, 8]  # 0, 3, 4: "Table of Contents" boilerplate. 2 duplicates the table on 62.
    reps = [0, 1, 1, 0, 0]

    assert inherited_pages(reps, pages, tokens, min_tokens=32) == {0: [], 1: [85]}


def test_inherited_pages_ignore_duplicates_on_the_same_page():
    assert inherited_pages([0, 0], [5, 5], [100, 100], min_tokens=32) == {0: []}


def test_representatives_agree_with_deduplicate():
    emb = _unit([1, 0], [1, 0.15], [1, 0.32], [0, 1])
    reps = representatives(emb, threshold=0.985)

    assert [i for i, r in enumerate(reps) if r == i] == deduplicate(emb, threshold=0.985)
