import numpy as np
import pytest

from regulatory_helper import retrieval
from regulatory_helper.chunking import OUT_PATH, Chunk, read_chunks
from regulatory_helper.store import NumpyVectorStore, VectorStore


def make_chunk(i: str, text: str) -> Chunk:
    return Chunk(i, "MDR", "article", "1", "Title", "1", text, "https://eur-lex.europa.eu/x", f"MDR {i}")


def test_rrf_prefers_items_high_in_both_lists():
    a = [("x", 9.0), ("y", 8.0), ("z", 1.0)]
    b = [("y", 0.9), ("w", 0.8), ("x", 0.1)]
    fused = retrieval.rrf([a, b])
    assert fused[0][0] == "y"
    assert {i for i, _ in fused} == {"x", "y", "z", "w"}


def test_tokenize_keeps_numbers_drops_stopwords():
    assert retrieval.tokenize("The class IIb software of Article 10(9)") == ["class", "iib", "software", "article", "10", "9"]


def test_numpy_store_cosine_and_roundtrip(tmp_path):
    m = np.array([[1, 0, 0], [0, 2, 0], [1, 1, 0]], dtype=np.float32)
    store = NumpyVectorStore(["a", "b", "c"], m, "test")
    assert isinstance(store, VectorStore)
    res = store.search(np.array([0, 5, 0]), k=2)
    assert res[0][0] == "b" and abs(res[0][1] - 1.0) < 1e-6
    assert res[1][0] == "c"
    store.save(tmp_path)
    again = NumpyVectorStore.load(tmp_path)
    assert again.ids == ["a", "b", "c"] and again.search(np.array([1, 0, 0]), 1)[0][0] == "a"


def test_similarity_for_given_ids():
    store = NumpyVectorStore(["a", "b"], np.array([[1, 0], [1, 1]], dtype=np.float32))
    sim = store.similarity(np.array([2, 0]), ["b", "a"])
    assert abs(sim["a"] - 1.0) < 1e-6 and abs(sim["b"] - 0.7071) < 1e-3


def test_hybrid_gives_cosine_for_bm25_only_hits():
    r = fake_retriever()
    # "risk management" matches c2 only via BM25; its cosine to the query vector [1,0,0] is 0
    hits = {h.chunk.id: h for h in r.search("risk management", mode="hybrid", k=3)}
    assert hits["c2"].cosine == pytest.approx(0.0)
    assert all(h.cosine is not None for h in hits.values())


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


@pytest.mark.parametrize("mode", retrieval.MODES)
def test_modes_return_ranked_hits(mode):
    r = fake_retriever()
    hits = r.search("erasure of personal data", mode=mode, k=2)
    assert hits[0].chunk.id == "c3" and hits[0].rank == 1
    assert len(hits) <= 2
    if mode != "bm25":
        assert hits[0].cosine is not None and hits[0].cosine > 0.99


def test_bm25_exact_term_and_default_k():
    r = fake_retriever()
    assert r.search("risk management", mode="bm25")[0].chunk.id == "c2"
    assert len(r.search("software", mode="hybrid")) <= retrieval.DEFAULT_K


def test_invalid_mode():
    with pytest.raises(ValueError):
        fake_retriever().search("x", mode="nope")


# --- integration with the real index (skipped if `index` has not been run) -------------
needs_index = pytest.mark.skipif(
    not (retrieval.PROCESSED / "index_meta.json").exists(), reason="run `regulatory-helper index` first"
)


@pytest.fixture(scope="module")
def real():
    return retrieval.Retriever.load()


@needs_index
@pytest.mark.parametrize("mode", ["bm25", "hybrid"])
def test_rule_11_found_in_top6(real, mode):
    ids = [h.chunk.id for h in real.search("Rule 11 software classification", mode=mode, k=6)]
    assert any(i.startswith("MDR-ANNEX-VIII-6.3") for i in ids), ids


@needs_index
def test_vector_finds_content_question(real):
    ids = [h.chunk.id for h in real.search("right of the data subject to erasure of personal data", mode="vector")]
    assert any(i.startswith("GDPR-17") for i in ids), ids


@needs_index
def test_index_matches_chunks(real):
    assert len(real.store) == len(read_chunks(OUT_PATH)) == len(real.chunks)


def test_store_search_with_k_zero_is_empty():
    store = NumpyVectorStore(["a", "b"], np.eye(2, dtype=np.float32))
    assert store.search(np.array([1.0, 0.0]), 0) == []
