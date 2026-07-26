# app/main.py
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.chunking import chunk_text
from app.config import get_settings
from app.extraction import UnsupportedFileType, extract_text
from app.retrieval import embed
from app.store import ChromaVectorStore, VectorStore

settings = get_settings()

# One persistent store for the process. Typed as the interface so callers below
# never depend on Chroma specifically.
store: VectorStore = ChromaVectorStore()

app = FastAPI(title="ask-your-docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
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
            embeddings = embed([c.text for c in chunks])
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
