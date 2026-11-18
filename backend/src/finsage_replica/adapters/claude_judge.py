"""Claude as the experiment B judge (Anthropic Messages API)."""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from finsage_replica.evaluation.judge import JUDGE_INSTRUCTIONS, judge_prompt, parse_verdict

# US$ per million tokens (input, output); Anthropic first-party rates.
PRICES_PER_MILLION = {"claude-opus-5-5": (4.00, 20.00)}
CACHE_WRITE_FACTOR, CACHE_READ_FACTOR = 1.25, 0.1  # relative to the input price


def judge_cost(
    model: str, input_tokens: int, cache_creation_tokens: int, cache_read_tokens: int, output_tokens: int
) -> float:
    """US$ for one call; prompt tokens may be billed as uncached input, cache writes or cache reads."""
    price_in, price_out = PRICES_PER_MILLION[model]
    prompt = input_tokens + cache_creation_tokens * CACHE_WRITE_FACTOR + cache_read_tokens * CACHE_READ_FACTOR
    return (prompt * price_in + output_tokens * price_out) / 1_000_000


@dataclass
class Grade:
    verdict: str
    reason: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float


class ClaudeJudge:
    def __init__(self, model: str = "claude-opus-5-5", effort: str = "medium"):
        if model not in PRICES_PER_MILLION:
            raise KeyError(f"no price for {model}")
        self.model = model
        self.effort = effort
        self._client = anthropic.Anthropic()

    def grade(self, question: str, reference: str, answer: str) -> Grade:
        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": self.effort},
            system=JUDGE_INSTRUCTIONS,
            messages=[{"role": "user", "content": judge_prompt(question, reference, answer)}],
        )
        usage = response.usage
        cache_write = usage.cache_creation_input_tokens or 0
        cache_read = usage.cache_read_input_tokens or 0
        tokens_in = usage.input_tokens + cache_write + cache_read
        tokens_out = usage.output_tokens
        cost = judge_cost(self.model, usage.input_tokens, cache_write, cache_read, tokens_out)
        if response.stop_reason == "refusal":
            return Grade("unparsed", "judge refused", response.model, tokens_in, tokens_out, cost)
        text = "".join(block.text for block in response.content if block.type == "text")
        verdict, reason = parse_verdict(text)
        return Grade(verdict, reason, response.model, tokens_in, tokens_out, cost)
