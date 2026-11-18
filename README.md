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

API keys live in a `.env` file in the repository root, which is never committed:

```
OPENAI_API_KEY=<your key>       # generator gpt-6-luna (rewriting, HyDE, summaries, reranking, answers)
ANTHROPIC_API_KEY=<your key>    # experiment B judge claude-opus-5-5
```

Optional settings, read from the environment or `.env`:

| Variable | Default | Meaning |
|---|---|---|
| `GENERATOR_MODEL` | `gpt-6-luna` | OpenAI model for every generation step |
| `FINSAGE_DOC` | `AMD_2022_10K` | FinanceBench document the chatbot and experiments use |
| `FINSAGE_RERANKER` | `llm` | `llm` grades candidates with the generator, `bge` uses local `bge-reranker-v2-m3` |
| `FINSAGE_SOURCE` | `live` | `live` runs the real pipeline, `dev` serves the development fixture |
| `FINSAGE_PORT` | `8000` | API port |

`.env` does not override variables already set in the shell. If an `ANTHROPIC_BASE_URL` is inherited from another tool, the judge calls go to that endpoint instead, so unset it first (`env -u ANTHROPIC_BASE_URL ...`).

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

Output goes to `data/processed/` (`pages/`, `chunks/`, `embeddings/`, `stats.json`).

## Chatbot

Requires Node 20+. Start the API and the web app in two terminals:

```bash
cd backend
uv run python -m finsage_replica.api
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API runs the live pipeline on `FINSAGE_DOC` (about 15 to 20 s and US$0.0014 per question). With `FINSAGE_SOURCE=dev` it serves a development fixture instead: every such run is labeled "Dev fixture" in the UI and is never recorded. Live runs are recorded automatically to `recordings/` and can be replayed from "Recorded runs", which is the fallback for the classroom demo.

The event contract is `contracts/pipeline-events.schema.json`, generated from `backend/src/finsage_replica/domain/events.py` with `uv run python -m finsage_replica.domain.events`. The frontend mirror is `frontend/src/contracts/events.ts`.

## Experiments

Run from `backend/`. Model outputs are cached under `results/`, so a rerun pays only for what is missing.

| Command | What it measures | Output |
|---|---|---|
| `uv run python -m finsage_replica.evaluation.experiment_a` | Path ablation: evidence-page recall for dense, +BM25, +metadata, +HyDE, +expansion | `results/experiment_a/` |
| `uv run python -m finsage_replica.evaluation.reranker_comparison` | `bge-reranker-v2-m3` vs the LLM grader on the same candidates | `results/reranker_comparison/` |
| `uv run python -m finsage_replica.evaluation.experiment_b` | B: FinSage vs naive dense RAG, same generator, graded by Claude Opus, plus cited-page hit. C: time and cost per stage | `results/experiment_b/` |

Results on `AMD_2022_10K` (7 questions, anecdotal rather than a benchmark score): FinSage 7/7 correct vs naive RAG 3.5/7, the cited page is an evidence page in 6/7 vs 1/7, and FinSage takes 20.4 s vs 3.1 s per question.

## Tests

`uv run pytest` in `backend/`, `npm test` and `npm run typecheck` in `frontend/`. Each stage caches per document, so an interrupted run resumes. Chunk page indexes are 0-based, matching FinanceBench `evidence_page_num`.
