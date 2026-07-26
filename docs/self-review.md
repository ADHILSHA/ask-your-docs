# Self-review

A security/quality pass over the repo, split into **what I fixed** (cheap and
real) and **what I deliberately deferred, with reasons**. Deciding what *not* to
fix — and being able to defend it — is the point of this document. Scope context:
single-user, no-auth demo (see CLAUDE.md); several items below only become
serious at the multi-user/public stage the project is heading toward.

## Fixed now (cheap + real)

| # | Fix | Why it was worth doing now |
|---|-----|----------------------------|
| M1 | Unreadable/corrupt files (e.g. a `.pdf` with bad bytes) now return **400**, not an uncaught **500** | One `try/except` at the parse boundary; turns a server error into a clear client error. Doesn't leak the raw parser message. |
| M5 | All OpenAI failures (rate limit, auth, timeout, connection) map to a clean **502** | Single app-level exception handler — covers every route in one place. Rate/quota errors are the *most likely* production failure. |
| M6 / L7a | `k` bounded to `1..20`; question required non-empty, ≤4000 chars (both `/ask` and `/search`) | Pydantic/Query constraints — a few characters. Stops `k=1_000_000` (perf/DoS), `k=0` (500), and wasted embed calls on blank input. |
| H2 | Per-file **10 MB** cap and **20-files**/request cap on upload | Directly caps the memory/cost blast radius of the one unauthenticated write endpoint. Also shrinks the malformed-PDF DoS surface (M7). |
| L1 | CORS `allow_credentials=False` | No cookies/auth are used, so opting into credentialed CORS was needless surface. |
| L8 | Disabled Chroma's anonymized telemetry | No background network egress from a process that handles user documents. One kwarg. |

Each fix has a test in `tests/test_api.py` (status-code assertions) or existing suites; full suite stays green.

## Known weaknesses / deferred (with reasons)

### Security / scope
- **No authentication or rate limiting on paid endpoints (H1).** *Known weakness / deferred because* single-user + no-auth is the documented product cut; auth, tenancy, and per-tenant rate limits belong to the multi-user milestone. **This is the #1 thing to add before any public deployment** — until then anyone with the URL can spend OpenAI budget.
- **No hard request-body cap at the edge (H2 residual).** *Deferred because* the complete fix (reject oversized bodies before they're spooled) lives at the proxy/ASGI layer (Render/nginx `client_max_body_size`), not app code. The app-level per-file guard is the portion the app owns.
- **`/search` debug endpoint is public and dumps chunk text (L2).** *Deferred because* it's a genuinely useful retrieval-inspection tool during development and the store is single-user. **Remove or gate it before multi-user/public deploy** — it's an unauthenticated read of stored content.
- **Container runs as root (L5).** *Deferred because* I can't verify a non-root image build in this environment (no Docker daemon), and a `USER` change risks `.chroma` write-permission bugs I couldn't test. Low marginal value for a single-service demo; flagged for prod hardening.

### Correctness
- **Re-uploading an edited, *shorter* file leaves orphaned chunks (M2).** IDs are `filename::chunk_index` with `upsert`, so higher-index chunks from a previous, longer version aren't removed and can still be retrieved/cited. *Known correctness weakness / deferred because* the clean fix is delete-by-filename on re-ingest, which lands naturally with the document-delete feature that was explicitly scoped-and-deferred earlier — doing a half-version now would duplicate that logic. Low probability in the demo (requires re-uploading an edited same-named file). **Top correctness item to fix.**
- **Partial persistence on multi-file upload failure.** If an OpenAI error hits mid-batch, earlier files are already stored while later ones aren't; the client sees a 502. *Deferred because* transactional multi-file ingest is out of scope and recovery is trivial — ingest is idempotent per file, so retrying the upload converges.
- **Chroma/SQLite is single-writer.** Concurrent uploads+queries could contend. *Deferred because* single-user makes concurrency effectively nil; it's inherent to the deliberate in-process-Chroma choice.

### Grounding
- **Indirect prompt injection via document content (M3).** A poisoned document can carry instructions that try to steer the answer. *Known weakness / deferred because* it's inherent to RAG, mitigations are threat-model-dependent and substantial, and the risk is low when a single user uploads their own docs. Treat retrieved context as untrusted when the corpus becomes shared.
- **No server-side grounding verification (M4).** An answer with no `[n]` markers passes through as `sources: []`, indistinguishable from the fallback; the citation regex also assumes the prompt's `[n]` format. *Deferred because* a robust fix needs an evaluation harness and a policy call — auto-suppressing uncited answers can wrongly kill valid ones. The system prompt currently enforces the citation format; verification is the right *next* investment, not a quick patch.
- **Relevance gate checks only the top score (L6).** Below-threshold chunks still enter the prompt when the top passes. *Deferred because* it was a deliberate earlier decision; per-chunk filtering is a retrieval-tuning task best done against real eval data alongside the threshold value itself.

### Minor / UX
- **Silent success when no text is extracted (L3).** Image-only PDFs/empty files return 200 with `chunk_count: 0`. *Deferred because* the signal (`chunk_count: 0`) is already in the response; a friendly per-file warning is polish, not a correctness gap.
- **`latin-1` decode fallback masks bad input (L4).** *Deferred because* it trades one failure mode (a hard 500 on one stray byte) for another (garbage in); low impact, and the current choice favors resilience.
- **No client-side fetch timeout (L7b).** A hung backend spins the UI's loading state indefinitely. *Deferred because* it's frontend polish; the backend already fails fast on its own errors.

## Method / honesty notes
This was a **static read plus targeted tests**, not a live pentest or fuzzing run. The OpenAI call paths are exercised against a faked client, not the real API. The deferred items are choices, not oversights — each is here because the fix is either out of the stated scope, needs design/eval work a one-line patch would get wrong, or can't be safely verified in this environment.
