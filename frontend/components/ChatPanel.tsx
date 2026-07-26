"use client";

import { useCallback, useEffect, useState } from "react";
import {
  chat,
  createConversation,
  getMessages,
  listConversations,
  type ConversationInfo,
  type MessageInfo,
} from "@/lib/api";

export function ChatPanel() {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    const convs = await listConversations();
    setConversations(convs);
    return convs;
  }, []);

  // Load the most recent conversation (if any) on mount.
  useEffect(() => {
    (async () => {
      try {
        const convs = await refreshConversations();
        if (convs.length > 0) {
          setActiveId(convs[0].id);
          setMessages(await getMessages(convs[0].id));
        }
      } catch {
        // 401 clears the token in the api layer.
      }
    })();
  }, [refreshConversations]);

  async function selectConversation(id: string) {
    setActiveId(id);
    setError(null);
    try {
      setMessages(await getMessages(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversation");
    }
  }

  async function newChat() {
    setError(null);
    try {
      const conv = await createConversation();
      setConversations((c) => [conv, ...c]);
      setActiveId(conv.id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start a chat");
    }
  }

  async function handleSend(e: React.SyntheticEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    try {
      let id = activeId;
      if (!id) {
        const conv = await createConversation();
        setConversations((c) => [conv, ...c]);
        id = conv.id;
        setActiveId(id);
      }
      const stamp = Date.now();
      setMessages((m) => [
        ...m,
        { id: `u-${stamp}`, role: "user", content: text, sources: [], created_at: "" },
      ]);
      setInput("");
      const res = await chat(id, text);
      setMessages((m) => [
        ...m,
        { id: `a-${stamp}`, role: "assistant", content: res.answer, sources: res.sources, created_at: "" },
      ]);
      refreshConversations(); // first message sets the conversation title
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex items-center gap-2">
        <h2 className="mr-auto text-sm font-medium">Chat</h2>
        {conversations.length > 0 && (
          <select
            value={activeId ?? ""}
            onChange={(e) => selectConversation(e.target.value)}
            className="max-w-[55%] truncate rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-xs dark:border-zinc-700"
          >
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        )}
        <button
          type="button"
          onClick={newChat}
          className="rounded-md border border-zinc-300 px-2 py-1 text-xs dark:border-zinc-700"
        >
          New chat
        </button>
      </div>

      <div className="flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Ask a question about your uploaded documents. Follow-ups are understood
            in context.
          </p>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
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
