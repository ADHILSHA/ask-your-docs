"use client";

import { type DocumentInfo } from "@/lib/api";

export function DocumentsPanel({
  documents,
  onDelete,
}: {
  documents: DocumentInfo[] | null;
  onDelete: (id: string) => void;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-sm font-medium">Your documents</h2>
      {documents === null ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          No documents yet — upload one above.
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
          {documents.map((d) => (
            <li key={d.id} className="flex items-center justify-between gap-3 py-2">
              <span className="truncate font-mono text-xs">
                {d.filename}{" "}
                <span className="text-zinc-400">({d.chunk_count} chunks)</span>
              </span>
              <button
                type="button"
                onClick={() => onDelete(d.id)}
                className="shrink-0 text-xs text-red-600 hover:underline dark:text-red-400"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
