"""Section summaries as chunk metadata (FinSage FFP, semantic enhancement step c).

The paper has an LLM summarize each section and attaches the summary to every chunk of that
section, so each chunk keeps its context. A section here is a consecutive run of chunks under
the same heading. Sections shorter than `min_tokens` reuse their heading instead of an LLM call.
Results are appended per section, so an interrupted run resumes without paying twice.

    uv run python -m finsage_replica.ffp.summaries --dry-run   # count sections and estimate cost
    uv run python -m finsage_replica.ffp.summaries             # call the model
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from finsage_replica.ports.llm import LanguageModel

INSTRUCTIONS = (
    "You write metadata for a search index over a company's SEC filing. Summarize the section you are given "
    "in at most two sentences and 60 words. Name the company, the fiscal period and the main topics or figures "
    "the section covers, so that a search for a question about this content finds it. Plain text only."
)


@dataclass(frozen=True)
class SectionGroup:
    section_id: str
    section: str
    chunk_ids: list[str]
    text: str
    first_page: int
    last_page: int


@dataclass
class SummaryStats:
    sections: int = 0
    llm_calls: int = 0
    from_heading: int = 0
    cached: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


def group_sections(chunks: list[dict]) -> list[SectionGroup]:
    """Consecutive runs of chunks that share a heading, in reading order."""
    groups: list[SectionGroup] = []
    run: list[dict] = []

    def close() -> None:
        if run:
            doc = run[0]["doc_name"]
            groups.append(
                SectionGroup(
                    section_id=f"{doc}:s{len(groups)}",
                    section=run[0]["section"],
                    chunk_ids=[c["chunk_id"] for c in run],
                    text="\n\n".join(c["text"] for c in run),
                    first_page=run[0]["page_index"],
                    last_page=run[-1]["page_index"],
                )
            )

    for chunk in chunks:
        if run and chunk["section"] != run[0]["section"]:
            close()
            run = []
        run.append(chunk)
    close()
    return groups


def _truncate(text: str, max_tokens: int, count_tokens: Callable[[str], int]) -> str:
    if count_tokens(text) <= max_tokens:
        return text
    words = text.split()
    low, high = 0, len(words)
    while low < high:  # longest word prefix within budget
        mid = (low + high + 1) // 2
        if count_tokens(" ".join(words[:mid])) <= max_tokens:
            low = mid
        else:
            high = mid - 1
    return " ".join(words[:low])


def _load_done(out_path: Path) -> set[str]:
    if not out_path.is_file():
        return set()
    with out_path.open(encoding="utf-8") as fh:
        return {json.loads(line)["section_id"] for line in fh if line.strip()}


def summarize_sections(
    groups: list[SectionGroup],
    llm: LanguageModel,
    company: str,
    doc_title: str,
    out_path: Path,
    count_tokens: Callable[[str], int],
    max_input_tokens: int = 3000,
    min_tokens: int = 40,
    max_output_tokens: int = 400,
) -> SummaryStats:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _load_done(out_path)
    stats = SummaryStats(sections=len(groups))

    with out_path.open("a", encoding="utf-8") as fh:
        for group in groups:
            if group.section_id in done:
                stats.cached += 1
                continue
            record = {"section_id": group.section_id, "section": group.section, "chunk_ids": group.chunk_ids}
            if count_tokens(group.text) < min_tokens:
                record |= {"summary": group.section, "source": "heading", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
                stats.from_heading += 1
            else:
                prompt = (
                    f"Company: {company}\nDocument: {doc_title}\nSection heading: {group.section}\n"
                    f"Pages: {group.first_page + 1}-{group.last_page + 1}\n\n"
                    f"Section text:\n{_truncate(group.text, max_input_tokens, count_tokens)}"
                )
                result = llm.complete(INSTRUCTIONS, prompt, max_output_tokens=max_output_tokens)
                record |= {"summary": result.text or group.section, "source": "llm", "model": result.model,
                           "tokens_in": result.tokens_in, "tokens_out": result.tokens_out, "cost_usd": result.cost_usd}
                stats.llm_calls += 1
                stats.tokens_in += result.tokens_in
                stats.tokens_out += result.tokens_out
                stats.cost_usd += result.cost_usd
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
    return stats


def main() -> None:
    from dotenv import load_dotenv

    from finsage_replica.adapters.openai_llm import cost_usd
    from finsage_replica.adapters.tiktoken_counter import TiktokenCounter
    from finsage_replica.corpus.financebench import QUESTIONS_FILE
    from finsage_replica.corpus.scope import DEFAULT_DOC, load_scope

    repo = Path(__file__).resolve().parents[4]
    data = repo / "data"
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--doc", default=DEFAULT_DOC)
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--max-input-tokens", type=int, default=3000)
    parser.add_argument("--min-tokens", type=int, default=40)
    parser.add_argument("--dry-run", action="store_true", help="count sections and estimate the cost without calling the model")
    args = parser.parse_args()

    scope = load_scope(data / "financebench" / QUESTIONS_FILE, args.doc, pages_dir=data / "processed" / "pages")
    with (data / "processed" / "chunks" / f"{args.doc}.jsonl").open(encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh if line.strip()]
    groups = group_sections(chunks)
    counter = TiktokenCounter()
    out_path = data / "processed" / "summaries" / f"{args.doc}.jsonl"

    if args.dry_run:
        to_call = [g for g in groups if counter(g.text) >= args.min_tokens]
        est_in = sum(min(counter(g.text), args.max_input_tokens) + 120 for g in to_call)
        est_out = 80 * len(to_call)
        print(json.dumps({"doc": args.doc, "sections": len(groups), "llm_calls": len(to_call),
                          "from_heading": len(groups) - len(to_call), "est_tokens_in": est_in,
                          "est_tokens_out": est_out, "est_cost_usd": round(cost_usd(args.model, est_in, est_out), 4)}, indent=2))
        return

    load_dotenv(repo / ".env")
    from finsage_replica.adapters.openai_llm import OpenAILanguageModel

    stats = summarize_sections(groups, OpenAILanguageModel(args.model), company=scope.company, doc_title=scope.title,
                               out_path=out_path, count_tokens=counter, max_input_tokens=args.max_input_tokens,
                               min_tokens=args.min_tokens)
    print(json.dumps(asdict(stats), indent=2))


if __name__ == "__main__":
    main()
