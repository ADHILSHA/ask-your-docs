# app/api/routes/qa.py
from fastapi import APIRouter, Depends, Query

from app.auth.deps import get_current_user
from app.config import get_settings
from app.dependencies import get_vector_store
from app.models.user import User
from app.rag import generation, retrieval
from app.schemas import ChatRequest
from app.store import VectorStore

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    store: VectorStore = Depends(get_vector_store),
    current_user: User = Depends(get_current_user),
):
    """Answer the latest user message, grounded in the uploaded documents.

    condense (rewrite the follow-up into a standalone question using history) →
    embed → retrieve top-k → threshold gate → grounded generation. Returns
    {answer, sources}; history is used only to resolve the question, never as a
    source of facts.
    """
    settings = get_settings()
    history = [m.model_dump() for m in req.messages[:-1]]
    latest = req.messages[-1].content

    question = generation.condense_question(history, latest)
    embedding = retrieval.embed([question])[0]
    results = store.query(embedding, k=req.k)

    # Relevance gate: if even the best match is below the similarity threshold,
    # the documents likely don't cover this. Skip the LLM call and return the
    # grounded fallback rather than risk an ungrounded answer from weak matches.
    if not results or results[0][1] < settings.similarity_threshold:
        return generation.not_found()

    chunks = [chunk for chunk, _score in results]
    return generation.generate_answer(question, chunks)


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
    results = store.query(embedding, k=k)
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
