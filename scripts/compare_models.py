"""Compare embedding model candidates on scripts/eval_queries.py (vector search only).

Usage: uv run python scripts/compare_models.py [substring of model name ...]
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from eval_queries import QUERIES, is_hit  # noqa: E402

from regulatory_helper import retrieval  # noqa: E402
from regulatory_helper.chunking import read_chunks  # noqa: E402

CANDIDATES = [
    # (name, query prefix)
    ("sentence-transformers/all-MiniLM-L6-v2", ""),
    ("BAAI/bge-small-en-v1.5", retrieval.QUERY_PREFIX),
    ("BAAI/bge-base-en-v1.5", retrieval.QUERY_PREFIX),
]

if len(sys.argv) > 1:
    CANDIDATES = [c for c in CANDIDATES if any(a in c[0] for a in sys.argv[1:])]

chunks = read_chunks()
texts = [retrieval.doc_text(c) for c in chunks]
ids = [c.id for c in chunks]
for name, prefix in CANDIDATES:
    retrieval._model = None
    t0 = time.time()
    model = retrieval.get_model(name)
    mx = model.max_seq_length
    emb = model.encode(texts, batch_size=32, normalize_embeddings=True)
    t_embed = time.time() - t0
    hit6 = rr = 0.0
    for q, gold in QUERIES:
        qv = model.encode(prefix + q, normalize_embeddings=True)
        order = np.argsort(-(emb @ qv))[:50]
        ranks = [r for r, i in enumerate(order, 1) if is_hit(ids[i], gold)]
        if ranks and ranks[0] <= 6:
            hit6 += 1
        rr += 1 / ranks[0] if ranks else 0
    n = len(QUERIES)
    print(f"{name}: max_seq={mx} dim={emb.shape[1]} index_time={t_embed:.0f}s hit@6={hit6/n:.2f} MRR={rr/n:.3f}", flush=True)
