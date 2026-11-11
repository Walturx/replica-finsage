"""FFP preprocessing: parse PDFs, chunk, embed, drop near duplicates.

The functions here depend only on ports (`PdfParser`, `Embedder`, `TokenCounter`);
`main` is the composition root that plugs in the concrete adapters.
Every stage caches its output per document, so an interrupted run resumes where it stopped.

    data/processed/pages/<doc>.json        parsed markdown per page
    data/processed/chunks/<doc>.jsonl      kept chunks after deduplication, each with `also_on_pages`
                                           (pages of the duplicates it stands in for)
    data/processed/embeddings/<doc>.npy    vectors of the kept chunks (float16, L2-normalized)
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np

from finsage_replica.ffp.chunking import Page, chunk_pages
from finsage_replica.ffp.dedup import inherited_pages, representatives
from finsage_replica.ports.text import Embedder, PdfParser, TokenCounter

ALIAS_MIN_TOKENS = 32  # shorter duplicates are boilerplate and pass no page on to the kept chunk


def _parse_to_cache(parser_factory: Callable[[], PdfParser], pdf: Path, out: Path) -> tuple[str, int, float]:
    start = time.perf_counter()
    pages = parser_factory().parse(pdf)
    out.write_text(json.dumps([asdict(p) for p in pages], ensure_ascii=False), encoding="utf-8")
    return pdf.stem, len(pages), time.perf_counter() - start


def parse_all(pdf_dir: Path, pages_dir: Path, workers: int, parser_factory: Callable[[], PdfParser]) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    todo = [p for p in sorted(pdf_dir.glob("*.pdf")) if not (pages_dir / f"{p.stem}.json").exists()]
    print(f"[parse] {len(todo)} to parse, {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_parse_to_cache, parser_factory, pdf, pages_dir / f"{pdf.stem}.json") for pdf in todo
        ]
        for done, future in enumerate(as_completed(futures), 1):
            name, n_pages, seconds = future.result()
            print(f"[parse] {done}/{len(todo)} {name}: {n_pages} pages in {seconds:.0f}s", flush=True)


def chunk_and_dedup_all(
    pages_dir: Path,
    out_dir: Path,
    max_tokens: int,
    threshold: float,
    embedder: Embedder,
    count_tokens: TokenCounter,
    alias_min_tokens: int = ALIAS_MIN_TOKENS,
) -> dict:
    chunks_dir, emb_dir = out_dir / "chunks", out_dir / "embeddings"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    emb_dir.mkdir(parents=True, exist_ok=True)

    stats = {"documents": 0, "pages": 0, "chunks_before_dedup": 0, "chunks_after_dedup": 0}
    for pages_file in sorted(pages_dir.glob("*.json")):
        doc = pages_file.stem
        pages = [Page(**p) for p in json.loads(pages_file.read_text(encoding="utf-8"))]
        chunks_file, emb_file = chunks_dir / f"{doc}.jsonl", emb_dir / f"{doc}.npy"
        if chunks_file.exists() and emb_file.exists():
            kept_count = sum(1 for _ in chunks_file.open(encoding="utf-8"))
            before = kept_count  # unknown for cached docs, reported as kept
        else:
            chunks = chunk_pages(doc, pages, max_tokens=max_tokens, count_tokens=count_tokens)
            vectors = embedder.encode([c.text for c in chunks])
            reps = representatives(vectors, threshold=threshold)
            keep = [i for i, rep in enumerate(reps) if rep == i]
            also_on = inherited_pages(
                reps, [c.page_index for c in chunks], [c.n_tokens for c in chunks], alias_min_tokens
            )
            with chunks_file.open("w", encoding="utf-8") as fh:
                for i in keep:
                    record = asdict(chunks[i]) | {"also_on_pages": also_on[i]}
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            np.save(emb_file, vectors[keep].astype(np.float16))
            before, kept_count = len(chunks), len(keep)
            print(f"[chunk] {doc}: {len(pages)} pages, {before} chunks, {kept_count} kept", flush=True)
        stats["documents"] += 1
        stats["pages"] += len(pages)
        stats["chunks_before_dedup"] += before
        stats["chunks_after_dedup"] += kept_count
    return stats


def main() -> None:
    from finsage_replica.adapters.bge_m3 import BgeM3Embedder
    from finsage_replica.adapters.pymupdf4llm_parser import Pymupdf4llmParser
    from finsage_replica.adapters.tiktoken_counter import TiktokenCounter

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", type=Path, default=Path("../data/financebench"))
    parser.add_argument("--out", type=Path, default=Path("../data/processed"))
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--dedup-threshold", type=float, default=0.98)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    parse_all(args.corpus / "pdfs", args.out / "pages", args.workers, Pymupdf4llmParser)
    counter = TiktokenCounter()
    stats = chunk_and_dedup_all(
        args.out / "pages", args.out, args.max_tokens, args.dedup_threshold,
        embedder=BgeM3Embedder(device=args.device), count_tokens=counter,
    )
    stats.update(max_tokens=args.max_tokens, dedup_threshold=args.dedup_threshold, tokenizer=counter.encoding)
    (args.out / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
