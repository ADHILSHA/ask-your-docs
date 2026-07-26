# tests/test_generation.py
"""Grounding/citation tests. The chat client is faked, so these assert prompt
construction and source extraction without hitting the network."""
from types import SimpleNamespace

import app.rag.generation as generation
from app.rag.chunking import Chunk

CHUNKS = [
    Chunk(text="Refunds are issued within 30 days.", filename="policy.pdf", chunk_index=0),
    Chunk(text="Shipping takes 5 business days.", filename="policy.pdf", chunk_index=1),
    Chunk(text="Support hours are 9 to 5.", filename="faq.md", chunk_index=0),
]


def _fake_chat(monkeypatch, answer_text, capture=None):
    def create(model, messages, temperature):
        if capture is not None:
            capture["model"] = model
            capture["messages"] = messages
            capture["temperature"] = temperature
        message = SimpleNamespace(content=answer_text)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(generation, "_client", lambda: client)


def test_build_context_numbers_chunks():
    ctx = generation.build_context(CHUNKS)
    assert ctx.startswith("[1] (source: policy.pdf #chunk 0)")
    assert "[2] (source: policy.pdf #chunk 1)" in ctx
    assert "[3] (source: faq.md #chunk 0)" in ctx


def test_extract_cited_sources_maps_dedupes_and_ignores_out_of_range():
    answer = "Refunds take 30 days [1]. See also [1] and hours [3]. Bogus [9]."
    sources = generation.extract_cited_sources(answer, CHUNKS)
    assert sources == [
        {"n": 1, "filename": "policy.pdf", "chunk_index": 0, "document_id": None},
        {"n": 3, "filename": "faq.md", "chunk_index": 0, "document_id": None},
    ]


def test_extract_no_citations_returns_empty():
    assert generation.extract_cited_sources("I couldn't find this in the documents.", CHUNKS) == []


def test_generate_answer_returns_answer_and_cited_sources(monkeypatch):
    capture = {}
    _fake_chat(monkeypatch, "Support is available 9 to 5 [3].", capture)
    result = generation.generate_answer("What are the support hours?", CHUNKS)

    assert result["answer"] == "Support is available 9 to 5 [3]."
    assert result["sources"] == [{"n": 3, "filename": "faq.md", "chunk_index": 0, "document_id": None}]
    # the hand-written system prompt must be passed through untouched
    assert capture["messages"][0]["role"] == "system"
    assert capture["messages"][0]["content"] == generation.SYSTEM_PROMPT
    assert capture["temperature"] == 0


def test_generate_answer_no_chunks_short_circuits_without_calling_model(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("chat model must not be called when there are no chunks")

    monkeypatch.setattr(generation, "_client", lambda: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=boom))
    ))
    result = generation.generate_answer("anything", [])
    assert result == {"answer": "I couldn't find this in the documents.", "sources": []}


def test_fallback_answer_yields_no_sources(monkeypatch):
    _fake_chat(monkeypatch, "I couldn't find this in the documents.")
    result = generation.generate_answer("unrelated question", CHUNKS)
    assert result["answer"] == "I couldn't find this in the documents."
    assert result["sources"] == []
