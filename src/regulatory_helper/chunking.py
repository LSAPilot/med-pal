"""Split the raw EUR-Lex XHTML files into chunks (one paragraph per chunk).

Input:  data/raw/*.xhtml (see fetch.py)
Output: data/processed/chunks.jsonl, one JSON object per line.

Chunk kinds
-----------
* article   : one chunk per numbered paragraph (continuation sub-paragraphs and
              lists stay with their paragraph). Articles without numbered
              paragraphs become one chunk; "Definitions" articles become one
              chunk per defined term.
* annex     : one chunk per numbered point (table row) or per heading section.
* recital   : one chunk per recital.

Chunks longer than MAX_CHARS are split into parts "<id>-s1", "<id>-s2", ...

IDs: "<LAW>-<article>-<paragraph>" (e.g. MDR-10-9), "<LAW>-REC-<n>", "<LAW>-ANNEX-<numeral>-<point>"
("intro" for text before the first heading, "n<k>" for unnumbered sections). Details: docs/chunking.md.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = ROOT / "data" / "processed" / "chunks.jsonl"

# Soft limit (characters) above which a chunk is split at line boundaries.
# 2000 chars are roughly 450 tokens, which fits common embedding models.
MAX_CHARS = 2000

CELEX_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:"

# law -> which raw file is used for which kind of content
LAWS = {
    "MDR": {
        "name": "Regulation (EU) 2017/745 (MDR)",
        "articles_annexes": "mdr-consolidated",
        "recitals": "mdr-original",
        "celex": {"mdr-consolidated": "02017R0745-20260101", "mdr-original": "32017R0745"},
    },
    "GDPR": {
        "name": "Regulation (EU) 2016/679 (GDPR)",
        "articles_annexes": "gdpr",
        "recitals": "gdpr",
        "celex": {"gdpr": "32016R0679"},
    },
    "AIACT": {
        "name": "Regulation (EU) 2024/1689 (AI Act)",
        "articles_annexes": "ai-act",
        "recitals": "ai-act",
        "celex": {"ai-act": "32024R1689"},
    },
}
LAW_LABEL = {"MDR": "MDR", "GDPR": "GDPR", "AIACT": "AI Act"}

DEFINITION_TITLES = {"Definitions"}


@dataclass
class Chunk:
    id: str
    law: str  # MDR | GDPR | AIACT
    type: str  # article | annex | recital
    article: str | None  # "10", "10a", "ANNEX VIII" or None (recitals)
    title: str  # article title, annex title + heading path, or "Recital 4"
    paragraph: str | None  # "9", "(3)", "6.3", "intro", None
    text: str
    source_url: str
    citation: str  # human readable, e.g. "MDR Art. 10(9)"

    def contextual_text(self) -> str:
        """Text with its context in front (what gets embedded and BM25-indexed)."""
        return f"{self.citation} - {self.title}\n{self.text}"


# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

_MARKER_RE = re.compile(r"[►▼]\s*[A-Z]\d*|◄")
_WS_RE = re.compile(r"[ \t\r\n   ]+")


def clean(s: str) -> str:
    """Normalise whitespace and drop consolidation markers (►M1 ... ◄)."""
    s = _MARKER_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def _drop_noise(root: etree._Element) -> None:
    """Remove footnote references/texts and consolidation markers in place."""
    for el in root.xpath(
        '//a[starts-with(@id,"ntr")] | //p[contains(@class,"oj-note")] | //p[@class="footnote"]'
        ' | //p[@class="modref"] | //hr | //span[@class="superscript"][not(normalize-space(translate(., "0123456789", "")))]'
    ):
        _remove(el)


def _remove(el: etree._Element) -> None:
    parent = el.getparent()
    if parent is None:
        return
    tail = el.tail or ""
    prev = el.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or "") + tail
    else:
        parent.text = (parent.text or "") + tail
    parent.remove(el)


def text_of(el: etree._Element) -> str:
    return clean("".join(el.itertext()))


def _cells(table: etree._Element) -> list[list[etree._Element]]:
    rows = table.xpath("./tbody/tr | ./tr")
    return [r.xpath("./td") for r in rows]


def render(el: etree._Element, level: int = 0) -> list[str]:
    """Render an element into text lines. Nested lists are indented by two spaces."""
    ind = "  " * level
    cls = el.get("class") or ""
    if el.tag == "table":
        lines: list[str] = []
        for tds in _cells(el):
            if len(tds) == 2:
                marker = text_of(tds[0])
                sub = _render_children(tds[1], level + 1)
                if sub:
                    lines.append(f"{ind}{marker} {sub[0].lstrip()}".rstrip())
                    lines.extend(sub[1:])
                else:
                    lines.append(f"{ind}{marker}")
            else:  # data table: one line per row
                cells = [text_of(td) for td in tds]
                lines.append(ind + " | ".join(c for c in cells if c))
        return lines
    if "grid-container" in cls:
        col1 = el.xpath('./div[contains(@class,"grid-list-column-1")]')
        col2 = el.xpath('./div[contains(@class,"grid-list-column-2")]')
        marker = text_of(col1[0]) if col1 else ""
        sub = _render_children(col2[0], level + 1) if col2 else []
        if sub:
            return [f"{ind}{marker} {sub[0].lstrip()}".rstrip()] + sub[1:]
        return [f"{ind}{marker}"]
    # plain block (p, div): its own text, descending into nested list structures
    nested = el.xpath("./table | ./div[contains(@class,'grid-container')]")
    if not nested:
        t = text_of(el)
        return [ind + t] if t else []
    return _render_children(el, level)


def _render_children(el: etree._Element, level: int) -> list[str]:
    """Render the content of a cell/container: text nodes, paragraphs and nested lists."""
    lines: list[str] = []
    ind = "  " * level
    if el.text and clean(el.text):
        lines.append(ind + clean(el.text))
    for ch in el:
        if ch.tag in ("table", "p", "div") or "grid-container" in (ch.get("class") or ""):
            lines.extend(render(ch, level))
        else:  # inline element directly in a cell
            t = clean(etree.tostring(ch, method="text", encoding="unicode"))
            if t:
                lines.append(ind + t)
        if ch.tail and clean(ch.tail):
            lines.append(ind + clean(ch.tail))
    return lines


def split_lines(lines: list[str], max_chars: int = MAX_CHARS) -> list[list[str]]:
    """Split lines into parts of at most max_chars (never inside a line, unless one line is longer).

    If the text starts with a lead-in line ending in ':' (e.g. "Manufacturers shall:"),
    that line is repeated at the start of every following part so each part stays understandable.
    """
    if sum(len(ln) + 1 for ln in lines) <= max_chars:
        return [list(lines)]
    lead = lines[0] if len(lines) > 1 and lines[0].rstrip().endswith(":") and len(lines[0]) < max_chars // 2 else None
    parts: list[list[str]] = []
    cur: list[str] = []
    size = 0
    for ln in lines:
        pieces = _split_sentences(ln, max_chars) if len(ln) > max_chars else [ln]
        for piece in pieces:
            if cur and size + len(piece) + 1 > max_chars:
                parts.append(cur)
                cur = [lead] if lead else []
                size = len(lead) + 1 if lead else 0
            cur.append(piece)
            size += len(piece) + 1
    if cur:
        parts.append(cur)
    return parts


def _split_sentences(line: str, max_chars: int) -> list[str]:
    indent = line[: len(line) - len(line.lstrip())]
    sentences = re.split(r"(?<=[.;:])\s+", line.strip())
    out: list[str] = []
    cur = ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > max_chars:
            out.append(indent + cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(indent + cur)
    return out


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def load(name: str, raw_dir: Path = RAW_DIR) -> etree._Element:
    tree = etree.parse(str(raw_dir / f"{name}.xhtml"), etree.HTMLParser(encoding="utf-8"))
    root = tree.getroot()
    _drop_noise(root)
    return root


def source_url(law: str, raw_name: str, anchor: str) -> str:
    return f"{CELEX_URL}{LAWS[law]['celex'][raw_name]}#{anchor}"


# --------------------------------------------------------------------------
# articles
# --------------------------------------------------------------------------

_NUM_PAR_RE = re.compile(r"^(\d+[a-z]?)\.\s*")
_ITEM_RE = re.compile(r"^\((\d+[a-z]?)\)\s*")


def _article_key(art_id: str) -> str:
    return art_id[len("art_"):]


def _article_header(art: etree._Element) -> tuple[str, str]:
    num_el = art.xpath('./p[contains(@class,"title-article") or contains(@class,"oj-ti-art")]')
    title_el = art.xpath('./div[contains(@class,"eli-title")]')
    num = text_of(num_el[0]) if num_el else art.get("id")
    num = re.sub(r"^Article\s+", "", num)
    title = text_of(title_el[0]) if title_el else ""
    return num, title


def _is_numbered_paragraph(ch: etree._Element) -> str | None:
    """Return the paragraph number if ch starts a numbered paragraph."""
    if ch.tag != "div":
        return None
    span = ch.xpath('./span[@class="no-parag"]')
    if span:  # consolidated MDR layout
        m = _NUM_PAR_RE.match(text_of(span[0]))
        return m.group(1) if m else None
    if ch.get("id") and not ch.get("class"):  # OJ layout: <div id="009.001">
        m = _NUM_PAR_RE.match(text_of(ch))
        return m.group(1) if m else None
    return None


def _paragraph_lines(ch: etree._Element, number: str | None) -> list[str]:
    """Lines of a paragraph div without its leading number."""
    inline = ch.xpath('./div[contains(@class,"inline-element")]')
    if ch.xpath('./span[@class="no-parag"]') and inline:
        return render(inline[0])
    lines = _render_children(ch, 0)
    if number and lines:
        lines[0] = _NUM_PAR_RE.sub("", lines[0], count=1)
    return [ln for ln in lines if ln.strip()]


def chunk_articles(law: str, root: etree._Element, raw_name: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    label = LAW_LABEL[law]
    arts = root.xpath('//div[starts-with(@id,"art_") and not(contains(@id,"."))]')
    for art in arts:
        num, title = _article_header(art)
        key = _article_key(art.get("id"))
        url = source_url(law, raw_name, art.get("id"))
        blocks: list[tuple[str | None, list[str]]] = []  # (paragraph number, lines)
        for ch in art:
            if ch.get("class") and re.search(r"title-article|oj-ti-art|eli-title", ch.get("class")):
                continue
            number = _is_numbered_paragraph(ch)
            if number:
                blocks.append((number, _paragraph_lines(ch, number)))
                continue
            lines = render(ch)
            if not lines:
                continue
            if blocks:  # continuation: belongs to the previous paragraph
                blocks[-1][1].extend(lines)
            else:
                blocks.append((None, lines))
        if not blocks:
            continue
        numbered = [b for b in blocks if b[0]]
        if numbered:
            # unnumbered lead-in before paragraph 1 (rare) is kept as its own chunk
            for number, lines in blocks:
                chunks.extend(
                    _make(law, "article", num, title, number, lines,
                          f"{law}-{key}-{number}" if number else f"{law}-{key}-intro", url,
                          f"{label} Art. {num}" + (f"({number})" if number else ""))
                )
        elif title in DEFINITION_TITLES:
            chunks.extend(_definition_chunks(law, num, title, key, url, blocks[0][1], label))
        else:
            chunks.extend(
                _make(law, "article", num, title, None, [ln for _, ls in blocks for ln in ls],
                      f"{law}-{key}", url, f"{label} Art. {num}")
            )
    return chunks


def _definition_chunks(law, num, title, key, url, lines, label) -> list[Chunk]:
    """Definitions article: one chunk per defined term, numbered (1), (2) ..."""
    items: list[tuple[str, list[str]]] = []
    for ln in lines:
        m = _ITEM_RE.match(ln) if not ln.startswith(" ") else None
        if m:
            items.append((m.group(1), [_ITEM_RE.sub("", ln, count=1)]))
        elif items:
            items[-1][1].append(ln)
        # lines before the first item (the lead-in sentence) are dropped on purpose
    out: list[Chunk] = []
    for number, ils in items:
        out.extend(
            _make(law, "article", num, title, f"({number})", ils, f"{law}-{key}-{number}", url,
                  f"{label} Art. {num}({number})")
        )
    return out


def _make(law, typ, article, title, paragraph, lines, base_id, url, citation) -> list[Chunk]:
    parts = split_lines(lines)
    out = []
    for i, part in enumerate(parts, 1):
        cid = base_id if len(parts) == 1 else f"{base_id}-s{i}"
        cit = citation if len(parts) == 1 else f"{citation} (part {i}/{len(parts)})"
        out.append(Chunk(cid, law, typ, article, title, paragraph, "\n".join(part), url, cit))
    return out


# --------------------------------------------------------------------------
# recitals
# --------------------------------------------------------------------------


def chunk_recitals(law: str, root: etree._Element, raw_name: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    label = LAW_LABEL[law]
    for rec in root.xpath('//div[starts-with(@id,"rct_")]'):
        tds = rec.xpath(".//tr[1]/td")
        number = re.sub(r"[()]", "", text_of(tds[0]))
        lines = _render_children(tds[1], 0)
        note = " [recital of the original 2017 text]" if raw_name == "mdr-original" else ""
        chunks.extend(
            _make(law, "recital", None, f"Recital {number}", number, lines, f"{law}-REC-{number}",
                  source_url(law, raw_name, rec.get("id")), f"{label} Recital {number}{note}")
        )
    return chunks


# --------------------------------------------------------------------------
# annexes
# --------------------------------------------------------------------------

_HEAD_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+")
_LABEL_RE = re.compile(r"^(CHAPTER|SECTION|PART|Section|Part|Chapter)\s+(\w+)")


def _annex_numeral(name: str) -> str:
    return re.sub(r"^ANNEX\s+", "", name.strip()).replace(" ", "-")


def _heading_depth(ch: etree._Element) -> int | None:
    cls = ch.get("class") or ""
    m = re.match(r"title-gr-seq-level-(\d)", cls)
    if m:
        return int(m.group(1))
    if cls.startswith("oj-ti-grseq-"):
        return 2
    return None


def chunk_annexes(law: str, root: etree._Element, raw_name: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    label = LAW_LABEL[law]
    for annex in root.xpath('//div[starts-with(@id,"anx_") and @id!="anx_ES"]'):
        # annex name and title
        kids = list(annex)
        name_el = [k for k in kids if (k.get("class") or "") in ("title-annex-1", "oj-doc-ti") and text_of(k).startswith("ANNEX")]
        if not name_el:
            continue
        name = text_of(name_el[0])  # "ANNEX VIII"
        numeral = _annex_numeral(name)
        pre = f"{law}-ANNEX-{numeral}"
        url = source_url(law, raw_name, annex.get("id"))
        titles = [k for k in kids if (k.get("class") or "") in ("title-gr-seq-level-1", "oj-doc-ti") and k is not name_el[0]]
        annex_title = text_of(titles[0]) if titles else ""
        # a heading-stack walk
        stack: list[tuple[int, str, str | None]] = []  # (depth, text, number)
        units: list[dict] = []  # each: {path, number, lines, intro[, point]}
        cur: dict | None = None

        def flush():
            nonlocal cur
            if cur and cur["lines"]:
                units.append(cur)
            cur = None

        def start(number, path_after, intro=False):
            nonlocal cur
            flush()
            cur = {"path": [t for _, t, _ in path_after], "number": number, "lines": [], "intro": intro}

        skip_first_titles = {id(name_el[0])} | {id(t) for t in titles[:1]}
        label_depth: int | None = None  # depth of a preceding "CHAPTER II"-style heading without title
        for ch in kids:
            if id(ch) in skip_first_titles:
                continue
            if ch.tag == "hr" or (ch.tag == "p" and not text_of(ch)):
                continue
            depth = _heading_depth(ch)
            if depth is not None:
                htxt = text_of(ch)
                if not htxt:
                    continue
                flush()
                if label_depth == depth and stack and stack[-1][0] == depth:
                    # "CHAPTER II" followed by its title: merge into one path entry
                    d, t, n = stack[-1]
                    stack[-1] = (d, f"{t} - {htxt}", n)
                    label_depth = None
                else:
                    while stack and stack[-1][0] >= depth:
                        stack.pop()
                    m = _HEAD_NUM_RE.match(htxt)
                    stack.append((depth, htxt, m.group(1) if m else None))
                    label_depth = depth if _LABEL_RE.fullmatch(htxt) else None
                start(stack[-1][2], stack)
                continue
            label_depth = None
            # numbered top-level point (two-column table with a number in the first cell)
            if ch.tag == "table":
                tds = _cells(ch)
                if tds and len(tds[0]) == 2:
                    for row in tds:
                        mark = text_of(row[0])
                        m = re.match(r"^(\d+(?:\.\d+)*)\.?$", mark)
                        if m:
                            flush()
                            cur = {"path": [t for _, t, _ in stack], "number": m.group(1),
                                   "lines": render_row_body(row[1]), "intro": False, "point": True}
                            flush()
                            # content after the point continues as a fresh section of the same heading
                        else:
                            if cur is None:
                                start(stack[-1][2] if stack else None, stack, intro=not units)
                            cur["lines"].extend(render(ch))
                            break
                    continue
            lines = render(ch)
            if not lines:
                continue
            if cur is None or cur.get("point"):
                start(stack[-1][2] if stack else None, stack, intro=not stack)
            cur["lines"].extend(lines)
        flush()

        used: set[str] = set()
        unnumbered = 0
        for u in units:
            path = u["path"]
            number = u["number"]
            if number:
                suffix = number
            elif u["intro"]:
                suffix = "intro"
            else:
                unnumbered += 1
                suffix = f"n{unnumbered}"  # unnumbered section, counted per annex
            base = f"{pre}-{suffix}"
            if base in used:  # same number in another chapter/section: prefix the chapter token
                tok = _path_token(path)
                base = f"{pre}-{tok}-{suffix}" if tok else base
            n = 2
            orig = base
            while base in used:
                base = f"{orig}-{n}"
                n += 1
            used.add(base)
            ttl = " > ".join([f"Annex {numeral.replace('-', ' ')}: {annex_title}".strip(": ")] + path)
            para = number or ("intro" if u["intro"] else None)
            cit = f"{label} Annex {numeral.replace('-', ' ')}"
            if para and para != "intro":
                cit += f", point {para}"
            elif para == "intro":
                cit += " (introduction)"
            heading_hint = path[-1] if path and number and _HEAD_NUM_RE.match(path[-1]) else None
            if heading_hint and "Rule" in heading_hint:
                cit += " (" + _HEAD_NUM_RE.sub("", heading_hint) + ")"
            parts = split_lines(u["lines"])
            for i, part in enumerate(parts, 1):
                cid = base if len(parts) == 1 else f"{base}-s{i}"
                c = cit if len(parts) == 1 else f"{cit} (part {i}/{len(parts)})"
                chunks.append(Chunk(cid, law, "annex", name, ttl, para, "\n".join(part), url, c))
    return chunks


def render_row_body(td: etree._Element) -> list[str]:
    return [ln for ln in _render_children(td, 0) if ln.strip()]


def _path_token(path: list[str]) -> str:
    for p in path:
        m = _LABEL_RE.match(p)
        if m:
            return f"{m.group(1)[0].upper()}{m.group(2)}"
    return ""


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def build_chunks(raw_dir: Path = RAW_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for law, cfg in LAWS.items():
        main = load(cfg["articles_annexes"], raw_dir)
        chunks.extend(chunk_recitals(law, load(cfg["recitals"], raw_dir), cfg["recitals"]))
        chunks.extend(chunk_articles(law, main, cfg["articles_annexes"]))
        chunks.extend(chunk_annexes(law, main, cfg["articles_annexes"]))
    dup = [cid for cid, n in Counter(c.id for c in chunks).items() if n > 1]
    if dup:
        raise ValueError(f"duplicate chunk ids: {sorted(dup)[:10]}")
    return chunks


def write_chunks(chunks: list[Chunk], path: Path = OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def read_chunks(path: Path = OUT_PATH) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f if line.strip()]


def ingest(raw_dir: Path = RAW_DIR, out: Path = OUT_PATH) -> list[Chunk]:
    chunks = build_chunks(raw_dir)
    write_chunks(chunks, out)
    return chunks
