import json

from fastapi.testclient import TestClient

from finsage_replica.api.app import create_app
from finsage_replica.corpus.scope import load_scope
from finsage_replica.demo.dev_source import DevSource


def _write_questions(path):
    rows = [
        {"financebench_id": "id_1", "company": "AMD", "doc_name": "AMD_2022_10K", "question": "Q one?"},
        {"financebench_id": "id_2", "company": "3M", "doc_name": "3M_2018_10K", "question": "Other doc?"},
        {"financebench_id": "id_3", "company": "AMD", "doc_name": "AMD_2022_10K", "question": "Q two?"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_scope_keeps_only_the_chosen_document_questions(tmp_path):
    questions = tmp_path / "q.jsonl"
    _write_questions(questions)
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "AMD_2022_10K.json").write_text(json.dumps([{"page_index": 0, "markdown": ""}] * 121), encoding="utf-8")

    scope = load_scope(questions, "AMD_2022_10K", pages_dir=pages)

    assert scope.doc_name == "AMD_2022_10K"
    assert scope.company == "AMD"
    assert scope.title == "AMD 2022 10K"
    assert scope.page_count == 121
    assert [(q.id, q.question) for q in scope.questions] == [("id_1", "Q one?"), ("id_3", "Q two?")]


def test_scope_page_count_is_unknown_without_parsed_pages(tmp_path):
    questions = tmp_path / "q.jsonl"
    _write_questions(questions)

    assert load_scope(questions, "AMD_2022_10K", pages_dir=tmp_path / "missing").page_count is None


def test_scope_endpoint_exposes_the_document_and_its_questions(tmp_path):
    questions = tmp_path / "q.jsonl"
    _write_questions(questions)
    scope = load_scope(questions, "AMD_2022_10K", pages_dir=tmp_path)
    client = TestClient(create_app(source=DevSource(delay_s=0), pdf_dir=tmp_path, recordings_dir=tmp_path / "r", scope=scope))

    body = client.get("/api/scope").json()

    assert body["doc_name"] == "AMD_2022_10K"
    assert body["company"] == "AMD"
    assert [q["question"] for q in body["questions"]] == ["Q one?", "Q two?"]


def test_scope_endpoint_is_404_when_no_document_is_configured(tmp_path):
    client = TestClient(create_app(source=DevSource(delay_s=0), pdf_dir=tmp_path, recordings_dir=tmp_path / "r"))

    assert client.get("/api/scope").status_code == 404
