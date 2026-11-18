"""Claude as the experiment B judge (Anthropic Messages API)."""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from finsage_replica.evaluation.judge import JUDGE_INSTRUCTIONS, judge_prompt, parse_verdict

# US$ per million tokens (input, output); Anthropic first-party rates.
PRICES_PER_MILLION = {"claude-opus-5-5": (4.00, 20.00)}


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
        tokens_in, tokens_out = response.usage.input_tokens, response.usage.output_tokens
        price_in, price_out = PRICES_PER_MILLION[self.model]
        cost = (tokens_in * price_in + tokens_out * price_out) / 1_000_000
        if response.stop_reason == "refusal":
            return Grade("unparsed", "judge refused", response.model, tokens_in, tokens_out, cost)
        text = "".join(block.text for block in response.content if block.type == "text")
        verdict, reason = parse_verdict(text)
        return Grade(verdict, reason, response.model, tokens_in, tokens_out, cost)
