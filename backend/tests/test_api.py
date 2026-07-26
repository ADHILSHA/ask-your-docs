# tests/test_api.py
"""API-boundary tests: input validation, upload guards, and error mapping.

The store is injected via dependency override; embeddings are faked. These
assert HTTP behavior (status codes) rather than retrieval quality.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
from fastapi.testclient import TestClient
from openai import OpenAIError

import app.api.routes.documents as documents
import app.main as main
import app.rag.retrieval as retrieval
from app.auth.deps import get_current_user
from app.dependencies import get_vector_store
from app.models.user import User
from app.store import ChromaVectorStore

_TEST_USER = User(id="u-test", email="test@example.com", password_hash="x")


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ChromaVectorStore(persist_directory=tmp_path, collection_name="documents")
    main.app.dependency_overrides[get_vector_store] = lambda: store
    main.app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    monkeypatch.setattr(retrieval, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _txt(name, body):
    return ("files", (name, body, "text/plain"))


def test_corrupt_pdf_returns_400_not_500(client):
    resp = client.post("/upload", files=[("files", ("bad.pdf", b"%PDF-not-really", "application/pdf"))])
    assert resp.status_code == 400
    assert "extract" in resp.json()["detail"].lower()


def test_oversized_file_rejected(client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_BYTES", 50)
    resp = client.post("/upload", files=[_txt("big.txt", b"x" * 200)])
    assert resp.status_code == 413


def test_too_many_files_rejected(client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILES", 2)
    resp = client.post("/upload", files=[_txt(f"f{i}.txt", b"hi") for i in range(3)])
    assert resp.status_code == 400
    assert "Too many files" in resp.json()["detail"]


def _chat(client, messages, **extra):
    return client.post("/chat", json={"messages": messages, **extra})


def test_chat_rejects_blank_content(client):
    assert _chat(client, [{"role": "user", "content": ""}]).status_code == 422


def test_chat_rejects_out_of_range_k(client):
    msg = [{"role": "user", "content": "hi"}]
    assert _chat(client, msg, k=0).status_code == 422
    assert _chat(client, msg, k=9999).status_code == 422


def test_chat_requires_nonempty_history_ending_in_user(client):
    assert _chat(client, []).status_code == 422  # empty messages
    # last message must be from the user
    assert _chat(
        client, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    ).status_code == 422


def test_search_validates_params(client):
    assert client.get("/search", params={"q": "hi", "k": 0}).status_code == 422
    assert client.get("/search").status_code == 422  # q required


def test_openai_error_maps_to_502(client, monkeypatch):
    def boom(*a, **k):
        raise OpenAIError("simulated outage")

    monkeypatch.setattr(retrieval, "embed", boom)
    resp = client.post("/upload", files=[_txt("a.txt", b"hello world")])
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Upstream AI service error. Please try again."
