# Embedding model (Section 2)

**Choice: `BAAI/bge-small-en-v1.5`** (33M parameters, 384 dimensions, 512 token input, runs on CPU).

## What was compared
Vector search only, on 16 hand-made English queries with known target chunks
(`scripts/eval_queries.py`, run with `scripts/compare_models.py`). Document text is the
`citation - title` line followed by the chunk text (see `Chunk.contextual_text`).
hit@6 = the expected chunk is among the top 6 (6 chunks go to the LLM later); MRR = mean of 1 / rank of the first expected chunk.

| Model | Params | Dim | Max input | Index time for 2632 chunks (CPU)* | hit@6 | MRR |
|---|---|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 22M | 384 | 256 tokens | 122 s | 0.81 | 0.712 |
| `BAAI/bge-small-en-v1.5` | 33M | 384 | 512 tokens | 232 s | **1.00** | 0.828 |
| `BAAI/bge-base-en-v1.5` | 110M | 768 | 512 tokens | 858 s | **1.00** | **0.927** |

\* Wall-clock times are rough: several runs shared the CPU with other jobs. Read them as relative, not absolute.

## Why bge-small
- **MiniLM is out.** It cuts input at 256 tokens (about 1000 characters) while our chunks go up to 2000 characters,
  so long paragraphs and annex points are embedded only in part. It also missed 3 of 16 expected chunks in the top 6.
- **bge-small vs bge-base:** both find every expected chunk in the top 6. bge-base ranks them higher on average (MRR 0.93 vs 0.83),
  but for the product that matters less: the LLM gets all 6 chunks, and the order within them changes little.
  bge-base costs 3 to 4 times more compute, doubles the index file (8 MB instead of 4 MB) and makes query embedding
  and cold start slower on the free Hugging Face CPU tier.
- **Small test set.** 16 queries cannot separate two models that both reach 1.00. The real comparison belongs to
  section 5. The model name sits in one constant (`retrieval.MODEL_NAME`); switching means running `index` again.
  If validation shows recall problems, bge-base is the first thing to try.
- The same 16 queries were used to pick the model and to illustrate search in `search-examples.md`.
  That is fine for orientation, but not an independent measurement.

## Usage notes
- bge models want a prefix on **queries** (not on documents): "Represent this sentence for searching relevant passages: ".
  It is set in `retrieval.QUERY_PREFIX`.
- Embeddings are L2-normalised, so cosine similarity is a plain matrix product (`store.NumpyVectorStore`).
- The model (about 130 MB) is downloaded from the Hugging Face Hub on first use and cached in `~/.cache/huggingface`.
