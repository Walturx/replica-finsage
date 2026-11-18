"""Multi-path retrieval (FinSage MPR) for one sub-question: run the configured paths, merge, expand."""

from __future__ import annotations

from dataclasses import dataclass, field

from finsage_replica.ports.text import Embedder
from finsage_replica.retrieval.expansion import expand_bundles
from finsage_replica.retrieval.index import DocumentIndex, Scored
from finsage_replica.retrieval.merge import Candidate, merge_paths

ALL_PATHS = ("dense", "bm25", "metadata", "hyde")


@dataclass(frozen=True)
class MprConfig:
    paths: tuple[str, ...] = ALL_PATHS
    expand: bool = True
    k_per_path: int = 10  # candidates per retriever (R=10 in the official repo's reranking results)
    k_sections: int = 2  # metadata path: sections whose chunks are returned
    tau: float = 0.85  # bundling similarity threshold, from the paper
    max_bundle: int = 5  # bundling size limit K, from the paper


@dataclass
class SubQueryResult:
    subquestion: str
    per_path: dict[str, Scored]
    candidates: list[Candidate]
    expanded: list[int]
    hyde_text: str | None = None
    retrieved: list[int] = field(default_factory=list)  # candidates then expansion, no duplicates


class MultiPathRetriever:
    def __init__(self, index: DocumentIndex, embedder: Embedder):
        self.index = index
        self.embedder = embedder

    def search(self, subquestion: str, config: MprConfig, hyde_text: str | None = None) -> SubQueryResult:
        unknown = set(config.paths) - set(ALL_PATHS)
        if unknown:
            raise ValueError(f"unknown retrieval paths: {sorted(unknown)}")
        if "hyde" in config.paths and not hyde_text:
            raise ValueError("the hyde path needs a hypothetical document")

        texts = []
        if {"dense", "metadata"} & set(config.paths):
            texts.append(subquestion)
        if "hyde" in config.paths:
            texts.append(hyde_text)
        vectors = dict(zip(texts, self.embedder.encode(texts))) if texts else {}

        per_path: dict[str, Scored] = {}
        if "dense" in config.paths:
            per_path["dense"] = self.index.dense(vectors[subquestion], config.k_per_path)
        if "bm25" in config.paths:
            per_path["bm25"] = self.index.bm25(subquestion, config.k_per_path)
        if "metadata" in config.paths:
            per_path["metadata"] = self.index.metadata(vectors[subquestion], config.k_sections)
        if "hyde" in config.paths:
            per_path["hyde"] = self.index.dense(vectors[hyde_text], config.k_per_path)

        candidates = merge_paths(per_path)
        seeds = [c.index for c in candidates]
        expanded = expand_bundles(seeds, self.index.embeddings, config.tau, config.max_bundle) if config.expand else []
        return SubQueryResult(subquestion, per_path, candidates, expanded, hyde_text, seeds + expanded)
