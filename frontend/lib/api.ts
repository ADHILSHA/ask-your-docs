// lib/api.ts
// Thin client for the FastAPI backend. All calls go to NEXT_PUBLIC_API_URL —
// the only public env var. No keys here: the backend owns every LLM call.

export interface Source {
  filename: string;
  chunk_index: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
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

export interface DocumentInfo {
  id: string;
  filename: string;
  char_count: number;
  chunk_count: number;
  created_at: string;
}

function baseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) {
    throw new Error("NEXT_PUBLIC_API_URL is not set");
  }
  return url.replace(/\/$/, "");
}

// --- Auth token (localStorage + Bearer) ---
const TOKEN_KEY = "ayd_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Surface FastAPI's {detail: ...} error body when a request fails, so the UI
// can show something more useful than a bare status code.
async function toData<T>(res: Response): Promise<T> {
  // An expired/invalid token: drop it so the app falls back to the login screen.
  if (res.status === 401) {
    clearToken();
  }
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
    headers: { ...authHeaders() },
    body: form,
  });
  return toData<UploadResponse>(res);
}

// Send the full (client-held) conversation; the backend answers the last user
// message grounded in the uploaded docs. History resolves follow-ups.
export async function chat(messages: Message[]): Promise<ChatResponse> {
  const res = await fetch(`${baseUrl()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ messages }),
  });
  return toData<ChatResponse>(res);
}

// --- Auth endpoints ---
interface TokenResponse {
  access_token: string;
  token_type: string;
}

async function authenticate(path: string, email: string, password: string): Promise<void> {
  const res = await fetch(`${baseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await toData<TokenResponse>(res);
  setToken(data.access_token);
}

export function signup(email: string, password: string): Promise<void> {
  return authenticate("/auth/signup", email, password);
}

export function login(email: string, password: string): Promise<void> {
  return authenticate("/auth/login", email, password);
}

// --- Documents ---
export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${baseUrl()}/documents`, { headers: { ...authHeaders() } });
  return toData<DocumentInfo[]>(res);
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${baseUrl()}/documents/${id}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  // 204 No Content has no JSON body, so don't route it through toData().
  if (res.status === 401) clearToken();
  if (!res.ok && res.status !== 204) {
    throw new Error(`Delete failed (${res.status})`);
  }
}
