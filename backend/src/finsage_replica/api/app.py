"""FastAPI adapter for the chatbot. It streams pipeline events as Server-Sent Events."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from finsage_replica.corpus.scope import DocumentScope
from finsage_replica.demo.recording import RecordingSource, RecordingWriter, list_recordings, recording_path
from finsage_replica.domain.events import Event, RunError, RunStarted
from finsage_replica.evaluation.judge_tab import judge_overview, load_saved_outputs
from finsage_replica.ports.judge import Judge
from finsage_replica.ports.pipeline import ChatPipeline, Turn

_PDF_NAME = re.compile(r"^[A-Za-z0-9_-]+\.pdf$")
_MAX_ANSWER_CHARS = 20_000


class GradeRequest(BaseModel):
    question_id: str
    answer: str

    @field_validator("answer")
    @classmethod
    def answer_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("answer must not be empty")
        if len(value) > _MAX_ANSWER_CHARS:
            raise ValueError(f"answer must be at most {_MAX_ANSWER_CHARS} characters")
        return value.strip()


class ChatRequest(BaseModel):
    message: str
    history: list[Turn] = []

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be empty")
        return value.strip()


async def _with_first(first: Event, rest: AsyncIterator[Event]) -> AsyncIterator[Event]:
    yield first
    async for event in rest:
        yield event


async def _sse(events: AsyncIterator[Event]) -> AsyncIterator[str]:
    run_id, last_t = "unknown", 0
    try:
        async for event in events:
            run_id, last_t = event.run_id, event.t_ms
            yield f"data: {event.model_dump_json()}\n\n"
    except Exception as exc:  # surface failures to the UI instead of dropping the stream
        error = RunError(run_id=run_id, t_ms=last_t, message=f"{type(exc).__name__}: {exc}")
        yield f"data: {error.model_dump_json()}\n\n"


def create_app(
    source: ChatPipeline,
    pdf_dir: Path,
    recordings_dir: Path,
    record_live: bool = True,
    scope: DocumentScope | None = None,
    judge: Judge | None = None,
    judge_questions: list[dict] | None = None,
    judge_results_file: Path | None = None,
) -> FastAPI:
    """`judge_questions` are the benchmark questions with `answer` (the reference) and 0-based `evidence_pages`."""
    app = FastAPI(title="FinSage replica")
    writer = RecordingWriter(recordings_dir)
    benchmark = {q["id"]: q for q in judge_questions or []}

    @app.get("/api/health")
    def health() -> dict:
        return {"source": source.name}

    @app.get("/api/scope")
    def get_scope() -> dict:
        if scope is None:
            raise HTTPException(status_code=404, detail="no document configured")
        return asdict(scope)

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        async def events() -> AsyncIterator[Event]:
            stream = source.run(request.message, request.history)
            first = await anext(stream)
            chained = _with_first(first, stream)
            if record_live and isinstance(first, RunStarted) and first.source == "live":
                chained = writer.record(chained)
            async for event in chained:
                yield event

        return StreamingResponse(_sse(events()), media_type="text/event-stream")

    pdf_root = Path(pdf_dir).resolve()

    @app.get("/api/pdfs/{name}")
    def pdf(name: str) -> FileResponse:
        if not _PDF_NAME.fullmatch(name):
            raise HTTPException(status_code=404, detail="document not found")
        path = (pdf_root / name).resolve()  # follows links, so a link pointing outside is rejected below
        if path.parent != pdf_root or not path.is_file():
            raise HTTPException(status_code=404, detail="document not found")
        return FileResponse(path, media_type="application/pdf")

    @app.get("/api/recordings")
    def recordings() -> list[dict]:
        return [asdict(info) for info in list_recordings(recordings_dir)]

    @app.get("/api/recordings/{run_id}/replay")
    def replay(run_id: str, speed: float = Query(1.0, ge=0)) -> StreamingResponse:
        if recording_path(recordings_dir, run_id) is None:
            raise HTTPException(status_code=404, detail="recording not found")
        replayer = RecordingSource(recordings_dir, run_id, speed=speed)
        return StreamingResponse(_sse(replayer.run("", [])), media_type="text/event-stream")

    @app.get("/api/judge")
    def judge_tab() -> dict:
        outputs = load_saved_outputs(judge_results_file)
        return judge_overview(list(benchmark.values()), outputs, judge.model if judge else None)

    @app.post("/api/judge/grade")
    def grade(request: GradeRequest) -> dict:
        question = benchmark.get(request.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="Only FinanceBench benchmark questions can be graded.")
        if judge is None:
            raise HTTPException(status_code=503, detail="The judge is not configured. Set ANTHROPIC_API_KEY and run the live backend.")
        try:
            result = judge.grade(question["question"], question["answer"], request.answer)
        except Exception as exc:  # report provider errors to the UI as they are
            raise HTTPException(status_code=502, detail=f"The judge failed: {type(exc).__name__}: {exc}") from exc
        return {"question_id": request.question_id, "verdict": result.verdict, "reason": result.reason,
                "model": result.model, "cost_usd": result.cost_usd}

    return app
