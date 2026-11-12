"""Command line interface: fetch, ingest, index, search. The `ask` command follows in section 3."""
from __future__ import annotations

import argparse

from . import chunking, fetch


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="regulatory-helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch", help="download raw legal texts from EUR-Lex/Cellar into data/raw/")
    p.add_argument("--force", action="store_true", help="re-download existing files")
    sub.add_parser("index", help="compute embeddings and BM25 index from data/processed/chunks.jsonl")
    sp = sub.add_parser("search", help="search the chunks (no LLM)")
    sp.add_argument("query")
    sp.add_argument("--mode", choices=["bm25", "vector", "hybrid"], default="hybrid")
    sp.add_argument("--k", type=int, default=6)
    sub.add_parser("ingest", help="split data/raw/*.xhtml into data/processed/chunks.jsonl")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch.fetch_all(force=args.force)
    elif args.command == "index":
        from . import retrieval

        meta = retrieval.build_index()
        print(f"indexed {meta['chunks']} chunks with {meta['model']} (dim {meta['dim']})")
    elif args.command == "search":
        from . import retrieval

        hits = retrieval.Retriever.load().search(args.query, mode=args.mode, k=args.k)
        for h in hits:
            cos = f" cos={h.cosine:.3f}" if h.cosine is not None else ""
            first = h.chunk.text.replace("\n", " ")
            print(f"{h.rank}. {h.chunk.id}  score={h.score:.4f}{cos}\n   {h.chunk.citation} | {h.chunk.title[:90]}\n   {first[:160]}")
    elif args.command == "ingest":
        chunks = chunking.ingest()
        print(f"wrote {len(chunks)} chunks to {chunking.OUT_PATH}")


if __name__ == "__main__":
    main()
