# app/store.py
"""Vector storage behind a small, swappable interface.

`VectorStore` is the contract the rest of the backend codes against; retrieval
never imports Chroma directly. The concrete `ChromaVectorStore` persists to
disk in-process (backend/.chroma) — a deliberate no-external-DB choice for this
scale. Swapping to pgvector/Pinecone later means writing one more subclass, not
touching callers.

Embeddings are passed in, not computed here: turning text into vectors is the
embeddings module's job, which keeps this layer offline-testable and free of
any OpenAI dependency.
"""
from abc import ABC, abstractmethod
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag.chunking import Chunk

# Cosine distance in Chroma lands in [0, 2]; we return similarity = 1 - distance
# so scores are cosine similarity (higher = closer), matching the
# SIMILARITY_THRESHOLD the retrieval layer compares against.
_DISTANCE_SPACE = "cosine"

# backend/.chroma, resolved from this file so it's independent of the cwd the
# server is launched from. Gitignored.
_DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / ".chroma"


class VectorStore(ABC):
    """Minimal interface: add embedded chunks, query by embedding."""

    @abstractmethod
    def add_chunks(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        """Persist `chunks` alongside their parallel `embeddings`."""

    @abstractmethod
    def query(
        self, embedding: list[float], k: int = 5
    ) -> list[tuple[Chunk, float]]:
        """Return up to `k` nearest chunks as (chunk, similarity) pairs,
        most similar first."""

    @abstractmethod
    def reset(self) -> None:
        """Remove all stored chunks, leaving an empty store."""


class ChromaVectorStore(VectorStore):
    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str = "documents",
    ) -> None:
        persist_directory = persist_directory or _DEFAULT_PERSIST_DIR
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        # Disable Chroma's anonymized telemetry — no background egress from a
        # process handling user documents.
        self._client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection_name = collection_name
        self._collection = self._open_collection()

    def _open_collection(self):
        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": _DISTANCE_SPACE},
        )

    def add_chunks(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must be the same length"
            )
        if not chunks:
            return

        # Deterministic ids so re-uploading a file replaces its chunks in place
        # rather than duplicating them. (Two distinct files sharing a name would
        # collide — acceptable for single-user; revisit with a content hash if
        # that changes.)
        ids = [f"{c.filename}::{c.chunk_index}" for c in chunks]
        self._collection.upsert(
            ids=ids,
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[
                {"filename": c.filename, "chunk_index": c.chunk_index}
                for c in chunks
            ],
        )

    def query(
        self, embedding: list[float], k: int = 5
    ) -> list[tuple[Chunk, float]]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        # Chroma nests results per query embedding; we sent exactly one.
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        pairs: list[tuple[Chunk, float]] = []
        for text, meta, distance in zip(documents, metadatas, distances):
            chunk = Chunk(
                text=text,
                filename=meta["filename"],
                chunk_index=meta["chunk_index"],
            )
            pairs.append((chunk, 1.0 - distance))
        return pairs

    def reset(self) -> None:
        # Drop the whole collection and recreate it empty — simpler and more
        # thorough than deleting ids one by one, and it clears the HNSW index too.
        self._client.delete_collection(self._collection_name)
        self._collection = self._open_collection()
