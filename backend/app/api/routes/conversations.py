# app/api/routes/conversations.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.user import User
from app.schemas import ConversationCreate, ConversationOut, DocumentOut, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: ConversationCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = Conversation(
        user_id=current_user.id,
        title=(req.title if req and req.title else "New conversation"),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _owned_conversation_or_404(db, conversation_id, current_user.id)
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )


@router.get("/{conversation_id}/documents", response_model=list[DocumentOut])
def list_context_documents(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the documents in this conversation's context."""
    conversation = _owned_conversation_or_404(db, conversation_id, current_user.id)
    return conversation.documents


@router.post(
    "/{conversation_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_context_document(
    conversation_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add one of the user's documents to this conversation's context."""
    conversation = _owned_conversation_or_404(db, conversation_id, current_user.id)
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    if document not in conversation.documents:
        conversation.documents.append(document)
        db.commit()


@router.delete(
    "/{conversation_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_context_document(
    conversation_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a document from this conversation's context (keeps the document)."""
    conversation = _owned_conversation_or_404(db, conversation_id, current_user.id)
    document = db.get(Document, document_id)
    if document is not None and document in conversation.documents:
        conversation.documents.remove(document)
        db.commit()


def _owned_conversation_or_404(
    db: Session, conversation_id: str, user_id: str
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
