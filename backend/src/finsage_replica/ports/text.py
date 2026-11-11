"""Ports for text processing. The pipeline depends on these, never on a concrete model."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from finsage_replica.domain.documents import Page


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray:
        """L2-normalized float32 vectors, one row per text, in input order."""
        ...


class TokenCounter(Protocol):
    def __call__(self, text: str) -> int: ...


class PdfParser(Protocol):
    def parse(self, path: Path) -> list[Page]:
        """Markdown per page with 0-based page indexes."""
        ...
