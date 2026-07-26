# Plan: conversational (multi-turn) chat

> **Status: implemented.** M1 (multi-turn) and M2 (query condensation) are built;
> chat is server-persisted per conversation. M3 polish (history truncation,
> streaming) is deferred — see `self-review.md`.

Turn the single-shot "ask one question, get one answer" flow into a chat where
the user can have a back-and-forth — follow-ups, and answering the app's
clarifying questions — while keeping every answer grounded in retrieved context.

## Goal & why now
The grounding contract already includes "ask ONE clarifying question when
ambiguous" — but that only makes sense in a conversation, where the user can
reply. Multi-turn also makes natural follow-ups work ("what about sick leave?",
"summarize that"). This is the missing half of the intended UX.

## Guiding constraint
**Stay inside the current scope: no database, no auth, single-user.** We can do
this by keeping conversation history **client-side** — the frontend holds the
message list and sends it with each request; the backend stays stateless. No
session store, no user table. (This is the key decision that lets us add chat
without crossing the CLAUDE.md hard rules.)

## The central design problem: retrieval on follow-ups
A follow-up like *"what about sick leave?"* is not self-contained — embedding it
alone retrieves poorly. Standard fix: **query condensation** — before retrieval,
use the LLM to rewrite the latest message into a standalone question using the
recent history, then embed + retrieve on the rewritten query.

- **Phase 1 (naive):** retrieve on the raw latest user message. Cheap, works for
  self-contained questions, weak on pronoun/reference follow-ups.
- **Phase 2 (condensation):** add a rewrite step. One extra small LLM call;
  markedly better follow-up retrieval. This is where chat actually feels good.

## Grounding: what must NOT change
- **Answers still come only from freshly retrieved context each turn.** History
  is used to *resolve references*, not as a knowledge source — the model must not
  answer from something it "remembers" saying earlier without re-retrieving.
- **Threshold gate still applies** to the (condensed) query — below it → the
  fixed fallback, and the conversation simply continues.
- **Citations per assistant message**, same `[n] → {filename, chunk_index}`
  mapping. Clarifying-question and fallback turns still return `sources: []`.
- ⚠️ **The system prompt will likely need an edit** (instructions for using
  history only to resolve references, and keeping each answer grounded). That
  file is marked "do not modify without asking" — **this needs explicit sign-off
  before implementation.**

## Backend changes
- **New endpoint `POST /chat`** (keep `/ask` for the simple path):
  - Request: `{ messages: [{role, content}], k? }` — the full short history,
    client-supplied.
  - Flow: (optional) condense latest user message using history → embed →
    retrieve top-k → threshold gate → generate grounded answer with the recent
    history in the prompt → return `{ answer, sources }`.
  - Response shape stays `{ answer, sources }` (one assistant turn).
- **History bounds:** cap to the last N turns / M tokens before prompting, to
  control cost and stay in the model's context window. Reject over-long payloads.
- **Schema/validation:** `messages` non-empty, last role must be `user`, per-role
  content length caps (reuse the existing validation posture).
- Stateless — no storage; the store/retrieval/generation modules are reused.

## Frontend changes
- Replace `AskPanel` (single Q→A) with a **`ChatPanel`**:
  - Scrollable message list: user + assistant bubbles; assistant bubbles show the
    per-message **Sources** list (reuse `AnswerView` styling).
  - Input box + send; disable while a turn is in flight; loading + error states
    per turn.
  - Holds the `messages` array in state; on send, POST the history to `/chat`,
    append the reply.
- `lib/api.ts`: add `chat(messages)`; keep types.
- `UploadPanel` unchanged — docs are still the grounding source.

## Milestones (incremental, each shippable)
1. **M1 — multi-turn plumbing:** `/chat` (naive retrieval on latest message) +
   `ChatPanel`. Follow-ups that are self-contained work; clarifying-question flow
   becomes usable end-to-end.
2. **M2 — query condensation:** rewrite-then-retrieve for good follow-up recall.
3. **M3 — polish:** history truncation, streaming responses (tokens render
   progressively), and better error/empty states.

## Tests
- Multi-turn grounding: answer stays grounded; history doesn't become an
  ungrounded source (assert a fact only in history but not re-retrieved isn't
  answered).
- Follow-up resolution (with M2): "what about X?" retrieves the right chunks.
- Clarifying → user reply → grounded answer, across two turns.
- Threshold gate still fires on an off-topic follow-up.
- Validation: empty messages / wrong last role / oversized history rejected.

## Out of scope / deferred (with reasons)
- **Server-side chat persistence & history across sessions** — needs a DB; out of
  the current no-DB scope. Client-held history is enough for single-user.
- **Multi-user / per-user conversations** — belongs to the multi-user milestone
  (`user_id` + filtered retrieval), not this change.
- **Streaming** — real UX win but additive; deferred to M3.
- **Summarizing long histories** (beyond simple truncation) — only if cost/window
  becomes a real problem.

## Open questions (need your call before building)
1. **Approve a system-prompt edit** for history handling? (Required for correct
   grounding in chat.)
2. **Condensation in M1 or wait for M2?** (Affects how good follow-ups feel on
   first ship.)
3. **Replace `/ask` + single-shot UI, or keep both** (chat as the primary view,
   simple ask retained)?
