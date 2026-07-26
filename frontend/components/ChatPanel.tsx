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
import { MessageContent } from "@/components/MessageContent";
import { UploadButton } from "@/components/UploadButton";

function DocIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="h-10 w-10 text-zinc-300 dark:text-zinc-600"
      aria-hidden
    >
      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
      <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
    </svg>
  );
}

export function ChatPanel({
  hasDocuments,
  onActiveConversationChange,
  onDocumentsUploaded,
}: {
  hasDocuments: boolean;
  onActiveConversationChange: (id: string | null) => void;
  onDocumentsUploaded: () => void;
}) {
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

  // On mount: load the most recent conversation, or create one so there's
  // always an active conversation to attach uploads to.
  useEffect(() => {
    (async () => {
      try {
        const convs = await refreshConversations();
        if (convs.length > 0) {
          setActiveId(convs[0].id);
          setMessages(await getMessages(convs[0].id));
        } else {
          const conv = await createConversation();
          setConversations([conv]);
          setActiveId(conv.id);
        }
      } catch {
        // 401 clears the token in the api layer.
      }
    })();
  }, [refreshConversations]);

  // Keep the parent in sync with which conversation is active (for uploads +
  // the "This chat" documents view).
  useEffect(() => {
    onActiveConversationChange(activeId);
  }, [activeId, onActiveConversationChange]);

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
    if (!text || sending || !hasDocuments) return;
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
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <h2 className="mr-auto text-sm font-medium">Chat</h2>
        {conversations.length > 0 && (
          <select
            value={activeId ?? ""}
            onChange={(e) => selectConversation(e.target.value)}
            className="max-w-[16rem] truncate rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-xs dark:border-zinc-700"
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

      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
            <DocIcon />
            <p className="max-w-xs text-sm text-zinc-500 dark:text-zinc-400">
              {hasDocuments
                ? "Ask a question about your documents to get started."
                : "Upload a document to start chatting."}
            </p>
            <div className="w-64">
              <UploadButton conversationId={activeId} onUploaded={onDocumentsUploaded} />
            </div>
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
            disabled={!hasDocuments}
            placeholder={hasDocuments ? "Ask a question…" : "Upload a document to start chatting"}
            className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700"
          />
          <button
            type="submit"
            disabled={sending || !hasDocuments || input.trim().length === 0}
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
