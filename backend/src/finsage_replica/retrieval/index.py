"""The three indexes FinSage searches over one document (MPR): BM25, dense (FAISS) and section metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were what which with".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


@dataclass(frozen=True)
class SectionMeta:
    section_id: str
    section: str
    chunk_ids: list[str]
    summary: str


Scored = list[tuple[int, float]]  # (chunk index in reading order, score)


class DocumentIndex:
    def __init__(
        self,
        chunks: list[dict],
        embeddings: np.ndarray,
        sections: list[SectionMeta] | None = None,
        summary_embeddings: np.ndarray | None = None,
    ):
        self.chunks = chunks
        self.embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        self._position = {c["chunk_id"]: i for i, c in enumerate(chunks)}
        self._bm25 = BM25Okapi([tokenize(f"{c['section']} {c['text']}") for c in chunks])
        self._dense = faiss.IndexFlatIP(self.embeddings.shape[1])  # exact inner product on unit vectors = cosine
        self._dense.add(self.embeddings)
        self.sections = sections or []
        self._summaries = None
        if self.sections and summary_embeddings is not None:
            vectors = np.ascontiguousarray(summary_embeddings, dtype=np.float32)
            self._summaries = faiss.IndexFlatIP(vectors.shape[1])
            self._summaries.add(vectors)

    def position(self, chunk_id: str) -> int:
        return self._position[chunk_id]

    def bm25(self, query: str, k: int) -> Scored:
        scores = self._bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]

    def dense(self, query_vector: np.ndarray, k: int) -> Scored:
        return self._search(self._dense, query_vector, k)

    def metadata(self, query_vector: np.ndarray, k_sections: int) -> Scored:
        """Chunks of the sections whose summaries best match the query, in reading order."""
        if self._summaries is None:
            return []
        hits: Scored = []
        for section_index, score in self._search(self._summaries, query_vector, k_sections):
            for chunk_id in self.sections[section_index].chunk_ids:
                if chunk_id in self._position:
                    hits.append((self._position[chunk_id], score))
        return hits

    @staticmethod
    def _search(index: faiss.Index, query_vector: np.ndarray, k: int) -> Scored:
        query = np.ascontiguousarray(query_vector, dtype=np.float32).reshape(1, -1)
        scores, ids = index.search(query, min(k, index.ntotal))
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
