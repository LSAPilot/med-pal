# Source data format (Section 1a)

All files are downloaded reproducibly with `uv run regulatory-helper fetch` from the Cellar API
(`http://publications.europa.eu/resource/celex/<CELEX>` with `Accept` header and
`Accept-Language: eng`). No scraping of eur-lex.europa.eu is needed (that site answers
automated requests with an empty HTTP 202). `data/raw/manifest.json` records URL, SHA-256 and time.
XHTML downloads were byte-identical on a second run; the Formex zips differ in zip metadata only
between runs for some files.

## What is available

| Key | CELEX | XHTML | Formex zip | Recitals | Articles | Annexes |
|---|---|---|---|---|---|---|
| `mdr-consolidated` | 02017R0745-20260101 | 1.6 MB | 177 KB | **no** | 123 | 17 (+ `anx_ES`, a table of contents) |
| `mdr-original` | 32017R0745 | 1.7 MB | 205 KB | 101 | 123 | 17 |
| `gdpr` | 32016R0679 | 0.8 MB | 90 KB | 173 | 99 | none |
| `ai-act` | 32024R1689 | 1.3 MB | 172 KB | 180 | 113 | 13 |

Key finding: the **consolidated MDR has no preamble**, so no recitals. They exist only in the
original 2017 act. The original text lacks later amendments (e.g. Regulation 2020/561, 2023/607),
so: articles and annexes from the consolidated version, recitals (if wanted) from the original.
Recitals stay as adopted in 2017, so they should be marked as such ("recital, original 2017 text"). The consolidated file also contains amendment markers
(`►M1`, `◄`) and an amendment table of contents that the parser must skip.

## Format 1: XHTML (`application/xhtml+xml`)
One file per law. Ids make most structure addressable. The two families differ in class names:
consolidated MDR uses `norm`/`title-article-norm`, OJ originals (GDPR, AI Act, original MDR) use `oj-normal`/`oj-ti-art`.

Article (MDR consolidated, Art. 10): explicit `id="art_10"`, number and title with own classes,
paragraph number in `<span class="no-parag">`:
```html
<div class="eli-subdivision" id="art_10">
  <p class="title-article-norm">Article 10</p>
  <div class="eli-title" id="art_10.tit_1"><p class="stitle-article-norm">General obligations of manufacturers</p></div>
  <div class="norm">
    <span class="no-parag">1.  </span>
    <div class="norm inline-element">When placing their devices on the market ...</div>
  </div>
```
Article (GDPR, Art. 9): paragraph numbers are part of the text, but the div carries an id (`009.001`):
```html
<div class="eli-subdivision" id="art_9"> ... <p class="oj-sti-art">Processing of special categories of personal data</p>
  <div id="009.001"><p class="oj-normal">1.   Processing of personal data revealing racial ...</p></div>
  <div id="009.002"><p class="oj-normal">2.   Paragraph 1 shall not apply if one of the following applies:</p>
     <table> ... <p class="oj-normal">(a)</p> | <p class="oj-normal">the data subject has given explicit consent ...
```
Lists (a), (b), ... are tables in OJ files and `grid-list` divs in the consolidated file.

Articles without numbered paragraphs (e.g. MDR Art. 2 definitions, 30 of 123 MDR articles) are
a plain `<p class="norm">` followed by a list `(1)`, `(2)`, ... In Art. 2 the definitions are the natural units.

Recital (GDPR, `id="rct_4"`): table row with number in one cell, text in the other:
```html
<div class="eli-subdivision" id="rct_4"><table><tr><td><p class="oj-normal">(4)</p></td>
  <td><p class="oj-normal">The processing of personal data should be designed to serve mankind. ...
```
Annex (MDR consolidated): `id="anx_VIII"`, headings only as CSS classes, **no ids for chapters or rules**:
```html
<div id="anx_VIII"> <p class="title-annex-1">ANNEX VIII</p>
  <p class="title-gr-seq-level-1"><span class="boldface">CLASSIFICATION RULES</span></p>
  <p class="title-gr-seq-level-2">CHAPTER III</p> ...
  <p class="title-gr-seq-level-4">6.3.   <span class="boldface">Rule 11</span></p>
  <p class="norm">Software intended to provide information which is used to take decisions with diagnosis or therapeutic purposes is classified as class IIa, except if ...</p>
  <div class="grid-container grid-list"> ... — death or an irreversible deterioration ...
```
AI Act Annex III is a nested table structure (`1.` -> `(a)` -> ...), with `id="anx_III"` and
title in `oj-doc-ti`.
The consolidated MDR also has an `anx_ES` block; it is only the annex table of contents and must be skipped.

## Format 2: Formex 4 (`application/zip;mtype=fmx4`)
Zip with semantic XML. Tags are explicit: `<ARTICLE IDENTIFIER="001"><TI.ART>Article 1</TI.ART><STI.ART>Subject matter and scope</STI.ART><PARAG IDENTIFIER="001.001"><NO.PARAG>1.</NO.PARAG><ALINEA>...`,
recitals as `<CONSID><NP><NO.P>(1)</NO.P><TXT>...` (101 in the original MDR),
annexes as `<ANNEX>` (one file per annex for the MDR original, one big file for the consolidated one).
Drawbacks: the structure differs by publication type (original vs consolidated vs the AI Act
`*.fmx.xml` split), footnotes are inline `<NOTE>`, annex content is mixed and partly untagged.
Rule headings in annexes are not semantic here either.

## Comparison
| | XHTML | Formex |
|---|---|---|
| One file per law | yes | MDR original: 19 files |
| Articles / paragraphs | ids + classes, two class families | clean semantic tags |
| Recitals | `rct_N` ids | `<CONSID>` |
| Annex structure (rules) | CSS classes only | similar, deeper nesting |
| Consolidated MDR | available | available (same limitations) |
| Parser variants needed | 2 class families | 3 layouts |
| Readable for debugging in a browser | yes | no |

## Recommendation
**XHTML.** Reasons: one file per law, article and recital ids are present everywhere, and it can be
inspected in a browser, which helps with the sample checks in 1b. The two class families are a small,
well-defined cost (a mapping table). Formex has cleaner paragraph tags but needs three layouts and
does not solve the real problem (annex structure).

Sources to use:
- Articles and annexes: `mdr-consolidated` (current law), `gdpr`, `ai-act`.
- Recitals: GDPR, AI Act and `mdr-original` (the consolidated MDR has none).
- The Formex files stay in `data/raw/` as a cross-check only.

## Open decision: recitals
Recommendation: include them, flagged as `type=recital` with IDs like `GDPR-REC-4`. They explain the
purpose of the rules (useful for "why" questions), but have no legal force themselves, so answers
should label them. Cost: about 454 more chunks (173 + 180 + 101).
