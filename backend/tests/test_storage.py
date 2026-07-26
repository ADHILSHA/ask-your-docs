# tests/test_storage.py
"""LocalStorage round-trip: save -> load -> delete, in a tmp dir."""
from app.storage import LocalStorage, build_key


def test_save_load_delete(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    key = storage.save("u1", "d1", "notes.txt", b"hello bytes")

    assert key == build_key("u1", "d1", "notes.txt") == "u1/d1/notes.txt"
    assert storage.load(key) == b"hello bytes"
    # written under the per-user/per-document prefix
    assert (tmp_path / "u1" / "d1" / "notes.txt").read_bytes() == b"hello bytes"

    storage.delete(key)
    assert not (tmp_path / "u1" / "d1" / "notes.txt").exists()
    # deleting again is a no-op, not an error
    storage.delete(key)
