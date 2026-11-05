import json

import pytest

from finsage_replica.corpus.financebench import (
    PDF_URL_TEMPLATE,
    QUESTIONS_URL,
    download_corpus,
    referenced_documents,
)


def _question(doc_name: str, qid: str) -> dict:
    return {"financebench_id": qid, "doc_name": doc_name, "question": "q", "answer": "a"}


def _fake_remote(questions: list[dict]) -> dict[str, bytes]:
    jsonl = "\n".join(json.dumps(q) for q in questions).encode()
    files = {QUESTIONS_URL: jsonl}
    for doc in {q["doc_name"] for q in questions}:
        files[PDF_URL_TEMPLATE.format(doc_name=doc)] = f"%PDF {doc}".encode()
    return files


def test_referenced_documents_are_unique_and_sorted():
    questions = [_question("B_DOC", "1"), _question("A_DOC", "2"), _question("B_DOC", "3")]

    assert referenced_documents(questions) == ["A_DOC", "B_DOC"]


def test_download_corpus_fetches_questions_and_only_referenced_pdfs(tmp_path):
    questions = [_question("3M_2018_10K", "1"), _question("AMD_2022_10K", "2")]
    remote = _fake_remote(questions)
    requested: list[str] = []

    def fetch(url: str) -> bytes:
        requested.append(url)
        return remote[url]

    report = download_corpus(tmp_path, fetch=fetch)

    assert (tmp_path / "financebench_open_source.jsonl").read_bytes() == remote[QUESTIONS_URL]
    assert (tmp_path / "pdfs" / "3M_2018_10K.pdf").read_bytes() == b"%PDF 3M_2018_10K"
    assert (tmp_path / "pdfs" / "AMD_2022_10K.pdf").read_bytes() == b"%PDF AMD_2022_10K"
    assert sorted(report.downloaded) == ["3M_2018_10K", "AMD_2022_10K"]
    assert report.skipped == []
    assert len(requested) == 3
    assert not list(tmp_path.rglob("*.part"))


def test_download_corpus_skips_pdfs_already_on_disk(tmp_path):
    questions = [_question("3M_2018_10K", "1"), _question("AMD_2022_10K", "2")]
    remote = _fake_remote(questions)
    (tmp_path / "pdfs").mkdir()
    (tmp_path / "pdfs" / "3M_2018_10K.pdf").write_bytes(b"%PDF existing")
    requested: list[str] = []

    def fetch(url: str) -> bytes:
        requested.append(url)
        return remote[url]

    report = download_corpus(tmp_path, fetch=fetch)

    assert report.skipped == ["3M_2018_10K"]
    assert report.downloaded == ["AMD_2022_10K"]
    assert (tmp_path / "pdfs" / "3M_2018_10K.pdf").read_bytes() == b"%PDF existing"
    assert PDF_URL_TEMPLATE.format(doc_name="3M_2018_10K") not in requested


def test_download_corpus_leaves_no_partial_file_when_fetch_fails(tmp_path):
    questions = [_question("3M_2018_10K", "1")]
    remote = _fake_remote(questions)

    def fetch(url: str) -> bytes:
        if url.endswith(".pdf"):
            raise ConnectionError("network down")
        return remote[url]

    with pytest.raises(ConnectionError):
        download_corpus(tmp_path, fetch=fetch)

    assert not (tmp_path / "pdfs" / "3M_2018_10K.pdf").exists()
    assert not list(tmp_path.rglob("*.part"))
