# app/store.py
"""Vector storage behind a small, swappable interface.

`VectorStore` is the contract the rest of the backend codes against; retrieval
never imports Chroma directly. The concrete `ChromaVectorStore` persists to
disk in-process (backend/.chroma).

Storage is **per-user**: every chunk carries `user_id` (and `document_id`) in
its metadata, and every query filters by `user_id`. That's how one user's
documents stay invisible to another — a single collection, real isolation.

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
    """Minimal, per-user interface: add embedded chunks, query, delete, reset."""

    @abstractmethod
    def add_chunks(
        self,
        user_id: str,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Persist `chunks` (+ parallel `embeddings`) owned by `user_id`."""

    @abstractmethod
    def query(
        self, user_id: str, embedding: list[float], k: int = 5
    ) -> list[tuple[Chunk, float]]:
        """Return up to `k` nearest chunks *belonging to `user_id`* as
        (chunk, similarity) pairs, most similar first."""

    @abstractmethod
    def delete_document(self, user_id: str, document_id: str) -> None:
        """Remove all chunks of one document owned by `user_id`."""

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
        self,
        user_id: str,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must be the same length"
            )
        if not chunks:
            return

        # Ids are unique per (user, document, chunk) so no cross-user or
        # cross-document collision; re-uploading the same document replaces it.
        ids = [f"{user_id}::{document_id}::{c.chunk_index}" for c in chunks]
        self._collection.upsert(
            ids=ids,
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "user_id": user_id,
                    "document_id": document_id,
                    "filename": c.filename,
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ],
        )

    def query(
        self, user_id: str, embedding: list[float], k: int = 5
    ) -> list[tuple[Chunk, float]]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where={"user_id": user_id},
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
                document_id=meta.get("document_id"),
            )
            pairs.append((chunk, 1.0 - distance))
        return pairs

    def delete_document(self, user_id: str, document_id: str) -> None:
        self._collection.delete(
            where={"$and": [{"user_id": user_id}, {"document_id": document_id}]}
        )

    def reset(self) -> None:
        # Drop the whole collection and recreate it empty — simpler and more
        # thorough than deleting ids one by one, and it clears the HNSW index too.
        self._client.delete_collection(self._collection_name)
        self._collection = self._open_collection()
