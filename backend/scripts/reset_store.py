#!/usr/bin/env python
"""Clear the vector store — delete every uploaded document.

Run from the backend/ directory, locally or via Render Shell:

    python scripts/reset_store.py

Uses the same default persistence location as the app, so it clears exactly
what the running server reads. No OpenAI key required. Restart the service
afterwards if it was running, so it reopens the fresh, empty collection.
"""
import os
import sys

# Make `app` importable no matter how this script is launched.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.store import ChromaVectorStore


def main() -> None:
    store = ChromaVectorStore()
    store.reset()
    print("Vector store cleared — all documents removed.")


if __name__ == "__main__":
    main()
