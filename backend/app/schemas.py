# app/schemas.py
"""Request/response models for the API layer.

Kept separate from domain logic so shapes can evolve independently as the API
grows. Responses are currently plain dicts; add models here when they need to
be typed/validated.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    # The full (client-held) conversation. Bounded so a client can't send a
    # runaway history or an oversized k. The last message must be the user's —
    # that's the turn we answer.
    messages: list[Message] = Field(min_length=1, max_length=50)
    k: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def _last_message_is_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    char_count: int
    chunk_count: int
    created_at: datetime
