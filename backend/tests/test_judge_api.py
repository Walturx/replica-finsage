"""Judge tab API: benchmark questions with their reference, saved experiment B grades, and live grading."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from finsage_replica.api.app import create_app
from finsage_replica.demo.dev_source import DevSource
from finsage_replica.ports.judge import Grade

QUESTIONS = [
    {"id": "q1", "question": "Did AMD report customer concentration in FY22?",
     "answer": "Yes, one customer accounted for 16% of net revenue.", "evidence_pages": [11]},
    {"id": "q2", "question": "What drove revenue change as of the FY22 for AMD?",
     "answer": "Data Center, Gaming and the Xilinx acquisition.", "evidence_pages": [42]},
]


def _saved(verdicts: dict[str, tuple[str, str]]) -> dict:
    outputs = {}
    for qid, (finsage, naive) in verdicts.items():
        outputs[qid] = {
            system: {"answer": f"{system} answer", "cited_pages": [11],
                     "grade": {"verdict": verdict, "reason": f"{system} reason", "model": "claude-opus-5-5",
                               "tokens_in": 1, "tokens_out": 1, "cost_usd": 0.007}}
            for system, verdict in (("finsage", finsage), ("naive", naive))
        }
    return {"questions": QUESTIONS, "outputs": outputs}


class FakeJudge:
    model = "claude-opus-5-5"

    def __init__(self, fail: bool = False):
        self.calls: list[tuple[str, str, str]] = []
        self.fail = fail

    def grade(self, question: str, reference: str, answer: str) -> Grade:
        self.calls.append((question, reference, answer))
        if self.fail:
            raise RuntimeError("Error code: 401 - invalid key")
        return Grade("correct", "Matches the 16% figure.", self.model, 900, 40, 0.0044)


def _client(tmp_path: Path, judge=None, saved: dict | None = None) -> TestClient:
    results = tmp_path / "results.json"
    if saved is not None:
        results.write_text(json.dumps(saved), encoding="utf-8")
    app = create_app(source=DevSource(delay_s=0), pdf_dir=tmp_path, recordings_dir=tmp_path / "recordings",
                     judge=judge, judge_questions=QUESTIONS, judge_results_file=results)
    return TestClient(app)


def test_overview_lists_questions_with_reference_evidence_and_saved_grades(tmp_path):
    saved = _saved({"q1": ("correct", "incorrect"), "q2": ("correct", "partially_correct")})
    body = _client(tmp_path, judge=FakeJudge(), saved=saved).get("/api/judge").json()

    assert body["judge_available"] is True
    assert body["judge_model"] == "claude-opus-5-5"
    first = body["questions"][0]
    assert first["id"] == "q1"
    assert first["reference"] == "Yes, one customer accounted for 16% of net revenue."
    assert first["evidence_pages"] == [11]
    assert first["saved"]["finsage"] == {"verdict": "correct", "reason": "finsage reason", "cited_pages": [11]}
    assert first["saved"]["naive"]["verdict"] == "incorrect"
    assert body["saved_scores"] == {"finsage": 2.0, "naive": 0.5}


def test_overview_without_saved_results_or_judge_still_lists_the_questions(tmp_path):
    body = _client(tmp_path).get("/api/judge").json()

    assert body["judge_available"] is False
    assert body["judge_model"] is None
    assert [q["id"] for q in body["questions"]] == ["q1", "q2"]
    assert all(q["saved"] is None for q in body["questions"])
    assert body["saved_scores"] is None


def test_grade_sends_the_reference_to_the_judge_and_returns_its_verdict(tmp_path):
    judge = FakeJudge()
    response = _client(tmp_path, judge=judge).post(
        "/api/judge/grade", json={"question_id": "q1", "answer": "Yes. One customer was 16% of revenue [1]."})

    assert response.status_code == 200
    assert response.json() == {"question_id": "q1", "verdict": "correct", "reason": "Matches the 16% figure.",
                               "model": "claude-opus-5-5", "cost_usd": 0.0044}
    assert judge.calls == [(QUESTIONS[0]["question"], QUESTIONS[0]["answer"],
                            "Yes. One customer was 16% of revenue [1].")]


def test_grade_refuses_questions_outside_the_benchmark(tmp_path):
    judge = FakeJudge()
    response = _client(tmp_path, judge=judge).post("/api/judge/grade", json={"question_id": "nope", "answer": "x"})

    assert response.status_code == 404
    assert judge.calls == []


def test_grade_rejects_a_blank_answer(tmp_path):
    response = _client(tmp_path, judge=FakeJudge()).post("/api/judge/grade", json={"question_id": "q1", "answer": "  "})

    assert response.status_code == 422


def test_grade_without_a_judge_says_it_is_not_configured(tmp_path):
    response = _client(tmp_path).post("/api/judge/grade", json={"question_id": "q1", "answer": "Yes."})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_grade_reports_a_judge_failure_with_its_message(tmp_path):
    response = _client(tmp_path, judge=FakeJudge(fail=True)).post(
        "/api/judge/grade", json={"question_id": "q1", "answer": "Yes."})

    assert response.status_code == 502
    assert "401" in response.json()["detail"]
