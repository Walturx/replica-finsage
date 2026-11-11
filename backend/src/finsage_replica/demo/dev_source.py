"""Development fixture for building the chatbot UI before the real pipeline exists.

It replays one fixed scenario for any question and marks every run as `source="dev"`.
The UI shows a development banner for these runs, and `RecordingWriter` refuses to
record them, so fixture output can never pass as a pipeline result in the demo.
The chunk texts are real excerpts from AMD_2022_10K (the default scope, verified in T2a); the scores and
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

_CHUNKS = {
    "concentration": ChunkRef(
        chunk_id="AMD_2022_10K:11:0", doc_name="AMD_2022_10K", page_index=11, section="Customers",
        snippet="One customer accounted for 16% of our consolidated net revenue for the year ended December 31, 2022.",
        score=0.0,
    ),
    "oem": ChunkRef(
        chunk_id="AMD_2022_10K:11:1", doc_name="AMD_2022_10K", page_index=11,
        section="Original Equipment Manufacturers",
        snippet="We focus on three types of OEM partners: multi-nationals, selected regional accounts and selected "
        "global and local system integrators.",
        score=0.0,
    ),
    "segments": ChunkRef(
        chunk_id="AMD_2022_10K:47:2", doc_name="AMD_2022_10K", page_index=47, section="Results of Operations",
        snippet="|Net revenue:|||\n|Data Center|$ 6,043|$ 3,694|\n|Client|6,201|6,887|\n|Gaming|6,805|5,607|",
        score=0.0,
    ),
}
_ANSWER = (
    "Development fixture, not a pipeline answer. "
    "Example layout: AMD reported that one customer accounted for 16% of its consolidated net revenue in FY2022 [1]."
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
            ("bm25", [_hit("concentration", 11.8), _hit("oem", 7.2)], None),
            ("dense", [_hit("concentration", 0.69), _hit("segments", 0.52)], None),
            ("metadata", [_hit("concentration", 0.71), _hit("oem", 0.64)], None),
            ("hyde", [_hit("concentration", 0.83)],
             "In fiscal 2022 one large customer represented a significant share of AMD's net revenue."),
        ]:
            await pause(0.6)
            yield Retrieval(run_id=run_id, t_ms=t(), sub_question=0, path=path, hits=hits, hyde_text=hyde)
        await pause()
        yield Rerank(run_id=run_id, t_ms=t(), sub_question=0,
                     top=[_hit("concentration", 0.96), _hit("oem", 0.58), _hit("segments", 0.21)])
        for word in _ANSWER.split(" "):
            await pause(0.08)
            yield AnswerDelta(run_id=run_id, t_ms=t(), text=word + " ")
        yield Citation(run_id=run_id, t_ms=t(), marker=1, chunk_id="AMD_2022_10K:11:0",
                       doc_name="AMD_2022_10K", page_index=11)
        yield Done(run_id=run_id, t_ms=t(), latency_ms=t(), stages_ms={}, tokens_in=0, tokens_out=0, cost_usd=0.0)
