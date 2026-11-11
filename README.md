# FinSage replica

Replication of **FinSage: A Multi-aspect RAG System for Financial Filings Question Answering** (Wang et al., CIKM 2025, DOI 10.1145/3746252.3761587) on the FinanceBench open-source set, with a FastAPI + React front end.

The task log and specs live in [`odd/tasks/finsage-replica.md`](odd/tasks/finsage-replica.md).

## Layout

Packages are named after the FinSage modules (screaming architecture). Models are plugged in through ports and adapters (hexagonal architecture), so swapping a provider is a configuration change.

```
backend/src/finsage_replica/
  domain/       Shared types (Page, Chunk, and later Question, Citation, PipelineEvent)
  corpus/       FinanceBench download
  ffp/          Module 1, FFP preprocessing: parsing, chunking, dedup, section summaries
  retrieval/    Module 2, MPR multi-path retrieval (T3)
  reranking/    Module 3, DRR reranking (T4)
  answering/    Answers per sub-question, merging, page citations (T4)
  ports/        Interfaces the modules depend on (Embedder, TokenCounter, PdfParser, ...)
  adapters/     Concrete implementations (BGE-M3, tiktoken, pymupdf4llm, LLM providers)
  evaluation/   Experiments A, B and C (T5)
  demo/         Record and replay real pipeline runs (T6)
  api/          FastAPI streaming endpoints for the chatbot (T6)
frontend/       React chatbot: chat, pipeline trace, PDF viewer (T6)
contracts/      Pipeline event schema shared by backend and frontend (T6)
results/        Experiment tables and metrics (committed)
recordings/     Recorded real runs for the live demo (committed)
data/           Corpus, chunks and indexes (git-ignored, regenerable)
odd/tasks/      Feature document: specs, tasks, log
```

One pipeline emits one stream of events consumed by the chatbot, the evaluation and the demo recorder, so what the demo shows is what was evaluated.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 (`uv python install 3.12`).

```bash
cd backend
uv sync
uv run pytest
```

The language model provider is not wired yet (see S2 in the feature document). It will be configured through a `.env` file in the repository root, for example:

```
OPENAI_API_KEY=<your key>
GENERATOR_MODEL=<model id>
```

## Data

Download the 150 FinanceBench open-source questions and the 84 PDFs they reference (about 158 MB) from [patronus-ai/financebench](https://github.com/patronus-ai/financebench):

```bash
cd backend
uv run python -m finsage_replica.corpus.financebench --dest ../data/financebench
```

Re-running skips PDFs already on disk.

## Preprocessing (FFP)

Parse every PDF to per-page markdown, split it into chunks of at most 256 tokens (`o200k_base`), embed them with BGE-M3 on the GPU and drop near duplicates (cosine >= 0.98, first occurrence kept):

```bash
cd backend
uv run python -m finsage_replica.ffp.pipeline --workers 10
```

Output goes to `data/processed/` (`pages/`, `chunks/`, `embeddings/`, `stats.json`). Each stage caches per document, so an interrupted run resumes. Chunk page indexes are 0-based, matching FinanceBench `evidence_page_num`.
