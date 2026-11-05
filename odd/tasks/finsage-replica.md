# FinSage replica

Objective: replicate FinSage (Wang et al., CIKM 2025, DOI 10.1145/3746252.3761587) on FinanceBench open source, with a FastAPI + React front end, for the PI course Week 13 deliverable.
Branch: `feat/finsage-replica` · Delivery strategy: `ask-on-risk` (local repo, no remote yet) · Test runners: pytest (backend), vitest (frontend, from T6).

## Specs

- **S1 Replication target.** "Para la entrega de la semana 13 tenemos que vivecodear un paper o replicar la investigacion. Creo que podemos aplicar la de finsage". Rebuild the FinSage pipeline in Python: FFP preprocessing, MPR retrieval (BM25, dense BGE-M3 + FAISS, metadata, HyDE, bundle expansion), DRR reranking, answer generation. Corpus: the 150 FinanceBench open-source questions and only the 84 documents they reference (paper: 149 questions, 83 documents).
- **S2 Models.** "podemos usar gpt 5.6 luna". GPT-5.6 Luna for query rewriting, HyDE, section summaries and answers. Judge: GPT-5.6 Terra (assumption: recommended by the assistant, not yet explicitly confirmed by the user). Embeddings and reranker run locally on the RTX 5070.
- **S3 Front end.** "En el scope hay que generar un front end tdv hay tiempo de sobrea" and "FastAPI + React". A query view that streams each pipeline stage live (per-path hits, reranked chunks, answer, cited page) and a results view with the experiment tables.
- **S4 Experiments.** A: path ablation (dense, +BM25, +metadata, +HyDE, +expansion), metric = evidence-page recall. B: naive dense RAG vs FinSage replica, both with Luna, judged by Terra, plus cited-page hit rate. C: latency, tokens and cost per stage.
- **S5 Architecture.** The pipeline is a standalone Python package. FastAPI and React are adapters on top and never change experiment results.
- **S6 Declared limitations.** No VLM figure captioning, no DPO-trained reranker (use `bge-reranker-v2-m3`), no SFT HyDE, MinerU replaced by pymupdf4llm, coreference resolution optional by budget, Company (Lotus) dataset out of scope.

## Tasks

| ID | Specs | Task | Route | Status | Evidence |
|---|---|---|---|---|---|
| T1 | S1, S5 | Repo, Python 3.12 env, package skeleton, FinanceBench download script | inline | code done, corpus download awaiting user OK | RED: ModuleNotFoundError. GREEN: 4 passed (pytest) |
| T2 | S1, S6 | FFP: PDF to 256-token chunks, dedup, section summaries, cached on disk | inline | pending | |
| T3 | S1, S4 | Indexes and MPR retrieval, experiment A | inline | pending | |
| T4 | S1, S2 | Reranker and answer generation | inline | pending | |
| T5 | S2, S4 | Evaluation: judge, naive baseline, cost/latency, experiments B and C | inline | pending | |
| T6 | S3, S5 | FastAPI streaming API and React front end | inline | pending | |
| T7 | S4 | Week 13 presentation material | inline | pending | |

## Log

- **L1 (2026-11-05, user):** "Para la entrega de la semana 13 tenemos que vivecodear un paper o replicar la investigacion. Creo que podemos aplicar la de finsage pero puedes empezar la fase de discovery para ver como podemos abarcarlo usando las buenas practicas indicadas en gentle ai"
- **L2 (2026-11-05, discovery):** Official repo `simplew4y/finsage` is production service code. It lacks the FFP pipeline, DPO reranker training, HyDE SFT, trained weights and FinanceBench evaluation. FinanceBench open source: 150 questions, 368 PDFs (672 MB), 84 referenced documents (158 MB). Evidence records carry `evidence_page_num` (assumption to verify in T3: whether it is 0-indexed). Hardware: RTX 5070 12 GB (needs torch built for CUDA 12.8+). Python 3.12.15 available through uv.
- **L3 (2026-11-05, user):** "podemos usar gpt 5.6 luna". Verified it exists, about US$0.20 / US$1.20 per 1M input/output tokens. Paper used GPT-4o, so experiment B compares against a naive baseline with the same model instead of the paper's absolute number.
- **L4 (2026-11-05, user):** "Vamos a hacer front end  o algun modelo de machine learning ahi quiero que me expliques que vamos a hacer si me puedes hacer un artefacto para entenderlo seria mejor". Explainer published: https://claude.ai/artifact/MM2ofobmiqFR7ZiurrLQus
- **L5 (2026-11-05, user):** "En el scope hay que generar un front end tdv hay tiempo de sobrea". Front end added as T6.
- **L6 (2026-11-05, user):** "FastAPI + React". Repo created at `C:\Users\USER\Downloads\finsage-replica` (outside Google Drive). Engram mirror pending: Engram server failed to connect this session.
- **L7 (2026-11-05, T1):** uv project on Python 3.12, package `finsage_replica` with `corpus.financebench` (questions + only referenced PDFs, atomic writes, skips existing). Writing `.env.example` was denied by the permission settings, so the env vars are documented in README instead. Heavy ML dependencies (torch for CUDA 12.8, FlagEmbedding, faiss) are deferred to T2/T3. Next: run the corpus download once the user approves it (84 PDFs, about 158 MB).
