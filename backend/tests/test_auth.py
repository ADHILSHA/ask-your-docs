# tests/test_auth.py
"""Auth flows (signup/login/me) and route guarding, against an isolated
SQLite DB injected via the get_db dependency."""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
from app.db import Base, get_db

CREDS = {"email": "user@example.com", "password": "supersecret"}


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/auth.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_db
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_signup_returns_token(client):
    r = client.post("/auth/signup", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_duplicate_email_conflicts(client):
    assert client.post("/auth/signup", json=CREDS).status_code == 201
    r = client.post("/auth/signup", json=CREDS)
    assert r.status_code == 409


def test_login_success_and_me(client):
    client.post("/auth/signup", json=CREDS)
    r = client.post("/auth/login", json=CREDS)
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == CREDS["email"]


def test_login_wrong_password_401(client):
    client.post("/auth/signup", json=CREDS)
    r = client.post("/auth/login", json={**CREDS, "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_email_401(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever12"})
    assert r.status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


def test_guarded_route_requires_auth(client):
    # Valid body, no token -> 401 (only auth is missing; unambiguous).
    assert client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    # /auth/me has no body: missing and garbage tokens both -> 401.
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_valid_token_passes_guard(client):
    token = client.post("/auth/signup", json=CREDS).json()["access_token"]
    # Authenticated but missing files -> 422 (not 401), proving the guard passed.
    r = client.post("/upload", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
