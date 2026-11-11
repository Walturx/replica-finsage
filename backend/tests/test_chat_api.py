import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from finsage_replica.api.app import create_app
from finsage_replica.demo.dev_source import DevSource
from finsage_replica.demo.recording import RecordingSource, RecordingWriter, list_recordings, recording_path
from finsage_replica.domain.events import Event, RunStarted

EVENTS = TypeAdapter(Event)


def _sse_events(response) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in response.text.splitlines() if line.startswith("data: ")]


@pytest.fixture
def pdf_dir(tmp_path: Path) -> Path:
    d = tmp_path / "pdfs"
    d.mkdir()
    (d / "3M_2018_10K.pdf").write_bytes(b"%PDF-1.7 fake")
    return d


@pytest.fixture
def client(tmp_path: Path, pdf_dir: Path) -> TestClient:
    app = create_app(source=DevSource(delay_s=0), pdf_dir=pdf_dir, recordings_dir=tmp_path / "recordings")
    return TestClient(app)


def test_chat_streams_a_complete_run_of_valid_events(client):
    response = client.post("/api/chat", json={"message": "What was 3M capex in FY2018?", "history": []})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response)
    for event in events:
        EVENTS.validate_python(event)
    types = [e["type"] for e in events]
    assert types[0] == "run_started" and types[-1] == "done"
    assert {"rewrite", "retrieval", "rerank", "answer_delta", "citation"} <= set(types)
    assert events[0]["source"] == "dev"
    assert events[0]["question"] == "What was 3M capex in FY2018?"
    assert len({e["run_id"] for e in events}) == 1
    t = [e["t_ms"] for e in events]
    assert t == sorted(t)


def test_chat_rejects_an_empty_message(client):
    response = client.post("/api/chat", json={"message": "   ", "history": []})

    assert response.status_code == 422


def test_pdf_endpoint_serves_known_documents_only(client):
    ok = client.get("/api/pdfs/3M_2018_10K.pdf")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "application/pdf"
    assert ok.content == b"%PDF-1.7 fake"

    assert client.get("/api/pdfs/UNKNOWN_DOC.pdf").status_code == 404
    assert client.get("/api/pdfs/..%2F..%2Fpyproject.toml").status_code == 404
    assert client.get("/api/pdfs/3M_2018_10K.txt").status_code == 404


def _live_events(run_id: str = "run-1") -> list[dict]:
    return [
        {"type": "run_started", "run_id": run_id, "t_ms": 0, "question": "q", "source": "live", "model": "m"},
        {"type": "answer_delta", "run_id": run_id, "t_ms": 5, "text": "hello"},
        {"type": "done", "run_id": run_id, "t_ms": 9, "latency_ms": 9, "stages_ms": {}, "tokens_in": 1,
         "tokens_out": 1, "cost_usd": 0.0},
    ]


async def _aiter(items):
    for item in items:
        yield EVENTS.validate_python(item)


async def _collect(aiterable):
    return [e async for e in aiterable]


def test_recording_roundtrip_replays_the_same_events_marked_as_recording(tmp_path):
    import asyncio

    writer = RecordingWriter(tmp_path)
    asyncio.run(_collect(writer.record(_aiter(_live_events()))))
    replayed = asyncio.run(_collect(RecordingSource(tmp_path, "run-1", speed=0).run("ignored", [])))

    original = _live_events()
    assert [e.model_dump(exclude={"source", "recorded_at"}) for e in replayed] == [
        EVENTS.validate_python(e).model_dump(exclude={"source", "recorded_at"}) for e in original
    ]
    first = replayed[0]
    assert isinstance(first, RunStarted)
    assert first.source == "recording"
    assert first.recorded_at is not None


def test_dev_runs_are_never_recorded(tmp_path):
    import asyncio

    events = _live_events()
    events[0]["source"] = "dev"
    writer = RecordingWriter(tmp_path)

    with pytest.raises(ValueError, match="dev"):
        asyncio.run(_collect(writer.record(_aiter(events))))
    assert list(tmp_path.glob("*.jsonl")) == []


def test_recordings_endpoint_lists_saved_runs(client, tmp_path):
    import asyncio

    asyncio.run(_collect(RecordingWriter(tmp_path / "recordings").record(_aiter(_live_events("run-7")))))

    listed = client.get("/api/recordings").json()

    assert [r["run_id"] for r in listed] == ["run-7"]
    assert listed[0]["question"] == "q"
    assert list_recordings(tmp_path / "recordings")[0].run_id == "run-7"


def test_replay_endpoint_streams_a_recording(client, tmp_path):
    import asyncio

    asyncio.run(_collect(RecordingWriter(tmp_path / "recordings").record(_aiter(_live_events("run-7")))))

    response = client.get("/api/recordings/run-7/replay?speed=0")

    events = _sse_events(response)
    assert [e["type"] for e in events] == ["run_started", "answer_delta", "done"]
    assert events[0]["source"] == "recording"
    assert client.get("/api/recordings/nope/replay?speed=0").status_code == 404


def test_replay_refuses_files_that_were_not_live_runs(client, tmp_path):
    import asyncio

    recordings = tmp_path / "recordings"
    recordings.mkdir()
    events = _live_events("planted")
    events[0]["source"] = "dev"
    (recordings / "planted.jsonl").write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

    with pytest.raises(ValueError, match="live"):
        asyncio.run(_collect(RecordingSource(recordings, "planted", speed=0).run("", [])))
    assert "planted" not in [r["run_id"] for r in client.get("/api/recordings").json()]
    replayed = _sse_events(client.get("/api/recordings/planted/replay?speed=0"))
    assert [e["type"] for e in replayed] == ["error"]


def test_listing_skips_malformed_recordings(client, tmp_path):
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    (recordings / "broken.jsonl").write_text("not json\n", encoding="utf-8")

    response = client.get("/api/recordings")

    assert response.status_code == 200
    assert response.json() == []


def test_names_with_a_trailing_newline_are_rejected(tmp_path):
    assert recording_path(tmp_path, "nl\n") is None
    (tmp_path / "x.pdf").write_bytes(b"%PDF")
    client = TestClient(create_app(source=DevSource(delay_s=0), pdf_dir=tmp_path, recordings_dir=tmp_path / "r"))

    assert client.get("/api/pdfs/x.pdf%0A").status_code == 404


def test_pdf_symlinks_that_leave_the_directory_are_not_served(tmp_path):
    import os

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.pdf").write_bytes(b"%PDF-SECRET")
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    try:
        os.symlink(outside / "secret.pdf", pdfs / "link.pdf")
    except OSError:
        pytest.skip("symlinks not available on this system")
    client = TestClient(create_app(source=DevSource(delay_s=0), pdf_dir=pdfs, recordings_dir=tmp_path / "r"))

    assert client.get("/api/pdfs/link.pdf").status_code == 404


def test_committed_contract_matches_the_event_models():
    contract = Path(__file__).resolve().parents[2] / "contracts" / "pipeline-events.schema.json"

    assert json.loads(contract.read_text(encoding="utf-8")) == EVENTS.json_schema()
