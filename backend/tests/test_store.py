# tests/test_store.py
"""Store round-trip and reset behavior, against a real Chroma in a tmp dir."""
from app.rag.chunking import Chunk
from app.store import ChromaVectorStore


def _seed(store):
    chunks = [
        Chunk(text="alpha", filename="a.txt", chunk_index=0),
        Chunk(text="beta", filename="a.txt", chunk_index=1),
    ]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    store.add_chunks(chunks, embeddings)


def test_add_then_query_returns_stored_chunk(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store)
    results = store.query([1.0, 0.0], k=1)
    assert len(results) == 1
    chunk, score = results[0]
    assert (chunk.filename, chunk.chunk_index) == ("a.txt", 0)
    assert score > 0.99


def test_reset_empties_the_store(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store)
    assert store.query([1.0, 0.0], k=5)  # non-empty before

    store.reset()

    assert store.query([1.0, 0.0], k=5) == []  # nothing left


def test_usable_after_reset(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store)
    store.reset()
    # the collection was recreated, so it still accepts writes/reads
    _seed(store)
    assert len(store.query([0.0, 1.0], k=5)) >= 1
