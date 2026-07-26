"use client";

import { useState } from "react";
import { type DocumentInfo } from "@/lib/api";
import { UploadButton } from "@/components/UploadButton";
import { DocumentsPanel } from "@/components/DocumentsPanel";

type Tab = "chat" | "all";

export function DocumentsSidebar({
  documents,
  activeConversationId,
  onUploaded,
  onDelete,
  onDownload,
}: {
  documents: DocumentInfo[] | null;
  activeConversationId: string | null;
  onUploaded: () => void;
  onDelete: (id: string) => void;
  onDownload: (id: string, filename: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("chat");

  const chatDocs =
    documents === null
      ? null
      : documents.filter((d) => d.conversation_id === activeConversationId);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-200 p-4 dark:border-zinc-800">
        <UploadButton conversationId={activeConversationId} onUploaded={onUploaded} />
      </div>

      <div className="flex border-b border-zinc-200 dark:border-zinc-800">
        <button
          type="button"
          onClick={() => setTab("chat")}
          className={
            tab === "chat"
              ? "flex-1 border-b-2 border-zinc-900 px-3 py-2 text-sm font-medium dark:border-zinc-100"
              : "flex-1 px-3 py-2 text-sm text-zinc-500 dark:text-zinc-400"
          }
        >
          This chat
        </button>
        <button
          type="button"
          onClick={() => setTab("all")}
          className={
            tab === "all"
              ? "flex-1 border-b-2 border-zinc-900 px-3 py-2 text-sm font-medium dark:border-zinc-100"
              : "flex-1 px-3 py-2 text-sm text-zinc-500 dark:text-zinc-400"
          }
        >
          All documents
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === "chat" ? (
          <DocumentsPanel
            documents={chatDocs}
            onDelete={onDelete}
            onDownload={onDownload}
            emptyMessage="No documents in this chat yet — upload one above."
          />
        ) : (
          <DocumentsPanel documents={documents} onDelete={onDelete} onDownload={onDownload} />
        )}
      </div>
    </div>
  );
}
