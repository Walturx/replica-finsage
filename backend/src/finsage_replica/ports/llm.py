"""Port for text generation. FinSage modules depend on this, never on a provider SDK."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    cost_usd: float


@dataclass(frozen=True)
class TextDelta:
    text: str


class LanguageModel(Protocol):
    model: str

    def complete(self, instructions: str, prompt: str, max_output_tokens: int = 512) -> Completion: ...

    def stream(self, instructions: str, prompt: str, max_output_tokens: int = 1500) -> Iterator[TextDelta | Completion]:
        """Text deltas as they arrive, then one final Completion with the full text and usage."""
        ...
