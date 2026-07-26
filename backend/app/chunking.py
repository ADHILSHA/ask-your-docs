# app/chunking.py
"""Split extracted text into overlapping, token-sized chunks for embedding.

Strategy, in order of preference:
  1. Split on paragraph boundaries (blank lines).
  2. Any paragraph that alone exceeds the target is split on sentence
     boundaries, so a chunk never breaks mid-sentence.
  3. Greedily pack these atomic units into ~`target_tokens` chunks, then start
     each following chunk with the trailing units of the previous one to give
     ~`overlap_tokens` of overlap.

Token counts use tiktoken's cl100k_base — the encoding for
text-embedding-3-small, the model these chunks are embedded with — so the size
budget matches what the embedder actually sees.
"""
import re
from dataclasses import dataclass

import tiktoken

# ~600-token chunks with ~15% (90-token) overlap. Overlap preserves context
# across chunk boundaries so a fact split across two chunks stays retrievable.
TARGET_TOKENS = 600
OVERLAP_TOKENS = 90

_ENCODING = tiktoken.get_encoding("cl100k_base")

# Paragraphs: one or more blank lines. Sentences: end punctuation followed by
# whitespace. The sentence regex is intentionally simple (it will mis-split on
# abbreviations like "Dr."); good enough for chunk sizing and fully explainable.
_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    text: str
    filename: str
    chunk_index: int


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _atomic_units(text: str, target_tokens: int) -> list[str]:
    """Break text into the smallest units we're willing to pack.

    A paragraph stays whole unless it alone exceeds the target, in which case
    it's split into sentences. A single over-long sentence is left intact — we
    never break mid-sentence, even if that means one oversized chunk.
    """
    units: list[str] = []
    for para in _PARAGRAPH_RE.split(text):
        para = para.strip()
        if not para:
            continue
        if count_tokens(para) <= target_tokens:
            units.append(para)
        else:
            units.extend(s.strip() for s in _SENTENCE_RE.split(para) if s.strip())
    return units


def chunk_text(
    text: str,
    filename: str,
    *,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split `text` into overlapping `Chunk`s tagged with `filename`."""
    units = _atomic_units(text, target_tokens)
    if not units:
        return []

    unit_tokens = [count_tokens(u) for u in units]
    n = len(units)

    chunks: list[Chunk] = []
    start = 0
    while start < n:
        # Grow the window until one more unit would blow the budget, but always
        # take at least one unit so we make progress on an oversized unit.
        end, total = start, 0
        while end < n:
            if end > start and total + unit_tokens[end] > target_tokens:
                break
            total += unit_tokens[end]
            end += 1

        chunks.append(
            Chunk(
                text="\n".join(units[start:end]),
                filename=filename,
                chunk_index=len(chunks),
            )
        )

        if end >= n:
            break

        # Step the next start back over trailing units until we've covered
        # ~overlap_tokens, but never back to `start` — that guarantees forward
        # progress and avoids an infinite loop on a single oversized unit.
        overlap, new_start = 0, end
        while new_start > start + 1 and overlap < overlap_tokens:
            new_start -= 1
            overlap += unit_tokens[new_start]
        start = new_start

    return chunks
