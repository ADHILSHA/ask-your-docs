# app/dependencies.py
"""FastAPI dependency providers.

Centralizes construction of shared resources so routes receive them via
`Depends(...)` instead of reaching for module globals. This is the seam that
keeps routes thin and makes the store overridable in tests (dependency_overrides)
and swappable later (e.g. per-tenant) without touching route code.
"""
from functools import lru_cache

from app.config import get_settings
from app.storage import DocumentStorage, LocalStorage, S3Storage
from app.store import ChromaVectorStore, VectorStore


@lru_cache
def get_vector_store() -> VectorStore:
    """Process-wide vector store, built lazily on first request.

    Chroma Cloud when the CHROMA_* vars are set (durable across deploys),
    otherwise in-process Chroma persisting to backend/.chroma.
    """
    settings = get_settings()
    if settings.chroma_api_key:
        return ChromaVectorStore.cloud(
            api_key=settings.chroma_api_key,
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
        )
    return ChromaVectorStore()


@lru_cache
def get_document_storage() -> DocumentStorage:
    """Raw-file storage, chosen by config: local disk (dev) or R2 (prod)."""
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint,
            region=settings.s3_region,
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
        )
    return LocalStorage()
