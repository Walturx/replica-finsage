"""Ports for text processing. The pipeline depends on these, never on a concrete model."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from finsage_replica.domain.documents import Page
from finsage_replica.ports.llm import Completion


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray:
        """L2-normalized float32 vectors, one row per text, in input order."""
        ...


class TokenCounter(Protocol):
    def __call__(self, text: str) -> int: ...


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]:
        """Relevance of each passage to the query, higher is more relevant, in input order."""
        ...


@runtime_checkable
class ReportsUsage(Protocol):
    """Implemented by adapters that call a paid model, so the pipeline can account for their cost."""

    def take_usage(self) -> Completion | None: ...


class PdfParser(Protocol):
    def parse(self, path: Path) -> list[Page]:
        """Markdown per page with 0-based page indexes."""
        ...
