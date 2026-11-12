"""Copy exactly what the Hugging Face Space needs into the Space clone (section 4).

    uv run python scripts/build_space.py [--space-dir DIR] [--dry-run]

Development happens only in this repo. This script fills the Space clone; it never runs git there
(commit and push are done by hand after review, see docs/deployment.md).

What goes in:        app.py, src/regulatory_helper/*.py, requirements.txt, data/processed/{index files}, data/examples.json,
                     README.md (YAML header of the Space is kept untouched, only the text below it is replaced)
What stays out:      data/raw/, tests/, scripts/, docs/, .env, .venv, caches
Safety checks:       index hash matches chunks.jsonl, example sources match chunks.jsonl, Space README header is intact
                     and its sdk_version equals the Gradio version pinned in pyproject.toml.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regulatory_helper import retrieval  # noqa: E402
from regulatory_helper.chunking import read_chunks  # noqa: E402
from regulatory_helper.service import load_examples  # noqa: E402

DEFAULT_SPACE = Path("/home/lorenz/medical-app-regulatory-helper")
INDEX_FILES = ["chunks.jsonl", "embeddings.npy", "ids.json", "bm25.json", "index_meta.json"]
FORBIDDEN = ["data/raw", "tests", "scripts", "docs", ".env", ".venv", "uv.lock", "pyproject.toml"]
TORCH_INDEX = "--extra-index-url https://download.pytorch.org/whl/cpu"
SPACE_GITIGNORE = "__pycache__/\n*.pyc\n.env\n.env.*\n"


def die(msg: str) -> None:
    sys.exit(f"build_space: {msg}")


def export_requirements() -> str:
    """requirements.txt for the Space via `uv export`. Gradio itself is left out (the Space installs it from `sdk_version`)."""
    out = subprocess.run(
        ["uv", "export", "--no-dev", "--no-group", "app", "--no-hashes", "--no-emit-project", "--no-annotate"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    if re.search(r"^gradio(-client)?==", out, re.M):
        die("gradio is in the exported requirements; keep it out (sdk_version provides it)")
    return TORCH_INDEX + "\n" + out  # the +cpu wheel of torch lives on this extra index


def pinned_gradio() -> str:
    m = re.search(r'"gradio==([0-9.]+)"', (ROOT / "pyproject.toml").read_text())
    if not m:
        die("no pinned gradio version found in pyproject.toml")
    return m.group(1)


def check_index() -> None:
    proc = ROOT / "data" / "processed"
    missing = [f for f in INDEX_FILES if not (proc / f).exists()]
    if missing:
        die(f"missing in data/processed: {missing}. Run `ingest` and `index` first.")
    try:
        retrieval.Retriever.load(proc)  # raises if the index hash does not match chunks.jsonl (stale)
    except RuntimeError as e:
        die(str(e))
    chunks = {c.id: c for c in read_chunks(proc / "chunks.jsonl")}
    ex = load_examples()
    if not ex:
        die("data/examples.json is missing. Run scripts/precompute_examples.py.")
    for e in ex:
        for lang, r in e["replies"].items():
            for s in r["sources"]:
                if s["id"] not in chunks or chunks[s["id"]].text != s["quote"]:
                    die(f"example {e['id']}/{lang} cites {s['id']} which no longer matches chunks.jsonl; re-run precompute_examples.py")


def space_readme(current: str) -> str:
    """Keep the Space's YAML header exactly, replace only the text below it with notices and sources from the code README."""
    m = re.match(r"^(---\n.*?\n---\n)", current, re.S)
    if not m:
        die("Space README.md has no YAML header; refusing to overwrite it")
    head = m.group(1)
    for key in ("sdk: gradio", "app_file: app.py"):
        if key not in head:
            die(f"Space README header lacks '{key}'")
    sdk = re.search(r"sdk_version:\s*['\"]?([0-9.]+)", head)
    if not sdk or sdk.group(1) != pinned_gradio():
        die(f"sdk_version in the Space README ({sdk and sdk.group(1)}) differs from the pinned gradio {pinned_gradio()}")
    code = (ROOT / "README.md").read_text()
    sections = []
    for title in ("Important notices", "Sources"):
        sm = re.search(rf"^## {title}\n.*?(?=^## |\Z)", code, re.S | re.M)
        if sm:
            sections.append(sm.group(0).strip())
    intro = (
        "# Regulatory Copilot\n\n"
        "Ask questions about the MDR, GDPR and the EU AI Act (German or English). Answers are based **only** on the original "
        "texts and every statement is backed by a source with the original quote. The collapsed *Under the hood* area shows the "
        "rewritten search query and the retrieved passages with scores, and lets you compare search modes (BM25, vector, hybrid).\n\n"
        "Code and documentation: see the project repository. After a period of inactivity the Space needs a moment to start (cold start).\n"
    )
    return head + "\n" + intro + "\n" + "\n\n".join(sections) + "\n"


def copy_tree(space: Path, dry: bool) -> list[str]:
    done: list[str] = []

    def put(src: Path | str, rel: str, text: str | None = None) -> None:
        dst = space / rel
        done.append(rel)
        if dry:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            dst.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(src, dst)

    put(ROOT / "app.py", "app.py")
    pkg = sorted(p for p in (ROOT / "src" / "regulatory_helper").glob("*.py"))
    pkg_dst = space / "src" / "regulatory_helper"
    if pkg_dst.exists() and not dry:  # mirror: drop modules that no longer exist in the source
        for old in pkg_dst.glob("*.py"):
            if old.name not in {p.name for p in pkg}:
                old.unlink()
    for p in pkg:
        put(p, f"src/regulatory_helper/{p.name}")
    for f in INDEX_FILES:
        put(ROOT / "data" / "processed" / f, f"data/processed/{f}")
    put(ROOT / "data" / "examples.json", "data/examples.json")
    reqs = export_requirements()
    if not dry:
        (ROOT / "requirements.txt").write_text(reqs, encoding="utf-8")  # tracked copy in this repo
    put(None, "requirements.txt", reqs)
    put(None, ".gitignore", SPACE_GITIGNORE)
    put(None, "README.md", space_readme((space / "README.md").read_text(encoding="utf-8")))
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space-dir", type=Path, default=DEFAULT_SPACE)
    ap.add_argument("--dry-run", action="store_true", help="check and list, write nothing")
    a = ap.parse_args()
    space = a.space_dir.resolve()
    if space == ROOT:
        die("space-dir is the code repo itself")
    if not (space / ".git").exists() or not (space / "README.md").exists():
        die(f"{space} is not a Space clone (no .git or README.md)")
    check_index()
    done = copy_tree(space, a.dry_run)
    print(("would copy" if a.dry_run else "copied") + f" {len(done)} files to {space}:")
    for rel in done:
        print("  " + rel)
    bad = [f for f in FORBIDDEN if (space / f).exists()]
    if bad:
        die(f"forbidden paths exist in the Space clone: {bad}")
    print("No git command was run. Review with `git status` in the Space clone, then commit and push by hand.")


if __name__ == "__main__":
    main()
