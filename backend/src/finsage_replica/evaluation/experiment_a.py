"""Experiment A: contribution of each retrieval path (mirror of FinSage Table 1).

For every FinanceBench question of the document, the question is rewritten into sub-questions and each
configuration retrieves candidates for every sub-question. A question counts as a hit when any retrieved
chunk covers one of its evidence pages. LLM outputs (sub-questions and HyDE passages) are generated once,
saved to results/experiment_a/llm_outputs.json and reused, so every configuration sees the same inputs
and reruns cost nothing.

    uv run python -m finsage_replica.evaluation.experiment_a
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from finsage_replica.evaluation.metrics import evidence_page_hit, evidence_precision
from finsage_replica.retrieval.mpr import ALL_PATHS, MprConfig


@dataclass(frozen=True)
class NamedConfig:
    name: str
    config: MprConfig


CONFIGS = [
    NamedConfig("Dense (FAISS)", MprConfig(paths=("dense",), expand=False)),
    NamedConfig("Dense + Expansion", MprConfig(paths=("dense",), expand=True)),
    NamedConfig("Dense + BM25", MprConfig(paths=("dense", "bm25"), expand=False)),
    NamedConfig("Dense + BM25 + Metadata", MprConfig(paths=("dense", "bm25", "metadata"), expand=False)),
    NamedConfig("Dense + HyDE", MprConfig(paths=("dense", "hyde"), expand=False)),
    NamedConfig("FinSage (all paths + Expansion)", MprConfig(paths=ALL_PATHS, expand=True)),
]


def needs_generation(entry: dict | None) -> bool:
    """A cached LLM output is reusable only with one non-empty HyDE passage per sub-question."""
    if not entry:
        return True
    hydes = entry.get("hyde", [])
    return len(hydes) != len(entry.get("subquestions", [])) or any(not h.strip() for h in hydes)


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    return {
        "questions": n,
        "hits": hits,
        "recall": hits / n if n else 0.0,
        "precision": sum(r["precision"] for r in rows) / n if n else 0.0,
        "avg_retrieved": sum(r["retrieved"] for r in rows) / n if n else 0.0,
    }


def _questions(questions_file: Path, doc: str) -> list[dict]:
    with questions_file.open(encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    return [
        {"id": r["financebench_id"], "question": r["question"], "answer": r["answer"],
         "evidence_pages": sorted({e["evidence_page_num"] for e in r["evidence"]})}
        for r in rows if r["doc_name"] == doc
    ]


def main() -> None:
    from dotenv import load_dotenv

    from finsage_replica.adapters.bge_m3 import BgeM3Embedder
    from finsage_replica.adapters.openai_llm import OpenAILanguageModel
    from finsage_replica.corpus.financebench import QUESTIONS_FILE
    from finsage_replica.corpus.scope import DEFAULT_DOC, load_scope
    from finsage_replica.retrieval.hyde import hypothetical_document
    from finsage_replica.retrieval.loader import load_document_index
    from finsage_replica.retrieval.mpr import MultiPathRetriever
    from finsage_replica.retrieval.rewrite import rewrite_question

    repo = Path(__file__).resolve().parents[4]
    data = repo / "data"
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc", default=DEFAULT_DOC)
    parser.add_argument("--model", default="gpt-6-luna")
    args = parser.parse_args()

    out_dir = repo / "results" / "experiment_a"
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = _questions(data / "financebench" / QUESTIONS_FILE, args.doc)
    scope = load_scope(data / "financebench" / QUESTIONS_FILE, args.doc, pages_dir=data / "processed" / "pages")

    cache_file = out_dir / "llm_outputs.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else {}
    missing = [q for q in questions if needs_generation(cache.get(q["id"]))]
    if missing:
        load_dotenv(repo / ".env")
        llm = OpenAILanguageModel(args.model)
        for q in missing:
            subs, rewrite_call = rewrite_question(llm, q["question"], scope.company, scope.title)
            hydes = [hypothetical_document(llm, s, scope.company, scope.title) for s in subs]
            cache[q["id"]] = {
                "question": q["question"], "subquestions": subs, "hyde": [h.text for h in hydes], "model": llm.model,
                "tokens_in": rewrite_call.tokens_in + sum(h.tokens_in for h in hydes),
                "tokens_out": rewrite_call.tokens_out + sum(h.tokens_out for h in hydes),
                "cost_usd": rewrite_call.cost_usd + sum(h.cost_usd for h in hydes),
            }
            cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    embedder = BgeM3Embedder()
    index = load_document_index(data / "processed", args.doc, embedder)
    retriever = MultiPathRetriever(index, embedder)

    results = {"doc": args.doc, "model": args.model, "configs": [], "per_question": {}, "path_hits": {}}
    for named in CONFIGS:
        rows = []
        for q in questions:
            llm_out = cache[q["id"]]
            retrieved: list[int] = []
            path_hit: dict[str, bool] = {}
            for sub, hyde in zip(llm_out["subquestions"], llm_out["hyde"]):
                result = retriever.search(sub, named.config, hyde_text=hyde)
                retrieved += [i for i in result.retrieved if i not in retrieved]
                for path, hits in result.per_path.items():
                    found = evidence_page_hit([index.chunks[i] for i, _ in hits], q["evidence_pages"])
                    path_hit[path] = path_hit.get(path, False) or found
            chunks = [index.chunks[i] for i in retrieved]
            row = {"id": q["id"], "hit": evidence_page_hit(chunks, q["evidence_pages"]),
                   "precision": evidence_precision(chunks, q["evidence_pages"]), "retrieved": len(chunks),
                   "evidence_pages": q["evidence_pages"],
                   "pages_retrieved": sorted({c["page_index"] for c in chunks})}
            rows.append(row)
            results["per_question"].setdefault(named.name, []).append(row)
            if named is CONFIGS[-1]:
                results["path_hits"][q["id"]] = path_hit
        results["configs"].append({"name": named.name, "config": asdict(named.config), **aggregate(rows)})

    results["llm_cost_usd"] = sum(v["cost_usd"] for v in cache.values())
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# Experiment A on {args.doc}", "",
             "Evidence-page recall: share of questions where a retrieved chunk covers an evidence page.", "",
             "| Configuration | Recall | Hits | Precision | Avg retrieved |", "|---|---|---|---|---|"]
    for c in results["configs"]:
        lines.append(f"| {c['name']} | {c['recall']:.2f} | {c['hits']}/{c['questions']} | {c['precision']:.3f} | {c['avg_retrieved']:.1f} |")
    lines += ["", "Which path alone reached an evidence page (full configuration):", "",
              "| Question | " + " | ".join(ALL_PATHS) + " |", "|---|" + "---|" * len(ALL_PATHS)]
    for q in questions:
        hits = results["path_hits"].get(q["id"], {})
        lines.append(f"| {q['question'][:70]} | " + " | ".join("yes" if hits.get(p) else "no" for p in ALL_PATHS) + " |")
    lines += ["", f"LLM cost for rewriting and HyDE: US${results['llm_cost_usd']:.4f} ({args.model})."]
    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
