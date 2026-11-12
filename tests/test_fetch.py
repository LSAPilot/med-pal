import json
from pathlib import Path

from regulatory_helper import fetch

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_sources_defined():
    assert set(fetch.SOURCES) == {"mdr-consolidated", "mdr-original", "gdpr", "ai-act"}


def test_raw_files_and_manifest_present():
    manifest = json.loads((RAW / "manifest.json").read_text())
    for name, entry in manifest.items():
        assert (RAW / name).stat().st_size == entry["bytes"]
