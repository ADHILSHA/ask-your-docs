# tests/test_chunking.py
from app.rag.chunking import OVERLAP_TOKENS, TARGET_TOKENS, chunk_text, count_tokens


def _make_text(n_sentences: int) -> str:
    """Distinct sentences grouped into short paragraphs.

    Every sentence is unique so overlap between chunks is detectable by
    content, and paragraphs contain no internal newlines — which lets the
    tests recover a chunk's units by splitting its text on "\n".
    """
    sentences = [
        f"Sentence number {i} describes a unique fact about topic {i}."
        for i in range(n_sentences)
    ]
    paras = [" ".join(sentences[i : i + 5]) for i in range(0, n_sentences, 5)]
    return "\n\n".join(paras)


def test_multiple_chunks_within_size_budget():
    chunks = chunk_text(_make_text(200), "doc.txt")
    assert len(chunks) > 1
    for c in chunks:
        # Packing keeps content <= target; the rendered text adds one join
        # token per unit boundary, so allow that much slack.
        tolerance = len(c.text.split("\n"))
        assert count_tokens(c.text) <= TARGET_TOKENS + tolerance


def test_chunks_are_reasonably_full():
    chunks = chunk_text(_make_text(200), "doc.txt")
    # Every chunk but the last should be near the target, not a sliver.
    for c in chunks[:-1]:
        assert count_tokens(c.text) >= TARGET_TOKENS * 0.5


def test_overlap_exists_between_consecutive_chunks():
    chunks = chunk_text(_make_text(200), "doc.txt")
    for a, b in zip(chunks, chunks[1:]):
        a_units = a.text.split("\n")
        b_units = b.text.split("\n")
        # The next chunk begins with trailing unit(s) of the previous chunk.
        assert b_units[0] in a_units
        shared_tokens = count_tokens(
            "\n".join(u for u in b_units if u in a_units)
        )
        assert shared_tokens > 0
        # Overlap is whole-unit granular, so it can exceed the target by up to
        # one unit but shouldn't run away.
        assert shared_tokens <= OVERLAP_TOKENS + max(count_tokens(u) for u in a_units)


def test_metadata_filename_and_index():
    chunks = chunk_text(_make_text(200), "report.pdf")
    assert len(chunks) > 1
    for i, c in enumerate(chunks):
        assert c.filename == "report.pdf"
        assert c.chunk_index == i


def test_empty_text_returns_no_chunks():
    assert chunk_text("   \n\n  ", "empty.txt") == []


def test_short_text_is_a_single_chunk():
    chunks = chunk_text("One short sentence about a cat.", "s.txt")
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].filename == "s.txt"
