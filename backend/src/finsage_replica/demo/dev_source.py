"""Development fixture for building the chatbot UI before the real pipeline exists.

It replays one fixed scenario for any question and marks every run as `source="dev"`.
The UI shows a development banner for these runs, and `RecordingWriter` refuses to
record them, so fixture output can never pass as a pipeline result in the demo.
The chunk texts are real excerpts from 3M_2018_10K (verified in T2a); the scores and
the answer are made up for layout purposes.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator

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
from finsage_replica.ports.pipeline import Turn

_CASHFLOW = "3M Company and Subsidiaries Consolidated Statement of Cash Flows"
_CAPEX_ROW = (
    "|(Millions)|2018|2017|2016|\n|---|---|---|---|\n"
    "|Purchases of property, plant and equipment (PP&E)|(1,577)|(1,373)|(1,420)|"
)
_CHUNKS = {
    "cashflow": ChunkRef(chunk_id="3M_2018_10K:59:3", doc_name="3M_2018_10K", page_index=59,
                         section=_CASHFLOW, snippet=_CAPEX_ROW, score=0.0),
    "mdna": ChunkRef(chunk_id="3M_2018_10K:45:2", doc_name="3M_2018_10K", page_index=45,
                     section="Financial Condition and Liquidity",
                     snippet="Purchases of property, plant and equipment (PP&E) ... investing activities", score=0.0),
    "segments": ChunkRef(chunk_id="3M_2018_10K:48:1", doc_name="3M_2018_10K", page_index=48,
                         section="Cash Flows from Investing Activities",
                         snippet="Purchases of property, plant and equipment (PP&E) (1,577)", score=0.0),
}
_ANSWER = (
    "Development fixture, not a pipeline answer. "
    "Example layout: 3M reported purchases of property, plant and equipment of $1,577 million in FY2018 [1]."
)


def _hit(key: str, score: float) -> ChunkRef:
    return _CHUNKS[key].model_copy(update={"score": score})


class DevSource:
    name = "dev"

    def __init__(self, delay_s: float = 0.35):
        self._delay = delay_s

    async def run(self, question: str, history: list[Turn]) -> AsyncIterator[Event]:
        run_id = f"dev-{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()

        def t() -> int:
            return int((time.perf_counter() - start) * 1000)

        async def pause(factor: float = 1.0) -> None:
            if self._delay:
                await asyncio.sleep(self._delay * factor)

        yield RunStarted(run_id=run_id, t_ms=t(), question=question, source="dev", model="dev-fixture")
        await pause()
        yield Rewrite(run_id=run_id, t_ms=t(), sub_questions=[question])
        for path, hits, hyde in [
            ("bm25", [_hit("cashflow", 12.4), _hit("segments", 10.9)], None),
            ("dense", [_hit("mdna", 0.71), _hit("cashflow", 0.66)], None),
            ("metadata", [_hit("cashflow", 0.74)], None),
            ("hyde", [_hit("cashflow", 0.81), _hit("segments", 0.77)],
             "3M's capital expenditures for fiscal 2018 were approximately $1.5 billion."),
        ]:
            await pause(0.6)
            yield Retrieval(run_id=run_id, t_ms=t(), sub_question=0, path=path, hits=hits, hyde_text=hyde)
        await pause()
        yield Rerank(run_id=run_id, t_ms=t(), sub_question=0,
                     top=[_hit("cashflow", 0.97), _hit("segments", 0.81), _hit("mdna", 0.44)])
        for word in _ANSWER.split(" "):
            await pause(0.08)
            yield AnswerDelta(run_id=run_id, t_ms=t(), text=word + " ")
        yield Citation(run_id=run_id, t_ms=t(), marker=1, chunk_id="3M_2018_10K:59:3",
                       doc_name="3M_2018_10K", page_index=59)
        yield Done(run_id=run_id, t_ms=t(), latency_ms=t(), stages_ms={}, tokens_in=0, tokens_out=0, cost_usd=0.0)
