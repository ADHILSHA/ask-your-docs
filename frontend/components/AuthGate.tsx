"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
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
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <AuthForm onAuthed={() => setAuthed(true)} />
      </div>
    );
  }

  return <>{children}</>;
}
