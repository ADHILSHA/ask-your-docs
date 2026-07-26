"use client";

import { useState } from "react";
import { chat, type Message, type Source } from "@/lib/api";

interface ChatMessage extends Message {
  sources?: Source[];
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(e: React.SyntheticEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const withUser: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(withUser);
    setInput("");
    setSending(true);
    setError(null);
    try {
      // send role+content only (drop the per-message sources we keep for display)
      const history: Message[] = withUser.map(({ role, content }) => ({ role, content }));
      const res = await chat(history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-sm font-medium">2. Chat with your documents</h2>

      <div className="flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Ask a question about your uploaded documents. Follow-ups are understood
            in context.
          </p>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "self-end max-w-[85%] rounded-lg bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "self-start max-w-[85%] rounded-lg border border-zinc-200 px-3 py-2 dark:border-zinc-800"
            }
          >
            <p className="whitespace-pre-wrap text-sm leading-6">{m.content}</p>
            {m.sources && m.sources.length > 0 && (
              <ul className="mt-2 flex flex-col gap-0.5 border-t border-zinc-200 pt-2 dark:border-zinc-700">
                {m.sources.map((s, j) => (
                  <li
                    key={`${s.filename}-${s.chunk_index}-${j}`}
                    className="font-mono text-xs text-zinc-500 dark:text-zinc-400"
                  >
                    {s.filename} #{s.chunk_index + 1}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {sending && (
          <p className="self-start text-sm text-zinc-500 dark:text-zinc-400">Thinking…</p>
        )}
      </div>

      <form onSubmit={handleSend} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700"
        />
        <button
          type="submit"
          disabled={sending || input.trim().length === 0}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Send
        </button>
      </form>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </section>
  );
}
