import re

import pytest

from regulatory_helper import chunking

ID_RE = re.compile(
    r"^(MDR|GDPR|AIACT)-("
    r"REC-\d+(-s\d+)?"  # recital (optionally a split part)
    r"|ANNEX-[IVX]+-[\w.\-]+"  # annex point / intro / section
    r"|\d+[a-z]?(-[\w()]+)*"  # article, article-paragraph, article-intro, split parts
    r")$"
)


@pytest.fixture(scope="module")
def chunks():
    return chunking.build_chunks()


@pytest.fixture(scope="module")
def by_id(chunks):
    return {c.id: c for c in chunks}


def test_ids_unique(chunks):
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


def test_id_schema(chunks):
    bad = [c.id for c in chunks if not ID_RE.match(c.id)]
    assert not bad, bad[:10]


def test_required_fields(chunks):
    for c in chunks:
        assert c.id and c.law in {"MDR", "GDPR", "AIACT"}
        assert c.type in {"article", "annex", "recital"}
        assert c.title.strip() and c.text.strip() and c.citation.strip(), c.id
        assert c.source_url.startswith("https://eur-lex.europa.eu/")
        if c.type == "article":
            assert c.article, c.id
        if c.type == "recital":
            assert c.article is None and c.paragraph, c.id
        assert len(c.text) <= chunking.MAX_CHARS + 50, c.id


def test_no_consolidation_markers(chunks):
    assert not [c.id for c in chunks if re.search(r"[►◄▼]", c.text)]


def test_counts_per_law(chunks):
    arts = {(c.law, c.article) for c in chunks if c.type == "article"}
    assert sum(1 for law, _ in arts if law == "GDPR") == 99
    assert sum(1 for law, _ in arts if law == "AIACT") == 113
    assert sum(1 for law, _ in arts if law == "MDR") == 124  # 123 articles + Article 10a
    recitals = {law: sum(1 for c in chunks if c.law == law and c.type == "recital") for law in ("GDPR", "AIACT", "MDR")}
    assert recitals["GDPR"] >= 173 and recitals["AIACT"] >= 180 and recitals["MDR"] == 101


def test_known_mdr_article_10(by_id):
    c = by_id["MDR-10-2"]
    assert c.law == "MDR" and c.type == "article" and c.article == "10" and c.paragraph == "2"
    assert c.title == "General obligations of manufacturers"
    assert "system for risk management" in c.text
    assert c.citation == "MDR Art. 10(2)"
    assert any(i.startswith("MDR-10-9") for i in by_id)


def test_known_mdr_annex_viii_rule_11(chunks):
    hits = [c for c in chunks if c.id.startswith("MDR-ANNEX-VIII-") and "Rule 11" in c.title]
    assert len(hits) == 1
    c = hits[0]
    assert c.type == "annex" and c.article == "ANNEX VIII"
    assert "Software intended to provide information" in c.text
    assert "All other software is classified as class I." in c.text
    assert "Rule 11" in c.citation


def test_known_gdpr_article_9(by_id):
    c = by_id["GDPR-9-1"]
    assert c.title == "Processing of special categories of personal data"
    assert "data concerning health" in c.text and c.text.rstrip().endswith("prohibited.")
    assert not c.text.startswith("1.")  # paragraph number lives in metadata
    assert any(i.startswith("GDPR-9-2") for i in by_id)


def test_definitions_split_per_term(by_id):
    assert by_id["MDR-2-1"].text.startswith("‘medical device’ means")
    assert by_id["GDPR-4-1"].text.startswith("‘personal data’ means")
    assert by_id["MDR-2-1"].paragraph == "(1)"


def test_recital(by_id):
    c = by_id["GDPR-REC-4"]
    assert c.type == "recital" and "designed to serve mankind" in c.text
    assert "original 2017" in by_id["MDR-REC-60"].citation


def test_split_parts_repeat_lead_in(chunks):
    """Every later part of a split chunk repeats the lead-in line of the first part (if it ends in ':')."""
    first = {c.id[: -len("-s1")]: c for c in chunks if c.id.endswith("-s1")}
    checked = 0
    for c in chunks:
        m = re.match(r"^(.*)-s([2-9]\d*)$", c.id)
        if not m or m.group(1) not in first:
            continue
        lead = first[m.group(1)].text.splitlines()[0]
        if lead.endswith(":"):
            assert c.text.startswith(lead), c.id
            checked += 1
    assert checked > 0
    assert sum(1 for c in chunks if re.search(r"-s\d+$", c.id)) > 0


def test_split_lines_unit():
    lines = ["Lead:"] + [f"({i}) " + "x" * 300 for i in range(10)]
    parts = chunking.split_lines(lines, max_chars=1000)
    assert len(parts) > 1
    assert all(sum(len(x) + 1 for x in p) <= 1000 for p in parts)
    assert all(p[0] == "Lead:" for p in parts)


def test_roundtrip_jsonl(tmp_path, chunks):
    out = tmp_path / "chunks.jsonl"
    chunking.write_chunks(chunks, out)
    assert chunking.read_chunks(out) == chunks
