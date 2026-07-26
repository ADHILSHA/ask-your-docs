// lib/api.ts
// Thin client for the FastAPI backend. All calls go to NEXT_PUBLIC_API_URL —
// the only public env var. No keys here: the backend owns every LLM call.

export interface Source {
  filename: string;
  chunk_index: number;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

export interface UploadedFile {
  filename: string;
  char_count: number;
  chunk_count: number;
}

export interface UploadResponse {
  files: UploadedFile[];
  chunks_indexed: number;
  message: string;
}

function baseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error("NEXT_PUBLIC_API_URL is not set");
  }
  return url.replace(/\/$/, "");
}

// Surface FastAPI's {detail: ...} error body when a request fails, so the UI
// can show something more useful than a bare status code.
async function toData<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // non-JSON error body; keep the status-based message
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  const res = await fetch(`${baseUrl()}/upload`, {
    method: "POST",
    body: form,
  });
  return toData<UploadResponse>(res);
}

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch(`${baseUrl()}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return toData<AskResponse>(res);
}
