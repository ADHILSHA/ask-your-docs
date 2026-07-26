# tests/test_config.py
"""The production guard on JWT_SECRET."""
import pytest
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings

_PROD_DB = "postgresql://u:p@host/db"


def test_prod_config_rejects_default_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(openai_api_key="x", database_url=_PROD_DB, jwt_secret=DEV_JWT_SECRET)


def test_prod_config_accepts_strong_jwt_secret():
    s = Settings(openai_api_key="x", database_url=_PROD_DB, jwt_secret="a-strong-secret")
    assert s.jwt_secret == "a-strong-secret"


def test_local_dev_allows_default_jwt_secret():
    s = Settings(
        openai_api_key="x",
        database_url="sqlite:///./x.db",
        storage_backend="local",
        jwt_secret=DEV_JWT_SECRET,
    )
    assert s.jwt_secret == DEV_JWT_SECRET


def _url(raw: str) -> str:
    return Settings(openai_api_key="x", database_url=raw, jwt_secret="strong").database_url


def test_database_url_normalized_to_psycopg():
    assert _url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert _url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    # already-qualified and sqlite pass through unchanged
    assert _url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert _url("sqlite:///./x.db") == "sqlite:///./x.db"
