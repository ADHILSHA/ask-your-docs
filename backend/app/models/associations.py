# app/models/associations.py
"""Association tables (many-to-many links)."""
from sqlalchemy import Column, ForeignKey, Table

from app.db import Base

# Which documents are in a conversation's context. A document can belong to
# many conversations; a conversation draws its answers from these documents.
conversation_documents = Table(
    "conversation_documents",
    Base.metadata,
    Column("conversation_id", ForeignKey("conversations.id"), primary_key=True),
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
)
