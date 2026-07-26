"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, type DocumentInfo } from "@/lib/api";
import { UploadPanel } from "@/components/UploadPanel";
import { DocumentsPanel } from "@/components/DocumentsPanel";
import { ChatPanel } from "@/components/ChatPanel";

export function Workspace() {
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);

  const reload = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch {
      // 401 clears the token in the api layer; other errors leave the last list.
    }
  }, []);

  useEffect(() => {
    // Load the document list once on mount (reload() setStates after an await).
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

  return (
    <>
      <UploadPanel onUploaded={reload} />
      <DocumentsPanel documents={documents} onDelete={handleDelete} />
      <ChatPanel />
    </>
  );
}
