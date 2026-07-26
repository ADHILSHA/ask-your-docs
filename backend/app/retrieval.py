# app/retrieval.py
"""Embeddings (and, later, query-side retrieval).

The OpenAI client lives here, server-side only, with the key read from config —
never exposed to the frontend. `embed` turns a batch of texts into vectors in
as few API calls as possible: the embeddings endpoint accepts a list per call,
so we group inputs rather than making one call per chunk.
"""
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings

# OpenAI caps inputs per embeddings request; 128 is comfortably under the limit
# and keeps a typical document to a single call while staying safe for large ones.
EMBED_BATCH_SIZE = 128


@lru_cache
def _client() -> OpenAI:
    """One OpenAI client per process; key from server-side config only."""
    return OpenAI(api_key=get_settings().openai_api_key)


def embed(texts: list[str]) -> list[list[float]]:
    """Embed `texts` with the configured model, batched, order preserved.

    Returns one vector per input text, in the same order as `texts`.
    """
    if not texts:
        return []

    model = get_settings().embedding_model
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        response = _client().embeddings.create(model=model, input=batch)
        # Sort by index defensively so vectors line up with inputs even if the
        # API returns them out of order.
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend(item.embedding for item in ordered)
    return vectors
