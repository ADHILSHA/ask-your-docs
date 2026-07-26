# ask-your-docs

A multi-user RAG app: sign up, upload documents, pick which documents each chat
draws from, and get answers grounded in that context — with clickable citations.
If the documents don't cover a question, it says so instead of guessing.

**Live demo:** https://ask-your-docs-eight.vercel.app/
**Backend API:** https://ask-your-docs-j96g.onrender.com (`/health`)

> The backend runs on Render's free tier and spins down when idle — the **first
> request after a while can take ~30–60s** to cold-start. Demo storage is
> ephemeral (resets on redeploy).

## Features
- **Accounts** — email/password sign up + login (JWT bearer). Each user's
  documents and conversations are private.
- **Documents** — upload PDF / `.txt` / `.md` to Chroma; files stored in
  Cloudflare R2. Download or delete anytime.
- **Per-chat context** — each conversation answers only from the documents you
  add to it; reuse a document across chats.
- **Grounded chat** — multi-turn, follow-ups understood in context, answers cite
  their sources inline (`[1]` opens the document).

## Architecture (in brief)
- **Frontend** (Next.js, Vercel): 3-pane app (conversations · chat · documents),
  calls the backend at `NEXT_PUBLIC_API_URL`. No API keys ever reach the browser.
- **Backend** (FastAPI, Render/Docker): auth (bcrypt + JWT), **Postgres** for
  users/documents/conversations, **Cloudflare R2** for raw files, **Chroma**
  (in-process) for vectors — each behind a swappable interface.
- **Ask flow:** load conversation history → condense the message into a
  standalone question → embed → retrieve top-k **scoped to the chat's context
  documents** (and the user) → similarity gate (0.35) → `gpt-4o-mini` answers
  only from retrieved context, citing `[n]` mapped back to `{filename, document}`.
- **Schema** is owned by **Alembic** migrations (`alembic upgrade head`).

## Run locally

### Backend (FastAPI, Python 3.12)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set OPENAI_API_KEY; JWT_SECRET; DATABASE_URL (SQLite default is fine)
alembic upgrade head          # create/migrate the schema
uvicorn app.main:app --reload # http://localhost:8000
```
Key env vars (see `backend/.env.example`): `OPENAI_API_KEY`, `EMBEDDING_MODEL`,
`CHAT_MODEL`, `SIMILARITY_THRESHOLD`, `ALLOWED_ORIGINS`, `DATABASE_URL`,
`JWT_SECRET`, `JWT_EXPIRE_MINUTES`, and (for R2) `STORAGE_BACKEND` + `S3_*` /
`AWS_*`. Locally, `DATABASE_URL` defaults to SQLite and `STORAGE_BACKEND=local`,
so no Postgres/R2 is needed for dev.

Run the tests: `python -m pytest` (from `backend/`).

### Frontend (Next.js)
```bash
cd frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                    # http://localhost:3000
```

## Deploy
- **Backend → Render** (Docker): the image runs `alembic upgrade head` then
  uvicorn on `$PORT`. Set env vars (incl. a **strong `JWT_SECRET`**, Postgres
  `DATABASE_URL`, R2 credentials). See `docs/multiuser-plan.md`.
- **Frontend → Vercel**: root directory `frontend`, set `NEXT_PUBLIC_API_URL`.

## Deliverables & docs
- `docs/design-note.md` — decomposition, key decisions, deferrals
- `docs/ai-usage.md` — what was decided vs. delegated to AI
- `docs/self-review.md` — trade-offs, findings by severity, next steps
- `docs/multiuser-plan.md` — the multi-user architecture (auth, R2, context)
- `docs/chat-plan.md` — the conversational design
- `.claude/skills/grounding/SKILL.md` — the grounding/citation contract
