"use client";

import { useRef, useState } from "react";
import { type DocumentInfo } from "@/lib/api";

function Spinner() {
  return (
    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600 dark:border-zinc-700 dark:border-t-zinc-300" />
  );
}

export function DocumentsSidebar({
  documents,
  contextIds,
  onUpload,
  onAddToContext,
  onRemoveFromContext,
  onDelete,
  onDownload,
}: {
  documents: DocumentInfo[] | null;
  contextIds: Set<string>;
  onUpload: (files: File[]) => Promise<void>;
  onAddToContext: (id: string) => void;
  onRemoveFromContext: (id: string) => void;
  onDelete: (id: string) => void;
  onDownload: (id: string, filename: string) => void;
}) {
  const [mode, setMode] = useState<"list" | "upload">("list");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function doUpload(files: File[]) {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      await onUpload(files);
      setMode("list"); // return to the list on success
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  if (mode === "upload") {
    return (
      <div className="flex h-full flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium">Upload documents</h2>
          <button
            type="button"
            onClick={() => setMode("list")}
            disabled={uploading}
            className="text-xs text-zinc-500 underline disabled:opacity-40 dark:text-zinc-400"
          >
            Cancel
          </button>
        </div>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            doUpload(Array.from(e.dataTransfer.files));
          }}
          onClick={() => !uploading && inputRef.current?.click()}
          className={`flex flex-1 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center ${
            dragOver
              ? "border-zinc-500 bg-zinc-50 dark:bg-zinc-900"
              : "border-zinc-300 dark:border-zinc-700"
          }`}
        >
          {uploading ? (
            <>
              <Spinner />
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Uploading…</p>
            </>
          ) : (
            <>
              <p className="text-sm text-zinc-600 dark:text-zinc-300">Drag &amp; drop files here</p>
              <p className="text-xs text-zinc-400">
                or click to browse — PDF, .txt, .md (max 10 MB)
              </p>
            </>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          className="hidden"
          onChange={(e) => doUpload(Array.from(e.target.files ?? []))}
        />
        {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
      </div>
    );
  }

  // Context documents first, then the rest (sort is stable, preserving order).
  const sorted =
    documents === null
      ? null
      : [...documents].sort(
          (a, b) => (contextIds.has(a.id) ? 0 : 1) - (contextIds.has(b.id) ? 0 : 1),
        );

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-200 p-3 dark:border-zinc-800">
        <button
          type="button"
          onClick={() => {
            setError(null);
            setMode("upload");
          }}
          className="w-full rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          Upload documents
        </button>
      </div>
      <div className="border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <h2 className="text-sm font-medium">Documents</h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Highlighted documents are in this chat&apos;s context.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {sorted === null ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</p>
        ) : sorted.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No documents yet — upload one above.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {sorted.map((d) => {
              const inContext = contextIds.has(d.id);
              return (
                <li
                  key={d.id}
                  className={
                    inContext
                      ? "rounded-md border border-blue-300 bg-blue-50 p-2 dark:border-blue-900 dark:bg-blue-950/40"
                      : "rounded-md border border-zinc-200 p-2 dark:border-zinc-800"
                  }
                >
                  <div className="truncate font-mono text-xs" title={d.filename}>
                    {d.filename}
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs">
                    {inContext ? (
                      <button
                        type="button"
                        onClick={() => onRemoveFromContext(d.id)}
                        className="font-medium text-blue-700 hover:underline dark:text-blue-300"
                      >
                        ✓ In chat
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => onAddToContext(d.id)}
                        className="text-zinc-600 hover:underline dark:text-zinc-300"
                      >
                        + Add to chat
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onDownload(d.id, d.filename)}
                      className="text-zinc-500 hover:underline dark:text-zinc-400"
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(d.id)}
                      className="ml-auto text-red-600 hover:underline dark:text-red-400"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
