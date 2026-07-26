# tests/test_documents.py
"""End-to-end per-user isolation over the real auth + upload + documents routes.
Two real users (real signup/JWT), faked embeddings, isolated SQLite + Chroma."""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
import app.rag.retrieval as retrieval
from app.db import Base, get_db
from app.dependencies import get_document_storage, get_vector_store
from app.storage import LocalStorage
from app.store import ChromaVectorStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    store = ChromaVectorStore(persist_directory=tmp_path)
    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[get_vector_store] = lambda: store
    main.app.dependency_overrides[get_document_storage] = lambda: LocalStorage(tmp_path / "storage")
    monkeypatch.setattr(retrieval, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _signup(client, email):
    r = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload(client, headers, name, body):
    return client.post(
        "/upload", headers=headers, files=[("files", (name, body.encode(), "text/plain"))]
    )


def test_documents_are_isolated_per_user(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")

    assert _upload(client, alice, "cats.txt", "cats are wonderful pets").status_code == 200
    assert _upload(client, bob, "dogs.txt", "dogs are loyal pets").status_code == 200

    a_docs = client.get("/documents", headers=alice).json()
    b_docs = client.get("/documents", headers=bob).json()
    assert [d["filename"] for d in a_docs] == ["cats.txt"]
    assert [d["filename"] for d in b_docs] == ["dogs.txt"]


def test_cannot_delete_another_users_document(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")
    _upload(client, bob, "dogs.txt", "dogs are loyal pets")

    bob_doc_id = client.get("/documents", headers=bob).json()[0]["id"]

    # Alice cannot delete Bob's document (404 hides its existence).
    assert client.delete(f"/documents/{bob_doc_id}", headers=alice).status_code == 404
    # Bob can delete his own.
    assert client.delete(f"/documents/{bob_doc_id}", headers=bob).status_code == 204
    assert client.get("/documents", headers=bob).json() == []


def test_uploaded_file_is_downloadable(client):
    alice = _signup(client, "alice@example.com")
    _upload(client, alice, "cats.txt", "cats are wonderful pets")
    doc = client.get("/documents", headers=alice).json()[0]

    r = client.get(f"/documents/{doc['id']}/download", headers=alice)
    assert r.status_code == 200
    assert r.content == b"cats are wonderful pets"


def test_cannot_download_another_users_file(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")
    _upload(client, bob, "dogs.txt", "dogs are loyal")
    bob_doc = client.get("/documents", headers=bob).json()[0]

    assert client.get(f"/documents/{bob_doc['id']}/download", headers=alice).status_code == 404


def test_upload_tags_document_with_conversation(client):
    alice = _signup(client, "alice@example.com")
    conv_id = client.post("/conversations", headers=alice).json()["id"]

    r = client.post(
        "/upload",
        headers=alice,
        data={"conversation_id": conv_id},
        files=[("files", ("cats.txt", b"cats are pets", "text/plain"))],
    )
    assert r.status_code == 200

    doc = client.get("/documents", headers=alice).json()[0]
    assert doc["conversation_id"] == conv_id


def test_upload_rejects_another_users_conversation(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")
    bob_conv = client.post("/conversations", headers=bob).json()["id"]

    r = client.post(
        "/upload",
        headers=alice,
        data={"conversation_id": bob_conv},
        files=[("files", ("cats.txt", b"cats are pets", "text/plain"))],
    )
    assert r.status_code == 404


def test_documents_requires_auth(client):
    assert client.get("/documents").status_code == 401


def test_conversations_are_isolated_per_user(client):
    alice = _signup(client, "alice@example.com")
    bob = _signup(client, "bob@example.com")
    conv = client.post("/conversations", headers=bob).json()

    # Alice can neither read nor post into Bob's conversation.
    assert client.get(f"/conversations/{conv['id']}/messages", headers=alice).status_code == 404
    assert (
        client.post(
            "/chat", headers=alice, json={"conversation_id": conv["id"], "message": "hi"}
        ).status_code
        == 404
    )
