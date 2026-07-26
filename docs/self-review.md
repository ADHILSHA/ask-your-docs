# Self-review (PR-style)

**What this delivers:** a multi-user RAG app — sign up, upload documents, curate
which documents each chat draws from, and get answers grounded in that context
with clickable citations. Frontend on Vercel, backend on Render (Docker),
Postgres for identity/ownership/conversations, Cloudflare R2 for files, Chroma
for vectors. This review is the honest reviewer's-eye pass over the current
state.

## Main trade-offs
- **Owned RAG over a framework.** Retrieval, prompting, condensation, and
  citation parsing are hand-written (no LangChain) — every decision is
  explainable; the cost is re-implementing small pieces.
- **In-process Chroma, one shared collection, isolated by metadata filter.** No
  vector DB to run; per-user (and per-conversation) isolation is a `where`
  filter on `user_id` / `document_id`. Simple and fast; the cost is that
  isolation rests on filter correctness (see weaknesses).
- **Postgres for relational data, R2 for blobs, Chroma for vectors** — three
  stores, each behind an interface. Clean seams; the cost is no cross-store
  transaction (see partial-persistence below).
- **Minimal auth** (email/password, bcrypt, JWT bearer in localStorage). Fast to
  build and reason about; the cost is real security posture gaps (below).
- **Per-conversation context.** A chat answers only from documents added to it —
  precise grounding; the cost is an empty new chat can't answer until you add a
  doc.

## Fixed in this pass (cheap + real)
- **C1 — `JWT_SECRET` fail-fast.** The app now refuses to start with the dev
  default when a production config is present (Postgres or S3/R2) — a silent
  takeover risk became a loud startup error. (You still set a strong secret; it's
  now enforced.)
- **M1 — filename sanitization.** `build_key` uses only the basename, so a
  `../../…` filename can't escape the storage prefix.
- **M2 — bounded history.** Condensation now uses the last 20 messages, not the
  whole conversation.
- **M3 — storage errors → 502.** R2/disk failures on upload/download return a
  clean 502 instead of a bare 500.
- **L1 — removed the `/search` debug endpoint** (it dumped chunk text).

Each has a test; suite is green.

## Remaining findings by severity (static review + tests, not a live pentest)

### High
- **No rate limiting anywhere.** `/auth/login` is brute-forceable; `/chat` and
  `/upload` spend OpenAI budget per call. Public + multi-user makes this real.
- **No hard request-body cap at the edge** — app-level per-file/count guards
  exist, but a giant body spools before they run. Belongs at the proxy.

### Medium
- **Partial persistence across DB + R2 + Chroma** on a mid-batch failure →
  orphaned blobs/chunks; re-upload doesn't clean up.
- **Indirect prompt injection** via document content (inherent to RAG).
- **No server-side grounding verification** — an uncited answer still returns
  `sources: []`; citation placement is prompt-nudged, not enforced.
- **pypdf on untrusted PDFs** (DoS surface; partly mitigated by the size cap).
- **JWT posture** — no revocation, 1-day expiry, localStorage (XSS-exposed).

### Low
- no email verification / password complexity / lockout · no pagination ·
  isolation rests on one shared Chroma collection · vestigial
  `Document.conversation_id` · container runs as root · threshold gates top score
  only · bcrypt 72-byte vs 72-char edge · no client fetch timeout.

### Done right
Per-user isolation (`user_id` filter + ownership 404s, cross-user tested) ·
retrieval scoped to conversation context · bcrypt-hashed passwords · CORS
credentials off + env origins · input bounds (`k`, message length) · OpenAI→502,
corrupt file→400 · **Alembic migrations** with a data-preserving backfill ·
secrets server-side, `.env` git/docker-ignored, none in the image · delete
cascades context links + chunks + blob · Chroma telemetry disabled.

## Known weaknesses (product-level)
- **Render free tier cold starts** (~30–60s on first request). Vectors are
  durable when the `CHROMA_*` vars point at Chroma Cloud; without them the
  in-process Chroma index resets on redeploy (Postgres/R2 persist either way).
- **No OCR** — image-only PDFs extract no text.
- **No reranking / hybrid search** — pure vector top-k.
- **Citations can still cluster** on list-heavy answers — placement is a prompt
  nudge, not enforced.

## What I'd do next (priority order)
1. **Harden auth for prod:** rate-limit `/auth/*` and the paid endpoints, and add
   a body-size cap at the proxy. (`JWT_SECRET` fail-fast is done.)
2. **Remaining correctness gap:** an orphan-cleanup path for uploads that fail
   mid-batch across DB + R2 + Chroma. (Filename sanitization, history cap, and
   storage→502 are done.)
3. **Grounding hardening:** server-side "answer ⇒ has citation" check, and an
   eval harness to tune threshold + citation behavior.
4. **Reranking + hybrid search**, then **streaming** responses.

Honest caveat: reviews here are static reads + tests with a mocked LLM and
LocalStorage; the real OpenAI, Postgres, and R2 paths are exercised by
interfaces/fakes, not end-to-end in this environment.
