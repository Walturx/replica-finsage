import numpy as np
import pytest

from finsage_replica.evaluation.metrics import evidence_page_hit, evidence_precision
from finsage_replica.retrieval.expansion import expand_bundles
from finsage_replica.retrieval.index import DocumentIndex, SectionMeta
from finsage_replica.retrieval.merge import merge_paths
from finsage_replica.retrieval.rewrite import parse_subquestions


def _unit(rows):
    m = np.array(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def _chunk(i, page, section, text, also=()):
    return {"chunk_id": f"D:{page}:{i}", "doc_name": "D", "page_index": page, "section": section,
            "text": text, "n_tokens": len(text.split()), "also_on_pages": list(also)}


CHUNKS = [
    _chunk(0, 3, "Products", "AMD sells server microprocessors and graphics processors"),
    _chunk(1, 11, "Customers", "One customer accounted for 16% of consolidated net revenue"),
    _chunk(2, 11, "Customers", "Sales to this customer consisted of gaming products"),
    _chunk(3, 42, "Overview", "Net revenue increased driven by Data Center segment"),
]
EMB = _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0.95, 0.31, 0], [0, 0, 0, 1]])
SECTIONS = [
    SectionMeta("D:s0", "Products", ["D:3:0"], "AMD products"),
    SectionMeta("D:s1", "Customers", ["D:11:1", "D:11:2"], "AMD customer concentration"),
    SectionMeta("D:s2", "Overview", ["D:42:3"], "AMD revenue overview"),
]
SUMMARY_EMB = _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]])


@pytest.fixture
def index():
    return DocumentIndex(CHUNKS, EMB, SECTIONS, SUMMARY_EMB)


def test_bm25_ranks_the_chunk_with_the_query_words_first(index):
    hits = index.bm25("which customer accounted for revenue", k=2)

    assert index.chunks[hits[0][0]]["chunk_id"] == "D:11:1"
    assert 1 <= len(hits) <= 2
    assert all(score > 0 for _, score in hits)  # chunks sharing no informative word are not returned


def test_dense_returns_nearest_chunks_by_cosine(index):
    hits = index.dense(_unit([[0, 1, 0.05, 0]])[0], k=2)

    assert [index.chunks[i]["chunk_id"] for i, _ in hits] == ["D:11:1", "D:11:2"]
    assert hits[0][1] >= hits[1][1]


def test_metadata_returns_every_chunk_of_the_best_sections_in_reading_order(index):
    hits = index.metadata(_unit([[0, 1, 0, 0.1]])[0], k_sections=1)

    assert [index.chunks[i]["chunk_id"] for i, _ in hits] == ["D:11:1", "D:11:2"]
    assert hits[0][1] == hits[1][1]


def test_expansion_adds_similar_neighbours_up_to_the_bundle_size():
    emb = _unit([[1, 0], [1, 0.1], [1, 0.2], [0, 1], [1, 0.15]])

    added = expand_bundles([1], emb, tau=0.85, max_bundle=3)

    assert added == [0, 2]


def test_expansion_stops_at_dissimilar_neighbours():
    emb = _unit([[1, 0], [0, 1], [0, 1]])

    assert expand_bundles([0], emb, tau=0.85, max_bundle=5) == []


def test_merge_deduplicates_and_records_which_paths_found_each_chunk():
    merged = merge_paths({"bm25": [(1, 9.0), (0, 2.0)], "dense": [(1, 0.8), (3, 0.7)], "hyde": [(2, 0.6)]})

    # Found by two paths first, then by best rank inside its path (HyDE's top hit beats two second places).
    assert [(h.index, h.paths) for h in merged] == [(1, ("bm25", "dense")), (2, ("hyde",)), (0, ("bm25",)), (3, ("dense",))]


def test_page_hit_counts_the_chunk_page_and_the_pages_of_its_duplicates():
    retrieved = [_chunk(0, 5, "s", "x"), _chunk(1, 62, "s", "y", also=[85])]

    assert evidence_page_hit(retrieved, [85]) is True
    assert evidence_page_hit(retrieved, [7]) is False
    assert evidence_precision(retrieved, [85]) == 0.5
    assert evidence_precision([], [85]) == 0.0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('["What was AMD revenue in FY2022?", "What was AMD revenue in FY2021?"]',
         ["What was AMD revenue in FY2022?", "What was AMD revenue in FY2021?"]),
        ('```json\n["Did AMD report customer concentration in FY2022?"]\n```',
         ["Did AMD report customer concentration in FY2022?"]),
        ("not json at all", ["original question"]),
        ("[]", ["original question"]),
        ('["a", "a", " ", "b", "c", "d", "e"]', ["a", "b", "c", "d"]),
    ],
)
def test_subquestions_are_parsed_defensively(text, expected):
    assert parse_subquestions(text, fallback="original question") == expected
