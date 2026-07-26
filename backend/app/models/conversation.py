# app/models/conversation.py
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.associations import conversation_documents

if TYPE_CHECKING:
    from app.models.document import Document


def _uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False, default="New conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Documents in this conversation's context (many-to-many).
    documents: Mapped[list["Document"]] = relationship(
        secondary=conversation_documents, lazy="selectin"
    )
