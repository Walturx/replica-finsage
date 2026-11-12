from types import SimpleNamespace

import pytest

from finsage_replica.adapters.openai_llm import OpenAILanguageModel, cost_usd


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text="  A summary.  ",
            usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
        )


def test_complete_sends_the_request_and_reports_tokens_and_cost():
    responses = FakeResponses()
    llm = OpenAILanguageModel(model="gpt-6-luna", client=SimpleNamespace(responses=responses))

    result = llm.complete("Be brief.", "Summarize this.", max_output_tokens=300)

    assert result.text == "A summary."
    assert (result.tokens_in, result.tokens_out, result.model) == (1000, 200, "gpt-6-luna")
    assert result.cost_usd == pytest.approx(1000 * 0.10 / 1e6 + 200 * 0.50 / 1e6)
    sent = responses.calls[0]
    assert sent["model"] == "gpt-6-luna"
    assert sent["instructions"] == "Be brief."
    assert sent["input"] == "Summarize this."
    assert sent["max_output_tokens"] == 300
    assert sent["store"] is False


def test_cost_uses_the_official_price_table():
    assert cost_usd("gpt-6-luna", 1_000_000, 1_000_000) == pytest.approx(0.60)
    assert cost_usd("gpt-6.1-terra", 1_000_000, 0) == pytest.approx(1.00)


def test_unknown_models_are_rejected_instead_of_reporting_zero_cost():
    with pytest.raises(KeyError, match="price"):
        cost_usd("some-new-model", 10, 10)
