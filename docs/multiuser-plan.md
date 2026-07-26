# Plan: multi-user (email/password) + per-user docs (S3) + persistent chat

> **Status: implemented.** Milestones A–D are built and tested (auth, per-user
> retrieval, R2 file storage, persistent conversations), plus per-conversation
> document context beyond the original plan. This doc is kept as the design
> record; deferred hardening (rate limiting, `JWT_SECRET` enforcement, filename
> sanitization, bounded history) is tracked in `self-review.md`.

Add simple accounts so each user has their own documents and conversations.
Deliberately minimal auth: email + password, **no email verification, no reset,
no OAuth**. This is a real architectural step up from the single-user demo.

## ⚠️ Governance first
Multi-user, authentication, a hosted relational DB, and S3 all currently
**violate CLAUDE.md hard rules**. Before building, update CLAUDE.md to make this
the sanctioned architecture (and record why), so the rules and the code agree.

## What changes at a high level
Three new pieces of state, three seams:
1. **A relational DB** (users, documents, conversations, messages) — the new
   source of truth for identity and ownership. → **Postgres** (Render managed);
   SQLite locally via the same SQLAlchemy code.
2. **S3 for raw files** — uploaded bytes live in object storage, behind a
   `DocumentStorage` interface (Local for dev, S3 for prod), mirroring the
   `VectorStore` ABC.
3. **Per-user isolation in retrieval** — every chunk is tagged with `user_id` in
   Chroma metadata, and **every query is filtered by `user_id`**. This is what
   makes one user's docs invisible to another — no per-user collections needed.

## Auth (kept simple)
- **Signup** `POST /auth/signup {email, password}` → create user, return a token.
- **Login** `POST /auth/login {email, password}` → verify, return a token.
- **Passwords:** hashed with **bcrypt** (already a dependency); never stored
  plaintext. Enforce a minimum length.
- **Sessions:** stateless **JWT** (HS256, `user_id` claim, signed with
  `JWT_SECRET`, short expiry). Sent as `Authorization: Bearer <token>`.
- **`get_current_user` dependency** resolves the token → user; every doc/chat
  route depends on it. Unauthenticated → 401.
- Frontend stores the token (localStorage for simplicity — note the XSS
  trade-off vs. an httpOnly cookie; cookie needs CORS credentials + CSRF care).

## Data model (Postgres via SQLAlchemy)
- **users:** `id` (uuid), `email` (unique), `password_hash`, `created_at`
- **documents:** `id`, `user_id` → users, `filename`, `s3_key`, `char_count`,
  `chunk_count`, `created_at`
- **conversations:** `id`, `user_id` → users, `title`, `created_at`
- **messages:** `id`, `conversation_id` → conversations, `role`, `content`,
  `sources` (json), `created_at`

Chunks stay in Chroma, now with metadata `{user_id, document_id, filename,
chunk_index}`. (Start with SQLAlchemy `create_all` for speed; add Alembic
migrations when the schema stabilizes.)

## Per-user retrieval (interface change)
`VectorStore` becomes user-scoped:
- `add_chunks(user_id, chunks, embeddings)` — writes `user_id` into metadata.
- `query(user_id, embedding, k)` — Chroma `where={"user_id": user_id}`.
- `delete_document(user_id, document_id)` — for the delete/re-upload path.
This also fixes the earlier shared-state and stale-chunk issues.

## Documents + S3
- **Upload** (auth): stream file → **S3** (`{user_id}/{document_id}/{filename}`) →
  record a `documents` row → extract → chunk → embed → store with `user_id`.
- **`GET /documents`** (auth): list the caller's documents from the DB.
- **`DELETE /documents/{id}`** (auth): ownership-checked → remove chunks
  (`user_id`+`document_id`), the S3 object, and the DB row.
- Optional: view/download via a **presigned S3 URL**.
- `boto3` dependency; `DocumentStorage` ABC with `LocalStorage` + `S3Storage`.

## Chat context maintenance (server-side)
Move history from client-held to **persisted per user**, so context survives
reloads and is tied to the account:
- **`POST /conversations`** → new conversation; **`GET /conversations`** → list;
  **`GET /conversations/{id}/messages`** → thread.
- **`POST /chat {conversation_id, message}`** (auth, ownership-checked):
  load recent messages from DB as history → **condense** (existing M1 logic) →
  embed → **retrieve filtered by `user_id`** → threshold gate → generate →
  **persist** the user + assistant messages (with sources) → return the answer.
- Bound history (last N messages / M tokens) before prompting, as today.
- Grounding rules unchanged: history resolves the question; answers stay grounded
  in freshly retrieved, user-scoped context.

## Proposed structure (extends the earlier scalable layout)
```
app/
  db.py                 # engine + session dependency
  models/               # user.py, document.py, conversation.py, message.py
  auth/                 # security.py (hash, jwt), deps.py (get_current_user), routes.py
  api/routes/           # documents.py, conversations.py, chat.py (all auth-guarded)
  stores/               # vector.py (user-scoped), documents.py (Local/S3)
  services/             # ingestion.py, qa.py (now take a user_id)
  schemas/              # auth.py, documents.py, chat.py
```

## Frontend
- **Auth screens:** signup + login; store token; attach `Authorization` header in
  `lib/api.ts`; redirect unauthenticated users.
- **Documents view:** list the user's uploaded docs (with delete).
- **Chat:** a conversation loaded from the server (optionally a conversation
  list/sidebar); messages persist across reloads.
- Reuse `UploadPanel` / `ChatPanel`, now behind auth and per-conversation.

## Config additions
`DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, and S3 (`S3_BUCKET`,
`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional
`S3_ENDPOINT` for R2-compatible). Keep `.env.example` in sync.

## Milestones (each shippable, tests green) — ✅ all done
- **A — Auth + DB:** users table, signup/login, JWT, `get_current_user`; guard
  existing routes. (No retrieval changes yet — one shared store still, but gated.)
- **B — Per-user retrieval:** `user_id` in chunk metadata + filtered queries +
  `documents` table + `GET /documents`. Real isolation.
- **C — S3 storage:** `DocumentStorage` (Local/S3), upload to S3, list/delete.
- **D — Persistent chat:** conversations + messages, `/chat` by `conversation_id`.

## Security notes
- Passwords hashed (bcrypt); JWT secret from env; enforce password min length.
- **Ownership checks on every resource** (documents, conversations) — filter by
  `user_id`, 404/403 on cross-user access.
- Rate-limit the auth endpoints (brute force) — simple per-IP limit.
- Keys/secrets stay server-side (unchanged rule).

## Deliberately deferred (with reasons)
- **Email verification / password reset / OAuth** — explicitly out of scope
  ("very simple"); note as known weakness (anyone can register any email).
- **Refresh tokens / token revocation** — short-lived JWT is enough to start.
- **Teams / roles / sharing** — single-owner per resource for now.
- **Streaming, OCR, reranking** — unchanged deferrals.

## Decisions (locked in)
1. **DB host:** **Render Postgres** (one platform). SQLite locally for dev/tests
   via the same SQLAlchemy code.
2. **Object store:** **Cloudflare R2** (S3-compatible; `boto3` with `S3_ENDPOINT`,
   no egress fees).
3. **Token storage:** **localStorage + Bearer JWT** (simple; XSS trade-off
   accepted and noted — mitigate by keeping token short-lived + strict frontend
   dep hygiene).
4. **Chat history:** **server-persisted** (`conversations` + `messages` tables),
   as specified above.

## Milestone A — slice breakdown (auth + DB)
Buildable and testable **locally on SQLite** — no Render/R2 provisioning needed
to verify. New deps: `sqlalchemy`, a Postgres driver (`psycopg[binary]`),
`pyjwt` (bcrypt is already present).
- **A0:** Update CLAUDE.md governance (record the sanctioned architecture).
- **A1:** Add deps + config (`DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`),
  `db.py` (engine + session dependency), keep `.env.example` in sync.
- **A2:** `User` model + table creation; `auth/security.py`
  (`hash_password`, `verify_password`, `create_access_token`, `decode_token`).
- **A3:** Auth schemas + routes (`POST /auth/signup`, `POST /auth/login`) and the
  `get_current_user` dependency.
- **A4:** Guard existing routes with `get_current_user` (401 when missing);
  tests for signup, login, bad creds, and protected-access.
- **A5 (frontend):** signup/login screens, token in localStorage, `Authorization`
  header in `lib/api.ts`, redirect unauthenticated users.

Milestones B–D (per-user retrieval, S3, persistent chat) follow once A is green.
