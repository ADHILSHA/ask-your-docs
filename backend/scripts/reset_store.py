#!/usr/bin/env python
"""Clear the vector store — delete every uploaded document.

Run from the backend/ directory, locally or via Render Shell:

    python scripts/reset_store.py

Targets the same vector backend as the app (reads the same .env/config), so it
clears exactly what the running server reads. Restart the service afterwards if
it was running, so it reopens the fresh, empty collection.
"""
import os
import sys

# Make `app` importable no matter how this script is launched.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dependencies import get_vector_store


def main() -> None:
    # Uses the same backend selection as the app (Chroma Cloud when the
    # CHROMA_* vars are set, local .chroma otherwise).
    store = get_vector_store()
    store.reset()
    print("Vector store cleared — all documents removed.")


if __name__ == "__main__":
    main()
