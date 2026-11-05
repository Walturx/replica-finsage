"""Download the FinanceBench open-source questions and the PDFs they reference.

FinSage indexes only the documents that contain the answers (83 in the paper),
so this module fetches the 150 open-source questions and just their documents
instead of the full 368-PDF collection.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

REPO_RAW = "https://raw.githubusercontent.com/patronus-ai/financebench/main"
QUESTIONS_URL = f"{REPO_RAW}/data/financebench_open_source.jsonl"
PDF_URL_TEMPLATE = REPO_RAW + "/pdfs/{doc_name}.pdf"
QUESTIONS_FILE = "financebench_open_source.jsonl"

Fetch = Callable[[str], bytes]


@dataclass
class DownloadReport:
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def referenced_documents(questions: Iterable[dict]) -> list[str]:
    """Unique document names referenced by the questions, sorted."""
    return sorted({q["doc_name"] for q in questions})


def load_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _http_fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def _write_atomic(path: Path, data: bytes) -> None:
    """Write through a .part file so an interrupted run never leaves a truncated file."""
    partial = path.with_name(path.name + ".part")
    try:
        partial.write_bytes(data)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def download_corpus(dest: Path, fetch: Fetch = _http_fetch) -> DownloadReport:
    """Fetch the questions file and every referenced PDF that is not already on disk."""
    dest = Path(dest)
    pdf_dir = dest / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    questions_path = dest / QUESTIONS_FILE
    _write_atomic(questions_path, fetch(QUESTIONS_URL))

    report = DownloadReport()
    for doc_name in referenced_documents(load_questions(questions_path)):
        target = pdf_dir / f"{doc_name}.pdf"
        if target.exists() and target.stat().st_size > 0:
            report.skipped.append(doc_name)
            continue
        _write_atomic(target, fetch(PDF_URL_TEMPLATE.format(doc_name=doc_name)))
        report.downloaded.append(doc_name)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("../data/financebench"))
    args = parser.parse_args()
    report = download_corpus(args.dest)
    print(f"downloaded={len(report.downloaded)} skipped={len(report.skipped)} dest={args.dest}")


if __name__ == "__main__":
    main()
