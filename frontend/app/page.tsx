"use client";

import { useState } from "react";
import { ask, uploadFiles, type AskResponse } from "@/lib/api";

export default function Home() {
  // Upload state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Ask state
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [askError, setAskError] = useState<string | null>(null);

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

  async function handleAsk(e: React.SyntheticEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    setAsking(true);
    setAskError(null);
    setResult(null);
    try {
      const res = await ask(trimmed);
      setResult(res);
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setAsking(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-8 px-6 py-12">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">ask-your-docs</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Upload documents, then ask questions answered only from their contents.
        </p>
      </header>

      {/* Upload */}
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

      {/* Ask */}
      <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="text-sm font-medium">2. Ask a question</h2>
        <form onSubmit={handleAsk} className="flex flex-col gap-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="What would you like to know?"
            className="w-full resize-y rounded-md border border-zinc-300 bg-transparent p-3 text-sm outline-none focus:border-zinc-500 dark:border-zinc-700"
          />
          <button
            type="submit"
            disabled={asking || question.trim().length === 0}
            className="self-start rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {asking ? "Asking…" : "Ask"}
          </button>
        </form>
        {askError && (
          <p className="text-sm text-red-600 dark:text-red-400">{askError}</p>
        )}
      </section>

      {/* Answer */}
      {result && (
        <section className="flex flex-col gap-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <div>
            <h2 className="mb-2 text-sm font-medium">Answer</h2>
            <p className="whitespace-pre-wrap text-sm leading-6">{result.answer}</p>
          </div>

          {result.sources.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-medium">Sources</h3>
              <ul className="flex flex-col gap-1">
                {result.sources.map((s, i) => (
                  <li
                    key={`${s.filename}-${s.chunk_index}-${i}`}
                    className="font-mono text-xs text-zinc-600 dark:text-zinc-400"
                  >
                    {s.filename} #{s.chunk_index+1}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
