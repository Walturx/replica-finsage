"""LanguageModel adapter for the OpenAI Responses API."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from finsage_replica.ports.llm import Completion, TextDelta

# US$ per 1M tokens (input, output), standard tier, from developers.openai.com/api/docs/pricing on 2026-11-11.
# Cached-input discounts are ignored, so reported costs are an upper bound.
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-6.1-terra": (1.00, 5.00),
}


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    if model not in PRICES_PER_MILLION:
        raise KeyError(f"no price for model {model!r}; add it to PRICES_PER_MILLION before using it")
    price_in, price_out = PRICES_PER_MILLION[model]
    return tokens_in * price_in / 1e6 + tokens_out * price_out / 1e6


class OpenAILanguageModel:
    def __init__(self, model: str = "gpt-6-luna", client: Any = None):
        cost_usd(model, 0, 0)  # fail fast on a model without a known price
        if client is None:
            from openai import OpenAI

            client = OpenAI()  # reads OPENAI_API_KEY from the environment
        self.model = model
        self._client = client

    def complete(self, instructions: str, prompt: str, max_output_tokens: int = 512) -> Completion:
        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=max_output_tokens,
            store=False,
        )
        tokens_in, tokens_out = response.usage.input_tokens, response.usage.output_tokens
        return Completion(
            text=(response.output_text or "").strip(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
            cost_usd=cost_usd(self.model, tokens_in, tokens_out),
        )

    def stream(self, instructions: str, prompt: str, max_output_tokens: int = 1500) -> Iterator[TextDelta | Completion]:
        events = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=max_output_tokens,
            store=False,
            stream=True,
        )
        parts: list[str] = []
        tokens_in = tokens_out = 0
        for event in events:
            if event.type == "response.output_text.delta":
                parts.append(event.delta)
                yield TextDelta(event.delta)
            elif event.type in ("response.completed", "response.incomplete"):
                tokens_in, tokens_out = event.response.usage.input_tokens, event.response.usage.output_tokens
        yield Completion(
            text="".join(parts).strip(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
            cost_usd=cost_usd(self.model, tokens_in, tokens_out),
        )
