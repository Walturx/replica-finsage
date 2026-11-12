"""Port for text generation. FinSage modules depend on this, never on a provider SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    model: str
    cost_usd: float


class LanguageModel(Protocol):
    model: str

    def complete(self, instructions: str, prompt: str, max_output_tokens: int = 512) -> Completion: ...
