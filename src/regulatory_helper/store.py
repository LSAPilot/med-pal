"""Vector store interface and its NumPy implementation.

The rest of the code only talks to `VectorStore`, so a database-backed store (e.g. pgvector)
can replace `NumpyVectorStore` without changes elsewhere.

Files written by `NumpyVectorStore.save`:
  embeddings.npy  float32 matrix (n_chunks x dim), rows L2-normalised
  ids.json        chunk id per row, plus the embedding model name
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class VectorStore(ABC):
    @abstractmethod
    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        """Return up to k (chunk_id, cosine similarity) pairs, best first."""

    @abstractmethod
    def similarity(self, query_vec: np.ndarray, ids: list[str]) -> dict[str, float]:
        """Cosine similarity of the query to the given chunk ids (used for hits found by BM25 only)."""

    @abstractmethod
    def __len__(self) -> int: ...


def _normalise(vec: np.ndarray) -> np.ndarray:
    q = np.asarray(vec, dtype=np.float32).reshape(-1)
    return q / max(float(np.linalg.norm(q)), 1e-12)


class NumpyVectorStore(VectorStore):
    def __init__(self, ids: list[str], matrix: np.ndarray, model_name: str = ""):
        if len(ids) != matrix.shape[0]:
            raise ValueError("ids and matrix rows differ")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.ids = list(ids)
        self._row = {cid: i for i, cid in enumerate(self.ids)}
        self.matrix = (matrix / np.clip(norms, 1e-12, None)).astype(np.float32)
        self.model_name = model_name

    def __len__(self) -> int:
        return len(self.ids)

    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        k = min(k, len(self.ids))
        if k <= 0:
            return []
        sims = self.matrix @ _normalise(query_vec)  # cosine similarity, because both sides are normalised
        top = np.argpartition(-sims, k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        return [(self.ids[i], float(sims[i])) for i in top]

    def similarity(self, query_vec: np.ndarray, ids: list[str]) -> dict[str, float]:
        q = _normalise(query_vec)
        return {cid: float(self.matrix[self._row[cid]] @ q) for cid in ids}

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "embeddings.npy", self.matrix)
        (directory / "ids.json").write_text(json.dumps({"model": self.model_name, "ids": self.ids}), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> NumpyVectorStore:
        matrix = np.load(directory / "embeddings.npy")
        meta = json.loads((directory / "ids.json").read_text(encoding="utf-8"))
        return cls(meta["ids"], matrix, meta.get("model", ""))
