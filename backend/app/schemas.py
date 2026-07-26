# app/schemas.py
"""Request/response models for the API layer.

Kept separate from domain logic so shapes can evolve independently as the API
grows. Responses are currently plain dicts; add models here when they need to
be typed/validated.
"""
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    k: int = 5
