"""The single FinanceBench document the replica works on (S1: one-document scope)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DOC = "AMD_2022_10K"


@dataclass(frozen=True)
class ScopedQuestion:
    id: str
    question: str


@dataclass(frozen=True)
class DocumentScope:
    doc_name: str
    company: str
    title: str
    page_count: int | None
    questions: list[ScopedQuestion] = field(default_factory=list)


def load_scope(questions_path: Path, doc_name: str, pages_dir: Path) -> DocumentScope:
    """Questions of `doc_name` from the FinanceBench file, plus its page count if it was parsed (T2a)."""
    rows = []
    with Path(questions_path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                if row["doc_name"] == doc_name:
                    rows.append(row)
    pages_file = Path(pages_dir) / f"{doc_name}.json"
    page_count = len(json.loads(pages_file.read_text(encoding="utf-8"))) if pages_file.is_file() else None
    return DocumentScope(
        doc_name=doc_name,
        company=rows[0]["company"] if rows else doc_name.split("_")[0],
        title=doc_name.replace("_", " "),
        page_count=page_count,
        questions=[ScopedQuestion(r["financebench_id"], r["question"]) for r in rows],
    )
