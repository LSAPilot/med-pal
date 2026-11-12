"""Download the legal source texts (English) from the EU Publications Office Cellar API.

Raw files are stored unchanged in data/raw/ together with a manifest.json
(source URL, resolved Cellar URL, SHA-256, download time).

Usage: uv run regulatory-helper fetch [--force]
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CELEX_BASE = "http://publications.europa.eu/resource/celex/"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

XHTML = "application/xhtml+xml"
FORMEX = "application/zip;mtype=fmx4"

# key -> (CELEX id, description). The MDR is fetched twice: the consolidated
# version (current text, but WITHOUT recitals) and the original act (with recitals).
SOURCES = {
    "mdr-consolidated": ("02017R0745-20260101", "MDR, consolidated version of 2026-01-01 (no recitals)"),
    "mdr-original": ("32017R0745", "MDR, original OJ text of 2017 (contains recitals)"),
    "gdpr": ("32016R0679", "GDPR, OJ text"),
    "ai-act": ("32024R1689", "AI Act, OJ text"),
}
FORMATS = {"xhtml": (XHTML, ".xhtml"), "formex": (FORMEX, ".formex.zip")}


def download(celex: str, accept: str, retries: int = 3) -> tuple[bytes, str]:
    req = urllib.request.Request(
        CELEX_BASE + celex, headers={"Accept": accept, "Accept-Language": "eng"}
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read(), resp.geturl()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_all(force: bool = False, raw_dir: Path = RAW_DIR) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    for key, (celex, desc) in SOURCES.items():
        for fmt, (accept, ext) in FORMATS.items():
            path = raw_dir / f"{key}{ext}"
            if path.exists() and not force:
                print(f"skip {path.name} (exists)")
                data, resolved = path.read_bytes(), None
            else:
                print(f"fetch {key} [{fmt}] ...")
                data, resolved = download(celex, accept)
                path.write_bytes(data)
            manifest[path.name] = {
                "celex": celex,
                "description": desc,
                "format": fmt,
                "requested": CELEX_BASE + celex,
                "resolved": resolved,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
    mpath = raw_dir / "manifest.json"
    old = json.loads(mpath.read_text()) if mpath.exists() else {}
    # keep earlier metadata (e.g. resolved URL) for files that were skipped
    for name, entry in manifest.items():
        if entry["resolved"] is None and name in old:
            entry["resolved"] = old[name].get("resolved")
            entry["fetched_at"] = old[name].get("fetched_at", entry["fetched_at"])
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
