# app/api/routes/qa.py
from fastapi import APIRouter, Depends, Query

from app.config import get_settings
from app.dependencies import get_vector_store
from app.rag import generation, retrieval
from app.schemas import AskRequest
from app.store import VectorStore

router = APIRouter()


@router.post("/ask")
def ask(req: AskRequest, store: VectorStore = Depends(get_vector_store)):
    """Answer a question grounded in the uploaded documents.

    embed question -> retrieve top-k chunks -> grounded generation. Returns
    {answer, sources}, where sources are the chunks the answer actually cited.
    """
    settings = get_settings()
    embedding = retrieval.embed([req.question])[0]
    results = store.query(embedding, k=req.k)

    # Relevance gate: if even the best match is below the similarity threshold,
    # the documents likely don't cover this. Skip the LLM call and return the
    # grounded fallback rather than risk an ungrounded answer from weak matches.
    if not results or results[0][1] < settings.similarity_threshold:
        return generation.not_found()

    chunks = [chunk for chunk, _score in results]
    return generation.generate_answer(req.question, chunks)


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Question to retrieve chunks for"),
    k: int = Query(5, ge=1, le=20),
    store: VectorStore = Depends(get_vector_store),
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
