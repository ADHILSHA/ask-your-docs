# tests/test_grounding.py
"""End-to-end grounding tests over /ask.

Embeddings are faked with a tiny keyword->topic space so similarity scores are
deterministic and the threshold gate is exercised for real. The LLM is mocked
where it would be called; where the threshold gate should short-circuit, the
mock asserts it is NOT called.
"""
import os
import re

# app.main builds Settings (needs a key) via create_app() at import time.
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main
import app.rag.generation as generation
import app.rag.retrieval as retrieval
from app.dependencies import get_vector_store
from app.store import ChromaVectorStore

# A single fixture document with two clear topics: office and vacation.
FIXTURE_NAME = "handbook.md"
FIXTURE_TEXT = (
    "The office is open with staff on weekdays. "
    "Employees receive paid vacation days each year."
)

# Two-topic embedding: [office-hits, vacation-hits, epsilon]. Distinct words per
# topic, counted by set intersection, give clean cosine separation.
_OFFICE = {"office", "open", "opening", "hours", "desk", "staff"}
_VACATION = {"vacation", "paid", "days", "leave", "holiday"}


def _fake_embed(texts):
    vecs = []
    for text in texts:
        words = set(re.findall(r"[a-z]+", text.lower()))
        vecs.append([float(len(words & _OFFICE)), float(len(words & _VACATION)), 0.01])
    return vecs


def _mock_llm(monkeypatch, answer_text):
    """Wire the chat client to return a fixed answer (assert prompt untouched)."""
    def create(model, messages, temperature):
        assert messages[0]["content"] == generation.SYSTEM_PROMPT
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer_text))]
        )

    monkeypatch.setattr(
        generation,
        "_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
    )


def _mock_llm_must_not_be_called(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("LLM must not be called when the top score is below threshold")

    monkeypatch.setattr(
        generation,
        "_client",
        lambda: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=boom))
        ),
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Inject a tmp-dir store via dependency override, and fake embeddings by
    # patching the module attribute the routes call (retrieval.embed).
    store = ChromaVectorStore(persist_directory=tmp_path, collection_name="documents")
    main.app.dependency_overrides[get_vector_store] = lambda: store
    monkeypatch.setattr(retrieval, "embed", _fake_embed)

    c = TestClient(main.app)
    resp = c.post(
        "/upload",
        files=[("files", (FIXTURE_NAME, FIXTURE_TEXT.encode(), "text/markdown"))],
    )
    assert resp.status_code == 200
    yield c
    main.app.dependency_overrides.clear()


def test_answerable_question_returns_grounded_answer_with_sources(client, monkeypatch):
    _mock_llm(monkeypatch, "The office is open on weekdays with staff [1].")

    resp = client.post("/ask", json={"question": "What are the office opening hours?"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["answer"] != generation.NOT_FOUND_MESSAGE
    assert body["sources"] == [{"filename": FIXTURE_NAME, "chunk_index": 0}]


def test_out_of_scope_question_returns_not_found_and_skips_llm(client, monkeypatch):
    _mock_llm_must_not_be_called(monkeypatch)

    resp = client.post("/ask", json={"question": "How do I bake sourdough bread?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": generation.NOT_FOUND_MESSAGE, "sources": []}


def test_ambiguous_question_returns_clarifying_response_without_sources(client, monkeypatch):
    # The question clears the relevance gate (shares the "days" topic word), so
    # the LLM is consulted; we mock it returning a single clarifying question.
    _mock_llm(monkeypatch, "Do you mean paid vacation days or sick days?")

    resp = client.post("/ask", json={"question": "How many days do I get?"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["answer"].endswith("?")
    assert body["sources"] == []  # a clarifying question cites nothing
