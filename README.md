# ask-your-docs

Upload documents, ask questions, get answers grounded in the source material
with visible citations. If the docs don't cover a question, it says so instead
of guessing.

**Live demo:** https://ask-your-docs-eight.vercel.app/
**Backend API:** https://ask-your-docs-j96g.onrender.com (`/health`)

> The backend runs on Render's free tier and spins down when idle — the **first
> request after a while can take ~30–60s** to cold-start. The demo store is
> ephemeral (resets on redeploy) and shared (single-user scope).

## Architecture (3 lines)
- **Frontend** (Next.js, Vercel) is a single page that calls the backend at
  `NEXT_PUBLIC_API_URL`; no API keys ever reach the browser.
- **Ingest:** extract text (pypdf / `.txt` / `.md`) → chunk (~600 tokens, ~15%
  overlap) → embed (`text-embedding-3-small`, batched) → store in Chroma
  (in-process, local persistence).
- **Ask:** embed the question → Chroma top-k → similarity gate (0.35) →
  `gpt-4o-mini` answers only from retrieved context, citing `[n]` markers mapped
  back to `{filename, chunk_index}`.

## Run locally

### Backend (FastAPI, Python 3.12)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set OPENAI_API_KEY (required)
alembic upgrade head          # create/migrate the database schema
uvicorn app.main:app --reload # http://localhost:8000
```
Key env vars (see `backend/.env.example`): `OPENAI_API_KEY`, `EMBEDDING_MODEL`,
`CHAT_MODEL`, `SIMILARITY_THRESHOLD`, `ALLOWED_ORIGINS`.

Run the tests: `python -m pytest` (from `backend/`).

### Frontend (Next.js)
```bash
cd frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                    # http://localhost:3000
```

## Deliverables
- `docs/design-note.md` — decomposition, key decisions, deferrals
- `docs/ai-usage.md` — what was delegated to AI, where it fell short, corrections
- `docs/self-review.md` — trade-offs, known weaknesses, next steps
- `.claude/skills/grounding/SKILL.md` — the grounding/citation contract
