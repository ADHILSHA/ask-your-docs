# app/generation.py
"""Grounded answer generation.

The system prompt is the contract: answer only from the numbered context, fall
back verbatim when the context doesn't cover the question, ask a single
clarifying question when it's ambiguous, and cite sources by their context
number. The wiring below builds the numbered context, calls the chat model, and
extracts the sources actually cited so callers get {answer, sources}.
"""
import re

from app.config import get_settings
from app.rag.chunking import Chunk

# Reuse the single server-side OpenAI client created for embeddings — same
# process, same key-from-config. Deliberately shared to avoid a second client.
from app.rag.retrieval import _client

# Hand-authored contract for the model. Do not edit casually — the citation
# convention here is what extract_cited_sources() parses, and the fallback
# string is asserted verbatim elsewhere.
SYSTEM_PROMPT = """You are a question-answering assistant in a conversation with a user. Answer using ONLY the numbered context provided in the user message. Do not use any outside knowledge, and do not treat earlier turns of the conversation as a source of facts — every answer must be grounded in the numbered context below.

Follow these rules exactly:
1. If the context does not contain the answer, reply with exactly this sentence and nothing else: I couldn't find this in the documents.
2. If the question is ambiguous or could reasonably mean several different things, do not guess — ask exactly ONE short clarifying question instead.
3. When you do answer, cite the numbered sources you used inline using their bracket numbers, for example [1] or [2][3]. Cite only the sources you actually relied on.
4. Keep the answer concise and grounded in the cited context."""

# The one grounded fallback string, used both when nothing is retrieved / the
# top match is too weak, and (per the prompt) when the model can't answer.
NOT_FOUND_MESSAGE = "I couldn't find this in the documents."

_CITATION_RE = re.compile(r"\[(\d+)\]")


def not_found() -> dict:
    """The grounded fallback response: fixed message, no sources."""
    return {"answer": NOT_FOUND_MESSAGE, "sources": []}


# Rewrites a conversational follow-up into a self-contained question so
# retrieval works on it. This is a separate concern from the grounding prompt
# above and never sees the documents — it only resolves references.
CONDENSE_PROMPT = """You rewrite a user's latest message into a standalone question.

Given the conversation so far and the latest message, rewrite the latest message as a single question that can be understood on its own, without the conversation — resolving references like "it", "that", or a short reply to a previous clarifying question. If the latest message is already standalone, return it unchanged. Return only the rewritten question, with no preamble."""


def condense_question(history: list[dict], latest: str) -> str:
    """Rewrite `latest` into a standalone question using prior turns.

    `history` is the conversation before the latest message ([{role, content}]).
    With no history there's nothing to resolve, so return it unchanged and skip
    the extra model call.
    """
    if not history:
        return latest

    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    response = _client().chat.completions.create(
        model=get_settings().chat_model,
        messages=[
            {"role": "system", "content": CONDENSE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Conversation so far:\n{conversation}\n\n"
                    f"Latest message: {latest}\n\nStandalone question:"
                ),
            },
        ],
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip() or latest


def build_context(chunks: list[Chunk]) -> str:
    """Render retrieved chunks as a numbered context block.

    Each block is labelled [n] (the citation handle the model uses) and also
    shows its filename/chunk_index so the model can reason about provenance.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[{i}] (source: {chunk.filename} #chunk {chunk.chunk_index})\n{chunk.text}"
        )
    return "\n\n".join(blocks)


def extract_cited_sources(answer: str, chunks: list[Chunk]) -> list[dict]:
    """Return {filename, chunk_index} for the [n] markers the answer actually
    cites — in order of first citation, deduped, ignoring out-of-range numbers.
    """
    sources: list[dict] = []
    seen: set[int] = set()
    for match in _CITATION_RE.finditer(answer):
        n = int(match.group(1))
        idx = n - 1
        if 0 <= idx < len(chunks) and n not in seen:
            seen.add(n)
            chunk = chunks[idx]
            sources.append(
                {"filename": chunk.filename, "chunk_index": chunk.chunk_index}
            )
    return sources


def generate_answer(question: str, chunks: list[Chunk]) -> dict:
    """Answer `question` grounded in `chunks`; return {answer, sources}."""
    # Nothing retrieved -> nothing to ground in. Return the fallback directly
    # rather than spend a chat call to be told the same thing.
    if not chunks:
        return not_found()

    context = build_context(chunks)
    user_message = f"Numbered context:\n{context}\n\nQuestion: {question}"

    response = _client().chat.completions.create(
        model=get_settings().chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )
    answer = (response.choices[0].message.content or "").strip()
    return {"answer": answer, "sources": extract_cited_sources(answer, chunks)}
