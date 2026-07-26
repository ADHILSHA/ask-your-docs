# Design note

## How I decomposed the problem
I built in narrow, verifiable slices rather than generating the pipeline in one
pass — each slice one concern, tested before the next:

1. Config + `/health` (typed settings, CORS from env)
2. Upload → **extract** text (pypdf / plain-text)
3. **Chunk** the text (token-sized, overlapping)
4. **Embed + store** (Chroma) and persist on upload
5. **Retrieve** (top-k by cosine similarity)
6. **Generate** grounded answers with citations
7. Threshold gate, frontend UI, deploy config, hardening

This kept every decision reviewable and let the failure modes (unanswerable /
ambiguous questions) drive the tests.

## Key decisions
- **RAG, no fine-tuning / no framework.** The task is grounded Q&A over
  user-supplied docs — retrieval + a tight prompt is the right tool. I avoided
  LangChain/LlamaIndex so the retrieval and prompt logic stay owned and
  explainable ("why did you do this?" has a real answer at every line).
- **Chroma in-process over pgvector/Pinecone.** At this scale a local,
  persistent, embedded vector store means zero external services, zero network
  hops, and nothing to provision. I hid it behind a `VectorStore` ABC, so
  swapping to pgvector/hosted Chroma later is one new subclass, not a rewrite.
- **Single-user, no auth.** A deliberate scope cut: it removes a large surface
  (sessions, tenancy, a user DB) that adds nothing to demonstrating grounded
  retrieval. The cost — one shared store — is documented, not hidden.
- **Chunking: ~600 tokens, ~15% overlap, boundary-aware.** Split on paragraphs,
  fall back to sentences, and **never break mid-sentence** (accepting an
  occasional oversized chunk over a severed one). Overlap preserves context
  across boundaries. Token counts use tiktoken `cl100k_base` to match the
  embedding model's view.
- **Similarity threshold (0.35) as a grounding gate.** If the top match scores
  below it, skip the LLM entirely and return the fixed fallback
  *"I couldn't find this in the documents."* — cheaper and safer than letting
  the model answer from weak matches. Sources returned are only the chunks the
  answer actually cited.

## What I deferred
Streaming, reranking, and hybrid (keyword+vector) search — noted, not silently
skipped. Also deferred: multi-user/tenancy, S3 document storage, per-chunk
relevance filtering, and durable persistence on the live demo (Render's disk is
ephemeral). Reasons for each are in `self-review.md`.
