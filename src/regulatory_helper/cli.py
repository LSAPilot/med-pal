"""Command line interface: fetch, ingest, index, search, ask, chat, serve.

Usage: uv run regulatory-helper <command> --help
Heavy dependencies (embedding model, Anthropic SDK, Gradio) are imported only by the commands that need them.
"""
from __future__ import annotations

import argparse
import logging

from . import chunking, fetch, retrieval
from .generate import LANGS, Config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="regulatory-helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch", help="download raw legal texts from EUR-Lex/Cellar into data/raw/")
    p.add_argument("--force", action="store_true", help="re-download existing files")
    sub.add_parser("ingest", help="split data/raw/*.xhtml into data/processed/chunks.jsonl")
    sub.add_parser("index", help="compute embeddings and BM25 index from data/processed/chunks.jsonl")
    sp = sub.add_parser("search", help="search the chunks (no LLM)")
    sp.add_argument("query")
    _add_search_args(sp)
    sub.add_parser("serve", help="start the Gradio app locally")
    for name, h in (("ask", "answer one question (calls the Claude API)"), ("chat", "interactive session with follow-up questions")):
        ap = sub.add_parser(name, help=h)
        if name == "ask":
            ap.add_argument("question")
        _add_search_args(ap)
        ap.add_argument("--lang", choices=LANGS, default="de", help="answer language")
        ap.add_argument("--no-rewrite", action="store_true", help="search with the raw question (ablation)")
        ap.add_argument("--threshold", type=float, default=Config.threshold, help="min. cosine of the best hit")
        ap.add_argument("--history-turns", type=int, default=Config.max_history_turns, help="rounds of history sent to the model")
        ap.add_argument("--verbose", action="store_true", help="show rewritten query and all hits")
    args = parser.parse_args(argv)

    if args.command == "fetch":
        fetch.fetch_all(force=args.force)
    elif args.command == "ingest":
        chunks = chunking.ingest()
        print(f"wrote {len(chunks)} chunks to {chunking.OUT_PATH}")
    elif args.command == "index":
        meta = retrieval.build_index()
        print(f"indexed {meta['chunks']} chunks with {meta['model']} (dim {meta['dim']})")
    elif args.command == "search":
        _search(args)
    elif args.command in ("ask", "chat"):
        _ask_or_chat(args)
    elif args.command == "serve":
        from .app import launch

        launch()


def _add_search_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--mode", choices=retrieval.MODES, default=retrieval.DEFAULT_MODE)
    p.add_argument("--k", type=int, default=retrieval.DEFAULT_K)


def _search(args) -> None:
    for h in retrieval.Retriever.load().search(args.query, mode=args.mode, k=args.k):
        cos = f" cos={h.cosine:.3f}" if h.cosine is not None else ""
        text = h.chunk.text.replace("\n", " ")
        print(f"{h.rank}. {h.chunk.id}  score={h.score:.4f}{cos}\n   {h.chunk.citation} | {h.chunk.title[:90]}\n   {text[:160]}")


def _print_answer(ans, verbose: bool) -> None:
    if verbose:
        cos = f"{ans.best_cosine:.3f}" if ans.best_cosine is not None else "-"
        print(f"[search query] {ans.search_query}\n[best cosine] {cos}  [reason] {ans.reason}")
        for h in ans.hits:
            hcos = f"{h.cosine:.3f}" if h.cosine is not None else "-"
            print(f"  {h.rank}. {h.chunk.id} cos={hcos}")
    print(f"\n{ans.text}\n")
    for s in ans.sources:
        quote = s.quote if len(s.quote) <= 400 else s.quote[:400] + "..."
        print(f'[{s.id}] {s.citation} | {s.title[:80]}\n    "{quote}"')
    u = ans.usage
    print(f"\n(tokens in/out: {u.input_tokens}/{u.output_tokens}, calls: {u.calls}, cost: ${u.cost_usd:.5f})")


def _ask_or_chat(args) -> None:
    from . import generate

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = Config(
        k=args.k, mode=args.mode, rewrite=not args.no_rewrite, max_history_turns=args.history_turns, threshold=args.threshold
    )
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
        _print_answer(ans, args.verbose)
        history = generate.trim_history([*history, generate.Turn(q, ans.text)], args.history_turns)


if __name__ == "__main__":
    main()
