# app/dependencies.py
"""FastAPI dependency providers.

Centralizes construction of shared resources so routes receive them via
`Depends(...)` instead of reaching for module globals. This is the seam that
keeps routes thin and makes the store overridable in tests (dependency_overrides)
and swappable later (e.g. per-tenant) without touching route code.
"""
from functools import lru_cache

from app.store import ChromaVectorStore, VectorStore


@lru_cache
def get_vector_store() -> VectorStore:
    """Process-wide vector store, built lazily on first request."""
    return ChromaVectorStore()
