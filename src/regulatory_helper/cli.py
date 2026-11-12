"""Command line interface: fetch, ingest, index, search, ask, chat."""
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
    for name, h in (("ask", "answer one question (calls the Claude API)"), ("chat", "interactive session with follow-up questions")):
        ap = sub.add_parser(name, help=h)
        if name == "ask":
            ap.add_argument("question")
        ap.add_argument("--lang", choices=["de", "en"], default="de", help="answer language")
        ap.add_argument("--mode", choices=["bm25", "vector", "hybrid"], default="hybrid")
        ap.add_argument("--k", type=int, default=6)
        ap.add_argument("--no-rewrite", action="store_true", help="search with the raw question (ablation)")
        ap.add_argument("--threshold", type=float, default=None, help="min. cosine of best hit (default from Config)")
        ap.add_argument("--history-turns", type=int, default=3, help="rounds of history sent to the model")
        ap.add_argument("--verbose", action="store_true", help="show rewritten query and all hits")
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
    elif args.command in ("ask", "chat"):
        _ask_or_chat(args)
    elif args.command == "ingest":
        chunks = chunking.ingest()
        print(f"wrote {len(chunks)} chunks to {chunking.OUT_PATH}")


def _print_answer(ans, verbose: bool) -> None:
    if verbose:
        cos = f"{ans.best_cosine:.3f}" if ans.best_cosine is not None else "-"
        print(f"[search query] {ans.search_query}\n[best cosine] {cos}  [reason] {ans.reason}")
        for h in ans.hits:
            print(f"  {h.rank}. {h.chunk.id} cos={h.cosine if h.cosine is None else round(h.cosine, 3)}")
    print(f"\n{ans.text}\n")
    for s in ans.sources:
        print(f"[{s.id}] {s.citation} | {s.title[:80]}\n    \"{s.quote[:400]}{'...' if len(s.quote) > 400 else ''}\"")
    u = ans.usage
    print(f"\n(tokens in/out: {u.input_tokens}/{u.output_tokens}, calls: {u.calls}, cost: ${u.cost_usd:.5f})")


def _ask_or_chat(args) -> None:
    import logging

    from . import generate, retrieval

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = generate.Config(k=args.k, mode=args.mode, rewrite=not args.no_rewrite, max_history_turns=args.history_turns)
    if args.threshold is not None:
        cfg.threshold = args.threshold
    retriever = retrieval.Retriever.load()
    client = generate.get_client()
    if args.command == "ask":
        _print_answer(generate.answer_question(args.question, [], args.lang, cfg, retriever, client), args.verbose)
        return
    history: list[generate.Turn] = []
    print("Chat session (empty line or Ctrl-D to end). History lives only in this process.")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q:
            break
        ans = generate.answer_question(q, history, args.lang, cfg, retriever, client)
        _print_answer(ans, True)
        history.append(generate.Turn(q, ans.text))
        history = generate.trim_history(history, args.history_turns)


if __name__ == "__main__":
    main()
