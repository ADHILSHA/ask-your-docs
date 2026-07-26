# app/extraction.py
"""Raw text extraction from uploaded files.

Turns uploaded bytes into plain text so the rest of the pipeline has something
to work with. PDFs go through pypdf; .txt/.md are decoded directly. No chunking
and no storage happen here — that's a later slice.
"""
import os
from io import BytesIO

from pypdf import PdfReader

# Lowercase extensions we can extract. Explicit allow-lists so unsupported
# types fail loudly instead of being decoded into garbage.
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | TEXT_EXTENSIONS


class UnsupportedFileType(ValueError):
    """Raised when a file's extension isn't one we can extract text from."""


def _extension(filename: str | None) -> str:
    return os.path.splitext(filename or "")[1].lower()


def extract_text(filename: str | None, data: bytes) -> str:
    """Extract raw text from an uploaded file's bytes.

    Dispatches on the filename extension. Raises UnsupportedFileType for
    anything that isn't a PDF or a plain-text format.
    """
    ext = _extension(filename)
    if ext in PDF_EXTENSIONS:
        return _extract_pdf(data)
    if ext in TEXT_EXTENSIONS:
        return _extract_plain_text(data)
    raise UnsupportedFileType(
        f"Unsupported file type '{ext or filename}'. "
        f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_plain_text(data: bytes) -> str:
    # Try utf-8, then fall back to latin-1 which never raises — a single stray
    # byte shouldn't 500 an otherwise readable text file.
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")
