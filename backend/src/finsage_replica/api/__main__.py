"""Run the chatbot API.

    uv run python -m finsage_replica.api            # dev fixture source, port 8000

Environment:
    FINSAGE_SOURCE   dev (default). The live pipeline source is wired in T4.
    FINSAGE_DOC      FinanceBench document in scope (default AMD_2022_10K).
    FINSAGE_PORT     default 8000
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from finsage_replica.api.app import create_app
from finsage_replica.corpus.financebench import QUESTIONS_FILE
from finsage_replica.corpus.scope import DEFAULT_DOC, load_scope
from finsage_replica.demo.dev_source import DevSource

REPO = Path(__file__).resolve().parents[4]
DATA = REPO / "data"


def main() -> None:
    source_name = os.environ.get("FINSAGE_SOURCE", "dev")
    if source_name != "dev":
        raise SystemExit(f"FINSAGE_SOURCE={source_name} is not available yet; only 'dev' until T4 lands")
    scope = load_scope(
        DATA / "financebench" / QUESTIONS_FILE,
        os.environ.get("FINSAGE_DOC", DEFAULT_DOC),
        pages_dir=DATA / "processed" / "pages",
    )
    if not scope.questions:
        raise SystemExit(f"{scope.doc_name} has no FinanceBench open-source questions; pick another FINSAGE_DOC")
    app = create_app(
        source=DevSource(),
        pdf_dir=DATA / "financebench" / "pdfs",
        recordings_dir=REPO / "recordings",
        scope=scope,
    )
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FINSAGE_PORT", "8000")))


if __name__ == "__main__":
    main()
