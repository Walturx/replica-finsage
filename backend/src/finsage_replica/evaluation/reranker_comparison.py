"""Reranker comparison: generic cross-encoder vs LLM grader (mirror of FinSage Figure 5).

Both rerankers receive the same candidates, retrieved by the full FinSage configuration with the
sub-questions and HyDE passages cached by experiment A. For each question we report whether a chunk
on an evidence page survives in the top 5 and at which rank the first one appears.

    uv run python -m finsage_replica.evaluation.reranker_comparison
"""

from __future__ import annotations

import json
from pathlib import Path

from finsage_replica.evaluation.metrics import evidence_precision, first_evidence_rank

TOP_K = 5


def main() -> None:
    from dotenv import load_dotenv

    from finsage_replica.adapters.bge_m3 import BgeM3Embedder
    from finsage_replica.adapters.bge_reranker import BgeReranker
    from finsage_replica.adapters.llm_reranker import LlmReranker
    from finsage_replica.adapters.openai_llm import OpenAILanguageModel
    from finsage_replica.corpus.financebench import QUESTIONS_FILE
    from finsage_replica.corpus.scope import DEFAULT_DOC
    from finsage_replica.evaluation.experiment_a import _questions
    from finsage_replica.reranking.drr import rerank
    from finsage_replica.retrieval.loader import load_document_index
    from finsage_replica.retrieval.mpr import MprConfig, MultiPathRetriever

    repo = Path(__file__).resolve().parents[4]
    data = repo / "data"
    load_dotenv(repo / ".env")
    cache = json.loads((repo / "results" / "experiment_a" / "llm_outputs.json").read_text(encoding="utf-8"))
    questions = _questions(data / "financebench" / QUESTIONS_FILE, DEFAULT_DOC)

    embedder = BgeM3Embedder()
    index = load_document_index(data / "processed", DEFAULT_DOC, embedder)
    retriever = MultiPathRetriever(index, embedder)
    llm_reranker = LlmReranker(OpenAILanguageModel("gpt-6-luna"))
    rerankers = {"bge-reranker-v2-m3 (generic cross-encoder)": BgeReranker(), "gpt-6-luna (LLM grader)": llm_reranker}

    rows = []
    llm_cost = 0.0
    for q in questions:
        out = cache[q["id"]]
        row = {"id": q["id"], "question": q["question"], "evidence_pages": q["evidence_pages"], "by_reranker": {}}
        candidates_per_sub = []
        for sub, hyde in zip(out["subquestions"], out["hyde"]):
            result = retriever.search(sub, MprConfig(), hyde_text=hyde)
            candidates_per_sub.append((sub, [index.chunks[i] for i in result.retrieved]))
        row["candidates"] = sum(len(c) for _, c in candidates_per_sub)
        row["candidates_cover_evidence"] = any(
            first_evidence_rank(c, q["evidence_pages"]) is not None for _, c in candidates_per_sub)
        for name, reranker in rerankers.items():
            top: list[dict] = []
            best_rank = None
            for sub, candidates in candidates_per_sub:
                ranked = rerank(sub, candidates, reranker, top_k=len(candidates))
                if reranker is llm_reranker:
                    llm_cost += llm_reranker.take_usage().cost_usd
                order = [c for c, _ in ranked]
                rank = first_evidence_rank(order, q["evidence_pages"])
                best_rank = rank if best_rank is None or (rank is not None and rank < best_rank) else best_rank
                top += [c for c in order[:TOP_K] if c not in top]
            row["by_reranker"][name] = {
                "first_evidence_rank": best_rank,
                "evidence_in_top5": best_rank is not None and best_rank <= TOP_K,
                "precision_at_5": evidence_precision(top, q["evidence_pages"]),
                "top5_pages": [c["page_index"] + 1 for c in top],
            }
        rows.append(row)

    summary = {}
    for name in rerankers:
        stats = [r["by_reranker"][name] for r in rows]
        summary[name] = {"evidence_in_top5": sum(s["evidence_in_top5"] for s in stats), "questions": len(stats),
                         "mean_precision_at_5": sum(s["precision_at_5"] for s in stats) / len(stats)}
    out_dir = repo / "results" / "reranker_comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps({"summary": summary, "rows": rows, "llm_cost_usd": llm_cost},
                                                     indent=2, ensure_ascii=False), encoding="utf-8")

    names = list(rerankers)
    lines = [f"# Reranker comparison on {DEFAULT_DOC}", "",
             "Same candidates for both rerankers (full FinSage retrieval). Rank = position of the first chunk on an "
             "evidence page after reranking (1 is best).", "",
             "| Reranker | Evidence kept in top 5 | Mean precision@5 |", "|---|---|---|"]
    for name in names:
        s = summary[name]
        lines.append(f"| {name} | {s['evidence_in_top5']}/{s['questions']} | {s['mean_precision_at_5']:.2f} |")
    lines += ["", "| Question | Evidence pages | " + " | ".join(f"Rank, {n.split(' (')[0]}" for n in names) + " |",
              "|---|---|" + "---|" * len(names)]
    for r in rows:
        ranks = [str(r["by_reranker"][n]["first_evidence_rank"] or "not found") for n in names]
        lines.append(f"| {r['question'][:60]} | {', '.join(str(p + 1) for p in r['evidence_pages'])} | " + " | ".join(ranks) + " |")
    lines += ["", f"LLM reranker cost: US${llm_cost:.4f}. Pages are 1-based."]
    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
