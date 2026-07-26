# app/api/routes/documents.py
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.deps import get_current_user
from app.dependencies import get_vector_store
from app.models.user import User
from app.rag import retrieval
from app.rag.chunking import chunk_text
from app.rag.extraction import UnsupportedFileType, extract_text
from app.store import VectorStore

router = APIRouter()

# App-level ingest guards. Cheap defense against accidental/abusive large
# uploads and the memory/cost blowup they cause. A hard request-body cap still
# belongs at the proxy/ASGI layer (see self-review); this is the app's share.
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file
MAX_FILES = 20  # per request


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...),
    store: VectorStore = Depends(get_vector_store),
    current_user: User = Depends(get_current_user),
):
    """Ingest one or more files: extract → chunk → embed → store.

    Each file's chunks are embedded in a batch and written to the vector store.
    An unsupported file type or an unreadable file aborts the whole batch with a
    400 — it's a client mistake to fix, not a per-file soft failure.
    """
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} (max {MAX_FILES} per request).",
        )

    results = []
    total_chunks = 0
    for f in files:
        # Reject oversized files by declared size before reading, then by actual
        # bytes as the authoritative check.
        if f.size is not None and f.size > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{f.filename!r} exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit.",
            )
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{f.filename!r} exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit.",
            )

        try:
            text = extract_text(f.filename, data)
        except UnsupportedFileType as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            # A supported extension whose bytes we couldn't parse (e.g. a corrupt
            # PDF). Return a clean 400 instead of a 500, without leaking the raw
            # parser error.
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {f.filename!r}; the file may be corrupt.",
            )

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
