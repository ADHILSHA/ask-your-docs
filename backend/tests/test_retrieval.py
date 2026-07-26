# tests/test_retrieval.py
"""Offline tests for embedding batching — the OpenAI client is faked, so these
assert call-batching and ordering without hitting the network."""
from types import SimpleNamespace

import app.rag.retrieval as retrieval


class _FakeEmbeddings:
    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, model, input):
        self._recorder.append({"model": model, "size": len(input)})
        # Return items out of order to prove embed() sorts by index. Each vector
        # encodes its input's global position so order is verifiable.
        base = self._recorder[-1].get("_base", 0)
        data = [
            SimpleNamespace(index=i, embedding=[float(base + i)])
            for i in range(len(input))
        ]
        return SimpleNamespace(data=list(reversed(data)))


class _FakeClient:
    def __init__(self, recorder):
        self.embeddings = _FakeEmbeddings(recorder)


def _install_fake(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(retrieval, "_client", lambda: _FakeClient(calls))
    return calls


def test_embed_batches_multiple_texts_into_few_calls(monkeypatch):
    calls = _install_fake(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    texts = [f"chunk {i}" for i in range(300)]
    vectors = retrieval.embed(texts)

    # 300 inputs, batch size 128 -> 3 calls, NOT 300.
    assert len(calls) == 3
    assert [c["size"] for c in calls] == [128, 128, 44]
    assert len(vectors) == 300
    # order preserved within each batch despite reversed API response
    assert vectors[0] == [0.0]
    assert vectors[127] == [127.0]


def test_embed_empty_makes_no_calls(monkeypatch):
    calls = _install_fake(monkeypatch)
    assert retrieval.embed([]) == []
    assert calls == []


def test_embed_uses_configured_model(monkeypatch):
    calls = _install_fake(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    # get_settings is lru_cached; clear so the env above takes effect.
    from app.config import get_settings

    get_settings.cache_clear()

    retrieval.embed(["hello"])
    assert calls[0]["model"] == "text-embedding-3-small"

    get_settings.cache_clear()
