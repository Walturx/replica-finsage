"""Record live pipeline runs and replay them with their original timing.

Recordings are the honest fallback for the classroom demo: they are real runs of the
pipeline, saved as JSONL and replayed as `source="recording"`. Development fixtures
are never recorded.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from finsage_replica.domain.events import EVENT_ADAPTER, Event, RunStarted
from finsage_replica.ports.pipeline import Turn

_RUN_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class RecordingInfo:
    run_id: str
    question: str
    model: str
    recorded_at: str


def recording_path(directory: Path, run_id: str) -> Path | None:
    """Path of a recording, or None when the id is malformed or the file does not exist."""
    if not _RUN_ID.match(run_id):
        return None
    path = Path(directory) / f"{run_id}.jsonl"
    return path if path.is_file() else None


class RecordingWriter:
    def __init__(self, directory: Path):
        self._dir = Path(directory)

    async def record(self, events: AsyncIterator[Event]) -> AsyncIterator[Event]:
        """Pass events through unchanged while saving them. The file appears only once the run ends."""
        handle = None
        partial = final = None
        try:
            async for event in events:
                if handle is None:
                    if not isinstance(event, RunStarted):
                        raise ValueError("a recording must start with run_started")
                    if event.source != "live":
                        raise ValueError(f"only live runs are recorded, got source={event.source} (dev fixtures never)")
                    if not _RUN_ID.match(event.run_id):
                        raise ValueError(f"invalid run_id {event.run_id!r}")
                    self._dir.mkdir(parents=True, exist_ok=True)
                    final = self._dir / f"{event.run_id}.jsonl"
                    partial = final.with_name(final.name + ".part")
                    handle = partial.open("w", encoding="utf-8")
                    stamped = event.model_copy(update={"recorded_at": datetime.now(timezone.utc).isoformat()})
                    handle.write(stamped.model_dump_json() + "\n")
                else:
                    handle.write(event.model_dump_json() + "\n")
                yield event
            if handle is not None:
                handle.close()
                handle = None
                partial.replace(final)
        finally:
            if handle is not None:
                handle.close()
            if partial is not None and partial.exists():
                partial.unlink()


class RecordingSource:
    name = "recording"

    def __init__(self, directory: Path, run_id: str, speed: float = 1.0):
        path = recording_path(directory, run_id)
        if path is None:
            raise FileNotFoundError(run_id)
        self._path = path
        self._speed = speed

    async def run(self, question: str, history: list[Turn]) -> AsyncIterator[Event]:
        previous_t = 0
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                event = EVENT_ADAPTER.validate_json(line)
                if self._speed > 0:
                    await asyncio.sleep(max(0, event.t_ms - previous_t) / 1000 / self._speed)
                previous_t = event.t_ms
                if isinstance(event, RunStarted):
                    event = event.model_copy(update={"source": "recording"})
                yield event


def list_recordings(directory: Path) -> list[RecordingInfo]:
    directory = Path(directory)
    if not directory.is_dir():
        return []
    infos = []
    for path in sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        first = json.loads(path.open(encoding="utf-8").readline())
        infos.append(RecordingInfo(first["run_id"], first["question"], first["model"], first.get("recorded_at") or ""))
    return infos
