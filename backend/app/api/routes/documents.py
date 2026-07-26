# app/api/routes/documents.py
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.dependencies import get_document_storage, get_vector_store
from app.models.document import Document
from app.models.user import User
from app.rag import retrieval
from app.rag.chunking import chunk_text
from app.rag.extraction import UnsupportedFileType, extract_text
from app.schemas import DocumentOut
from app.storage import DocumentStorage
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
    storage: DocumentStorage = Depends(get_document_storage),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest one or more files for the current user: extract → chunk → embed →
    store, scoped to `user_id`.

    Two passes: validate + extract everything first, so a bad file aborts the
    whole batch with a 400 *before* anything is written.
    """
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} (max {MAX_FILES} per request).",
        )

    # Pass 1 — read, size-check, and extract text. No writes yet; we keep the
    # raw bytes so pass 2 can persist the original file.
    extracted: list[tuple[str | None, bytes, str]] = []
    for f in files:
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
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {f.filename!r}; the file may be corrupt.",
            )
        extracted.append((f.filename, data, text))

    # Pass 2 — persist a Document row, save the raw file, embed, and store chunks.
    results = []
    total_chunks = 0
    for filename, data, text in extracted:
        chunks = chunk_text(text, filename)
        document = Document(
            user_id=current_user.id,
            filename=filename or "untitled",
            char_count=len(text),
            chunk_count=len(chunks),
        )
        db.add(document)
        db.flush()  # assign document.id before storing chunks / the file

        document.s3_key = storage.save(
            current_user.id, document.id, document.filename, data
        )

        if chunks:
            embeddings = retrieval.embed([c.text for c in chunks])
            store.add_chunks(current_user.id, document.id, chunks, embeddings)

        total_chunks += len(chunks)
        results.append(
            {
                "document_id": document.id,
                "filename": document.filename,
                "char_count": len(text),
                "chunk_count": len(chunks),
            }
        )

    db.commit()
    return {
        "files": results,
        "chunks_indexed": total_chunks,
        "message": f"Indexed {total_chunks} chunk(s) from {len(files)} file(s).",
    }


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's uploaded documents, newest first."""
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: str,
    storage: DocumentStorage = Depends(get_document_storage),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the original file for one of the current user's documents."""
    document = _owned_document_or_404(db, document_id, current_user.id)
    if not document.s3_key:
        raise HTTPException(status_code=404, detail="File not available")

    data = storage.load(document.s3_key)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    store: VectorStore = Depends(get_vector_store),
    storage: DocumentStorage = Depends(get_document_storage),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of the current user's documents: chunks, raw file, and row."""
    document = _owned_document_or_404(db, document_id, current_user.id)

    store.delete_document(current_user.id, document_id)
    if document.s3_key:
        storage.delete(document.s3_key)
    db.delete(document)
    db.commit()


def _owned_document_or_404(db: Session, document_id: str, user_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.user_id != user_id:
        # 404 (not 403) so we don't reveal that another user's id exists.
        raise HTTPException(status_code=404, detail="Document not found")
    return document
