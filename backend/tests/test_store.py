# tests/test_store.py
"""Store round-trip, per-user isolation, delete, and reset — against a real
Chroma in a tmp dir."""
import pytest

from app.rag.chunking import Chunk
from app.store import ChromaVectorStore


def _seed(store, user_id, text, *, document_id="doc1", chunk_index=0, embedding=(1.0, 0.0)):
    store.add_chunks(
        user_id,
        document_id,
        [Chunk(text=text, filename="a.txt", chunk_index=chunk_index)],
        [list(embedding)],
    )


def test_add_then_query_returns_stored_chunk(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store, "u1", "hello world")
    results = store.query("u1", [1.0, 0.0], k=5)
    assert len(results) == 1
    chunk, score = results[0]
    assert chunk.text == "hello world"
    assert score > 0.99


def test_query_is_isolated_per_user(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store, "u1", "user one doc")
    _seed(store, "u2", "user two doc")
    # Same query vector; the where-filter must keep users apart.
    assert [c.text for c, _ in store.query("u1", [1.0, 0.0], k=5)] == ["user one doc"]
    assert [c.text for c, _ in store.query("u2", [1.0, 0.0], k=5)] == ["user two doc"]


def test_delete_document_removes_only_that_document(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store, "u1", "doc one", document_id="d1")
    _seed(store, "u1", "doc two", document_id="d2")
    store.delete_document("u1", "d1")
    assert [c.text for c, _ in store.query("u1", [1.0, 0.0], k=5)] == ["doc two"]


def test_reset_empties_the_store(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    _seed(store, "u1", "x")
    assert store.query("u1", [1.0, 0.0], k=5)
    store.reset()
    assert store.query("u1", [1.0, 0.0], k=5) == []


def test_length_mismatch_raises(tmp_path):
    store = ChromaVectorStore(persist_directory=tmp_path)
    with pytest.raises(ValueError):
        store.add_chunks("u1", "d1", [Chunk("a", "f.txt", 0)], [])
