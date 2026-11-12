"""Command line interface. Further commands (ingest, index, search, ask) follow in later sections."""
from __future__ import annotations

import argparse

from . import fetch


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="regulatory-helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fetch", help="download raw legal texts from EUR-Lex/Cellar into data/raw/")
    p.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args(argv)
    if args.command == "fetch":
        fetch.fetch_all(force=args.force)


if __name__ == "__main__":
    main()
