"use client";

import { useState } from "react";
import { ask, type AskResponse } from "@/lib/api";
import { AnswerView } from "@/components/AnswerView";

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [askError, setAskError] = useState<string | null>(null);

  async function handleAsk(e: React.SyntheticEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    setAsking(true);
    setAskError(null);
    setResult(null);
    try {
      const res = await ask(trimmed);
      setResult(res);
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setAsking(false);
    }
  }

  return (
    <>
      <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="text-sm font-medium">2. Ask a question</h2>
        <form onSubmit={handleAsk} className="flex flex-col gap-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="What would you like to know?"
            className="w-full resize-y rounded-md border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700"
          />
          <button
            type="submit"
            disabled={asking || question.trim().length === 0}
            className="self-start rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {asking ? "Asking…" : "Ask"}
          </button>
        </form>
        {askError && (
          <p className="text-sm text-red-600 dark:text-red-400">{askError}</p>
        )}
      </section>

      {result && <AnswerView result={result} />}
    </>
  );
}
