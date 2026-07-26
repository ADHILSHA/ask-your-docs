# Self-review (PR-style)

**What this PR delivers:** a working RAG app — upload docs, ask questions, get
answers grounded in the sources with visible citations — deployed frontend
(Vercel) + backend (Render). This review is the honest "reviewer's eye" pass:
the trade-offs I made, what's knowingly weak, and what I'd do next.

## Main trade-offs
- **Owned code over a framework.** Retrieval and prompting are hand-written (no
  LangChain), so every decision is explainable. Cost: I re-implemented small
  pieces (batching, citation parsing) a framework gives free.
- **In-process Chroma over a hosted vector DB.** Zero infra, fast local queries,
  and a clean `VectorStore` ABC as the swap point. Cost: state is tied to the
  process/disk (see below).
- **Single shared store, no auth.** Big scope cut that keeps the demo focused on
  grounding. Cost: no isolation between users (a real concern on the live demo).
- **Grounding via a hard threshold gate + strict prompt.** Simple and cheap:
  weak top match → fixed fallback, no LLM call. Cost: it's a blunt instrument
  (top-score only) and leans on model compliance for citations.

## Known weaknesses
- **Ephemeral storage on the live demo.** Render's free disk resets on
  redeploy/idle spin-down, so uploaded docs don't persist and a cold start takes
  ~30–60s. Fine for a demo; not durable.
- **Shared in-memory/on-disk state.** One Chroma collection for everyone — on the
  public URL, one visitor's uploads are visible to the next visitor's questions.
  Documented single-user scope, but a real limitation of the hosted demo.
- **No OCR.** Image-only / scanned PDFs extract no text and silently index 0
  chunks (`pypdf` only reads embedded text).
- **No reranking / no hybrid search.** Pure vector top-k. Lexical-heavy or
  keyword queries can retrieve sub-optimally; there's no cross-encoder rerank to
  sharpen the top results.
- **Grounding isn't verified server-side.** An answer with no `[n]` markers
  passes through as `sources: []`; nothing checks the cited text actually
  supports the claim. Retrieved context is also trusted (indirect prompt
  injection is possible with a poisoned doc).
- **Re-uploading an edited, shorter file leaves stale chunks** (deterministic
  ids + upsert). Low-probability, but a correctness gap.

(Security-specific items — auth/rate-limiting, the public `/search` debug
endpoint, container-runs-as-root — and the cheap fixes already applied
(input validation, upload caps, corrupt-file → 400, OpenAI errors → 502) are
tracked in the git history and were part of this pass.)

## What I'd do with another week
1. **Durable persistence.** Attach a Render disk (keeps in-process Chroma), or
   move to hosted Chroma / pgvector via the existing `VectorStore` interface —
   one new subclass, no route changes.
2. **Hybrid search + reranking.** Add BM25/keyword retrieval fused with vector
   results, then a cross-encoder rerank of the top-k before generation.
3. **Multi-user via `user_id` + filtered retrieval.** Thread a `user_id` (or
   `tenant_id`) through ingest and query; store it in chunk metadata and filter
   every Chroma query by it — real isolation without a per-user database.
   This also fixes the shared-state and stale-chunk issues.
4. **Streaming responses.** Stream tokens from the chat model to the UI so
   answers render progressively instead of after a blocking call.

Honest caveat: reviews here were static reads + targeted tests, and OpenAI call
paths are exercised against a faked client — not a live end-to-end or load test.
