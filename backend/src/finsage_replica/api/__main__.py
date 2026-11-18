"""Run the chatbot API.

    uv run python -m finsage_replica.api            # live FinSage pipeline, port 8765

Environment (read from the repo `.env` too):
    FINSAGE_SOURCE   live (default) or dev (UI fixture, no models, no API calls)
    FINSAGE_DOC      FinanceBench document in scope (default AMD_2022_10K)
    GENERATOR_MODEL  OpenAI model for rewriting, HyDE and answers (default gpt-6-luna)
    FINSAGE_RERANKER llm (default, the generator grades candidates) or bge (bge-reranker-v2-m3 cross-encoder)
    OPENAI_API_KEY   required for live
    FINSAGE_PORT     default 8765
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from finsage_replica.api.app import create_app
from finsage_replica.corpus.financebench import QUESTIONS_FILE
from finsage_replica.corpus.scope import DEFAULT_DOC, load_scope

REPO = Path(__file__).resolve().parents[4]
DATA = REPO / "data"


def _live_source(scope):
    from finsage_replica.adapters.bge_m3 import BgeM3Embedder
    from finsage_replica.adapters.bge_reranker import BgeReranker
    from finsage_replica.adapters.openai_llm import OpenAILanguageModel
    from finsage_replica.pipeline import FinSagePipeline
    from finsage_replica.retrieval.loader import load_document_index

    from finsage_replica.adapters.llm_reranker import LlmReranker

    embedder = BgeM3Embedder()
    index = load_document_index(DATA / "processed", scope.doc_name, embedder)
    llm = OpenAILanguageModel(os.environ.get("GENERATOR_MODEL", "gpt-6-luna"))
    choice = os.environ.get("FINSAGE_RERANKER", "llm")
    if choice not in ("llm", "bge"):
        raise SystemExit(f"FINSAGE_RERANKER must be llm or bge, got {choice!r}")
    reranker = LlmReranker(llm) if choice == "llm" else BgeReranker()
    return FinSagePipeline(index, embedder, reranker, llm, company=scope.company, doc_title=scope.title)


def main() -> None:
    load_dotenv(REPO / ".env")
    scope = load_scope(DATA / "financebench" / QUESTIONS_FILE, os.environ.get("FINSAGE_DOC", DEFAULT_DOC),
                       pages_dir=DATA / "processed" / "pages")
    if not scope.questions:
        raise SystemExit(f"{scope.doc_name} has no FinanceBench open-source questions; pick another FINSAGE_DOC")

    source_name = os.environ.get("FINSAGE_SOURCE", "live")
    if source_name == "live":
        source = _live_source(scope)
    elif source_name == "dev":
        from finsage_replica.demo.dev_source import DevSource

        source = DevSource()
    else:
        raise SystemExit(f"FINSAGE_SOURCE must be live or dev, got {source_name!r}")

    app = create_app(source=source, pdf_dir=DATA / "financebench" / "pdfs", recordings_dir=REPO / "recordings", scope=scope)
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FINSAGE_PORT", "8765")))


if __name__ == "__main__":
    main()
