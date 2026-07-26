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
- **Single-user, no auth** as a deliberate scope cut, and later the decision to
  *defer* multi-user/tenancy/S3 rather than build them speculatively.
- **Chunking strategy:** ~600 tokens, ~15% overlap, boundary-aware, never break
  mid-sentence — I set the approach and the numbers.
- **Grounding contract:** the 0.35 similarity gate, the exact unanswerable
  fallback, the one-clarifying-question rule, and the citation format. The system
  prompt was mine and marked off-limits to the assistant.
- **Deployment topology** (why Render for the backend, Vercel for the frontend)
  and the **security triage** — which findings to fix now vs. defer, and why.

## What I delegated to the assistant
Implementation of the above, under my review:
- Boilerplate & scaffolding (monorepo, `config.py`, env examples, test setup).
- The FastAPI routes and the pipeline modules (extraction, chunking, the
  Chroma `VectorStore`, embeddings, generation + citation parsing).
- The Next.js UI and `lib/api.ts` client.
- Deploy config (Dockerfile reading `$PORT`, CORS-from-env) and the test suite.

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

## How I worked
One concern per change, reviewed before the next; tests for the retrieval and
grounding logic specifically (the unanswerable and ambiguous cases); and a
security self-review pass where I decided what to fix and what to defer — with a
reason for each — captured in `self-review.md`. The AI accelerated the build;
the direction, constraints, and final judgment were mine.
