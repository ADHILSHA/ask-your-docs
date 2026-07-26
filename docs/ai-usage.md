# AI usage

I used an AI coding assistant (Claude Code) as an implementation multiplier: I
made the engineering and product decisions and set the constraints; the
assistant wrote most of the code to execute them, in small slices I reviewed and
gated with tests. The judgment was mine; the typing was largely delegated.

## Decisions I owned
These were my calls, made up front or as trade-offs surfaced — not the
assistant's defaults:
- **Architecture & stack:** Next.js (Vercel) + FastAPI (Render), OpenAI for
  embeddings/generation, and the frontend/backend split with keys server-side.
- **RAG without a framework.** I chose to keep retrieval and prompting hand-owned
  (no LangChain/LlamaIndex) so every decision stays explainable.
- **Chroma in-process over pgvector/Pinecone**, hidden behind a `VectorStore`
  interface so it's swappable — my call on scale vs. infra cost.
- **Single-user first, then a deliberate expansion to multi-user.** I started
  single-user (no auth, no external DB) to keep the RAG core focused, then chose
  when to add accounts, per-user isolation, R2 storage, and per-conversation
  context — writing the plan down first and building it in phased, testable
  milestones rather than all at once.
- **Multi-user architecture:** Postgres for identity/ownership, Cloudflare R2 for
  files (behind a `DocumentStorage` interface), JWT-in-localStorage for auth
  (accepting the XSS trade-off for simplicity), and **per-conversation document
  context** (a chat answers only from documents I add to it). I also decided to
  make **Alembic** the schema source of truth once `create_all` couldn't handle a
  column addition.
- **Chunking strategy:** ~600 tokens, ~15% overlap, boundary-aware, never break
  mid-sentence — I set the approach and the numbers.
- **Grounding contract:** the 0.35 similarity gate, the exact unanswerable
  fallback, the one-clarifying-question rule, and the citation format. The system
  prompt was mine and marked off-limits to the assistant; I authorized each edit
  (conversation handling, inline-citation placement) explicitly.
- **Deployment topology** (why Render for the backend, Vercel for the frontend,
  Render Postgres + R2) and the **security triage** — which findings to fix now
  vs. defer, and why.

## What I delegated to the assistant
Implementation of the above, under my review:
- Boilerplate & scaffolding (monorepo, `config.py`, env examples, test setup).
- The FastAPI routes and the pipeline modules (extraction, chunking, the
  Chroma `VectorStore`, embeddings, generation + citation parsing).
- Auth (bcrypt + JWT), SQLAlchemy models, Alembic migrations, the R2/local
  `DocumentStorage`, and per-conversation context endpoints.
- The Next.js UI — the 3-pane app (conversations · chat · documents), the upload
  dropzone, inline citation rendering — and the `lib/api.ts` client.
- Deploy config (Dockerfile running migrations + reading `$PORT`, CORS-from-env)
  and the test suite (~50 tests, incl. cross-user isolation).

Delegating the code let me spend my time on the decisions and the review, and
move in tight, verifiable increments.

## Where I had to steer it
The assistant's raw defaults were sometimes wrong, and part of my job was
catching them:
- **Batching embeddings.** Left to default it would embed one chunk per API
  call; I required batching into one call per document.
- **Chunking edges.** Its sentence splitter mis-handles abbreviations and its
  re-join normalizes whitespace — I chose to accept these as *documented*
  trade-offs rather than let them ship unnoticed.
- **Protecting reviewed artifacts.** When it was pointed at a system prompt that
  didn't yet exist, I expected it to stop and ask rather than fabricate one — and
  I made the call on the citation format when it flagged an ambiguity.
- **Keys stay server-side.** I enforced the rule that nothing but the API URL is
  `NEXT_PUBLIC_*`, and verified no secret reaches the browser or the Docker image.
- **Runtime.** I decided to pin the image to the tested Python 3.12 when it
  flagged a mismatch with the project doc.
- **Migrations.** When a schema change broke against an existing DB (`create_all`
  can't add a column), I had it introduce Alembic properly — baseline + a
  data-preserving backfill — rather than drop the dev database.
- **Rendering vs. model behavior.** When citations rendered wrong or clustered at
  the end, I distinguished the actual causes it surfaced — a `cite:` URL the
  markdown sanitizer stripped (a real bug, fixed) vs. the model grouping
  citations (a prompt nudge, not a guaranteed fix) — and decided the response to
  each.

## How I worked
One concern per change, reviewed before the next; tests for the retrieval and
grounding logic specifically (the unanswerable and ambiguous cases); and a
security self-review pass where I decided what to fix and what to defer — with a
reason for each — captured in `self-review.md`. The AI accelerated the build;
the direction, constraints, and final judgment were mine.
