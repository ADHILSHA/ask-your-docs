# Design note

## How I decomposed the problem
I built in narrow, verifiable slices — one concern per change, tested before the
next. First the single-user RAG core, then multi-user on top of it:

1. Config + `/health`; **extract** (pypdf / text) → **chunk** → **embed + store**
   (Chroma) → **retrieve** → **generate** grounded answers with citations.
2. Similarity-threshold gate and the grounding contract (unanswerable / ambiguous).
3. Conversational chat (server-persisted history, query condensation).
4. Multi-user: accounts → per-user isolation → R2 file storage → per-conversation
   document context.

Failure modes (unanswerable, ambiguous, cross-user access) drove the tests.

## Key decisions
- **RAG, no framework.** Retrieval, prompting, condensation, and citation parsing
  stay owned and explainable — no LangChain/LlamaIndex abstracting them away.
- **Chroma in-process, isolated by metadata filter.** No external vector DB;
  every chunk carries `user_id` + `document_id`, and every query filters by them.
  A `VectorStore` ABC keeps it swappable (pgvector/hosted later = one subclass).
- **Three stores, three interfaces.** Postgres (identity, ownership,
  conversations) via SQLAlchemy + **Alembic** migrations; Cloudflare R2 (raw
  files) behind a `DocumentStorage` ABC (Local for dev); Chroma (vectors). Each
  is swappable and independently testable.
- **Minimal auth.** Email/password, bcrypt hashing, stateless JWT (bearer) — no
  email verification/reset, a deliberate scope cut. Keys stay server-side.
- **Per-conversation context.** A chat answers only from documents added to it
  (a many-to-many link); retrieval is scoped to that set. Precise grounding, and
  documents are reusable across chats.
- **Chunking:** ~600 tokens, ~15% overlap, boundary-aware, never mid-sentence;
  tiktoken `cl100k_base` to match the embedder. **Threshold 0.35** as the
  grounding gate — below it, skip the LLM and return the fixed fallback.
- **Query condensation** for follow-ups: history rewrites the question into a
  standalone query for retrieval; the *answer* is history-free, so it stays
  grounded in freshly retrieved context (and citations stay clean).

## What I deferred
Reranking, hybrid (keyword+vector) search, and streaming — noted, not silently
skipped. Also deferred: per-user rate limiting, filename sanitization, bounded
conversation history, orphan cleanup on failed uploads, OCR, and presigned
downloads. Reasons and severities are in `self-review.md`; the multi-user
architecture is in `multiuser-plan.md`.
