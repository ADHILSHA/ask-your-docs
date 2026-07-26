"use client";

import { useEffect, useState } from "react";
import { chat, getMessages, type MessageInfo } from "@/lib/api";
import { MessageContent } from "@/components/MessageContent";

export function ChatPanel({
  conversationId,
  hasContextDocs,
  onConversationChanged,
}: {
  conversationId: string | null;
  hasContextDocs: boolean;
  onConversationChanged: () => void;
}) {
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load messages whenever the active conversation changes.
  useEffect(() => {
    if (!conversationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const msgs = await getMessages(conversationId);
        if (!cancelled) setMessages(msgs);
      } catch {
        // 401 clears the token in the api layer.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  async function handleSend(e: React.SyntheticEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending || !hasContextDocs || !conversationId) return;
    setSending(true);
    setError(null);
    try {
      const stamp = Date.now();
      setMessages((m) => [
        ...m,
        { id: `u-${stamp}`, role: "user", content: text, sources: [], created_at: "" },
      ]);
      setInput("");
      const res = await chat(conversationId, text);
      setMessages((m) => [
        ...m,
        { id: `a-${stamp}`, role: "assistant", content: res.answer, sources: res.sources, created_at: "" },
      ]);
      onConversationChanged(); // first message sets the conversation title
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
            <p className="max-w-xs text-sm text-zinc-500 dark:text-zinc-400">
              {hasContextDocs
                ? "Ask a question about the documents in this chat."
                : "Add a document to this chat from the panel on the right to get started."}
            </p>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-3 px-4 py-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "self-end max-w-[85%] rounded-lg bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "self-start max-w-[85%] rounded-lg border border-zinc-200 px-3 py-2 dark:border-zinc-800"
                }
              >
                <MessageContent content={m.content} sources={m.sources} />
              </div>
            ))}
            {sending && (
              <p className="self-start text-sm text-zinc-500 dark:text-zinc-400">Thinking…</p>
            )}
          </div>
        )}
      </div>

      <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <form onSubmit={handleSend} className="mx-auto flex w-full max-w-3xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!hasContextDocs}
            placeholder={
              hasContextDocs ? "Ask a question…" : "Add a document to this chat to start"
            }
            className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700"
          />
          <button
            type="submit"
            disabled={sending || !hasContextDocs || input.trim().length === 0}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          >
            Send
          </button>
        </form>
        {error && (
          <p className="mx-auto mt-2 w-full max-w-3xl text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
