import asyncio

import numpy as np
from pydantic import TypeAdapter

from finsage_replica.domain.events import Event
from finsage_replica.pipeline import FinSagePipeline
from finsage_replica.ports.llm import Completion, TextDelta
from finsage_replica.ports.pipeline import Turn
from finsage_replica.retrieval.index import DocumentIndex, SectionMeta

EVENTS = TypeAdapter(Event)


def _unit(rows):
    m = np.array(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


CHUNKS = [
    {"chunk_id": f"D:{p}:{i}", "doc_name": "D", "page_index": p, "section": s, "text": t, "n_tokens": 5, "also_on_pages": []}
    for i, (p, s, t) in enumerate([
        (3, "Products", "server microprocessors graphics processors"),
        (11, "Customers", "one customer accounted for 16% of net revenue"),
        (42, "Overview", "revenue increased in the data center segment"),
    ])
]
INDEX = DocumentIndex(CHUNKS, _unit([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
                      [SectionMeta("D:s0", "Products", ["D:3:0"], "products"),
                       SectionMeta("D:s1", "Customers", ["D:11:1"], "customers"),
                       SectionMeta("D:s2", "Overview", ["D:42:2"], "overview")],
                      _unit([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))


class Embedder:
    def encode(self, texts):
        return _unit([[0.1, 1, 0.1] if "customer" in t.lower() else [0.1, 0.1, 1] for t in texts])


class Reranker:
    def score(self, query, passages):
        return [0.9 if "customer" in p else 0.2 for p in passages]


class FakeLLM:
    model = "fake-llm"

    def __init__(self, subquestions):
        self.subquestions = subquestions
        self.prompts: list[str] = []

    def complete(self, instructions, prompt, max_output_tokens=512):
        self.prompts.append(prompt)
        if "User question:" in prompt:
            import json
            text = json.dumps(self.subquestions)
        elif prompt.startswith("Company:"):
            text = "One customer represented a large share of AMD revenue."
        else:
            text = "Partial answer [1]."
        return Completion(text, 10, 5, self.model, 0.001)

    def stream(self, instructions, prompt, max_output_tokens=1500):
        self.prompts.append(prompt)
        yield TextDelta("Yes, one customer was 16% of revenue ")
        yield TextDelta("[1].")
        yield Completion("Yes, one customer was 16% of revenue [1].", 50, 12, self.model, 0.002)


def _run(pipeline, question, history=None):
    async def collect():
        return [e async for e in pipeline.run(question, history or [])]
    return asyncio.run(collect())


def _pipeline(subquestions):
    llm = FakeLLM(subquestions)
    return FinSagePipeline(INDEX, Embedder(), Reranker(), llm, company="AMD", doc_title="AMD 2022 10K", top_k=2), llm


def test_a_live_run_emits_every_stage_in_order_and_cites_the_reranked_chunk():
    pipeline, _ = _pipeline(["Did AMD report customer concentration in FY2022?"])

    events = _run(pipeline, "Did AMD report customer concentration?")

    for e in events:
        EVENTS.validate_python(e.model_dump())
    types = [e.type for e in events]
    assert types[0] == "run_started" and types[1] == "rewrite" and types[-1] == "done"
    assert [e.path for e in events if e.type == "retrieval"] == ["dense", "bm25", "metadata", "hyde"]
    rerank = next(e for e in events if e.type == "rerank")
    assert rerank.top[0].chunk_id == "D:11:1" and len(rerank.top) == 2
    assert "".join(e.text for e in events if e.type == "answer_delta") == "Yes, one customer was 16% of revenue [1]."
    citation = next(e for e in events if e.type == "citation")
    assert (citation.marker, citation.chunk_id, citation.page_index) == (1, "D:11:1", 11)
    assert events[0].source == "live" and events[0].model == "fake-llm"
    done = events[-1]
    assert done.cost_usd > 0 and done.tokens_in > 0
    assert set(done.stages_ms) == {"rewrite", "hyde", "retrieval", "rerank", "answer"}


def test_several_sub_questions_are_answered_separately_then_merged():
    pipeline, llm = _pipeline(["Q1 about customer?", "Q2 about revenue?"])

    events = _run(pipeline, "Two things?")

    assert len([e for e in events if e.type == "rerank"]) == 2
    partial_prompts = [p for p in llm.prompts if p.startswith("Sources:") and "Partial answers" not in p]
    assert len(partial_prompts) == 2
    assert any("Partial answers" in p for p in llm.prompts)


def test_history_reaches_the_rewriting_step():
    pipeline, llm = _pipeline(["What was AMD revenue in FY2021?"])

    _run(pipeline, "And the year before?", [Turn(role="user", content="AMD revenue FY2022?"),
                                           Turn(role="assistant", content="$23.6 billion")])

    assert "AMD revenue FY2022?" in llm.prompts[0] and "$23.6 billion" in llm.prompts[0]
