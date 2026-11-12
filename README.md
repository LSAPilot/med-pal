# Regulatory Copilot

RAG system for regulatory questions about medical device software. You ask a question
(German or English) and get an answer based **only** on the original legal texts, with
every statement backed by a source (e.g. "MDR Art. 10(9)") and the original quote.

> **Status:** work in progress. Sections 1a, 1b and 2 done (setup, raw data, chunking, search). No LLM answering yet.

## Important notices
- **Not legal advice.** This is a research/portfolio tool. Do not rely on it for compliance decisions.
- **IEC 62304 is not included.** The standard is paid and its text may not be reused freely.
  The knowledge base covers only the freely available EU texts below.
- Questions are not stored.

## Sources
All texts come from [EUR-Lex](https://eur-lex.europa.eu/) / the EU Publications Office (Cellar API),
English versions. Reuse is permitted under Commission Decision 2011/833/EU with attribution.
The consolidated MDR text is documentation only and has no legal effect; the authentic texts are
those in the Official Journal. Text may be restructured (split into paragraphs) by this project.

| Law | CELEX |
|---|---|
| MDR, Regulation (EU) 2017/745 (consolidated 2026-01-01; recitals from the original act) | 02017R0745-20260101, 32017R0745 |
| GDPR, Regulation (EU) 2016/679 | 32016R0679 |
| AI Act, Regulation (EU) 2024/1689 | 32024R1689 |

## Setup
```bash
uv sync
uv run regulatory-helper fetch     # downloads raw files into data/raw/ (+ manifest.json with hashes)
uv run regulatory-helper ingest    # splits them into data/processed/chunks.jsonl (see docs/chunking.md)
uv run regulatory-helper index     # embeddings + BM25 index (downloads the embedding model once, a few minutes on CPU)
uv run regulatory-helper search "Rule 11 software classification" --mode hybrid   # bm25 | vector | hybrid, --k 6
uv run pytest
```
Copy `.env.example` to `.env` for the API key (needed from section 3 on, never commit it).

## Layout
See `docs/data-format.md` (source formats) and `docs/chunking.md` (chunk fields, ID scheme, statistics), `docs/embedding-model.md` and `docs/search-examples.md`. Code lives in `src/regulatory_helper/`.
