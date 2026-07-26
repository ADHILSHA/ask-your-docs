import { UploadPanel } from "@/components/UploadPanel";
import { ChatPanel } from "@/components/ChatPanel";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-8 px-6 py-12">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">ask-your-docs</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Upload documents, then chat with them — answers come only from their
          contents, with sources.
        </p>
      </header>

      <UploadPanel />
      <ChatPanel />
    </main>
  );
}
