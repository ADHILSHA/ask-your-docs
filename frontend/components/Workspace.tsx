"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addContextDocument,
  clearToken,
  createConversation,
  deleteDocument,
  downloadDocument,
  getContextDocuments,
  listConversations,
  listDocuments,
  removeContextDocument,
  uploadFiles,
  type ConversationInfo,
  type DocumentInfo,
} from "@/lib/api";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { ChatPanel } from "@/components/ChatPanel";
import { DocumentsSidebar } from "@/components/DocumentsSidebar";

export function Workspace() {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [contextDocs, setContextDocs] = useState<DocumentInfo[] | null>(null);

  const refreshConversations = useCallback(async () => {
    const convs = await listConversations();
    setConversations(convs);
    return convs;
  }, []);

  const refreshDocuments = useCallback(async () => {
    setDocuments(await listDocuments());
  }, []);

  const refreshContext = useCallback(async (conversationId: string | null) => {
    if (!conversationId) {
      setContextDocs([]);
      return;
    }
    setContextDocs(await getContextDocuments(conversationId));
  }, []);

  // Bootstrap: load conversations (create one if none), documents, and context.
  useEffect(() => {
    (async () => {
      try {
        let convs = await refreshConversations();
        if (convs.length === 0) {
          const conv = await createConversation();
          convs = [conv];
          setConversations(convs);
        }
        setActiveId(convs[0].id);
        await Promise.all([refreshDocuments(), refreshContext(convs[0].id)]);
      } catch {
        // 401 clears the token in the api layer.
      }
    })();
  }, [refreshConversations, refreshDocuments, refreshContext]);

  async function selectConversation(id: string) {
    setActiveId(id);
    await refreshContext(id);
  }

  async function newChat() {
    const conv = await createConversation();
    setConversations((c) => [conv, ...c]);
    setActiveId(conv.id);
    setContextDocs([]);
  }

  const handleUpload = useCallback(
    async (files: File[]) => {
      await uploadFiles(files, activeId);
      await Promise.all([refreshDocuments(), refreshContext(activeId)]);
    },
    [activeId, refreshDocuments, refreshContext],
  );

  const handleAddToContext = useCallback(
    async (docId: string) => {
      if (!activeId) return;
      await addContextDocument(activeId, docId);
      await refreshContext(activeId);
    },
    [activeId, refreshContext],
  );

  const handleRemoveFromContext = useCallback(
    async (docId: string) => {
      if (!activeId) return;
      await removeContextDocument(activeId, docId);
      await refreshContext(activeId);
    },
    [activeId, refreshContext],
  );

  const handleDelete = useCallback(
    async (docId: string) => {
      await deleteDocument(docId);
      await Promise.all([refreshDocuments(), refreshContext(activeId)]);
    },
    [activeId, refreshDocuments, refreshContext],
  );

  const handleDownload = useCallback((id: string, filename: string) => {
    downloadDocument(id, filename).catch(() => {});
  }, []);

  function logout() {
    clearToken();
    window.location.reload();
  }

  const contextIds = new Set((contextDocs ?? []).map((d) => d.id));
  const hasContextDocs = (contextDocs?.length ?? 0) > 0;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight">Ask Your Docs</h1>
        <button
          type="button"
          onClick={logout}
          className="text-sm text-zinc-500 underline dark:text-zinc-400"
        >
          Log out
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-60 shrink-0 overflow-y-auto border-r border-zinc-200 dark:border-zinc-800 sm:block">
          <ConversationsSidebar
            conversations={conversations}
            activeId={activeId}
            onSelect={selectConversation}
            onNewChat={newChat}
          />
        </aside>

        <main className="min-w-0 flex-1 overflow-hidden">
          <ChatPanel
            conversationId={activeId}
            hasContextDocs={hasContextDocs}
            onConversationChanged={refreshConversations}
          />
        </main>

        <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-zinc-200 dark:border-zinc-800 md:block">
          <DocumentsSidebar
            documents={documents}
            contextIds={contextIds}
            onUpload={handleUpload}
            onAddToContext={handleAddToContext}
            onRemoveFromContext={handleRemoveFromContext}
            onDelete={handleDelete}
            onDownload={handleDownload}
          />
        </aside>
      </div>
    </div>
  );
}
