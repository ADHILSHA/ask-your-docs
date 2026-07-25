# ask-your-docs

A small RAG app: upload documents, ask questions, get answers grounded in the
source material with visible citations. Take-home assignment — optimizing for
clear decisions and honest trade-offs over feature count or polish.

## Stack
- Frontend: Next.js (App Router, TypeScript) — `frontend/`
- Backend: FastAPI (Python 3.11) — `backend/`
- LLM + embeddings: OpenAI (`text-embedding-3-small`, `gpt-4o-mini`)
- Vector store: Chroma, in-process, local persistence — no external DB
- Deploy: frontend on Vercel, backend on Render (same repo, separate root dirs)

## Repo layout
- `backend/app/` — FastAPI app; one module per concern (chunking, store,
  retrieval, generation). Mirrors the build slices — see NOTES.md for order.
- `frontend/app/` — single-page UI: upload, ask, answer + sources.
- `docs/` — design note, AI-usage note, self-review (required deliverables).
- `.claude/skills/grounding/` — the grounding/citation contract.
- `NOTES.md` — running log of decisions and corrections. Check before
  assuming a decision hasn't been made yet.

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
- **Do not add a hosted/managed database** (Postgres, pgvector, Pinecone,
  etc.) unless explicitly asked. In-process Chroma is a deliberate choice
  for this scale — see NOTES.md for the reasoning.
- **Do not add authentication or multi-user support** unless explicitly
  asked. Single-user is a deliberate scope cut.

## Working style
- Build in small, narrow slices — one concern per change. Do not generate
  an entire feature (e.g. "the whole RAG pipeline") in one pass.
- Prefer simple, explainable code over clever abstractions. This is a
  demo being reviewed by a human who will ask "why did you do this."
- When you make a non-trivial choice (library, threshold value, chunking
  strategy), state the reasoning in the response so it can be logged in
  NOTES.md.
- Write tests for retrieval and grounding logic specifically — especially
  the two failure modes: unanswerable questions and ambiguous questions.
- Keep commits atomic with clear, conventional messages
  (`feat:`, `fix:`, `chore:`, `docs:`).

## Config / environment
- Backend env vars: `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `CHAT_MODEL`,
  `SIMILARITY_THRESHOLD`, `ALLOWED_ORIGINS`. Documented in
  `backend/.env.example` — keep that file in sync with actual usage.
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