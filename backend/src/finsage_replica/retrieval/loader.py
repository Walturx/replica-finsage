"""Build the DocumentIndex of one document from the FFP outputs on disk."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from finsage_replica.ports.text import Embedder
from finsage_replica.retrieval.index import DocumentIndex, SectionMeta


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_document_index(processed_dir: Path, doc: str, embedder: Embedder) -> DocumentIndex:
    """Chunks and their vectors from T2a, section summaries from T2b. Summary vectors are cached next to them."""
    processed_dir = Path(processed_dir)
    chunks = _jsonl(processed_dir / "chunks" / f"{doc}.jsonl")
    embeddings = np.load(processed_dir / "embeddings" / f"{doc}.npy").astype(np.float32)
    if len(chunks) != len(embeddings):
        raise ValueError(f"{doc}: {len(chunks)} chunks but {len(embeddings)} vectors; rerun the FFP pipeline")

    summaries_file = processed_dir / "summaries" / f"{doc}.jsonl"
    if not summaries_file.is_file():
        return DocumentIndex(chunks, embeddings)
    sections = [SectionMeta(r["section_id"], r["section"], r["chunk_ids"], r["summary"]) for r in _jsonl(summaries_file)]
    cache = summaries_file.with_suffix(".npy")
    vectors = np.load(cache).astype(np.float32) if cache.is_file() else None
    if vectors is None or len(vectors) != len(sections):
        vectors = embedder.encode([f"{s.section}. {s.summary}" for s in sections])
        np.save(cache, vectors.astype(np.float16))
    return DocumentIndex(chunks, embeddings, sections, vectors)
