"""Download the legal source texts (English XHTML) from the EU Publications Office Cellar API.

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
ACCEPT = "application/xhtml+xml"

# key -> (CELEX id, description). The MDR is fetched twice: the consolidated
# version (current text, but WITHOUT recitals) and the original act (with recitals).
SOURCES = {
    "mdr-consolidated": ("02017R0745-20260101", "MDR, consolidated version of 2026-01-01 (no recitals)"),
    "mdr-original": ("32017R0745", "MDR, original OJ text of 2017 (contains recitals)"),
    "gdpr": ("32016R0679", "GDPR, OJ text"),
    "ai-act": ("32024R1689", "AI Act, OJ text"),
}


def download(celex: str, retries: int = 3) -> tuple[bytes, str]:
    req = urllib.request.Request(CELEX_BASE + celex, headers={"Accept": ACCEPT, "Accept-Language": "eng"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read(), resp.geturl()
        except OSError:  # URLError, HTTPError and timeouts are all OSError subclasses
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def fetch_all(force: bool = False, raw_dir: Path = RAW_DIR) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    mpath = raw_dir / "manifest.json"
    old = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    manifest: dict = {}
    for key, (celex, desc) in SOURCES.items():
        path = raw_dir / f"{key}.xhtml"
        entry = {"celex": celex, "description": desc, "requested": CELEX_BASE + celex}
        if path.exists() and not force:
            print(f"skip {path.name} (exists)")
            data = path.read_bytes()
            # keep the metadata of the earlier download
            prev = old.get(path.name, {})
            entry["resolved"] = prev.get("resolved")
            entry["fetched_at"] = prev.get("fetched_at")
        else:
            print(f"fetch {key} ...")
            data, entry["resolved"] = download(celex)
            path.write_bytes(data)
            entry["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["bytes"] = len(data)
        manifest[path.name] = entry
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
