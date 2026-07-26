# app/api/routes/documents.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.dependencies import get_vector_store
from app.rag import retrieval
from app.rag.chunking import chunk_text
from app.rag.extraction import UnsupportedFileType, extract_text
from app.store import VectorStore

router = APIRouter()


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...),
    store: VectorStore = Depends(get_vector_store),
):
    """Ingest one or more files: extract → chunk → embed → store.

    Each file's chunks are embedded in a batch and written to the vector store.
    An unsupported file type aborts the whole batch with a 400 — it's a client
    mistake to fix, not a per-file soft failure.
    """
    results = []
    total_chunks = 0
    for f in files:
        data = await f.read()
        try:
            text = extract_text(f.filename, data)
        except UnsupportedFileType as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        chunks = chunk_text(text, f.filename)
        if chunks:
            embeddings = retrieval.embed([c.text for c in chunks])
            store.add_chunks(chunks, embeddings)

        total_chunks += len(chunks)
        results.append(
            {
                "filename": f.filename,
                "char_count": len(text),
                "chunk_count": len(chunks),
            }
        )

    return {
        "files": results,
        "chunks_indexed": total_chunks,
        "message": f"Indexed {total_chunks} chunk(s) from {len(files)} file(s).",
    }
