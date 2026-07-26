# app/config.py
"""Typed application settings, loaded from the environment (or a local .env).

Single source of truth for everything the backend needs to reach OpenAI and
tune retrieval. Field names map to the UPPER_CASE env vars case-insensitively,
so `openai_api_key` reads `OPENAI_API_KEY`. See .env.example.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required — the app cannot embed or answer without it, so fail fast and
    # loud at startup rather than silently at the first OpenAI call.
    openai_api_key: str

    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # Cosine-similarity floor for treating a chunk as relevant. Below this we
    # return "I couldn't find this in the documents." rather than guess.
    similarity_threshold: float = 0.35

    # Comma-separated in the environment, e.g.
    # "http://localhost:3000,https://ask-your-docs.vercel.app".
    # Kept as a raw string and split on demand: pydantic-settings would try to
    # JSON-decode a `list[str]` env value and choke on the comma form.
    allowed_origins: str = "http://localhost:3000"

    # Database. Defaults to a local SQLite file so the app runs with no external
    # DB in dev; Render sets a Postgres URL. Same SQLAlchemy code either way.
    database_url: str = "sqlite:///./ask_your_docs.db"

    # Auth. JWT_SECRET MUST be overridden with a strong random value in
    # production — the default is a dev placeholder only.
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 24  # 1 day

    # Raw-file storage. "local" writes to disk (dev); "s3" uses Cloudflare R2
    # (S3-compatible). R2 vars are only needed when storage_backend == "s3".
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_endpoint: str = ""  # R2 endpoint, e.g. https://<account>.r2.cloudflarestorage.com
    s3_region: str = "auto"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so settings are parsed once per process."""
    return Settings()
