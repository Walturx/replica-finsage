# FinSage replica

Replication of **FinSage: A Multi-aspect RAG System for Financial Filings Question Answering** (Wang et al., CIKM 2025, DOI 10.1145/3746252.3761587) on the FinanceBench open-source set, with a FastAPI + React front end.

The task log and specs live in [`odd/tasks/finsage-replica.md`](odd/tasks/finsage-replica.md).

## Layout

```
backend/    Python package `finsage_replica` (the pipeline) and its tests
frontend/   React app (from T6)
data/       Downloaded corpus and generated indexes (git-ignored)
odd/tasks/  Feature document: specs, tasks, log
```

The pipeline is a standalone package. The API and the front end are adapters on top of it and never change experiment results.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 (`uv python install 3.12`).

```bash
cd backend
uv sync
uv run pytest
```

Create `.env` in the repository root with:

```
OPENAI_API_KEY=<your key>
GENERATOR_MODEL=gpt-5.6-luna
JUDGE_MODEL=gpt-5.6-terra
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
uv run python -m finsage_replica.preprocessing.pipeline --workers 10
```

Output goes to `data/processed/` (`pages/`, `chunks/`, `embeddings/`, `stats.json`). Each stage caches per document, so an interrupted run resumes. Chunk page indexes are 0-based, matching FinanceBench `evidence_page_num`.
