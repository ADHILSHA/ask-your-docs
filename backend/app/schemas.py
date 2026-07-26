# app/schemas.py
"""Request/response models for the API layer.

Kept separate from domain logic so shapes can evolve independently as the API
grows. Responses are currently plain dicts; add models here when they need to
be typed/validated.
"""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    # Non-empty and length-bounded: reject blank questions before spending an
    # embedding call, and cap prompt size. k is bounded so a client can't ask
    # for a runaway number of results.
    question: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)
