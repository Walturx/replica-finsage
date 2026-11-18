"""Experiment B pieces: the judge verdict parser, cited-page hit and the naive dense RAG baseline."""

import numpy as np

from finsage_replica.baseline import naive_answer
from finsage_replica.evaluation.judge import cited_page_hit, judge_prompt, parse_verdict
from finsage_replica.ports.llm import Completion


def test_parse_verdict_reads_json_inside_prose():
    text = 'Here is my grade:\n{"verdict": "correct", "reason": "Matches 16% of revenue."}'
    assert parse_verdict(text) == ("correct", "Matches 16% of revenue.")


def test_parse_verdict_accepts_partial_and_incorrect():
    assert parse_verdict('{"verdict": "partially_correct", "reason": "r"}')[0] == "partially_correct"
    assert parse_verdict('{"verdict": "incorrect", "reason": "r"}')[0] == "incorrect"


def test_parse_verdict_flags_unknown_or_broken_output():
    assert parse_verdict('{"verdict": "great", "reason": "r"}')[0] == "unparsed"
    assert parse_verdict("no json at all")[0] == "unparsed"


def test_judge_prompt_contains_question_reference_and_answer():
    prompt = judge_prompt("Q?", "REF", "ANS")
    assert "Q?" in prompt and "REF" in prompt and "ANS" in prompt


def test_cited_page_hit_is_none_without_citations():
    assert cited_page_hit([], [11]) is None
    assert cited_page_hit([11, 68], [11]) is True
    assert cited_page_hit([3], [11]) is False


class FakeEmbedder:
    def encode(self, texts):
        return np.ones((len(texts), 2), dtype=np.float32)


class FakeIndex:
    def __init__(self):
        self.chunks = [{"chunk_id": f"c{i}", "doc_name": "D", "page_index": i, "section": "S", "text": f"t{i}"}
                       for i in range(4)]

    def dense(self, query_vector, k):
        return [(2, 0.9), (0, 0.5)][:k]


class FakeLlm:
    model = "fake"

    def __init__(self):
        self.prompts = []

    def complete(self, instructions, prompt, max_output_tokens):
        self.prompts.append(prompt)
        return Completion(text="Answer [1].", tokens_in=10, tokens_out=3, model="fake", cost_usd=0.001)


def test_naive_answer_uses_raw_question_dense_top_k_and_cites():
    llm = FakeLlm()
    result = naive_answer("Q?", FakeIndex(), FakeEmbedder(), llm, k=2)
    assert [c["chunk_id"] for c in result.retrieved] == ["c2", "c0"]
    assert result.text == "Answer [1]."
    assert [c["page_index"] for c in result.cited] == [2]
    assert result.completion.cost_usd == 0.001
    assert "Q?" in llm.prompts[0] and "t2" in llm.prompts[0]
