# app/api/routes/qa.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db import get_db
from app.dependencies import get_vector_store
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.rag import generation, retrieval
from app.schemas import ChatRequest
from app.store import VectorStore

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    store: VectorStore = Depends(get_vector_store),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer the next message in a conversation, grounded in the user's docs.

    Load history from the DB → condense the message into a standalone question →
    embed → retrieve (scoped to the user) → threshold gate → grounded generation.
    Persists the user + assistant messages. History resolves the question only;
    answers stay grounded in freshly retrieved context.
    """
    settings = get_settings()

    conversation = db.get(Conversation, req.conversation_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    prior = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in prior]

    # Name a fresh conversation after its first message.
    if not prior:
        conversation.title = req.message[:60]

    db.add(
        Message(conversation_id=conversation.id, role="user", content=req.message, sources=[])
    )

    # Answer only from the documents in this conversation's context. No context
    # docs -> nothing to ground in.
    context_ids = [d.id for d in conversation.documents]
    if not context_ids:
        answer = generation.not_found()
        db.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=answer["answer"],
                sources=answer["sources"],
            )
        )
        db.commit()
        return answer

    question = generation.condense_question(history, req.message)
    embedding = retrieval.embed([question])[0]
    results = store.query(current_user.id, embedding, k=req.k, document_ids=context_ids)

    # Relevance gate: if even the best match is below the similarity threshold,
    # the documents likely don't cover this. Skip the LLM call and return the
    # grounded fallback rather than risk an ungrounded answer from weak matches.
    if not results or results[0][1] < settings.similarity_threshold:
        answer = generation.not_found()
    else:
        chunks = [chunk for chunk, _score in results]
        answer = generation.generate_answer(question, chunks)

    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer["answer"],
            sources=answer["sources"],
        )
    )
    db.commit()
    return answer


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Question to retrieve chunks for"),
    k: int = Query(5, ge=1, le=20),
    store: VectorStore = Depends(get_vector_store),
    current_user: User = Depends(get_current_user),
):
    """TEMPORARY debug endpoint: embed the question and return the top-k chunks
    with raw similarity scores and metadata. No threshold, no LLM answer."""
    embedding = retrieval.embed([q])[0]
    results = store.query(current_user.id, embedding, k=k)
    return {
        "question": q,
        "results": [
            {
                "score": score,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            for chunk, score in results
        ],
    }
