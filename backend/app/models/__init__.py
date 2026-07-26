# app/models/__init__.py
"""ORM models. Importing this package registers all tables on `Base.metadata`
so `init_db()` can create them."""
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.user import User

__all__ = ["User", "Document", "Conversation", "Message"]
