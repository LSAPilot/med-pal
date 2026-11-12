"""Retrieval: BM25, vector search and hybrid (Reciprocal Rank Fusion).

Index artefacts live in data/processed/:
  chunks.jsonl     (section 1b)
  embeddings.npy + ids.json   vector store
  bm25.json        tokenised corpus (the BM25 index is rebuilt from it at load time, which takes milliseconds)
  index_meta.json  model name, chunk count, text hash (to detect a stale index)
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from .chunking import OUT_PATH, Chunk, read_chunks
from .store import NumpyVectorStore, VectorStore

PROCESSED = OUT_PATH.parent
MODES = ("bm25", "vector", "hybrid")
DEFAULT_K = 6
# Embedding model, see docs/embedding-model.md
MODEL_NAME = "BAAI/bge-small-en-v1.5"
# bge models expect this prefix on queries (not on documents) for retrieval
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RRF_K = 60  # standard constant of Reciprocal Rank Fusion
CANDIDATES = 50  # depth of each ranked list that goes into the fusion

_STOPWORDS = frozenset(
    "a an the of to in on for and or by with as at is are be shall may that this these those it its from "
    "which such any under into than their other not no".split()
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens without stop words. Numbers are kept (articles, class IIb, 2017/745)."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def doc_text(c: Chunk) -> str:
    """Text that is indexed for a chunk: citation and title in front, as decided in the architecture."""
    return c.contextual_text()


@dataclass
class Hit:
    chunk: Chunk
    score: float  # mode specific: BM25 score, cosine similarity, or RRF score
    rank: int  # 1-based
    cosine: float | None = None  # cosine similarity of the chunk to the query (hybrid/vector), for section 3's threshold


# --------------------------------------------------------------------------
# embedding
# --------------------------------------------------------------------------

_model = None


def get_model(name: str = MODEL_NAME):
    global _model
    if _model is None or getattr(_model, "_name", None) != name:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(name, device="cpu")
        _model._name = name
    return _model


def embed_documents(texts: list[str], name: str = MODEL_NAME, batch_size: int = 32) -> np.ndarray:
    model = get_model(name)
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=len(texts) > 100)


def embed_query(text: str, name: str = MODEL_NAME) -> np.ndarray:
    return get_model(name).encode(QUERY_PREFIX + text, normalize_embeddings=True)


# --------------------------------------------------------------------------
# index building
# --------------------------------------------------------------------------


def _hash_chunks(chunks: list[Chunk]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode())
        h.update(doc_text(c).encode())
    return h.hexdigest()


def build_index(chunks_path: Path = OUT_PATH, out_dir: Path = PROCESSED, model_name: str = MODEL_NAME) -> dict:
    chunks = read_chunks(chunks_path)
    texts = [doc_text(c) for c in chunks]
    matrix = embed_documents(texts, model_name)
    NumpyVectorStore([c.id for c in chunks], matrix, model_name).save(out_dir)
    (out_dir / "bm25.json").write_text(
        json.dumps({"ids": [c.id for c in chunks], "tokens": [tokenize(t) for t in texts]}), encoding="utf-8"
    )
    meta = {"model": model_name, "chunks": len(chunks), "dim": int(matrix.shape[1]), "hash": _hash_chunks(chunks)}
    (out_dir / "index_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


# --------------------------------------------------------------------------
# searching
# --------------------------------------------------------------------------


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        store: VectorStore | None,
        bm25_ids: list[str] | None,
        bm25_tokens: list[list[str]] | None,
        model_name: str = MODEL_NAME,
        embed_query_fn=None,
    ):
        self.chunks = {c.id: c for c in chunks}
        self.store = store
        self.model_name = model_name
        self._embed_query = embed_query_fn or (lambda q: embed_query(q, model_name))
        self.bm25_ids = bm25_ids
        self.bm25 = BM25Okapi(bm25_tokens) if bm25_tokens else None

    @classmethod
    def load(cls, directory: Path = PROCESSED, chunks_path: Path | None = None) -> "Retriever":
        chunks = read_chunks(chunks_path or directory / "chunks.jsonl")
        meta = json.loads((directory / "index_meta.json").read_text())
        if meta["hash"] != _hash_chunks(chunks):
            raise RuntimeError("index is stale: chunks.jsonl changed, run `regulatory-helper index` again")
        store = NumpyVectorStore.load(directory)
        bm = json.loads((directory / "bm25.json").read_text())
        return cls(chunks, store, bm["ids"], bm["tokens"], meta["model"])

    # --- single rankings -------------------------------------------------
    def bm25_ranking(self, query: str, k: int) -> list[tuple[str, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[:k]
        return [(self.bm25_ids[i], float(scores[i])) for i in order if scores[i] > 0]

    def vector_ranking(self, query: str, k: int) -> list[tuple[str, float]]:
        return self.store.search(self._embed_query(query), k)

    # --- public API ------------------------------------------------------
    def search(self, query: str, mode: str = "hybrid", k: int = DEFAULT_K) -> list[Hit]:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        if mode == "bm25":
            ranked = self.bm25_ranking(query, k)
            return [Hit(self.chunks[i], s, r) for r, (i, s) in enumerate(ranked, 1)]
        qvec = self._embed_query(query)
        vec = self.store.search(qvec, max(k, CANDIDATES) if mode == "hybrid" else k)
        cos = dict(vec)
        if mode == "vector":
            return [Hit(self.chunks[i], s, r, cosine=s) for r, (i, s) in enumerate(vec[:k], 1)]
        fused = rrf([self.bm25_ranking(query, CANDIDATES), vec])
        hits = []
        for r, (i, s) in enumerate(fused[:k], 1):
            c = cos.get(i)
            if c is None:  # found by BM25 only: compute its cosine directly
                c = float(self.store.matrix[self.store.ids.index(i)] @ (qvec / np.linalg.norm(qvec))) if hasattr(self.store, "matrix") else None
            hits.append(Hit(self.chunks[i], s, r, cosine=c))
        return hits


def rrf(rankings: list[list[tuple[str, float]]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score(d) = sum over lists of 1 / (k + rank(d)).

    Only ranks are used, so scores of different scales (BM25 vs cosine) can be combined
    without normalising them. A chunk that is high in both lists wins.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, (cid, _) in enumerate(ranking, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])
