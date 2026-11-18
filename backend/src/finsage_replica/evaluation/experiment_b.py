"""Experiments B and C: FinSage replica vs naive dense RAG, judged by Claude, with per-stage cost.

Both systems use the same generator, answer prompt and citation format. The judge belongs to a
different model family (spec S4). System outputs and grades are cached in
results/experiment_b/outputs.json, so a rerun only pays for what is missing.

    uv run python -m finsage_replica.evaluation.experiment_b
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from finsage_replica.evaluation.judge import cited_page_hit

SYSTEMS = ("finsage", "naive")
SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0, "unparsed": 0.0}


async def _run_finsage(pipeline, question: str) -> dict:
    from finsage_replica.domain.events import AnswerDelta, Citation, Done

    text, cited, done = "", [], None
    async for event in pipeline.run(question, []):
        if isinstance(event, AnswerDelta):
            text += event.text
        elif isinstance(event, Citation):
            cited.append(event.page_index)
        elif isinstance(event, Done):
            done = event
    return {"answer": text, "cited_pages": sorted(set(cited)), "latency_ms": done.latency_ms,
            "stages_ms": done.stages_ms, "tokens_in": done.tokens_in, "tokens_out": done.tokens_out,
            "cost_usd": done.cost_usd}


def main() -> None:
    from dotenv import load_dotenv

    from finsage_replica.adapters.bge_m3 import BgeM3Embedder
    from finsage_replica.adapters.claude_judge import ClaudeJudge
    from finsage_replica.adapters.llm_reranker import LlmReranker
    from finsage_replica.adapters.openai_llm import OpenAILanguageModel
    from finsage_replica.baseline import naive_answer
    from finsage_replica.corpus.financebench import QUESTIONS_FILE
    from finsage_replica.corpus.scope import DEFAULT_DOC, load_scope
    from finsage_replica.evaluation.experiment_a import _questions
    from finsage_replica.pipeline import FinSagePipeline
    from finsage_replica.retrieval.loader import load_document_index

    repo = Path(__file__).resolve().parents[4]
    data = repo / "data"
    load_dotenv(repo / ".env")
    out_dir = repo / "results" / "experiment_b"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_file = out_dir / "outputs.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}

    def save() -> None:
        cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    questions = _questions(data / "financebench" / QUESTIONS_FILE, DEFAULT_DOC)
    scope = load_scope(data / "financebench" / QUESTIONS_FILE, DEFAULT_DOC, pages_dir=data / "processed" / "pages")
    embedder = BgeM3Embedder()
    index = load_document_index(data / "processed", DEFAULT_DOC, embedder)
    llm = OpenAILanguageModel("gpt-6-luna")
    pipeline = FinSagePipeline(index, embedder, LlmReranker(llm), llm, company=scope.company, doc_title=scope.title)
    judge = ClaudeJudge()

    for q in questions:
        entry = cache.setdefault(q["id"], {})
        if "finsage" not in entry:
            entry["finsage"] = asyncio.run(_run_finsage(pipeline, q["question"]))
            save()
        if "naive" not in entry:
            began = time.perf_counter()
            result = naive_answer(q["question"], index, embedder, llm)
            entry["naive"] = {"answer": result.text, "cited_pages": sorted({c["page_index"] for c in result.cited}),
                              "latency_ms": int((time.perf_counter() - began) * 1000),
                              "tokens_in": result.completion.tokens_in, "tokens_out": result.completion.tokens_out,
                              "cost_usd": result.completion.cost_usd}
            save()
        for system in SYSTEMS:
            if "grade" not in entry[system]:
                grade = judge.grade(q["question"], q["answer"], entry[system]["answer"])
                entry[system]["grade"] = grade.__dict__
                save()
        print(q["id"], {s: entry[s]["grade"]["verdict"] for s in SYSTEMS}, flush=True)

    _write_report(out_dir, questions, cache)


def _write_report(out_dir: Path, questions: list[dict], cache: dict) -> None:
    lines = ["# Experiment B: FinSage replica vs naive dense RAG (AMD_2022_10K)", "",
             "Generator gpt-6-luna for both systems. Judge claude-opus-5-5 (different model family). "
             "Score: correct 1, partially correct 0.5, incorrect 0. Pages are 1-based.", "",
             "| System | Score | Correct | Partial | Incorrect | Cited page is evidence | Mean latency s | Mean cost US$ |",
             "|---|---|---|---|---|---|---|---|"]
    for system in SYSTEMS:
        rows = [cache[q["id"]][system] for q in questions]
        verdicts = [r["grade"]["verdict"] for r in rows]
        hits = [cited_page_hit(r["cited_pages"], q["evidence_pages"]) for r, q in zip(rows, questions)]
        lines.append(
            f"| {system} | {sum(SCORE[v] for v in verdicts):.1f}/{len(rows)} | {verdicts.count('correct')} | "
            f"{verdicts.count('partially_correct')} | {verdicts.count('incorrect') + verdicts.count('unparsed')} | "
            f"{sum(h is True for h in hits)}/{len(rows)} | {sum(r['latency_ms'] for r in rows) / len(rows) / 1000:.1f} | "
            f"{sum(r['cost_usd'] for r in rows) / len(rows):.4f} |")
    lines += ["", "| Question | FinSage | Naive | FinSage cited pages | Naive cited pages | Evidence pages |",
              "|---|---|---|---|---|---|"]
    for q in questions:
        e = cache[q["id"]]
        lines.append(f"| {q['question'][:60]} | {e['finsage']['grade']['verdict']} | {e['naive']['grade']['verdict']} | "
                     f"{', '.join(str(p + 1) for p in e['finsage']['cited_pages']) or 'none'} | "
                     f"{', '.join(str(p + 1) for p in e['naive']['cited_pages']) or 'none'} | "
                     f"{', '.join(str(p + 1) for p in q['evidence_pages'])} |")
    stages = [cache[q["id"]]["finsage"]["stages_ms"] for q in questions]
    lines += ["", "## Experiment C: FinSage time per stage (mean over the questions, seconds)", "",
              "| " + " | ".join(stages[0]) + " | total |", "|" + "---|" * (len(stages[0]) + 1)]
    means = {k: sum(s[k] for s in stages) / len(stages) / 1000 for k in stages[0]}
    total = sum(cache[q["id"]]["finsage"]["latency_ms"] for q in questions) / len(questions) / 1000
    lines.append("| " + " | ".join(f"{v:.1f}" for v in means.values()) + f" | {total:.1f} |")
    judge_cost = sum(cache[q["id"]][s]["grade"]["cost_usd"] for q in questions for s in SYSTEMS)
    system_cost = sum(cache[q["id"]][s]["cost_usd"] for q in questions for s in SYSTEMS)
    lines += ["", f"Generator cost: US${system_cost:.4f}. Judge cost: US${judge_cost:.4f}."]
    for q in questions:
        for system in SYSTEMS:
            lines.append(f"\n- {q['id']} {system}: {cache[q['id']][system]['grade']['reason']}")
    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps({"questions": questions, "outputs": cache}, indent=2,
                                                     ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
