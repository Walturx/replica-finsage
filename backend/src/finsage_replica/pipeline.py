"""The live FinSage pipeline for one chat turn: rewrite, MPR, DRR, answer, merge.

It emits the pipeline event contract (domain/events.py), so the chatbot, the evaluation and the
demo recorder all consume the same stream. Blocking work (embeddings, reranking, LLM calls) runs in
worker threads so the event loop keeps streaming.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator

from starlette.concurrency import iterate_in_threadpool

from finsage_replica.answering.generate import (
    ANSWER_INSTRUCTIONS,
    MERGE_INSTRUCTIONS,
    answer_prompt,
    build_sources,
    extract_citations,
    merge_prompt,
)
from finsage_replica.domain.events import (
    AnswerDelta,
    ChunkRef,
    Citation,
    Done,
    Event,
    Rerank,
    Retrieval,
    Rewrite,
    RunStarted,
)
from finsage_replica.ports.llm import Completion, LanguageModel, TextDelta
from finsage_replica.ports.pipeline import Turn
from finsage_replica.ports.text import Embedder, Reranker, ReportsUsage
from finsage_replica.reranking.drr import rerank
from finsage_replica.retrieval.hyde import hypothetical_document
from finsage_replica.retrieval.index import DocumentIndex
from finsage_replica.retrieval.mpr import ALL_PATHS, MprConfig, MultiPathRetriever
from finsage_replica.retrieval.rewrite import rewrite_question

SNIPPET_CHARS = 400
SHOWN_PER_PATH = 10


class FinSagePipeline:
    name = "live"

    def __init__(self, index: DocumentIndex, embedder: Embedder, reranker: Reranker, llm: LanguageModel,
                 company: str, doc_title: str, config: MprConfig | None = None, top_k: int = 5):
        self.index = index
        self.retriever = MultiPathRetriever(index, embedder)
        self.reranker = reranker
        self.llm = llm
        self.company = company
        self.doc_title = doc_title
        self.config = config or MprConfig()
        self.top_k = top_k

    def _ref(self, chunk: dict, score: float) -> ChunkRef:
        return ChunkRef(chunk_id=chunk["chunk_id"], doc_name=chunk["doc_name"], page_index=chunk["page_index"],
                        section=chunk["section"], snippet=chunk["text"][:SNIPPET_CHARS], score=round(float(score), 4))

    async def run(self, question: str, history: list[Turn]) -> AsyncIterator[Event]:
        run_id = f"live-{uuid.uuid4().hex[:10]}"
        start = time.perf_counter()
        stages = {name: 0 for name in ("rewrite", "hyde", "retrieval", "rerank", "answer")}
        usage = {"in": 0, "out": 0, "cost": 0.0}

        def t() -> int:
            return int((time.perf_counter() - start) * 1000)

        def account(completion: Completion) -> None:
            usage["in"] += completion.tokens_in
            usage["out"] += completion.tokens_out
            usage["cost"] += completion.cost_usd

        async def timed(stage: str, fn, *args):
            began = time.perf_counter()
            result = await asyncio.to_thread(fn, *args)
            stages[stage] += int((time.perf_counter() - began) * 1000)
            return result

        yield RunStarted(run_id=run_id, t_ms=t(), question=question, source="live", model=self.llm.model)

        turns = [(turn.role, turn.content) for turn in history]
        subquestions, completion = await timed("rewrite", rewrite_question, self.llm, question, self.company,
                                               self.doc_title, turns)
        account(completion)
        yield Rewrite(run_id=run_id, t_ms=t(), sub_questions=subquestions)

        tops: list[list[dict]] = []
        for i, sub in enumerate(subquestions):
            hyde = await timed("hyde", hypothetical_document, self.llm, sub, self.company, self.doc_title)
            account(hyde)
            config = self.config
            if not hyde.text and "hyde" in config.paths:  # an empty passage cannot be searched; run the other paths
                config = MprConfig(**{**config.__dict__, "paths": tuple(p for p in config.paths if p != "hyde")})
            result = await timed("retrieval", self.retriever.search, sub, config, hyde.text or None)
            for path in ALL_PATHS:
                if path in result.per_path:
                    hits = [self._ref(self.index.chunks[j], s) for j, s in result.per_path[path][:SHOWN_PER_PATH]]
                    yield Retrieval(run_id=run_id, t_ms=t(), sub_question=i, path=path, hits=hits,
                                    hyde_text=hyde.text if path == "hyde" else None)
            candidates = [self.index.chunks[j] for j in result.retrieved]
            ranked = await timed("rerank", rerank, sub, candidates, self.reranker, self.top_k)
            if isinstance(self.reranker, ReportsUsage):
                rerank_usage = self.reranker.take_usage()
                if rerank_usage:
                    account(rerank_usage)
            tops.append([chunk for chunk, _ in ranked])
            yield Rerank(run_id=run_id, t_ms=t(), sub_question=i, top=[self._ref(c, s) for c, s in ranked])

        sources = build_sources(tops)
        if len(subquestions) == 1:
            prompt, instructions = answer_prompt(question, sources), ANSWER_INSTRUCTIONS
        else:
            partials = []
            for sub, top in zip(subquestions, tops):
                own = [s for s in sources if s.chunk in top]
                partial = await timed("answer", self.llm.complete, ANSWER_INSTRUCTIONS, answer_prompt(sub, own), 1500)
                account(partial)
                partials.append(partial.text)
            prompt, instructions = merge_prompt(question, subquestions, partials, sources), MERGE_INSTRUCTIONS

        began = time.perf_counter()
        final_text = ""
        async for item in iterate_in_threadpool(self.llm.stream(instructions, prompt, 1500)):
            if isinstance(item, TextDelta):
                yield AnswerDelta(run_id=run_id, t_ms=t(), text=item.text)
            else:
                account(item)
                final_text = item.text
        stages["answer"] += int((time.perf_counter() - began) * 1000)

        for source in extract_citations(final_text, sources):
            yield Citation(run_id=run_id, t_ms=t(), marker=source.marker, chunk_id=source.chunk["chunk_id"],
                           doc_name=source.chunk["doc_name"], page_index=source.chunk["page_index"])
        yield Done(run_id=run_id, t_ms=t(), latency_ms=t(), stages_ms=stages, tokens_in=usage["in"],
                   tokens_out=usage["out"], cost_usd=round(usage["cost"], 6))
