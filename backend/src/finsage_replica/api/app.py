"""FastAPI adapter for the chatbot. It streams pipeline events as Server-Sent Events."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from finsage_replica.demo.recording import RecordingSource, RecordingWriter, list_recordings, recording_path
from finsage_replica.domain.events import Event, RunError, RunStarted
from finsage_replica.ports.pipeline import ChatPipeline, Turn

_PDF_NAME = re.compile(r"^[A-Za-z0-9_-]+\.pdf$")


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


def create_app(source: ChatPipeline, pdf_dir: Path, recordings_dir: Path, record_live: bool = True) -> FastAPI:
    app = FastAPI(title="FinSage replica")
    writer = RecordingWriter(recordings_dir)

    @app.get("/api/health")
    def health() -> dict:
        return {"source": source.name}

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

    return app
