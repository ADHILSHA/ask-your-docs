"use client";

import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/api";
import { AuthForm } from "@/components/AuthForm";

export function AuthGate({ children }: { children: React.ReactNode }) {
  // null = still checking localStorage (avoids an auth/unauth flash on load).
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    // Read the token only after mount, so the server prerender and the first
    // client render both show `null` (localStorage isn't available during SSR).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAuthed(getToken() !== null);
  }, []);

  if (authed === null) return null;

  if (!authed) {
    return <AuthForm onAuthed={() => setAuthed(true)} />;
  }

  return (
    <>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => {
            clearToken();
            setAuthed(false);
          }}
          className="text-sm text-zinc-500 underline dark:text-zinc-400"
        >
          Log out
        </button>
      </div>
      {children}
    </>
  );
}
