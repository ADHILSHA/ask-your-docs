"use client";

import { type ConversationInfo } from "@/lib/api";

export function ConversationsSidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
}: {
  conversations: ConversationInfo[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          + New chat
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-3">
        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onSelect(c.id)}
            className={
              c.id === activeId
                ? "mb-0.5 block w-full truncate rounded-md bg-zinc-100 px-3 py-2 text-left text-sm dark:bg-zinc-800"
                : "mb-0.5 block w-full truncate rounded-md px-3 py-2 text-left text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }
          >
            {c.title}
          </button>
        ))}
      </nav>
    </div>
  );
}
