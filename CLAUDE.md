# ask-your-docs

A small RAG app: upload documents, ask questions, get answers grounded in the
source material with visible citations. Take-home assignment — optimizing for
clear decisions and honest trade-offs over feature count or polish.

## Stack
- Frontend: Next.js (App Router, TypeScript) — `frontend/`
- Backend: FastAPI (Python 3.12) — `backend/`
- LLM + embeddings: OpenAI (`text-embedding-3-small`, `gpt-4o-mini`)
- Vector store: Chroma, in-process, local persistence (per-user isolation via a
  `user_id` metadata filter)
- Database: Postgres (Render) — users, document ownership, conversations;
  SQLite locally via the same SQLAlchemy code
- File storage: Cloudflare R2 (S3-compatible) for raw uploaded documents
- Auth: email/password, bcrypt-hashed, stateless JWT (Bearer) — no email
  verification (deliberate simplification)
- Deploy: frontend on Vercel, backend on Render (same repo, separate root dirs)

## Repo layout
- `backend/app/` — FastAPI app, split by concern:
  - `api/routes/` — HTTP routes (health, documents, conversations, qa/chat)
  - `rag/` — the owned pipeline (extraction, chunking, retrieval, generation)
  - `auth/` — bcrypt + JWT security, `get_current_user`, auth routes
  - `models/` — SQLAlchemy models (user, document, conversation, message + links)
  - `store.py` (Chroma vectors), `storage.py` (R2/local files), `config.py`,
    `db.py`, `dependencies.py`, `schemas.py`
  - `alembic/` — DB migrations (source of truth for schema)
- `frontend/` — Next.js app: 3-pane UI (`components/`: conversations · chat ·
  documents), `lib/api.ts` client. Auth-gated.
- `docs/` — design note, AI-usage note, self-review (required deliverables),
  plus the multi-user and chat plans.
- `.claude/skills/grounding/` — the grounding/citation contract.

## Hard rules — do not violate
- **Never put API keys in frontend code or in anything `NEXT_PUBLIC_*`.**
  All LLM/embedding calls happen server-side, in `backend/`, reading keys
  from environment variables only.
- **Answers must be grounded in retrieved context only.** No outside
  knowledge in generated answers. If the context doesn't cover the
  question, return: "I couldn't find this in the documents." Never
  hallucinate a plausible-sounding answer.
- **Every answer must return its sources** (filename + chunk index) —
  citations are a scored requirement, not a nice-to-have.
- **Do not modify the system prompt in `generation.py`** without being
  asked explicitly — it's hand-written and reviewed, not a draft.
- **Multi-user with email/password auth is the current direction** (see
  `docs/multiuser-plan.md`). Postgres (Render) is the source of truth for
  identity, document ownership, and conversations; Cloudflare R2 stores raw
  uploaded files. Passwords are bcrypt-hashed; JWTs are signed with a
  server-side secret. All secrets stay server-side.
- **Chroma stays the vector store** — Postgres/pgvector do not replace it.
  Per-user isolation is done by tagging chunks with `user_id` in Chroma
  metadata and filtering every query by it, not by adding a second vector DB.
- **Every resource is owned** — documents and conversations are scoped to a
  `user_id`; filter every query by the authenticated user and never return
  another user's data.

## Working style
- Build in small, narrow slices — one concern per change. Do not generate
  an entire feature (e.g. "the whole RAG pipeline") in one pass.
- Prefer simple, explainable code over clever abstractions. This is a
  demo being reviewed by a human who will ask "why did you do this."
- When you make a non-trivial choice (library, threshold value, chunking
  strategy), state the reasoning in the response and, where relevant, in the
  design note / self-review.
- Write tests for retrieval and grounding logic specifically — especially
  the two failure modes: unanswerable questions and ambiguous questions.
- Keep commits atomic with clear, conventional messages
  (`feat:`, `fix:`, `chore:`, `docs:`).

## Config / environment
- Backend env vars: `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `CHAT_MODEL`,
  `SIMILARITY_THRESHOLD`, `ALLOWED_ORIGINS`, `DATABASE_URL`, `JWT_SECRET`,
  `JWT_EXPIRE_MINUTES`, for R2: `STORAGE_BACKEND`, `S3_BUCKET`,
  `S3_ENDPOINT`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  and for Chroma Cloud (durable vectors): `CHROMA_API_KEY`, `CHROMA_TENANT`,
  `CHROMA_DATABASE` (empty -> in-process Chroma).
  Documented in `backend/.env.example` — keep it in sync with actual usage.
  `DATABASE_URL` is normalized to the psycopg dialect, so a Render `postgres://`
  value can be used verbatim. `JWT_SECRET` must be non-default in production
  (the app fails fast otherwise).
- Frontend env vars: `NEXT_PUBLIC_API_URL` only — nothing else should be
  `NEXT_PUBLIC_*`.
- CORS origins are read from env, never hardcoded, so dev and prod don't
  require a code change.

## What NOT to do without being asked
- Don't add a framework like LangChain/LlamaIndex — retrieval and prompt
  logic should stay owned and explainable, not abstracted away.
- Don't add streaming responses, reranking, or hybrid search — noted as
  deferred, not silently skipped.
- Don't restructure the folder layout or rename modules — ask first if a
  change seems needed.

## See also
- `frontend/AGENTS.md` — Next.js version-specific warnings (framework
  quirks only, not project rules — this file is the source of truth for
  project rules).