# app/schemas.py
"""Request/response models for the API layer.

Kept separate from domain logic so shapes can evolve independently as the API
grows.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    conversation_id: str
    # The new user message. Non-empty and length-bounded; k bounds retrieval.
    message: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    sources: list
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str | None
    filename: str
    char_count: int
    chunk_count: int
    created_at: datetime
