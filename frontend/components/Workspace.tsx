"use client";

import { useCallback, useEffect, useState } from "react";
import {
  clearToken,
  deleteDocument,
  downloadDocument,
  listDocuments,
  type DocumentInfo,
} from "@/lib/api";
import { ChatPanel } from "@/components/ChatPanel";
import { DocumentsSidebar } from "@/components/DocumentsSidebar";

export function Workspace() {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      // 401 clears the token in the api layer; leave the last list otherwise.
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    reload();
  }, [reload]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteDocument(id);
      reload();
    },
    [reload],
  );

  const handleDownload = useCallback((id: string, filename: string) => {
    downloadDocument(id, filename).catch(() => {});
  }, []);

  function logout() {
    clearToken();
    window.location.reload();
  }

  const hasDocuments = (documents?.length ?? 0) > 0;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight">ask-your-docs</h1>
        <button
          type="button"
          onClick={logout}
          className="text-sm text-zinc-500 underline dark:text-zinc-400"
        >
          Log out
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="min-w-0 flex-1 overflow-hidden">
          <ChatPanel
            hasDocuments={hasDocuments}
            onActiveConversationChange={setActiveConversationId}
            onDocumentsUploaded={reload}
          />
        </main>
        <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-zinc-200 dark:border-zinc-800 sm:block">
          <DocumentsSidebar
            documents={documents}
            activeConversationId={activeConversationId}
            onUploaded={reload}
            onDelete={handleDelete}
            onDownload={handleDownload}
          />
        </aside>
      </div>
    </div>
  );
}
