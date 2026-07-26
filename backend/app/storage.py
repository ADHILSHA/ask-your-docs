# app/storage.py
"""Raw uploaded-file storage, behind a swappable interface.

`DocumentStorage` is the contract; `LocalStorage` writes to disk for dev and
`S3Storage` targets Cloudflare R2 (S3-compatible) in prod. Note: this stores the
original *file bytes* — distinct from `store.py`, which holds the vector chunks.

Keys are `"{user_id}/{document_id}/{filename}"`, which keeps every user's files
in their own prefix.
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path

# Resolved from this file so it's independent of the launch cwd. Gitignored.
_DEFAULT_LOCAL_DIR = Path(__file__).resolve().parent.parent / ".storage"


def build_key(user_id: str, document_id: str, filename: str) -> str:
    # Use only the basename so a malicious filename (e.g. "../../x") can't
    # escape the user/document prefix on local disk. Handle both separators.
    safe_name = os.path.basename(filename.replace("\\", "/")) or "file"
    return f"{user_id}/{document_id}/{safe_name}"


class DocumentStorage(ABC):
    @abstractmethod
    def save(self, user_id: str, document_id: str, filename: str, data: bytes) -> str:
        """Persist `data`; return the storage key."""

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Fetch the bytes stored under `key`."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object at `key` (no error if already gone)."""


class LocalStorage(DocumentStorage):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir or _DEFAULT_LOCAL_DIR)

    def _path(self, key: str) -> Path:
        return self._base / key

    def save(self, user_id: str, document_id: str, filename: str, data: bytes) -> str:
        key = build_key(user_id, document_id, filename)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage(DocumentStorage):
    """Cloudflare R2 (or any S3-compatible endpoint) via boto3."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        import boto3  # imported lazily so local dev needn't have R2 configured

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def save(self, user_id: str, document_id: str, filename: str, data: bytes) -> str:
        key = build_key(user_id, document_id, filename)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    def load(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
