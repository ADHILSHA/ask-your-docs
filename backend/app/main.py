# app/main.py
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.chunking import chunk_text
from app.config import get_settings
from app.extraction import UnsupportedFileType, extract_text

settings = get_settings()

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
    """Extract raw text from one or more uploaded files.

    Proves extraction and chunking work end to end; stores nothing yet. An
    unsupported file type aborts the whole batch with a 400 — it's a client
    mistake to fix, not a per-file soft failure.
    """
    results = []
    for f in files:
        data = await f.read()
        try:
            text = extract_text(f.filename, data)
        except UnsupportedFileType as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        chunks = chunk_text(text, f.filename)
        results.append(
            {
                "filename": f.filename,
                "char_count": len(text),
                "chunk_count": len(chunks),
            }
        )
    return {"files": results}
