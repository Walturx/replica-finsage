import asyncio

import numpy as np

from finsage_replica.adapters.llm_reranker import LlmReranker, parse_scores
from finsage_replica.evaluation.metrics import first_evidence_rank, hits_at_k
from finsage_replica.ports.llm import Completion


class FakeLLM:
    model = "fake-llm"

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def complete(self, instructions, prompt, max_output_tokens=512):
        self.prompts.append(prompt)
        return Completion(self.reply, 300, 40, self.model, 0.0003)


def test_scores_come_from_the_model_json_scaled_to_zero_one():
    llm = FakeLLM('{"1": 2, "2": 10, "3": 0}')
    reranker = LlmReranker(llm)

    scores = reranker.score("Did AMD report customer concentration?", ["history", "one customer was 16%", "board"])

    assert scores == [0.2, 1.0, 0.0]
    assert "[2] one customer was 16%" in llm.prompts[0]
    assert "Did AMD report customer concentration?" in llm.prompts[0]


def test_usage_is_reported_once_per_call():
    reranker = LlmReranker(FakeLLM('{"1": 5}'))
    reranker.score("q", ["p"])

    assert reranker.take_usage().cost_usd == 0.0003
    assert reranker.take_usage() is None


def test_parse_scores_tolerates_fences_missing_ids_and_out_of_range_values():
    assert parse_scores('```json\n{"1": 7, "3": 15}\n```', 3) == [0.7, 0.0, 1.0]
    assert parse_scores("no json here", 2) == [0.0, 0.0]
    assert parse_scores('{"x": 5, "2": -3}', 2) == [0.0, 0.0]


def test_long_passages_are_truncated_in_the_prompt():
    llm = FakeLLM('{"1": 1}')
    LlmReranker(llm, max_passage_chars=10).score("q", ["a" * 50])

    assert "a" * 11 not in llm.prompts[0]


def test_rank_metrics_find_the_first_evidence_chunk():
    chunks = [{"page_index": 4}, {"page_index": 11}, {"page_index": 11, "also_on_pages": []}]

    assert first_evidence_rank(chunks, [11]) == 2
    assert first_evidence_rank(chunks, [99]) is None
    assert hits_at_k(chunks, [11], k=1) is False
    assert hits_at_k(chunks, [11], k=2) is True


def test_pipeline_adds_the_reranker_cost_to_the_run():
    from finsage_replica.pipeline import FinSagePipeline
    from finsage_replica.ports.llm import TextDelta
    from finsage_replica.retrieval.index import DocumentIndex

    chunks = [{"chunk_id": "D:1:0", "doc_name": "D", "page_index": 1, "section": "S", "text": "customer revenue",
               "n_tokens": 2, "also_on_pages": []}]
    index = DocumentIndex(chunks, np.array([[1.0, 0.0]], dtype=np.float32))

    class Embedder:
        def encode(self, texts):
            return np.array([[1.0, 0.0]] * len(texts), dtype=np.float32)

    class Generator:
        model = "gen"

        def complete(self, instructions, prompt, max_output_tokens=512):
            return Completion('["q"]' if "User question:" in prompt else "hypothetical", 1, 1, "gen", 0.0)

        def stream(self, instructions, prompt, max_output_tokens=1500):
            yield TextDelta("ok [1]")
            yield Completion("ok [1]", 1, 1, "gen", 0.0)

    reranker = LlmReranker(FakeLLM('{"1": 9}'))
    pipeline = FinSagePipeline(index, Embedder(), reranker, Generator(), company="D", doc_title="D")

    async def run():
        return [e async for e in pipeline.run("q", [])]

    done = asyncio.run(run())[-1]
    assert done.cost_usd == 0.0003
    assert done.tokens_in == 300 + 3  # reranker call plus rewrite, HyDE and answer calls of the generator
