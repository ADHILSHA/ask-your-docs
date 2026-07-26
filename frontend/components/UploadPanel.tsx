"use client";

import { useState } from "react";
import { uploadFiles } from "@/lib/api";

export function UploadPanel() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function handleUpload(e: React.SyntheticEvent) {
    e.preventDefault();
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setUploadError(null);
    setUploadMessage(null);
    try {
      const res = await uploadFiles(selectedFiles);
      setUploadMessage(res.message);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-sm font-medium">1. Upload documents</h2>
      <form onSubmit={handleUpload} className="flex flex-col gap-3">
        <input
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
          className="block w-full text-sm text-zinc-600 file:mr-3 file:rounded-md file:border-0 file:bg-zinc-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-zinc-700 dark:text-zinc-300 dark:file:bg-zinc-100 dark:file:text-zinc-900"
        />
        <button
          type="submit"
          disabled={uploading || selectedFiles.length === 0}
          className="self-start rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {uploading
            ? "Uploading…"
            : selectedFiles.length > 0
              ? `Upload ${selectedFiles.length} file(s)`
              : "Upload"}
        </button>
      </form>
      {uploadMessage && (
        <p className="text-sm text-green-600 dark:text-green-400">{uploadMessage}</p>
      )}
      {uploadError && (
        <p className="text-sm text-red-600 dark:text-red-400">{uploadError}</p>
      )}
    </section>
  );
}
