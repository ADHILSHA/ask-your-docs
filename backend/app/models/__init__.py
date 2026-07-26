# app/models/__init__.py
"""ORM models. Importing this package registers all tables on `Base.metadata`
so `init_db()` can create them."""
from app.models.document import Document
from app.models.user import User

__all__ = ["User", "Document"]
