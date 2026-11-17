"""Test doubles shared by the test modules: a fixed clock, a tiny in-memory retriever and a fake Anthropic client."""
import json
from types import SimpleNamespace

import numpy as np

from regulatory_helper import retrieval
from regulatory_helper.chunking import Chunk
from regulatory_helper.store import NumpyVectorStore


class Clock:
    """Injectable clock; tests move time by setting `t`."""

    def __init__(self, t=1_700_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def make_chunk(i: str, text: str) -> Chunk:
    return Chunk(i, "MDR", "article", "1", "Title", "1", text, "https://eur-lex.europa.eu/x", f"MDR {i}")


def fake_retriever():
    chunks = [
        make_chunk("c1", "software classification rule class IIa"),
        make_chunk("c2", "obligations of manufacturers risk management"),
        make_chunk("c3", "right to erasure of personal data"),
    ]
    vecs = {"c1": [1, 0, 0], "c2": [0, 1, 0], "c3": [0, 0, 1]}
    store = NumpyVectorStore([c.id for c in chunks], np.array([vecs[c.id] for c in chunks], dtype=np.float32))
    toks = [retrieval.tokenize(retrieval.doc_text(c)) for c in chunks]

    def embed(q):  # "erasure" queries point to c3, everything else to c1
        return np.array([0, 0, 1] if "erasure" in q else [1, 0, 0], dtype=np.float32)

    return retrieval.Retriever(chunks, store, [c.id for c in chunks], toks, embed_query_fn=embed)


class FakeClient:
    """Stands in for anthropic.Anthropic. Replies are consumed in order; every request is recorded."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        text = self.replies.pop(0)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            stop_reason="end_turn",
        )


def ans_json(ids, found=True, answer="Software can be a device [c1]."):
    return json.dumps({"found": found, "answer": answer, "used_ids": ids})
