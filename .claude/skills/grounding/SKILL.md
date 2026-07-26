---
name: grounding
description: The grounding and citation contract for ask-your-docs answers — use retrieved context only, the exact unanswerable/ambiguous responses, citation format, and the no-keys-client-side rule. Apply whenever generating or reviewing answer/generation code.
---

# Grounding contract

Every answer the app produces must obey these rules. They are not suggestions —
they are what "grounded" means here.

## Rules

1. **Context only.** Answer using only the retrieved context passed to the
   model. No outside/model knowledge, no plausible-sounding filler.
2. **Unanswerable → fixed fallback.** If the context doesn't cover the
   question, reply with exactly:
   `I couldn't find this in the documents.`
   (verbatim, nothing else).
3. **Ambiguous → one question.** If the question could reasonably mean several
   things, don't guess — ask exactly **one** short clarifying question.
4. **Always cite.** When you answer, cite the sources used as
   `[filename #chunk_index]`. Cite only sources you actually relied on.
5. **Never expose keys client-side.** LLM/embedding calls happen server-side
   only; keys come from environment variables and never appear in frontend code
   or anything `NEXT_PUBLIC_*`.

## Sources returned

`sources` in the API response are the chunks the answer **actually cited** —
not everything retrieved. A fallback or clarifying-question answer returns
`sources: []`.

## Implementation note

On the wire the model cites numbered context blocks as `[n]`, which the backend
maps back to each chunk's `{filename, chunk_index}`. `[filename #chunk_index]`
is the contract's canonical, human-readable form.
