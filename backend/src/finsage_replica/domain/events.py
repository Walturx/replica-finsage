"""Pipeline event contract.

One pipeline run emits these events in order. The chatbot, the evaluation and the demo
recorder all consume the same stream, so the demo shows what was evaluated.
`contracts/pipeline-events.schema.json` is generated from these models:

    uv run python -m finsage_replica.domain.events
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

Source = Literal["live", "recording", "dev"]
RetrievalPath = Literal["bm25", "dense", "metadata", "hyde"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _EventBase(_Strict):
    run_id: str
    t_ms: int = Field(ge=0, description="Milliseconds since the run started.")


class ChunkRef(_Strict):
    chunk_id: str
    doc_name: str
    page_index: int = Field(ge=0, description="0-based, like FinanceBench evidence_page_num.")
    section: str
    snippet: str
    score: float


class RunStarted(_EventBase):
    type: Literal["run_started"] = "run_started"
    question: str
    source: Source = Field(description="live: real pipeline. recording: replay of a live run. dev: UI fixture.")
    model: str
    recorded_at: str | None = None


class Rewrite(_EventBase):
    type: Literal["rewrite"] = "rewrite"
    sub_questions: list[str]


class Retrieval(_EventBase):
    type: Literal["retrieval"] = "retrieval"
    sub_question: int = Field(ge=0)
    path: RetrievalPath
    hits: list[ChunkRef]
    hyde_text: str | None = None


class Rerank(_EventBase):
    type: Literal["rerank"] = "rerank"
    sub_question: int = Field(ge=0)
    top: list[ChunkRef]


class AnswerDelta(_EventBase):
    type: Literal["answer_delta"] = "answer_delta"
    text: str


class Citation(_EventBase):
    type: Literal["citation"] = "citation"
    marker: int = Field(ge=1, description="The [n] marker used in the answer text.")
    chunk_id: str
    doc_name: str
    page_index: int = Field(ge=0)


class Done(_EventBase):
    type: Literal["done"] = "done"
    latency_ms: int = Field(ge=0)
    stages_ms: dict[str, int]
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class RunError(_EventBase):
    type: Literal["error"] = "error"
    message: str


Event = Annotated[
    Union[RunStarted, Rewrite, Retrieval, Rerank, AnswerDelta, Citation, Done, RunError],
    Field(discriminator="type"),
]

EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
CONTRACT_PATH = Path(__file__).resolve().parents[4] / "contracts" / "pipeline-events.schema.json"


def main() -> None:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(json.dumps(EVENT_ADAPTER.json_schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CONTRACT_PATH}")


if __name__ == "__main__":
    main()
