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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
import app.rag.generation as generation
import app.rag.retrieval as retrieval
from app.auth.deps import get_current_user
from app.db import Base, get_db
from app.dependencies import get_document_storage, get_vector_store
from app.models.user import User
from app.storage import LocalStorage
from app.store import ChromaVectorStore

_TEST_USER = User(id="u-test", email="test@example.com", password_hash="x")


def _override_db(tmp_path):
    """Install an isolated SQLite DB (for Document rows) and return the override."""
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    return override

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
    main.app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    main.app.dependency_overrides[get_db] = _override_db(tmp_path)
    main.app.dependency_overrides[get_document_storage] = lambda: LocalStorage(tmp_path / "storage")
    monkeypatch.setattr(retrieval, "embed", _fake_embed)

    c = TestClient(main.app)
    resp = c.post(
        "/upload",
        files=[("files", (FIXTURE_NAME, FIXTURE_TEXT.encode(), "text/markdown"))],
    )
    assert resp.status_code == 200
    yield c
    main.app.dependency_overrides.clear()


def _ask(client, text):
    """Single-turn chat: a fresh conversation with one message (no history)."""
    conv = client.post("/conversations").json()
    return client.post("/chat", json={"conversation_id": conv["id"], "message": text})


def test_answerable_question_returns_grounded_answer_with_sources(client, monkeypatch):
    _mock_llm(monkeypatch, "The office is open on weekdays with staff [1].")

    resp = _ask(client, "What are the office opening hours?")
    assert resp.status_code == 200
    body = resp.json()

    assert body["answer"] != generation.NOT_FOUND_MESSAGE
    assert body["sources"] == [{"filename": FIXTURE_NAME, "chunk_index": 0}]


def test_out_of_scope_question_returns_not_found_and_skips_llm(client, monkeypatch):
    _mock_llm_must_not_be_called(monkeypatch)

    resp = _ask(client, "How do I bake sourdough bread?")
    assert resp.status_code == 200
    assert resp.json() == {"answer": generation.NOT_FOUND_MESSAGE, "sources": []}


def test_ambiguous_question_returns_clarifying_response_without_sources(client, monkeypatch):
    # The question clears the relevance gate (shares the "days" topic word), so
    # the LLM is consulted; we mock it returning a single clarifying question.
    _mock_llm(monkeypatch, "Do you mean paid vacation days or sick days?")

    resp = _ask(client, "How many days do I get?")
    assert resp.status_code == 200
    body = resp.json()

    assert body["answer"].endswith("?")
    assert body["sources"] == []  # a clarifying question cites nothing


def test_followup_is_condensed_then_answered_grounded(client, monkeypatch):
    _mock_llm(monkeypatch, "The office has staff on weekdays [1].")
    conv = client.post("/conversations").json()["id"]

    # First turn establishes history (no condensation call with empty history).
    client.post("/chat", json={"conversation_id": conv, "message": "Tell me about the office."})

    # Second turn: a short follow-up is rewritten to a standalone question via
    # condensation (mocked), then retrieved + answered grounded.
    monkeypatch.setattr(
        generation, "condense_question", lambda history, latest: "How many office staff are there?"
    )
    resp = client.post("/chat", json={"conversation_id": conv, "message": "and the staff?"})
    assert resp.status_code == 200
    assert resp.json()["sources"] == [{"filename": FIXTURE_NAME, "chunk_index": 0}]


def test_chat_persists_messages_to_the_conversation(client, monkeypatch):
    _mock_llm(monkeypatch, "The office is open on weekdays [1].")
    conv = client.post("/conversations").json()["id"]
    client.post("/chat", json={"conversation_id": conv, "message": "office hours?"})

    msgs = client.get(f"/conversations/{conv}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "office hours?"
    assert msgs[1]["sources"] == [{"filename": FIXTURE_NAME, "chunk_index": 0}]
