from types import SimpleNamespace

from finsage_replica.adapters.openai_llm import OpenAILanguageModel
from finsage_replica.answering.generate import answer_prompt, build_sources, extract_citations, merge_prompt
from finsage_replica.ports.llm import Completion, TextDelta
from finsage_replica.reranking.drr import rerank


def _chunk(cid, page, text="t"):
    return {"chunk_id": cid, "doc_name": "D", "page_index": page, "section": "S", "text": text, "also_on_pages": []}


class FakeReranker:
    def score(self, query, passages):
        return [float(len(p)) for p in passages]  # longer passage = more relevant, for the test


def test_rerank_keeps_the_top_k_by_score_in_order():
    chunks = [_chunk("a", 1, "xx"), _chunk("b", 2, "xxxx"), _chunk("c", 3, "x"), _chunk("d", 4, "xxx")]

    top = rerank("q", chunks, FakeReranker(), top_k=2)

    # The reranker sees "section\ntext", so the fake's length score includes the 2-char "S\n" prefix.
    assert [(c["chunk_id"], s) for c, s in top] == [("b", 6.0), ("d", 5.0)]
    assert rerank("q", [], FakeReranker(), top_k=5) == []


def test_sources_are_numbered_once_across_sub_questions():
    a, b, c = _chunk("a", 1), _chunk("b", 2), _chunk("c", 3)

    sources = build_sources([[a, b], [b, c]])

    assert [(s.marker, s.chunk["chunk_id"]) for s in sources] == [(1, "a"), (2, "b"), (3, "c")]


def test_answer_prompt_lists_numbered_sources_with_their_pages():
    sources = build_sources([[_chunk("a", 11, "One customer accounted for 16%")]])

    prompt = answer_prompt("Did AMD report customer concentration?", sources)

    assert "[1]" in prompt and "page 12" in prompt and "One customer accounted for 16%" in prompt
    assert "Did AMD report customer concentration?" in prompt


def test_merge_prompt_carries_the_partial_answers_and_the_sources():
    sources = build_sources([[_chunk("a", 1)], [_chunk("b", 2)]])

    prompt = merge_prompt("Q?", ["q1", "q2"], ["answer one [1]", "answer two [2]"], sources)

    assert "answer one [1]" in prompt and "answer two [2]" in prompt and "[2]" in prompt


def test_citations_follow_first_use_and_ignore_unknown_markers():
    sources = build_sources([[_chunk("a", 1), _chunk("b", 2)]])

    cited = extract_citations("B is true [2]. A too [1][2]. Not real [9].", sources)

    assert [(s.marker, s.chunk["chunk_id"]) for s in cited] == [(2, "b"), (1, "a")]


class FakeStreamClient:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        usage = SimpleNamespace(input_tokens=100, output_tokens=20)
        return iter([
            SimpleNamespace(type="response.created"),
            SimpleNamespace(type="response.output_text.delta", delta="Hello "),
            SimpleNamespace(type="response.output_text.delta", delta="world"),
            SimpleNamespace(type="response.completed", response=SimpleNamespace(usage=usage)),
        ])


def test_openai_stream_yields_text_deltas_then_the_completion():
    responses = FakeStreamClient()
    llm = OpenAILanguageModel("gpt-6-luna", client=SimpleNamespace(responses=responses))

    items = list(llm.stream("instr", "prompt", max_output_tokens=900))

    assert items[:2] == [TextDelta("Hello "), TextDelta("world")]
    final = items[-1]
    assert isinstance(final, Completion)
    assert (final.text, final.tokens_in, final.tokens_out) == ("Hello world", 100, 20)
    assert responses.kwargs["stream"] is True and responses.kwargs["max_output_tokens"] == 900
