import numpy as np

from finsage_replica.evaluation.experiment_a import CONFIGS, aggregate, needs_generation
from finsage_replica.retrieval.index import DocumentIndex, SectionMeta
from finsage_replica.retrieval.mpr import MprConfig, MultiPathRetriever


def _unit(rows):
    m = np.array(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


CHUNKS = [
    {"chunk_id": f"D:{p}:{i}", "doc_name": "D", "page_index": p, "section": s, "text": t, "also_on_pages": []}
    for i, (p, s, t) in enumerate([
        (3, "Products", "server microprocessors graphics processors"),
        (11, "Customers", "one customer accounted for 16% of net revenue"),
        (11, "Customers", "sales to this customer were gaming products"),
        (42, "Overview", "revenue increased in the data center segment"),
    ])
]
EMB = _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0.95, 0.31, 0], [0, 0, 0, 1]])
SECTIONS = [SectionMeta("D:s0", "Products", ["D:3:0"], "products"),
            SectionMeta("D:s1", "Customers", ["D:11:1", "D:11:2"], "customers"),
            SectionMeta("D:s2", "Overview", ["D:42:3"], "overview")]


class KeywordEmbedder:
    """Maps a text to the axis of the first keyword it contains."""

    def __init__(self):
        self.calls: list[str] = []

    def encode(self, texts):
        self.calls.extend(texts)
        axes = {"product": 0, "customer": 1, "gaming": 2, "revenue": 3}
        rows = []
        for t in texts:
            v = np.zeros(4, dtype=np.float32)
            v[next((a for k, a in axes.items() if k in t.lower()), 3)] = 1
            rows.append(v)
        return np.array(rows)


def _retriever():
    index = DocumentIndex(CHUNKS, EMB, SECTIONS, _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]))
    return MultiPathRetriever(index, KeywordEmbedder()), index


def test_only_the_configured_paths_run():
    retriever, _ = _retriever()

    result = retriever.search("Which customer accounted for revenue?", MprConfig(paths=("bm25",), expand=False, k_per_path=2))

    assert set(result.per_path) == {"bm25"}
    assert retriever.embedder.calls == []  # BM25 alone needs no embedding


def test_full_search_runs_four_paths_uses_the_given_hyde_text_and_expands():
    retriever, index = _retriever()
    config = MprConfig(paths=("dense", "bm25", "metadata", "hyde"), expand=True, k_per_path=1, k_sections=1)

    result = retriever.search("Which customer accounted for revenue?", config, hyde_text="A customer was 16% of revenue")

    assert set(result.per_path) == {"dense", "bm25", "metadata", "hyde"}
    assert "A customer was 16% of revenue" in retriever.embedder.calls
    ids = [index.chunks[i]["chunk_id"] for i in result.retrieved]
    assert "D:11:1" in ids and "D:11:2" in ids  # neighbour pulled in by expansion or metadata
    assert len(ids) == len(set(ids))


def test_configs_mirror_the_rows_of_the_paper_table_1():
    assert [c.name for c in CONFIGS] == [
        "Dense (FAISS)", "Dense + Expansion", "Dense + BM25", "Dense + BM25 + Metadata", "Dense + HyDE", "FinSage (all paths + Expansion)"
    ]
    assert CONFIGS[-1].config.paths == ("dense", "bm25", "metadata", "hyde") and CONFIGS[-1].config.expand


def test_cached_llm_outputs_with_an_empty_hyde_passage_are_generated_again():
    assert needs_generation(None)
    assert needs_generation({"subquestions": ["q"], "hyde": [""]})
    assert needs_generation({"subquestions": ["q", "r"], "hyde": ["text"]})
    assert not needs_generation({"subquestions": ["q"], "hyde": ["text"]})


def test_aggregate_reports_recall_precision_and_size():
    rows = [{"hit": True, "precision": 0.5, "retrieved": 10}, {"hit": False, "precision": 0.0, "retrieved": 20}]

    assert aggregate(rows) == {"questions": 2, "hits": 1, "recall": 0.5, "precision": 0.25, "avg_retrieved": 15.0}
