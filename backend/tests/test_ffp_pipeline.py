import hashlib
import json

import numpy as np

from finsage_replica.ffp.pipeline import chunk_and_dedup_all


def words(text: str) -> int:
    return len(text.split())


class FakeEmbedder:
    """Deterministic unit vectors: identical texts get identical vectors, others near-orthogonal."""

    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
            v = np.random.default_rng(seed).standard_normal(64)
            vectors.append(v / np.linalg.norm(v))
        return np.array(vectors, dtype=np.float32)


def _write_pages(pages_dir, doc, markdowns):
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages = [{"page_index": i, "markdown": md} for i, md in enumerate(markdowns)]
    (pages_dir / f"{doc}.json").write_text(json.dumps(pages), encoding="utf-8")


def test_writes_kept_chunks_with_inherited_pages_and_their_embeddings(tmp_path):
    table = " ".join(f"row{i}" for i in range(40))  # substantive, repeated on page 2
    _write_pages(tmp_path / "pages", "DOC", [table, "unique narrative text", table])

    stats = chunk_and_dedup_all(
        tmp_path / "pages", tmp_path, max_tokens=256, threshold=0.98,
        embedder=FakeEmbedder(), count_tokens=words, alias_min_tokens=32,
    )

    records = [json.loads(line) for line in (tmp_path / "chunks" / "DOC.jsonl").open(encoding="utf-8")]
    assert [(r["chunk_id"], r["also_on_pages"]) for r in records] == [("DOC:0:0", [2]), ("DOC:1:0", [])]
    embeddings = np.load(tmp_path / "embeddings" / "DOC.npy")
    assert embeddings.shape == (2, 64)
    assert embeddings.dtype == np.float16
    assert stats == {"documents": 1, "pages": 3, "chunks_before_dedup": 3, "chunks_after_dedup": 2}


def test_documents_already_processed_are_not_embedded_again(tmp_path):
    _write_pages(tmp_path / "pages", "DOC", ["some text"])
    embedder = FakeEmbedder()
    kwargs = dict(max_tokens=256, threshold=0.98, embedder=embedder, count_tokens=words, alias_min_tokens=32)

    chunk_and_dedup_all(tmp_path / "pages", tmp_path, **kwargs)
    chunk_and_dedup_all(tmp_path / "pages", tmp_path, **kwargs)

    assert embedder.calls == 1
